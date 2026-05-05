#!/usr/bin/env python3
"""Gera imagens sintéticas para testar a recuperação de arquivos."""

from __future__ import annotations

import struct
import sys
import zlib
from pathlib import Path

SAMPLES_DIR = Path(__file__).parent




def make_jpeg() -> bytes:
    return (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        b"\xff\xdb\x00\x43\x00" + b"\x10" * 64
        + b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00"
        + b"\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00"
        + b"\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b"
        + b"\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xf5\xd0"
        + b"\xff\xd9"
    )


def make_png() -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    magic = b"\x89PNG\r\n\x1a\n"
    ihdr  = chunk(b"IHDR", struct.pack(">IIBBBBB", 2, 2, 8, 2, 0, 0, 0))
    raw   = b"\x00\xff\x00\x00" * 2
    idat  = chunk(b"IDAT", zlib.compress(raw))
    iend  = chunk(b"IEND", b"")
    return magic + ihdr + idat + iend


def make_pdf() -> bytes:
    return (
        b"%PDF-1.4\n"
        b"% Garimpo synthetic test PDF\n"
        b"1 0 obj\n<</Type /Catalog /Pages 2 0 R>>\nendobj\n"
        b"2 0 obj\n<</Type /Pages /Kids [3 0 R] /Count 1>>\nendobj\n"
        b"3 0 obj\n<</Type /Page /Parent 2 0 R /MediaBox [0 0 595 842]>>\nendobj\n"
        b"xref\n0 4\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000062 00000 n \n"
        b"0000000119 00000 n \n"
        b"trailer\n<</Size 4 /Root 1 0 R>>\nstartxref\n210\n%%EOF\n"
    )


def make_gif() -> bytes:
    header  = b"GIF89a"
    lsd     = struct.pack("<HHBBB", 2, 2, 0x00, 0, 0)
    image_d = b"\x2c" + struct.pack("<HHHHB", 0, 0, 2, 2, 0)
    lzw     = b"\x02\x05\x4c\x5d\x0b\x00"
    trailer = b"\x3b"
    return header + lsd + image_d + lzw + trailer


def make_bmp() -> bytes:
    w, h    = 2, 2
    row     = b"\xff\x00\x00" * w
    padding = b"\x00" * ((4 - (w * 3) % 4) % 4)
    px_data = (row + padding) * h
    px_off  = 14 + 40
    f_size  = px_off + len(px_data)
    fh      = struct.pack("<2sIHHI", b"BM", f_size, 0, 0, px_off)
    dib     = struct.pack("<IiiHHIIiiII", 40, w, h, 1, 24, 0, len(px_data), 0, 0, 0, 0)
    return fh + dib + px_data


def make_zip_empty() -> bytes:
    lfh = (
        b"PK\x03\x04\x14\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\x08\x00\x00\x00README.txt"
    )
    eocd = (
        b"PK\x05\x06\x00\x00\x00\x00\x01\x00\x01\x00"
        + struct.pack("<I", len(lfh))
        + struct.pack("<I", 0)
        + b"\x00\x00"
    )
    return lfh + eocd


def make_slack(size: int = 512) -> bytes:
    """Gera ruído alinhado a setor."""
    import os
    return os.urandom(size // 4) + b"\x00" * (size - size // 4)




def build_basic_image() -> bytes:
    slack = b"\x00" * 512
    return slack + make_jpeg() + slack + make_png() + slack + make_pdf() + slack


def build_multi_image() -> bytes:
    slack = make_slack(512)
    parts = [
        slack,
        make_jpeg(),  slack,
        make_png(),   slack,
        make_pdf(),   slack,
        make_gif(),   slack,
        make_bmp(),   slack,
        make_zip_empty(), slack,
    ]
    return b"".join(parts)


def build_empty_image(size: int = 65_536) -> bytes:
    return b"\x00" * size


def build_corrupt_image() -> bytes:
    """Monta imagem com arquivos truncados."""
    jpeg_truncated = make_jpeg()[:30]
    png_corrupted  = make_png()[:8] + b"\xDE\xAD\xBE\xEF" + b"\x00" * 50
    pdf_ok         = make_pdf()
    slack          = b"\x00" * 256
    return slack + jpeg_truncated + slack + png_corrupted + slack + pdf_ok + slack




def main() -> None:
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

    images = {
        "sample_basic.img":   build_basic_image,
        "sample_multi.img":   build_multi_image,
        "sample_empty.img":   build_empty_image,
        "sample_corrupt.img": build_corrupt_image,
    }

    for filename, builder in images.items():
        path = SAMPLES_DIR / filename
        data = builder()
        path.write_bytes(data)
        print(f"  Criado: {path}  ({len(data):,} bytes)")

    print("\n✓ Imagens de exemplo geradas em:", SAMPLES_DIR)
    print("  Execute: garimpo scan samples/sample_basic.img -o recovered/")


if __name__ == "__main__":
    main()
