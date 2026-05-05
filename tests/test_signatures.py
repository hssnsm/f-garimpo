"""Testes dos plugins de formato."""

from __future__ import annotations

import pytest

from garimpo.signatures import ValidationStatus
from garimpo.plugins.jpeg import JPEGPlugin
from garimpo.plugins.png  import PNGPlugin
from garimpo.plugins.pdf  import PDFPlugin
from garimpo.plugins.gif  import GIFPlugin
from garimpo.plugins.bmp  import BMPPlugin
from garimpo.plugins.zip_based import ZIPPlugin




class TestJPEGPlugin:
    def test_valid_jpeg(self, jpeg_bytes):
        r = JPEGPlugin.validate(jpeg_bytes)
        assert r.status == ValidationStatus.VALID
        assert r.confidence > 0.8

    def test_truncated_jpeg(self, jpeg_bytes):
        truncated = jpeg_bytes[:-2]
        r = JPEGPlugin.validate(truncated)
        assert r.status == ValidationStatus.PARTIAL

    def test_corrupt_jpeg(self):
        r = JPEGPlugin.validate(b"\x00\x00\x00garbage")
        assert r.status == ValidationStatus.CORRUPT
        assert r.confidence == 0.0

    def test_too_small(self):
        r = JPEGPlugin.validate(b"\xff\xd8\xff")
        assert r.status == ValidationStatus.CORRUPT

    def test_headers_defined(self):
        assert len(JPEGPlugin.headers) > 0
        for h in JPEGPlugin.headers:
            assert h[:2] == b"\xff\xd8"




class TestPNGPlugin:
    def test_valid_png(self, png_bytes):
        r = PNGPlugin.validate(png_bytes)
        assert r.status == ValidationStatus.VALID
        assert r.confidence > 0.8

    def test_wrong_magic(self):
        r = PNGPlugin.validate(b"\x00\x00\x00\x00" + b"A" * 100)
        assert r.status == ValidationStatus.CORRUPT

    def test_truncated_png(self, png_bytes):
        r = PNGPlugin.validate(png_bytes[:20])

        assert r.status in (ValidationStatus.CORRUPT, ValidationStatus.PARTIAL)

    def test_footer_bytes(self):
        assert b"\x49\x45\x4e\x44\xae\x42\x60\x82" in PNGPlugin.footers




class TestPDFPlugin:
    def test_valid_pdf(self, pdf_bytes):
        r = PDFPlugin.validate(pdf_bytes)
        assert r.status == ValidationStatus.VALID
        assert r.confidence > 0.8

    def test_corrupt_pdf(self):
        r = PDFPlugin.validate(b"not a pdf at all")
        assert r.status == ValidationStatus.CORRUPT

    def test_partial_pdf(self, pdf_bytes):
        truncated = pdf_bytes[:80]
        r = PDFPlugin.validate(truncated)

        assert r.status in (ValidationStatus.VALID, ValidationStatus.PARTIAL)

    def test_header_bytes(self):
        assert b"%PDF-" in PDFPlugin.headers




class TestGIFPlugin:
    def test_valid_gif(self, gif_bytes):
        r = GIFPlugin.validate(gif_bytes)
        assert r.status == ValidationStatus.VALID

    def test_gif87a_header(self):
        assert b"GIF87a" in GIFPlugin.headers

    def test_gif89a_header(self):
        assert b"GIF89a" in GIFPlugin.headers

    def test_corrupt(self):
        r = GIFPlugin.validate(b"NOTGIF" + b"\x00" * 100)
        assert r.status == ValidationStatus.CORRUPT




class TestBMPPlugin:
    def test_valid_bmp(self, bmp_bytes):
        r = BMPPlugin.validate(bmp_bytes)
        assert r.status in (ValidationStatus.VALID, ValidationStatus.PARTIAL)
        assert r.confidence > 0.5

    def test_bm_magic(self):
        assert b"BM" in BMPPlugin.headers

    def test_corrupt(self):
        r = BMPPlugin.validate(b"XX" + b"\x00" * 100)
        assert r.status == ValidationStatus.CORRUPT

    def test_declared_size(self, bmp_bytes):
        size = BMPPlugin.declared_size(bmp_bytes)
        assert size is not None
        assert size > 0




class TestZIPPlugin:
    def test_valid_zip(self, zip_bytes):
        r = ZIPPlugin.validate(zip_bytes)
        assert r.status in (ValidationStatus.VALID, ValidationStatus.PARTIAL)

    def test_lfh_header(self):
        assert b"PK\x03\x04" in ZIPPlugin.headers

    def test_eocd_footer(self):
        assert b"PK\x05\x06" in ZIPPlugin.footers

    def test_corrupt(self):
        r = ZIPPlugin.validate(b"\x00" * 100)
        assert r.status == ValidationStatus.CORRUPT
