"""Plugin heurístico para recuperar blocos de texto simples."""

from __future__ import annotations

from garimpo.signatures import FileSignature, ValidationResult, ValidationStatus
from garimpo.utils import is_printable_ratio


_TEXT_PREFIXES: list[bytes] = [
    b"The ",
    b"This ",
    b"Dear ",
    b"From:",
    b"To: ",
    b"Date:",
    b"Subject:",
    b"<?xml",
    b"<!DOCTYPE",
    b"<html",
    b"[",
    b"# ",
    b"//",
    b"/*",
    b"---",
    b"BEGIN",
]


class TextPlugin(FileSignature):
    name      = "Texto simples"
    extension = ".txt"
    mime_type = "text/plain"



    headers   = []
    footers   = []

    max_size  = 10 * 1024 * 1024
    min_size  = 32


    PROBE_SIZE: int = 4096

    MIN_RATIO:  float = 0.90

    @classmethod
    def validate(cls, data: bytes) -> ValidationResult:
        if len(data) < cls.min_size:
            return ValidationResult(ValidationStatus.CORRUPT, 0.0, "Pequeno demais")


        try:
            text = data.decode("utf-8")
            encoding = "UTF-8"
        except UnicodeDecodeError:
            try:
                text = data.decode("latin-1")
                encoding = "Latin-1"
            except Exception:
                return ValidationResult(ValidationStatus.CORRUPT, 0.0, "Não decodificável como texto")

        ratio = is_printable_ratio(data, threshold=0.0)
        printable_count = sum(32 <= b < 127 or b in (9, 10, 13) for b in data)
        ratio = printable_count / len(data)

        if ratio < cls.MIN_RATIO:
            return ValidationResult(
                ValidationStatus.CORRUPT, ratio,
                f"Baixa proporção de caracteres imprimíveis: {ratio:.2%} (threshold {cls.MIN_RATIO:.0%})"
            )


        prefix_match = any(data.lstrip().startswith(p) for p in _TEXT_PREFIXES)
        confidence = min(0.95, ratio + (0.05 if prefix_match else 0.0))

        return ValidationResult(
            ValidationStatus.VALID, round(confidence, 3),
            f"{encoding} text, {ratio:.2%} proporção imprimível"
        )
