from __future__ import annotations

import json
import logging
import shutil
import threading
import uuid
import zipfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import Flask, abort, jsonify, redirect, render_template, request, send_file, url_for
from werkzeug.utils import secure_filename

from garimpo.config import ScanConfig
from garimpo.plugins import list_plugin_info
from garimpo.recovery import RecoveryEngine
from garimpo.reports import write_reports
from garimpo.logging_config import setup_logging
from garimpo.utils import ensure_dir, human_size, parse_size

log = logging.getLogger("garimpo.webapp")

_ALLOWED_UPLOAD_EXTENSIONS = {".img", ".dd", ".raw", ".iso", ".bin"}


@dataclass
class WebSession:
    id: str
    title: str
    image_name: str
    image_path: Path
    output_dir: Path
    mode: str
    report_format: str
    enabled_formats: list[str]
    chunk_size: int
    max_size: int
    validate: bool
    compute_hashes: bool
    skip_duplicates: bool
    max_files: int
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "queued"
    stage: str = "queued"
    message: str = "Aguardando início"
    progress: float = 0.0
    scanned_bytes: int = 0
    total_bytes: int = 0
    found_count: int = 0
    recovered_count: int = 0
    skipped_count: int = 0
    duplicate_count: int = 0
    bytes_recovered: int = 0
    latest_result: dict[str, Any] | None = None
    summary_text: str = ""
    error: str | None = None
    report_paths: list[Path] = field(default_factory=list)
    bundle_path: Path | None = None
    results: list[dict[str, Any]] = field(default_factory=list)

    def apply_progress(self, payload: dict[str, Any]) -> None:
        self.stage = payload.get("stage", self.stage)
        self.message = payload.get("message", self.message)
        self.progress = float(payload.get("progress", self.progress or 0.0))
        self.scanned_bytes = int(payload.get("scanned_bytes", self.scanned_bytes or 0))
        self.total_bytes = int(payload.get("total_bytes", self.total_bytes or 0))
        self.found_count = int(payload.get("found_count", self.found_count or 0))
        self.recovered_count = int(payload.get("recovered_count", self.recovered_count or 0))
        self.skipped_count = int(payload.get("skipped_count", self.skipped_count or 0))
        self.duplicate_count = int(payload.get("duplicate_count", self.duplicate_count or 0))
        self.bytes_recovered = int(payload.get("bytes_recovered", self.bytes_recovered or 0))
        latest = payload.get("latest_result")
        if latest:
            self.latest_result = latest
        summary = payload.get("summary")
        if summary:
            self.summary_text = summary
        if self.total_bytes and self.scanned_bytes:
            self.progress = max(self.progress, min(self.scanned_bytes / self.total_bytes, 1.0))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "image_name": self.image_name,
            "image_path": str(self.image_path),
            "output_dir": str(self.output_dir),
            "mode": self.mode,
            "report_format": self.report_format,
            "enabled_formats": self.enabled_formats,
            "chunk_size": self.chunk_size,
            "chunk_size_human": human_size(self.chunk_size),
            "max_size": self.max_size,
            "max_size_human": human_size(self.max_size),
            "validate": self.validate,
            "compute_hashes": self.compute_hashes,
            "skip_duplicates": self.skip_duplicates,
            "max_files": self.max_files,
            "created_at": self.created_at.isoformat(),
            "status": self.status,
            "stage": self.stage,
            "message": self.message,
            "progress": round(self.progress * 100, 2),
            "scanned_bytes": self.scanned_bytes,
            "scanned_bytes_human": human_size(self.scanned_bytes),
            "total_bytes": self.total_bytes,
            "total_bytes_human": human_size(self.total_bytes),
            "found_count": self.found_count,
            "recovered_count": self.recovered_count,
            "skipped_count": self.skipped_count,
            "duplicate_count": self.duplicate_count,
            "bytes_recovered": self.bytes_recovered,
            "bytes_recovered_human": human_size(self.bytes_recovered),
            "latest_result": self.latest_result,
            "summary_text": self.summary_text,
            "error": self.error,
            "report_files": [
                {
                    "name": p.name,
                    "download_url": f"/download/{self.id}/report/{p.name}",
                }
                for p in self.report_paths
            ],
            "bundle_url": f"/download/{self.id}/bundle" if self.status == "completed" else None,
            "results": self.results,
        }


class SessionStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._items: dict[str, WebSession] = {}

    def add(self, session: WebSession) -> None:
        with self._lock:
            self._items[session.id] = session

    def get(self, session_id: str) -> WebSession | None:
        with self._lock:
            return self._items.get(session_id)

    def update(self, session_id: str, **changes: Any) -> WebSession:
        with self._lock:
            session = self._items[session_id]
            for key, value in changes.items():
                setattr(session, key, value)
            return session

    def apply_progress(self, session_id: str, payload: dict[str, Any]) -> WebSession:
        with self._lock:
            session = self._items[session_id]
            session.apply_progress(payload)
            return session

    def latest(self, limit: int = 8) -> list[WebSession]:
        with self._lock:
            return sorted(self._items.values(), key=lambda item: item.created_at, reverse=True)[:limit]


def create_app(base_dir: str | Path | None = None) -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024 * 1024

    data_dir = Path(base_dir or "garimpo_web_data").resolve()
    uploads_dir = ensure_dir(data_dir / "uploads")
    sessions_dir = ensure_dir(data_dir / "sessions")

    store = SessionStore()
    app.config["GARIMPO_WEB_DATA_DIR"] = data_dir
    app.config["GARIMPO_WEB_UPLOADS_DIR"] = uploads_dir
    app.config["GARIMPO_WEB_SESSIONS_DIR"] = sessions_dir
    app.config["GARIMPO_WEB_STORE"] = store

    @app.context_processor
    def inject_globals() -> dict[str, Any]:
        return {
            "now": datetime.now(timezone.utc),
            "recent_sessions": store.latest(),
        }

    @app.get("/")
    def dashboard():
        return render_template(
            "index.html",
            plugins=list_plugin_info(),
            total_formats=len(list_plugin_info()),
            recent_sessions=store.latest(),
        )

    @app.post("/api/sessions")
    def create_session():
        uploaded = request.files.get("image")
        if uploaded is None or not uploaded.filename:
            return jsonify({"error": "Selecione uma imagem de disco para continuar."}), 400

        filename = secure_filename(uploaded.filename)
        suffix = Path(filename).suffix.lower()
        if suffix not in _ALLOWED_UPLOAD_EXTENSIONS:
            return jsonify({
                "error": "Formato de upload não suportado. Envie arquivos .img, .dd, .raw, .iso ou .bin.",
            }), 400

        enabled_formats = sorted(set(request.form.getlist("formats")))
        title = (request.form.get("title") or "Nova análise").strip() or "Nova análise"
        mode = (request.form.get("mode") or "fast").strip().lower()
        report_format = (request.form.get("report_format") or "all").strip().lower()
        chunk_size = parse_size(request.form.get("chunk_size") or "64KB")
        max_size = parse_size(request.form.get("max_size") or "100MB")
        max_files = int(request.form.get("max_files") or 0)
        validate = request.form.get("validate") == "on"
        compute_hashes = request.form.get("compute_hashes") == "on"
        skip_duplicates = request.form.get("skip_duplicates") == "on"

        session_id = uuid.uuid4().hex[:12]
        session_root = ensure_dir(sessions_dir / session_id)
        upload_dir = ensure_dir(session_root / "input")
        output_dir = ensure_dir(session_root / "output")
        image_path = upload_dir / filename
        uploaded.save(image_path)

        session = WebSession(
            id=session_id,
            title=title,
            image_name=filename,
            image_path=image_path,
            output_dir=output_dir,
            mode=mode,
            report_format=report_format,
            enabled_formats=enabled_formats,
            chunk_size=chunk_size,
            max_size=max_size,
            validate=validate,
            compute_hashes=compute_hashes,
            skip_duplicates=skip_duplicates,
            max_files=max_files,
            status="queued",
            stage="queued",
            message="Análise agendada.",
            total_bytes=image_path.stat().st_size,
        )
        store.add(session)

        thread = threading.Thread(
            target=_run_scan_session,
            args=(app, store, session_id),
            name=f"garimpo-web-{session_id}",
            daemon=True,
        )
        thread.start()

        return jsonify({
            "id": session_id,
            "detail_url": url_for("session_detail", session_id=session_id),
            "api_url": url_for("session_api", session_id=session_id),
        }), 201

    @app.get("/sessao/<session_id>")
    def session_detail(session_id: str):
        session = store.get(session_id)
        if session is None:
            abort(404)
        return render_template("session.html", session=session)

    @app.get("/api/sessions/<session_id>")
    def session_api(session_id: str):
        session = store.get(session_id)
        if session is None:
            return jsonify({"error": "Sessão não encontrada."}), 404
        return jsonify(session.to_dict())

    @app.get("/download/<session_id>/bundle")
    def download_bundle(session_id: str):
        session = store.get(session_id)
        if session is None:
            abort(404)
        if session.status != "completed":
            abort(409)
        bundle_path = _ensure_bundle(session)
        return send_file(bundle_path, as_attachment=True, download_name=bundle_path.name)

    @app.get("/download/<session_id>/report/<filename>")
    def download_report(session_id: str, filename: str):
        session = store.get(session_id)
        if session is None:
            abort(404)
        target = _resolve_safe_path(session.output_dir / "reports", filename)
        return send_file(target, as_attachment=True, download_name=target.name)

    @app.get("/download/<session_id>/file/<path:relative_path>")
    def download_recovered_file(session_id: str, relative_path: str):
        session = store.get(session_id)
        if session is None:
            abort(404)
        target = _resolve_safe_path(session.output_dir, relative_path)
        return send_file(target, as_attachment=True, download_name=target.name)

    return app


