"""Executa a recuperação, grava os arquivos encontrados e monta a sessão."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from garimpo.config import ScanConfig
from garimpo.scanner import Scanner
from garimpo.signatures import CarveResult
from garimpo.validators import DuplicateFilter, apply_filters
from garimpo.utils import ensure_dir, unique_output_path, human_size

log = logging.getLogger("garimpo.recovery")


@dataclass
class RecoverySession:
    """Resumo de uma execução."""

    image_path: Path
    output_dir: Path
    total_scanned: int = 0
    total_carved: int = 0
    total_skipped: int = 0
    total_duplicates: int = 0
    total_bytes_recovered: int = 0
    results: list[CarveResult] = field(default_factory=list)


    by_type: dict[str, int] = field(default_factory=dict)

    def summary(self) -> str:
        lines = [
            f"Imagem     : {self.image_path}",
            f"Saída      : {self.output_dir}",
            f"Recuperados: {self.total_carved} arquivo(s)",
            f"Ignorados  : {self.total_skipped} (baixa confiança / corrompido)",
            f"Duplicados : {self.total_duplicates}",
            f"Dados      : {human_size(self.total_bytes_recovered)}",
        ]
        if self.by_type:
            lines.append("Por tipo   :")
            for ftype, count in sorted(self.by_type.items()):
                lines.append(f"  {ftype:<40} {count}")
        return "\n".join(lines)


class RecoveryEngine:
    """Coordena varredura, filtros e gravação."""

    def __init__(self, config: ScanConfig) -> None:
        self.config = config

    def run(self) -> RecoverySession:
        """Executa a recuperação completa."""
        cfg = self.config
        cfg.validate_paths()

        session = RecoverySession(
            image_path=cfg.image_path,
            output_dir=cfg.output_dir,
        )
        cfg.notify_progress(
            stage="preparing",
            scanned_bytes=0,
            total_bytes=cfg.image_path.stat().st_size,
            recovered_count=0,
            skipped_count=0,
            duplicate_count=0,
            message="Preparando recuperação...",
        )

        dup_filter = DuplicateFilter()
        scanner = Scanner(cfg)


        type_indices: dict[str, int] = {}

        try:
            for result in scanner.scan(cfg.image_path):
                session.total_carved += 1


                keep = apply_filters(
                    result,
                    dup_filter,
                    min_confidence=0.0,
                    skip_duplicates=cfg.skip_duplicates,
                )

                if not keep:
                    session.total_skipped += 1
                    if result.is_duplicate:
                        session.total_duplicates += 1
                    cfg.notify_progress(
                        stage="filtered",
                        recovered_count=len(session.results),
                        skipped_count=session.total_skipped,
                        duplicate_count=session.total_duplicates,
                        latest_result=result.as_dict(),
                    )
                    continue


                output_path = self._write_candidate(result, type_indices)
                if output_path is None:
                    session.total_skipped += 1
                    continue

                result.output_path = output_path


                session.results.append(result)
                session.total_bytes_recovered += result.size
                session.by_type[result.file_type] = session.by_type.get(result.file_type, 0) + 1
                cfg.notify_progress(
                    stage="recovered",
                    recovered_count=len(session.results),
                    skipped_count=session.total_skipped,
                    duplicate_count=session.total_duplicates,
                    bytes_recovered=session.total_bytes_recovered,
                    latest_result=result.as_dict(),
                )

                if (
                    cfg.max_carved_files > 0
                    and len(session.results) >= cfg.max_carved_files
                ):
                    log.info("max_carved_files=%d reached.", cfg.max_carved_files)
                    break

        except KeyboardInterrupt:
            log.warning("Varredura interrompida pelo usuário.")

        log.info("\n%s", session.summary())
        return session



    def _write_candidate(
        self,
        result: CarveResult,
        type_indices: dict[str, int],
    ) -> Path | None:
        """Grava um candidato no diretório do tipo."""
        try:

            type_dir = self.config.output_dir / _sanitise_dirname(result.file_type)
            ensure_dir(type_dir)


            idx = type_indices.get(result.file_type, 0)
            type_indices[result.file_type] = idx + 1


            stem = "carved"
            out_path = unique_output_path(type_dir, stem, result.extension, idx)


            self._stream_to_file(result, out_path)
            return out_path

        except OSError as exc:
            log.error("Falha ao gravar arquivo recuperado de %s em 0x%X: %s",
                      result.file_type, result.offset_start, exc)
            return None

    def _stream_to_file(self, result: CarveResult, dest: Path) -> None:
        """Copia bytes da imagem para o destino."""
        chunk_size = self.config.chunk_size
        remaining = result.size

        with (
            open(self.config.image_path, "rb") as src,
            open(dest, "wb") as dst,
        ):
            src.seek(result.offset_start)
            while remaining > 0:
                to_read = min(chunk_size, remaining)
                chunk = src.read(to_read)
                if not chunk:
                    break
                dst.write(chunk)
                remaining -= len(chunk)

        log.debug("Gravado %s → %s", human_size(result.size), dest.name)




def _sanitise_dirname(name: str) -> str:
    """Normaliza o nome do diretório de saída."""

    import re
    safe = re.sub(r"[^\w\-]", "_", name)
    return safe.strip("_").lower() or "unknown"
