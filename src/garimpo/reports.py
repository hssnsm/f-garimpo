"""Gera relatórios JSON e CSV das recuperações."""

from __future__ import annotations

import csv
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from garimpo import __version__
from garimpo.recovery import RecoverySession
from garimpo.utils import human_size, ensure_dir

log = logging.getLogger("garimpo.reports")

_TIMESTAMP_FMT = "%Y-%m-%dT%H:%M:%SZ"


_CSV_FIELDS = [
    "index",
    "file_type",
    "extension",
    "offset_start",
    "offset_end",
    "size",
    "has_footer",
    "status",
    "validation_status",
    "validation_confidence",
    "validation_notes",
    "md5",
    "sha1",
    "sha256",
    "output_path",
    "is_duplicate",
]


def _now_utc() -> str:
    return datetime.now(tz=timezone.utc).strftime(_TIMESTAMP_FMT)


def write_reports(session: RecoverySession, fmt: str = "all") -> list[Path]:
    """Grava os relatórios solicitados."""
    ensure_dir(session.output_dir / "reports")
    created: list[Path] = []
    fmt = fmt.lower().strip()

    if fmt in ("json", "all"):
        p = _write_json(session)
        created.append(p)
        log.info("Relatório JSON: %s", p)

    if fmt in ("csv", "all"):
        p = _write_csv(session)
        created.append(p)
        log.info("Relatório CSV: %s", p)

    return created


def _write_json(session: RecoverySession) -> Path:
    report_path = session.output_dir / "reports" / "report.json"

    payload = {
        "garimpo_version": __version__,
        "generated_at": _now_utc(),
        "image": str(session.image_path),
        "output_dir": str(session.output_dir),
        "summary": {
            "total_carved": session.total_carved,
            "total_recovered": len(session.results),
            "total_skipped": session.total_skipped,
            "total_duplicates": session.total_duplicates,
            "total_bytes_recovered": session.total_bytes_recovered,
            "human_bytes_recovered": human_size(session.total_bytes_recovered),
            "by_type": session.by_type,
        },
        "evidence": [r.as_dict() for r in session.results],
    }

    report_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return report_path


def _write_csv(session: RecoverySession) -> Path:
    report_path = session.output_dir / "reports" / "report.csv"

    with open(report_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for r in session.results:
            writer.writerow(r.as_dict())

    return report_path
