"""Define contratos e estruturas compartilhadas pelos plugins."""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import ClassVar




class ValidationStatus(str, Enum):
    VALID    = "valid"
    PARTIAL  = "partial"
    CORRUPT  = "corrupt"
    UNKNOWN  = "unknown"


@dataclass
class ValidationResult:
    status: ValidationStatus = ValidationStatus.UNKNOWN
    confidence: float = 0.0
    notes: str = ""

    @property
    def is_acceptable(self) -> bool:
        """Indica se o candidato deve ser mantido."""
        return self.status in (ValidationStatus.VALID, ValidationStatus.PARTIAL)




@dataclass
class CarveResult:
    """Metadados de um candidato recuperado."""


    offset_start: int = 0
    offset_end: int = 0


    file_type: str = ""
    extension: str = ""
    size: int = 0
    index: int = 0


    validation: ValidationResult = field(default_factory=ValidationResult)


    md5: str = ""
    sha1: str = ""
    sha256: str = ""


    output_path: Path = field(default_factory=Path)


    has_footer: bool = False
    is_duplicate: bool = False

    @property
    def status_label(self) -> str:
        if self.is_duplicate:
            return "duplicate"
        if self.has_footer:
            return "recovered"
        return "partial"

    def as_dict(self) -> dict:
        return {
            "index": self.index,
            "file_type": self.file_type,
            "extension": self.extension,
            "offset_start": self.offset_start,
            "offset_end": self.offset_end,
            "size": self.size,
            "has_footer": self.has_footer,
            "status": self.status_label,
            "validation_status": self.validation.status.value,
            "validation_confidence": round(self.validation.confidence, 3),
            "validation_notes": self.validation.notes,
            "md5": self.md5,
            "sha1": self.sha1,
            "sha256": self.sha256,
            "output_path": str(self.output_path),
            "is_duplicate": self.is_duplicate,
        }




class FileSignature(abc.ABC):
    """Contrato base para plugins de formato."""


    name:       ClassVar[str]        = "Unknown"
    extension:  ClassVar[str]        = ".bin"
    mime_type:  ClassVar[str]        = "application/octet-stream"
    headers:    ClassVar[list[bytes]] = []
    footers:    ClassVar[list[bytes]] = []
    max_size:   ClassVar[int]        = 50 * 1024 * 1024
    min_size:   ClassVar[int]        = 64


    @classmethod
    def max_footer_len(cls) -> int:
        if not cls.footers:
            return 0
        return max(len(f) for f in cls.footers)


    @classmethod
    def max_header_len(cls) -> int:
        if not cls.headers:
            return 0
        return max(len(h) for h in cls.headers)

    @classmethod
    @abc.abstractmethod
    def validate(cls, data: bytes) -> ValidationResult:
        """Valida os bytes do candidato."""

    @classmethod
    def refine(cls, data: bytes) -> bytes:
        """Ajusta os bytes antes da gravação."""
        return data
