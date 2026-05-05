"""Plugins para ZIP e formatos Office baseados em ZIP."""

from __future__ import annotations

from garimpo.signatures import FileSignature, ValidationResult, ValidationStatus

_LFH    = b"PK\x03\x04"
_EOCD   = b"PK\x05\x06"


def _detect_office_subtype(data: bytes) -> tuple[str, str, str]:
    """Identifica subtipos Office dentro do ZIP."""
    if b"word/document.xml" in data or b"word/document.xml" in data[:4096]:
        return "Documento Word (DOCX)", ".docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if b"xl/workbook.xml" in data or b"xl/workbook.xml" in data[:4096]:
        return "Planilha Excel (XLSX)", ".xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    if b"ppt/presentation.xml" in data or b"ppt/presentation.xml" in data[:4096]:
        return "Apresentação PowerPoint (PPTX)", ".pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation"

    return "Arquivo ZIP", ".zip", "application/zip"


class ZIPPlugin(FileSignature):
    name      = "Arquivo ZIP / Office"
    extension = ".zip"
    mime_type = "application/zip"

    headers  = [_LFH]
    footers  = [_EOCD]

    max_size = 500 * 1024 * 1024
    min_size = 22

    @classmethod
    def validate(cls, data: bytes) -> ValidationResult:
        if len(data) < cls.min_size:
            return ValidationResult(ValidationStatus.CORRUPT, 0.0, f"Pequeno demais: {len(data)} bytes")


        if not data.startswith(_LFH):
            return ValidationResult(ValidationStatus.CORRUPT, 0.0, "Assinatura LFH de ZIP ausente")


        search_area = data[-(65535 + 22):]
        has_eocd = _EOCD in search_area


        name, ext, mime = _detect_office_subtype(data)


        has_cdfh = b"PK\x01\x02" in data

        if has_eocd and has_cdfh:
            return ValidationResult(
                ValidationStatus.VALID, 0.97,
                f"{name}: EOCD + Diretório Central encontrados"
            )

        if has_eocd:
            return ValidationResult(
                ValidationStatus.VALID, 0.80,
                f"{name}: EOCD encontrado"
            )

        if has_cdfh:
            return ValidationResult(
                ValidationStatus.PARTIAL, 0.55,
                f"{name}: Diretório Central encontrado, EOCD ausente (truncado)"
            )

        return ValidationResult(
            ValidationStatus.PARTIAL, 0.30,
            f"{name}: apenas LFH – fortemente truncado"
        )

    @classmethod
    def refine(cls, data: bytes) -> bytes:
        """Corta o ZIP no fim do diretório central."""
        idx = data.rfind(_EOCD)
        if idx == -1:
            return data

        end = idx + 22

        if end + 2 <= len(data):
            try:
                comment_len = int.from_bytes(data[idx + 20: idx + 22], "little")
                end = idx + 22 + comment_len
            except Exception:
                pass
        return data[:end]





class DOCXPlugin(ZIPPlugin):
    name      = "Documento Word (DOCX)"
    extension = ".docx"
    mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    @classmethod
    def validate(cls, data: bytes) -> ValidationResult:
        result = super().validate(data)
        if b"word/document.xml" not in data[:8192] and result.is_acceptable:
            return ValidationResult(
                ValidationStatus.CORRUPT, 0.0,
                "ZIP encontrado, mas word/document.xml não apareceu nos cabeçalhos locais"
            )
        return result


class XLSXPlugin(ZIPPlugin):
    name      = "Planilha Excel (XLSX)"
    extension = ".xlsx"
    mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    @classmethod
    def validate(cls, data: bytes) -> ValidationResult:
        result = super().validate(data)
        if b"xl/workbook.xml" not in data[:8192] and result.is_acceptable:
            return ValidationResult(
                ValidationStatus.CORRUPT, 0.0,
                "ZIP encontrado, mas xl/workbook.xml não apareceu nos cabeçalhos locais"
            )
        return result


class PPTXPlugin(ZIPPlugin):
    name      = "Apresentação PowerPoint (PPTX)"
    extension = ".pptx"
    mime_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"

    @classmethod
    def validate(cls, data: bytes) -> ValidationResult:
        result = super().validate(data)
        if b"ppt/presentation.xml" not in data[:8192] and result.is_acceptable:
            return ValidationResult(
                ValidationStatus.CORRUPT, 0.0,
                "ZIP encontrado, mas ppt/presentation.xml não apareceu nos cabeçalhos locais"
            )
        return result
