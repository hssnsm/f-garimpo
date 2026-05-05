"""Testes do scanner de assinaturas."""

from __future__ import annotations

from pathlib import Path

import pytest

from garimpo.config import ScanConfig
from garimpo.scanner import Scanner
from garimpo.signatures import CarveResult


def _cfg(image_path: Path, **overrides) -> ScanConfig:
    defaults = dict(
        image_path=image_path,
        output_dir=image_path.parent / "out",
        chunk_size=256,
        validate=True,
        compute_hashes=True,
    )
    defaults.update(overrides)
    return ScanConfig(**defaults)


class TestScannerBasic:
    def test_finds_jpeg(self, tmp_path, jpeg_bytes):
        img = tmp_path / "test.img"
        img.write_bytes(b"\x00" * 128 + jpeg_bytes + b"\x00" * 128)
        results = list(Scanner(_cfg(img, enabled_formats=["jpeg"])).scan(img))
        assert len(results) >= 1
        assert results[0].file_type == "Imagem JPEG"
        assert results[0].extension == ".jpg"
        assert results[0].offset_start == 128

    def test_finds_png(self, tmp_path, png_bytes):
        img = tmp_path / "test.img"
        img.write_bytes(b"\x00" * 64 + png_bytes + b"\x00" * 64)
        results = list(Scanner(_cfg(img, enabled_formats=["png"])).scan(img))
        assert len(results) >= 1
        assert results[0].file_type == "Imagem PNG"

    def test_finds_pdf(self, tmp_path, pdf_bytes):
        img = tmp_path / "test.img"
        img.write_bytes(b"\x00" * 64 + pdf_bytes + b"\x00" * 64)
        results = list(Scanner(_cfg(img, enabled_formats=["pdf"])).scan(img))
        assert len(results) >= 1
        assert results[0].extension == ".pdf"

    def test_finds_multiple_formats(self, synthetic_image):
        results = list(Scanner(_cfg(synthetic_image)).scan(synthetic_image))
        found_types = {r.file_type for r in results}
        assert "Imagem JPEG" in found_types
        assert "Imagem PNG" in found_types

    def test_no_duplicates_on_overlap(self, tmp_path, jpeg_bytes):
        img = tmp_path / "test.img"
        img.write_bytes(jpeg_bytes)
        results = list(Scanner(_cfg(img, enabled_formats=["jpeg"], chunk_size=8)).scan(img))
        offsets = [r.offset_start for r in results]
        assert len(offsets) == len(set(offsets)), "Duplicate offsets detected"

    def test_hashes_computed(self, tmp_path, jpeg_bytes):
        img = tmp_path / "test.img"
        img.write_bytes(jpeg_bytes)
        results = list(Scanner(_cfg(img, compute_hashes=True, enabled_formats=["jpeg"])).scan(img))
        assert results
        r = results[0]
        assert len(r.md5) == 32
        assert len(r.sha1) == 40
        assert len(r.sha256) == 64

    def test_no_hashes_when_disabled(self, tmp_path, jpeg_bytes):
        img = tmp_path / "test.img"
        img.write_bytes(jpeg_bytes)
        results = list(Scanner(_cfg(img, compute_hashes=False, enabled_formats=["jpeg"])).scan(img))
        assert results
        assert results[0].md5 == ""

    def test_result_has_correct_offset(self, tmp_path, png_bytes):
        padding = 300
        img = tmp_path / "test.img"
        img.write_bytes(b"\x00" * padding + png_bytes)
        results = list(Scanner(_cfg(img, enabled_formats=["png"])).scan(img))
        assert results
        assert results[0].offset_start == padding

    def test_result_type_is_carve_result(self, tmp_path, gif_bytes):
        img = tmp_path / "test.img"
        img.write_bytes(gif_bytes)
        results = list(Scanner(_cfg(img, enabled_formats=["gif"])).scan(img))
        for r in results:
            assert isinstance(r, CarveResult)

    def test_max_carved_files_limit(self, synthetic_image):
        results = list(Scanner(_cfg(synthetic_image, max_carved_files=1)).scan(synthetic_image))
        assert len(results) <= 1

    def test_empty_image(self, tmp_path):
        img = tmp_path / "empty.img"
        img.write_bytes(b"\x00" * 1024)
        results = list(Scanner(_cfg(img)).scan(img))
        assert results == []

    def test_header_at_chunk_boundary(self, tmp_path, jpeg_bytes):
        chunk_size = 64

        prefix = b"\x00" * (chunk_size - 2)
        img = tmp_path / "boundary.img"
        img.write_bytes(prefix + jpeg_bytes + b"\x00" * 64)
        results = list(Scanner(_cfg(img, chunk_size=chunk_size, enabled_formats=["jpeg"])).scan(img))
        assert len(results) >= 1
        assert results[0].offset_start == len(prefix)
