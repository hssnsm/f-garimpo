"""Aplica filtros de validação e deduplicação aos candidatos."""

from __future__ import annotations

import logging

from garimpo.signatures import CarveResult, ValidationStatus

log = logging.getLogger("garimpo.validators")


class DuplicateFilter:
    """Guarda hashes já emitidos."""

    def __init__(self) -> None:
        self._seen: set[str] = set()

    def is_duplicate(self, result: CarveResult) -> bool:
        """Registra o hash e indica duplicidade."""
        digest = result.sha256
        if not digest:
            return False
        if digest in self._seen:
            return True
        self._seen.add(digest)
        return False

    @property
    def unique_count(self) -> int:
        return len(self._seen)


def apply_filters(
    result: CarveResult,
    dup_filter: DuplicateFilter,
    min_confidence: float = 0.0,
    skip_duplicates: bool = True,
) -> bool:
    """Decide se o candidato deve ser mantido."""

    if result.validation.confidence < min_confidence:
        log.debug(
            "Descartando %s em 0x%X – confiança %.2f < limite %.2f",
            result.file_type, result.offset_start,
            result.validation.confidence, min_confidence,
        )
        return False


    if skip_duplicates and dup_filter.is_duplicate(result):
        log.debug(
            "Descartando %s duplicado em 0x%X (sha256=%s…)",
            result.file_type, result.offset_start, result.sha256[:12],
        )
        result.is_duplicate = True
        return False

    return True
