"""Testes das funções utilitárias."""

from __future__ import annotations

from pathlib import Path

import pytest

from garimpo.utils import (
    parse_size,
    human_size,
    safe_path,
    ensure_dir,
    unique_output_path,
    bytes_to_hex,
    is_printable_ratio,
    platform_name,
)


class TestParseSize:
    def test_plain_integer(self):
        assert parse_size(1024) == 1024

    def test_kb(self):
        assert parse_size("64KB") == 64 * 1024

    def test_mb(self):
        assert parse_size("100MB") == 100 * 1024 * 1024

    def test_gb(self):
        assert parse_size("2GB") == 2 * 1024 ** 3

    def test_bytes_no_unit(self):
        assert parse_size("512") == 512

    def test_lowercase(self):
        assert parse_size("50mb") == 50 * 1024 * 1024

    def test_invalid(self):
        with pytest.raises(ValueError):
            parse_size("abc_invalid")

    def test_fractional(self):

        assert parse_size("1.5KB") == 1536


class TestHumanSize:
    def test_bytes(self):
        assert "B" in human_size(512)

    def test_kib(self):
        assert "KiB" in human_size(2048)

    def test_mib(self):
        assert "MiB" in human_size(2 * 1024 * 1024)

    def test_gib(self):
        assert "GiB" in human_size(3 * 1024 ** 3)


class TestSafePath:
    def test_returns_path(self, tmp_path):
        p = safe_path(str(tmp_path))
        assert isinstance(p, Path)

    def test_expands_tilde(self):
        p = safe_path("~/")
        assert "~" not in str(p)

    def test_spaces_in_path(self, tmp_path):
        d = tmp_path / "my dir with spaces"
        d.mkdir()
        p = safe_path(str(d))
        assert p.exists()


class TestEnsureDir:
    def test_creates_directory(self, tmp_path):
        new_dir = tmp_path / "a" / "b" / "c"
        result = ensure_dir(new_dir)
        assert result.is_dir()

    def test_idempotent(self, tmp_path):
        d = tmp_path / "existing"
        d.mkdir()
        ensure_dir(d)
        assert d.is_dir()


class TestUniqueOutputPath:
    def test_returns_path_with_index(self, tmp_path):
        p = unique_output_path(tmp_path, "carved", ".jpg", 42)
        assert p.name == "carved_000042.jpg"
        assert p.parent == tmp_path

    def test_zero_index(self, tmp_path):
        p = unique_output_path(tmp_path, "carved", ".pdf", 0)
        assert p.name == "carved_000000.pdf"

    def test_different_indices_produce_different_paths(self, tmp_path):
        p1 = unique_output_path(tmp_path, "carved", ".png", 1)
        p2 = unique_output_path(tmp_path, "carved", ".png", 2)
        assert p1 != p2


class TestBytesToHex:
    def test_short_data(self):
        result = bytes_to_hex(b"\xDE\xAD\xBE\xEF")
        assert "DE" in result
        assert "AD" in result

    def test_truncation_marker(self):
        data = b"\x00" * 100
        result = bytes_to_hex(data, max_bytes=4)
        assert "…" in result

    def test_no_truncation_marker_when_short(self):
        data = b"\xAB\xCD"
        result = bytes_to_hex(data, max_bytes=16)
        assert "…" not in result


class TestIsPrintableRatio:
    def test_fully_printable(self):
        assert is_printable_ratio(b"Hello World! This is plain text.\n") is True

    def test_binary_data(self):
        assert is_printable_ratio(bytes(range(256))) is False

    def test_empty(self):
        assert is_printable_ratio(b"") is False

    def test_threshold(self):

        printable = b"A" * 90
        binary = bytes([0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A])
        data = printable + binary
        assert is_printable_ratio(data, threshold=0.85) is True


class TestPlatformName:
    def test_returns_string(self):
        name = platform_name()
        assert isinstance(name, str)
        assert name in ("Windows", "Linux", "macOS")
