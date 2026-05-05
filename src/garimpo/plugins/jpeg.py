"""Plugin de recuperação e validação de arquivos JPEG."""

from __future__ import annotations

from garimpo.signatures import FileSignature, ValidationResult, ValidationStatus


class JPEGPlugin(FileSignature):
    name      = "Imagem JPEG"
    extension = ".jpg"
    mime_type = "image/jpeg"


    headers = [
        b"\xff\xd8\xff\xe0",
        b"\xff\xd8\xff\xe1",
        b"\xff\xd8\xff\xe2",
        b"\xff\xd8\xff\xe8",
        b"\xff\xd8\xff\xdb",
        b"\xff\xd8\xff\xfe",
        b"\xff\xd8\xff\xed",
    ]
    footers  = [b"\xff\xd9"]

    max_size = 50 * 1024 * 1024
    min_size = 107

    @classmethod
    def validate(cls, data: bytes) -> ValidationResult:
        if len(data) < cls.min_size:
            return ValidationResult(
                ValidationStatus.CORRUPT, 0.0,
                f"Pequeno demais: {len(data)} bytes"
            )


        if data[:2] != b"\xff\xd8":
            return ValidationResult(ValidationStatus.CORRUPT, 0.0, "Marcador SOI ausente")


        if data[2] != 0xFF:
            return ValidationResult(ValidationStatus.CORRUPT, 0.1, "Terceiro byte inválido (esperado FF)")


        has_eoi = data[-2:] == b"\xff\xd9"


        has_dqt = b"\xff\xdb" in data
        has_sof = any(
            marker in data
            for marker in (b"\xff\xc0", b"\xff\xc2", b"\xff\xc4")
        )

        if has_eoi and (has_dqt or has_sof):
            return ValidationResult(ValidationStatus.VALID, 0.98, "SOI + EOI + marcadores internos presentes")

        if has_eoi:
            return ValidationResult(ValidationStatus.VALID, 0.85, "SOI + EOI presentes")

        if has_dqt or has_sof:
            return ValidationResult(ValidationStatus.PARTIAL, 0.60, "SOI presente, EOI ausente, marcadores internos encontrados")

        return ValidationResult(ValidationStatus.PARTIAL, 0.40, "SOI presente, EOI ausente")
