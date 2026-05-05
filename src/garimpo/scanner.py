"""Percorre imagens brutas e emite candidatos encontrados por assinatura."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterator

from tqdm import tqdm

from garimpo.config import ScanConfig
from garimpo.hashing import hash_bytes, EMPTY_HASHES
from garimpo.plugins import get_plugins
from garimpo.signatures import CarveResult, FileSignature, ValidationResult, ValidationStatus
from garimpo.utils import human_size

log = logging.getLogger("garimpo.scanner")



_FOOTER_LOOKBACK = 256


class Scanner:
    """Scanner de assinaturas por blocos."""

    def __init__(self, config: ScanConfig) -> None:
        self.config = config
        self.plugins: list[type[FileSignature]] = get_plugins(config.enabled_formats)



        self._max_hdr_len: int = max(
            (p.max_header_len() for p in self.plugins if p.headers),
            default=16,
        )


        self._max_ftr_len: int = max(
            (p.max_footer_len() for p in self.plugins if p.footers),
            default=8,
        )

        log.debug(
            "Scanner inicializado com %d plugin(s), max_hdr=%d, max_ftr=%d",
            len(self.plugins), self._max_hdr_len, self._max_ftr_len,
        )



    def scan(self, image_path: Path) -> Iterator[CarveResult]:
        """Varre a imagem e retorna candidatos."""
        image_path = Path(image_path)
        file_size = image_path.stat().st_size

        log.info("Iniciando varredura de %s (%s)", image_path.name, human_size(file_size))
        log.info("Modo: %s | Bloco: %s | Plugins: %s",
                 self.config.mode,
                 human_size(self.config.chunk_size),
                 ", ".join(p.name for p in self.plugins))
        self.config.notify_progress(
            stage="starting",
            scanned_bytes=0,
            total_bytes=file_size,
            found_count=0,
            message=f"Iniciando varredura de {image_path.name}",
        )

        seen_offsets: set[int] = set()
        carve_index: int = 0
        total_found: int = 0




        with (
            open(image_path, "rb") as seq_f,
            open(image_path, "rb") as rand_f,
        ):
            overlap: bytes = b""
            global_offset: int = 0

            bar = tqdm(
                total=file_size,
                unit="B",
                unit_scale=True,
                unit_divisor=1024,
                desc="Varrendo",
                leave=True,
                dynamic_ncols=True,
            )

            try:
                while global_offset < file_size:
                    to_read = min(self.config.chunk_size, file_size - global_offset)
                    chunk = seq_f.read(to_read)
                    if not chunk:
                        break


                    window = overlap + chunk
                    window_start = global_offset - len(overlap)


                    for plugin in self.plugins:
                        for header in plugin.headers:
                            search_pos = 0
                            while True:
                                hit = window.find(header, search_pos)
                                if hit == -1:
                                    break

                                abs_offset = window_start + hit


                                if abs_offset in seen_offsets:
                                    search_pos = hit + 1
                                    continue
                                seen_offsets.add(abs_offset)


                                candidate_bytes = self._extract_candidate(
                                    rand_f, abs_offset, plugin, file_size
                                )

                                if candidate_bytes is None or len(candidate_bytes) < plugin.min_size:
                                    log.debug(
                                        "Ignorando achado %s em 0x%X – pequeno demais",
                                        plugin.name, abs_offset
                                    )
                                    search_pos = hit + 1
                                    continue


                                try:
                                    candidate_bytes = plugin.refine(candidate_bytes)
                                except Exception as exc:
                                    log.debug("Plugin.refine() gerou erro: %s", exc)


                                if self.config.validate:
                                    try:
                                        validation = plugin.validate(candidate_bytes)
                                    except Exception as exc:
                                        log.warning(
                                            "Erro de validação em %s em 0x%X: %s",
                                            plugin.name, abs_offset, exc
                                        )
                                        validation = ValidationResult(
                                            ValidationStatus.UNKNOWN, 0.0, str(exc)
                                        )
                                else:
                                    validation = ValidationResult(
                                        ValidationStatus.UNKNOWN, 1.0, "validação ignorada"
                                    )


                                if (
                                    validation.status == ValidationStatus.CORRUPT
                                    and not self.config.is_deep_mode
                                ):
                                    log.debug(
                                        "Ignorando %s corrompido em 0x%X (%s)",
                                        plugin.name, abs_offset, validation.notes
                                    )
                                    search_pos = hit + 1
                                    continue


                                if self.config.compute_hashes:
                                    try:
                                        hashes = hash_bytes(candidate_bytes)
                                    except Exception:
                                        hashes = EMPTY_HASHES
                                else:
                                    hashes = EMPTY_HASHES


                                has_footer = self._data_has_footer(candidate_bytes, plugin)
                                result = CarveResult(
                                    offset_start=abs_offset,
                                    offset_end=abs_offset + len(candidate_bytes),
                                    file_type=plugin.name,
                                    extension=plugin.extension,
                                    size=len(candidate_bytes),
                                    index=carve_index,
                                    validation=validation,
                                    md5=hashes.md5,
                                    sha1=hashes.sha1,
                                    sha256=hashes.sha256,
                                    has_footer=has_footer,
                                )

                                carve_index += 1
                                total_found += 1
                                log.info(
                                    "Encontrado %-35s em 0x%010X  tamanho=%-12s  status=%s",
                                    plugin.name,
                                    abs_offset,
                                    human_size(len(candidate_bytes)),
                                    result.status_label,
                                )
                                self.config.notify_progress(
                                    stage="candidate_found",
                                    scanned_bytes=min(global_offset + to_read, file_size),
                                    total_bytes=file_size,
                                    found_count=total_found,
                                    latest_result=result.as_dict(),
                                    message=f"Arquivo encontrado: {plugin.name}",
                                )
                                yield result


                                if (
                                    self.config.max_carved_files > 0
                                    and total_found >= self.config.max_carved_files
                                ):
                                    log.info("Limite max_carved_files=%d atingido; parando.", total_found)
                                    return

                                search_pos = hit + 1


                    overlap = window[-self._max_hdr_len:] if len(window) >= self._max_hdr_len else window
                    global_offset += to_read
                    bar.update(to_read)
                    self.config.notify_progress(
                        stage="scanning",
                        scanned_bytes=global_offset,
                        total_bytes=file_size,
                        found_count=total_found,
                        progress=(global_offset / file_size) if file_size else 1.0,
                    )

            finally:
                bar.close()

        self.config.notify_progress(
            stage="scan_complete",
            scanned_bytes=file_size,
            total_bytes=file_size,
            found_count=total_found,
            progress=1.0,
        )
        log.info("Scan complete. %d arquivo(s) carved.", total_found)



    def _extract_candidate(
        self,
        rand_f,
        offset: int,
        plugin: type[FileSignature],
        image_size: int,
    ) -> bytes | None:
        """Extrai bytes a partir de um offset."""
        try:
            rand_f.seek(offset)
        except OSError as exc:
            log.error("Falha ao posicionar leitura em 0x%X: %s", offset, exc)
            return None

        effective_max = min(plugin.max_size, self.config.max_file_size, image_size - offset)

        if not plugin.footers:



            initial = rand_f.read(min(128, effective_max))
            if not initial:
                return None


            declared: int | None = None
            try:
                if hasattr(plugin, "declared_size"):
                    declared = plugin.declared_size(initial)
            except Exception:
                pass

            if declared and 0 < declared <= effective_max:
                remainder = rand_f.read(declared - len(initial))
                return initial + remainder


            remainder = rand_f.read(effective_max - len(initial))
            return initial + remainder


        data = b""
        read_so_far = 0
        found_footer = False
        read_chunk = self.config.chunk_size

        while read_so_far < effective_max and not found_footer:
            to_read = min(read_chunk, effective_max - read_so_far)
            try:
                chunk = rand_f.read(to_read)
            except OSError as exc:
                log.warning("Erro de leitura durante extração em 0x%X+%d: %s", offset, read_so_far, exc)
                break

            if not chunk:
                break

            prev_len = len(data)
            data += chunk
            read_so_far += len(chunk)



            search_start = max(0, prev_len - self._max_ftr_len - _FOOTER_LOOKBACK)

            for footer in plugin.footers:
                fp = data.find(footer, search_start)
                if fp != -1:
                    end = fp + len(footer)
                    data = data[:end]
                    found_footer = True
                    break

        return data if data else None

    @staticmethod
    def _data_has_footer(data: bytes, plugin: type[FileSignature]) -> bool:
        """Confere se há rodapé conhecido no bloco."""
        if not plugin.footers:
            return True
        return any(f in data for f in plugin.footers)
