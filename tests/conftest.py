"""Fixtures e amostras binárias usadas nos testes."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

import pytest




def _make_jpeg() -> bytes:

    app0_data = b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    app0 = b"\xff\xe0" + struct.pack(">H", len(app0_data) + 2) + app0_data

    comment = b"Garimpo synthetic test JPEG image data"
    com = b"\xff\xfe" + struct.pack(">H", len(comment) + 2) + comment

    dqt = b"\xff\xdb\x00\x43\x00" + b"\x08" * 64

    sof0 = b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00"

    sos = b"\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00\x7f\xa4\x00\xff\xd9"
    return b"\xff\xd8" + app0 + com + dqt + sof0 + sos


def _make_png() -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    magic  = b"\x89PNG\r\n\x1a\n"
    ihdr   = chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))

    raw    = b"\x00\x00\x00\x00"
    idat   = chunk(b"IDAT", zlib.compress(raw))
    iend   = chunk(b"IEND", b"")
    return magic + ihdr + idat + iend


def _make_pdf() -> bytes:
    return (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
        b"xref\n0 4\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"trailer\n<< /Size 4 /Root 1 0 R >>\n"
        b"startxref\n200\n"
        b"%%EOF\n"
    )


def _make_gif() -> bytes:
    header   = b"GIF89a"

    lsd      = struct.pack("<HHBBB", 10, 5, 0x00, 0, 0)

    netscape = (
        b"\x21\xff\x0b"
        b"NETSCAPE2.0"
        b"\x03\x01\x00\x00\x00"
    )

    image_d  = b"\x2c" + struct.pack("<HHHHB", 0, 0, 1, 1, 0)
    lzw      = b"\x02\x02\x4c\x01\x00"
    trailer  = b"\x3b"
    return header + lsd + netscape + image_d + lzw + trailer


def _make_bmp() -> bytes:
    pixel    = b"\x00\x00\xff"
    padding  = b"\x00"
    file_sz  = 14 + 40 + 3 + 1
    px_off   = 14 + 40
    fh = struct.pack("<2sIHHI", b"BM", file_sz, 0, 0, px_off)
    dib = struct.pack("<IiiHHIIiiII", 40, 1, 1, 1, 24, 0, 0, 0, 0, 0, 0)
    return fh + dib + pixel + padding


def _make_zip() -> bytes:
    lfh = (
        b"PK\x03\x04"
        + b"\x14\x00"
        + b"\x00\x00"
        + b"\x00\x00"
        + b"\x00\x00\x00\x00"
        + b"\x00\x00\x00\x00"
        + b"\x00\x00\x00\x00"
        + b"\x00\x00\x00\x00"
        + b"\x08\x00"
        + b"\x00\x00"
        + b"test.txt"
    )
    cdfh = (
        b"PK\x01\x02"
        + b"\x14\x00\x14\x00"
        + b"\x00\x00\x00\x00"
        + b"\x00\x00\x00\x00"
        + b"\x00\x00\x00\x00"
        + b"\x00\x00\x00\x00"
        + b"\x00\x00\x00\x00"
        + b"\x08\x00"
        + b"\x00\x00\x00\x00\x00\x00\x00\x00"
        + struct.pack("<I", 0)
        + b"test.txt"
    )
    eocd = (
        b"PK\x05\x06"
        + b"\x00\x00\x00\x00"
        + b"\x01\x00\x01\x00"
        + struct.pack("<I", len(cdfh))
        + struct.pack("<I", len(lfh))
        + b"\x00\x00"
    )
    return lfh + cdfh + eocd




@pytest.fixture()
def jpeg_bytes() -> bytes:
    return _make_jpeg()


@pytest.fixture()
def png_bytes() -> bytes:
    return _make_png()


@pytest.fixture()
def pdf_bytes() -> bytes:
    return _make_pdf()


@pytest.fixture()
def gif_bytes() -> bytes:
    return _make_gif()


@pytest.fixture()
def bmp_bytes() -> bytes:
    return _make_bmp()


@pytest.fixture()
def zip_bytes() -> bytes:
    return _make_zip()


@pytest.fixture()
def synthetic_image(tmp_path: Path, jpeg_bytes, png_bytes, pdf_bytes, gif_bytes) -> Path:
    slack = b"\x00" * 512
    image_data = (
        slack
        + jpeg_bytes
        + slack
        + png_bytes
        + slack
        + pdf_bytes
        + slack
        + gif_bytes
        + slack
    )
    image_path = tmp_path / "test.img"
    image_path.write_bytes(image_data)
    return image_path
