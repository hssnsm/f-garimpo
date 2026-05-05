"""Calcula hashes usados nos relatórios e na deduplicação."""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass
from pathlib import Path

_CHUNK = 65_536


@dataclass(frozen=True)
class FileHashes:
    """Hashes calculados para um arquivo."""
    md5: str
    sha1: str
    sha256: str

    def as_dict(self) -> dict[str, str]:
        return {"md5": self.md5, "sha1": self.sha1, "sha256": self.sha256}


def hash_bytes(data: bytes) -> FileHashes:
    """Calcula hashes de um bloco em memória."""
    md5 = hashlib.md5()
    sha1 = hashlib.sha1()
    sha256 = hashlib.sha256()

    buf = io.BytesIO(data)
    while chunk := buf.read(_CHUNK):
        md5.update(chunk)
        sha1.update(chunk)
        sha256.update(chunk)

    return FileHashes(
        md5=md5.hexdigest(),
        sha1=sha1.hexdigest(),
        sha256=sha256.hexdigest(),
    )


def hash_file(path: Path) -> FileHashes:
    """Calcula hashes lendo o arquivo em blocos."""
    md5 = hashlib.md5()
    sha1 = hashlib.sha1()
    sha256 = hashlib.sha256()

    with open(path, "rb") as fh:
        while chunk := fh.read(_CHUNK):
            md5.update(chunk)
            sha1.update(chunk)
            sha256.update(chunk)

    return FileHashes(
        md5=md5.hexdigest(),
        sha1=sha1.hexdigest(),
        sha256=sha256.hexdigest(),
    )


EMPTY_HASHES = FileHashes(md5="", sha1="", sha256="")
