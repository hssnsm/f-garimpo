"""Configura os logs do Garimpo."""

from __future__ import annotations

import logging
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler

_console = Console(stderr=True)


def setup_logging(
    level: str = "INFO",
    log_file: Path | None = None,
    verbose: bool = False,
) -> logging.Logger:
    """Prepara os handlers de log."""
    numeric_level = logging.DEBUG if verbose else getattr(logging, level.upper(), logging.INFO)

    logger = logging.getLogger("garimpo")
    logger.setLevel(numeric_level)
    logger.handlers.clear()


    rich_handler = RichHandler(
        console=_console,
        rich_tracebacks=verbose,
        show_path=verbose,
        markup=True,
        log_time_format="[%H:%M:%S]",
    )
    rich_handler.setLevel(numeric_level)
    logger.addHandler(rich_handler)


    if log_file is not None:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        fmt = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str = "garimpo") -> logging.Logger:
    """Retorna um logger do projeto."""
    return logging.getLogger(f"garimpo.{name}" if name != "garimpo" else name)
