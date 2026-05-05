"""Registra e resolve os plugins de formatos suportados."""

from __future__ import annotations

from garimpo.signatures import FileSignature


from garimpo.plugins.jpeg     import JPEGPlugin
from garimpo.plugins.png      import PNGPlugin
from garimpo.plugins.pdf      import PDFPlugin
from garimpo.plugins.zip_based import ZIPPlugin, DOCXPlugin, XLSXPlugin, PPTXPlugin
from garimpo.plugins.gif      import GIFPlugin
from garimpo.plugins.bmp      import BMPPlugin
from garimpo.plugins.mp4      import MP4Plugin
from garimpo.plugins.text     import TextPlugin



_ALL_PLUGINS: list[type[FileSignature]] = [
    JPEGPlugin,
    PNGPlugin,
    PDFPlugin,
    DOCXPlugin,
    XLSXPlugin,
    PPTXPlugin,
    ZIPPlugin,
    GIFPlugin,
    BMPPlugin,
    MP4Plugin,
    TextPlugin,
]



def all_plugins() -> list[type[FileSignature]]:
    """Retorna todos os plugins registrados."""
    return list(_ALL_PLUGINS)


def get_plugins(enabled_formats: list[str] | None = None) -> list[type[FileSignature]]:
    """Filtra plugins pelos formatos informados."""
    if not enabled_formats:
        return list(_ALL_PLUGINS)

    normalised = {f.lower().strip() for f in enabled_formats}
    selected: list[type[FileSignature]] = []

    for plugin in _ALL_PLUGINS:
        key = plugin.extension.lstrip(".").lower()
        name_key = plugin.name.lower()
        if key in normalised or any(n in name_key for n in normalised):
            selected.append(plugin)

    return selected


def list_plugin_info() -> list[dict]:
    """Monta os dados exibidos pela CLI."""
    return [
        {
            "name":      p.name,
            "extension": p.extension,
            "mime_type": p.mime_type,
            "headers":   len(p.headers),
            "footers":   len(p.footers),
            "max_size":  p.max_size,
        }
        for p in _ALL_PLUGINS
    ]




FORMAT_ALIASES: dict[str, type[FileSignature]] = {
    "jpeg": JPEGPlugin,
    "jpg":  JPEGPlugin,
    "png":  PNGPlugin,
    "pdf":  PDFPlugin,
    "docx": DOCXPlugin,
    "xlsx": XLSXPlugin,
    "pptx": PPTXPlugin,
    "zip":  ZIPPlugin,
    "gif":  GIFPlugin,
    "bmp":  BMPPlugin,
    "mp4":  MP4Plugin,
    "txt":  TextPlugin,
    "text": TextPlugin,
}
