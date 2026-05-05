"""Plugin de recuperação e validação de arquivos GIF."""

from __future__ import annotations

from garimpo.signatures import FileSignature, ValidationResult, ValidationStatus


class GIFPlugin(FileSignature):
    name      = "Imagem GIF"
    extension = ".gif"
    mime_type = "image/gif"

    headers  = [b"GIF87a", b"GIF89a"]
    footers  = [b"\x00\x3b", b"\x3b"]

    max_size = 50 * 1024 * 1024
    min_size = 35

    @classmethod
    def validate(cls, data: bytes) -> ValidationResult:
        if len(data) < cls.min_size:
            return ValidationResult(ValidationStatus.CORRUPT, 0.0, f"Pequeno demais: {len(data)} bytes")

        if not (data.startswith(b"GIF87a") or data.startswith(b"GIF89a")):
            return ValidationResult(ValidationStatus.CORRUPT, 0.0, "Cabeçalho GIF ausente")

        version = data[:6].decode(errors="replace")


        has_trailer = data[-1:] == b"\x3b"
        has_image   = b"\x2c" in data

        if has_trailer and has_image:
            return ValidationResult(ValidationStatus.VALID, 0.96, f"{version}: trailer + descritor de imagem encontrados")
        if has_trailer:
            return ValidationResult(ValidationStatus.VALID, 0.78, f"{version}: trailer encontrado")
        if has_image:
            return ValidationResult(ValidationStatus.PARTIAL, 0.55, f"{version}: descritor de imagem encontrado, trailer ausente")

        return ValidationResult(ValidationStatus.PARTIAL, 0.30, f"{version} apenas cabeçalho – truncado")
