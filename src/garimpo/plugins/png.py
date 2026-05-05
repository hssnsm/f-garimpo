"""Plugin de recuperação e validação de arquivos PNG."""

from __future__ import annotations

import struct

from garimpo.signatures import FileSignature, ValidationResult, ValidationStatus

_PNG_MAGIC  = b"\x89PNG\r\n\x1a\n"
_IEND_RAW   = b"IEND"
_IEND_CHUNK = b"\x49\x45\x4e\x44\xae\x42\x60\x82"


class PNGPlugin(FileSignature):
    name      = "Imagem PNG"
    extension = ".png"
    mime_type = "image/png"

    headers  = [_PNG_MAGIC]
    footers  = [_IEND_CHUNK]

    max_size = 200 * 1024 * 1024
    min_size = 67

    @classmethod
    def validate(cls, data: bytes) -> ValidationResult:
        if len(data) < cls.min_size:
            return ValidationResult(ValidationStatus.CORRUPT, 0.0, f"Pequeno demais: {len(data)} bytes")


        if data[:8] != _PNG_MAGIC:
            return ValidationResult(ValidationStatus.CORRUPT, 0.0, "Bytes mágicos de PNG ausentes")


        try:
            chunk_len = struct.unpack(">I", data[8:12])[0]
            chunk_type = data[12:16]
            if chunk_type != b"IHDR" or chunk_len != 13:
                return ValidationResult(ValidationStatus.CORRUPT, 0.2, "Primeiro bloco não é IHDR")
        except struct.error:
            return ValidationResult(ValidationStatus.CORRUPT, 0.1, "Não foi possível interpretar o bloco IHDR")


        has_iend = _IEND_CHUNK in data or _IEND_RAW in data


        has_idat = b"IDAT" in data

        if has_iend and has_idat:
            return ValidationResult(ValidationStatus.VALID, 0.97, "Assinatura PNG + IHDR + IDAT + IEND encontrados")

        if has_iend:
            return ValidationResult(ValidationStatus.VALID, 0.80, "Assinatura PNG + IHDR + IEND encontrados (sem IDAT)")

        if has_idat:
            return ValidationResult(ValidationStatus.PARTIAL, 0.55, "Assinatura PNG + IDAT; IEND ausente (truncado)")

        return ValidationResult(ValidationStatus.PARTIAL, 0.30, "Apenas assinatura PNG – fortemente truncado")
