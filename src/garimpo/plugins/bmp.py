"""Plugin de recuperação e validação de arquivos BMP."""

from __future__ import annotations

import struct

from garimpo.signatures import FileSignature, ValidationResult, ValidationStatus

_BMP_MAGIC = b"BM"


class BMPPlugin(FileSignature):
    name      = "Imagem BMP"
    extension = ".bmp"
    mime_type = "image/bmp"

    headers  = [_BMP_MAGIC]
    footers  = []

    max_size = 100 * 1024 * 1024
    min_size = 54

    @classmethod
    def validate(cls, data: bytes) -> ValidationResult:
        if len(data) < cls.min_size:
            return ValidationResult(ValidationStatus.CORRUPT, 0.0, f"Pequeno demais: {len(data)} bytes")

        if data[:2] != _BMP_MAGIC:
            return ValidationResult(ValidationStatus.CORRUPT, 0.0, "Assinatura BM ausente")

        try:
            file_size = struct.unpack_from("<I", data, 2)[0]
            px_offset = struct.unpack_from("<I", data, 10)[0]
            dib_size  = struct.unpack_from("<I", data, 14)[0]
        except struct.error:
            return ValidationResult(ValidationStatus.CORRUPT, 0.1, "Não foi possível interpretar o cabeçalho BMP")


        if file_size < cls.min_size or file_size > cls.max_size:
            return ValidationResult(
                ValidationStatus.CORRUPT, 0.2,
                f"Tamanho declarado do arquivo é implausível: {file_size} bytes"
            )


        if px_offset >= file_size:
            return ValidationResult(
                ValidationStatus.CORRUPT, 0.2,
                f"Offset de pixels {px_offset} >= declared size {file_size}"
            )


        valid_dib = {12, 40, 52, 56, 64, 108, 124}
        if dib_size not in valid_dib:
            return ValidationResult(
                ValidationStatus.CORRUPT, 0.3,
                f"Tamanho de cabeçalho DIB desconhecido: {dib_size}"
            )

        actual = len(data)
        if actual >= file_size:
            return ValidationResult(ValidationStatus.VALID, 0.97, f"BMP recuperado integralmente ({file_size} bytes)")

        pct = actual / file_size
        return ValidationResult(
            ValidationStatus.PARTIAL, round(0.5 * pct, 3),
            f"BMP parcial: {actual}/{file_size} bytes ({pct:.0%})"
        )

    @classmethod
    def declared_size(cls, data: bytes) -> int | None:
        """Lê o tamanho declarado no cabeçalho BMP."""
        try:
            return struct.unpack_from("<I", data, 2)[0]
        except struct.error:
            return None
