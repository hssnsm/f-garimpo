"""Define a configuração usada durante uma varredura."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


DEFAULT_CHUNK_SIZE: int = 65_536
DEFAULT_OVERLAP: int = 64
DEFAULT_MAX_FILE_SIZE: int = 100 * 1024 * 1024
DEFAULT_MIN_FILE_SIZE: int = 64

ProgressCallback = Callable[[dict[str, Any]], None]


@dataclass
class ScanConfig:
    """Configuração de uma varredura."""

    image_path: Path = field(default_factory=Path)
    output_dir: Path = field(default_factory=lambda: Path("garimpo_output"))

    chunk_size: int = DEFAULT_CHUNK_SIZE
    overlap: int = DEFAULT_OVERLAP

    mode: str = "fast"
    enabled_formats: list[str] = field(default_factory=list)

    max_file_size: int = DEFAULT_MAX_FILE_SIZE
    min_file_size: int = DEFAULT_MIN_FILE_SIZE

    validate: bool = True
    compute_hashes: bool = True
    skip_duplicates: bool = True
    max_carved_files: int = 0

    report_format: str = "all"
    log_level: str = "INFO"
    log_file: Path | None = None
    verbose: bool = False
    progress_callback: ProgressCallback | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        self.image_path = Path(self.image_path)
        self.output_dir = Path(self.output_dir)
        if self.log_file is not None:
            self.log_file = Path(self.log_file)

    @property
    def is_deep_mode(self) -> bool:
        return self.mode == "deep"

    @property
    def reports_dir(self) -> Path:
        return self.output_dir / "reports"

    @property
    def log_path(self) -> Path:
        return self.log_file or (self.output_dir / "garimpo_scan.log")

    def notify_progress(self, **payload: Any) -> None:
        """Notifica consumidores sobre o andamento."""
        if self.progress_callback is None:
            return
        try:
            self.progress_callback(payload)
        except Exception:
            pass

    def validate_paths(self) -> None:
        """Valida caminhos e limites básicos."""
        if not self.image_path.exists():
            raise ValueError(f"Imagem não encontrada: {self.image_path}")
        if not self.image_path.is_file():
            raise ValueError(f"O caminho da imagem não é um arquivo: {self.image_path}")
