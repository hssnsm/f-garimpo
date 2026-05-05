"""Funções utilitárias usadas pelo projeto."""

from __future__ import annotations

import re
import sys
from pathlib import Path




_SIZE_UNITS: dict[str, int] = {
    "b":   1,
    "kb":  1_024,
    "mb":  1_024 ** 2,
    "gb":  1_024 ** 3,
    "tb":  1_024 ** 4,
}


def parse_size(value: str | int) -> int:
    """Converte tamanho legível para bytes."""
    if isinstance(value, int):
        return value
    value = str(value).strip()
    match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*([a-zA-Z]*)", value)
    if not match:
        raise ValueError(f"Não foi possível interpretar o tamanho: {value!r}")
    num_str, unit = match.groups()
    multiplier = _SIZE_UNITS.get(unit.lower(), 1)
    return int(float(num_str) * multiplier)


def human_size(num_bytes: int) -> str:
    """Formata bytes para leitura humana."""
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if abs(num_bytes) < 1024.0:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} PiB"




def safe_path(p: str | Path) -> Path:
    """Resolve um caminho de forma portável."""
    return Path(p).expanduser().resolve()


def ensure_dir(path: Path) -> Path:
    """Cria e retorna um diretório."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def unique_output_path(directory: Path, stem: str, suffix: str, index: int) -> Path:
    """Monta o caminho de saída com índice."""
    return directory / f"{stem}_{index:06d}{suffix}"




def bytes_to_hex(data: bytes, max_bytes: int = 16) -> str:
    """Gera uma prévia hexadecimal curta."""
    preview = data[:max_bytes]
    hex_str = " ".join(f"{b:02X}" for b in preview)
    return hex_str + (" …" if len(data) > max_bytes else "")


def is_printable_ratio(data: bytes, threshold: float = 0.85) -> bool:
    """Confere a proporção de bytes imprimíveis."""
    if not data:
        return False
    printable = sum(32 <= b < 127 or b in (9, 10, 13) for b in data)
    return printable / len(data) >= threshold




IS_WINDOWS: bool = sys.platform.startswith("win")
IS_LINUX: bool = sys.platform.startswith("linux")
IS_MACOS: bool = sys.platform == "darwin"


def platform_name() -> str:
    if IS_WINDOWS:
        return "Windows"
    if IS_MACOS:
        return "macOS"
    return "Linux"
