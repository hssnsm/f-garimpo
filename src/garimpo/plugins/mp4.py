"""Plugin de recuperação e validação básica de arquivos MP4."""

from __future__ import annotations

import struct

from garimpo.signatures import FileSignature, ValidationResult, ValidationStatus


_FTYP_BRANDS: frozenset[bytes] = frozenset({
    b"isom", b"iso2", b"mp41", b"mp42",
    b"M4V ", b"M4A ", b"M4P ", b"M4B ",
    b"avc1", b"qt  ",
    b"f4v ", b"f4p ",
    b"mmp4", b"3gp4", b"3gp5", b"3gp6",
    b"MSNV",
})


def _has_ftyp_at_start(data: bytes) -> bool:
    """Confere se a caixa ftyp aparece no início."""
    for offset in range(0, min(12, len(data) - 7)):
        if data[offset + 4: offset + 8] == b"ftyp":
            return True
    return False


class MP4Plugin(FileSignature):
    name      = "Vídeo MP4 / MOV"
    extension = ".mp4"
    mime_type = "video/mp4"


    headers = [
        b"\x00\x00\x00\x08ftyp",
        b"\x00\x00\x00\x0cftyp",
        b"\x00\x00\x00\x10ftyp",
        b"\x00\x00\x00\x14ftyp",
        b"\x00\x00\x00\x18ftyp",
        b"\x00\x00\x00\x1cftyp",
        b"\x00\x00\x00\x20ftyp",
    ]
    footers  = []

    max_size = 2 * 1024 * 1024 * 1024
    min_size = 32

    @classmethod
    def validate(cls, data: bytes) -> ValidationResult:
        if len(data) < cls.min_size:
            return ValidationResult(ValidationStatus.CORRUPT, 0.0, f"Pequeno demais: {len(data)} bytes")

        if not _has_ftyp_at_start(data):
            return ValidationResult(ValidationStatus.CORRUPT, 0.0, "Caixa ftyp não encontrada no início")


        ftyp_start = 0
        for offset in range(0, min(12, len(data) - 11)):
            if data[offset + 4: offset + 8] == b"ftyp":
                ftyp_start = offset
                break

        brand = data[ftyp_start + 8: ftyp_start + 12]
        brand_known = brand in _FTYP_BRANDS


        has_moov = b"moov" in data
        has_mdat = b"mdat" in data

        if brand_known and has_moov and has_mdat:
            return ValidationResult(
                ValidationStatus.VALID, 0.95,
                f"MP4 ftyp={brand.decode(errors='replace')!r}, moov+mdat encontrados"
            )

        if has_moov and has_mdat:
            return ValidationResult(
                ValidationStatus.VALID, 0.80,
                f"ftyp={brand.decode(errors='replace')!r}, moov+mdat encontrados (marca não reconhecida)"
            )

        if has_mdat:
            return ValidationResult(
                ValidationStatus.PARTIAL, 0.50,
                "ftyp + mdat encontrados; moov ausente (pode exigir reparo)"
            )

        return ValidationResult(
            ValidationStatus.PARTIAL, 0.30,
            f"Apenas caixa ftyp – arquivo provavelmente truncado (brand={brand.decode(errors='replace')!r})"
        )
