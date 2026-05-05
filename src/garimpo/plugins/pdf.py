"""Plugin de recuperação e validação de arquivos PDF."""

from __future__ import annotations

import re

from garimpo.signatures import FileSignature, ValidationResult, ValidationStatus

_PDF_HEADER_RE = re.compile(rb"%PDF-(\d+\.\d+)")
_XREF_RE       = re.compile(rb"\bxref\b")


class PDFPlugin(FileSignature):
    name      = "Documento PDF"
    extension = ".pdf"
    mime_type = "application/pdf"

    headers = [b"%PDF-"]
    footers = [
        b"%%EOF\r\n",
        b"%%EOF\n",
        b"%%EOF\r",
        b"%%EOF",
    ]

    max_size = 500 * 1024 * 1024
    min_size = 67

    @classmethod
    def validate(cls, data: bytes) -> ValidationResult:
        if len(data) < cls.min_size:
            return ValidationResult(ValidationStatus.CORRUPT, 0.0, f"Pequeno demais: {len(data)} bytes")


        match = _PDF_HEADER_RE.match(data[:10])
        if not match:
            return ValidationResult(ValidationStatus.CORRUPT, 0.0, "Cabeçalho PDF (%PDF-x.x) ausente")

        version = match.group(1).decode(errors="replace")


        tail = data[-1024:]
        has_eof = b"%%EOF" in tail


        has_xref   = b"xref" in data
        has_xref_s = b"xref" in data or b"/XRef" in data


        has_obj = b" obj" in data or b"\nobj" in data

        if has_eof and has_xref_s and has_obj:
            return ValidationResult(
                ValidationStatus.VALID, 0.97,
                f"PDF válido {version} com xref e EOF"
            )

        if has_eof and has_obj:
            return ValidationResult(
                ValidationStatus.VALID, 0.85,
                f"PDF {version}: marcador EOF + objetos encontrados"
            )

        if has_obj:
            return ValidationResult(
                ValidationStatus.PARTIAL, 0.55,
                f"PDF {version}: objetos encontrados, EOF ausente (truncado)"
            )

        return ValidationResult(
            ValidationStatus.PARTIAL, 0.30,
            f"PDF {version} apenas cabeçalho – muito truncado"
        )