def _run_scan_session(app: Flask, store: SessionStore, session_id: str) -> None:
    session = store.get(session_id)
    if session is None:
        return

    def progress_callback(payload: dict[str, Any]) -> None:
        store.apply_progress(session_id, payload)

    try:
        store.update(session_id, status="running", stage="initializing", message="Inicializando ambiente...")
        cfg = ScanConfig(
            image_path=session.image_path,
            output_dir=session.output_dir,
            chunk_size=session.chunk_size,
            max_file_size=session.max_size,
            mode=session.mode,
            enabled_formats=session.enabled_formats,
            validate=session.validate,
            compute_hashes=session.compute_hashes,
            skip_duplicates=session.skip_duplicates,
            max_carved_files=session.max_files,
            report_format=session.report_format,
            log_level="INFO",
            verbose=False,
            progress_callback=progress_callback,
        )
        setup_logging(level="INFO", log_file=cfg.log_path, verbose=False)
        engine = RecoveryEngine(cfg)
        run_session = engine.run()
        report_paths = write_reports(run_session, fmt=session.report_format) if session.report_format != "none" else []

        results = []
        for result in run_session.results:
            relative_path = result.output_path.relative_to(session.output_dir).as_posix()
            results.append({
                **result.as_dict(),
                "size_human": human_size(result.size),
                "offset_start_hex": hex(result.offset_start),
                "offset_end_hex": hex(result.offset_end),
                "download_url": f"/download/{session_id}/file/{relative_path}",
                "relative_path": relative_path,
            })

        store.update(
            session_id,
            status="completed",
            stage="completed",
            message="Análise concluída com sucesso.",
            progress=1.0,
            report_paths=report_paths,
            results=results,
            recovered_count=len(run_session.results),
            skipped_count=run_session.total_skipped,
            duplicate_count=run_session.total_duplicates,
            bytes_recovered=run_session.total_bytes_recovered,
            summary_text=run_session.summary(),
        )
    except Exception as exc:
        log.exception("Falha durante a análise web %s", session_id)
        store.update(
            session_id,
            status="error",
            stage="error",
            message="A análise falhou.",
            error=str(exc),
        )


def _ensure_bundle(session: WebSession) -> Path:
    if session.bundle_path and session.bundle_path.exists():
        return session.bundle_path

    bundle_path = session.output_dir.parent / f"garimpo_resultados_{session.id}.zip"
    with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(session.output_dir.rglob("*")):
            if path.is_file():
                archive.write(path, arcname=path.relative_to(session.output_dir.parent))
    session.bundle_path = bundle_path
    return bundle_path


def _resolve_safe_path(root: Path, relative: str) -> Path:
    target = (root / relative).resolve()
    root = root.resolve()
    if root not in target.parents and target != root:
        abort(404)
    if not target.exists() or not target.is_file():
        abort(404)
    return target


if __name__ == "__main__":
    app = create_app()
    app.run(host="127.0.0.1", port=5000, debug=True)
