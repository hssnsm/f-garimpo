"""Testes da configuração de varredura."""

from __future__ import annotations

from pathlib import Path

import pytest

from garimpo.config import ScanConfig, DEFAULT_CHUNK_SIZE, DEFAULT_MAX_FILE_SIZE


class TestScanConfigDefaults:
    def test_default_chunk_size(self):
        cfg = ScanConfig()
        assert cfg.chunk_size == DEFAULT_CHUNK_SIZE

    def test_default_max_file_size(self):
        cfg = ScanConfig()
        assert cfg.max_file_size == DEFAULT_MAX_FILE_SIZE

    def test_default_mode_is_fast(self):
        cfg = ScanConfig()
        assert cfg.mode == "fast"

    def test_is_deep_mode_false_by_default(self):
        assert ScanConfig().is_deep_mode is False

    def test_is_deep_mode_true_when_set(self):
        cfg = ScanConfig(mode="deep")
        assert cfg.is_deep_mode is True


class TestScanConfigPathConversions:
    def test_image_path_is_path_object(self, tmp_path):
        img = tmp_path / "test.img"
        img.write_bytes(b"\x00")
        cfg = ScanConfig(image_path=str(img))
        assert isinstance(cfg.image_path, Path)

    def test_output_dir_is_path_object(self, tmp_path):
        cfg = ScanConfig(output_dir=str(tmp_path))
        assert isinstance(cfg.output_dir, Path)

    def test_log_file_none_by_default(self):
        cfg = ScanConfig()
        assert cfg.log_file is None

    def test_log_path_fallback(self, tmp_path):
        cfg = ScanConfig(output_dir=tmp_path)
        assert cfg.log_path == tmp_path / "garimpo_scan.log"

    def test_log_path_override(self, tmp_path):
        custom = tmp_path / "my.log"
        cfg = ScanConfig(log_file=custom)
        assert cfg.log_path == custom

    def test_reports_dir(self, tmp_path):
        cfg = ScanConfig(output_dir=tmp_path)
        assert cfg.reports_dir == tmp_path / "reports"


class TestScanConfigValidation:
    def test_validate_paths_raises_when_missing(self, tmp_path):
        cfg = ScanConfig(image_path=tmp_path / "nonexistent.img")
        with pytest.raises(ValueError, match="não encontrada"):
            cfg.validate_paths()

    def test_validate_paths_raises_when_directory(self, tmp_path):
        cfg = ScanConfig(image_path=tmp_path)
        with pytest.raises(ValueError, match="não é um arquivo"):
            cfg.validate_paths()

    def test_validate_paths_passes_for_real_file(self, tmp_path):
        img = tmp_path / "test.img"
        img.write_bytes(b"\x00" * 512)
        cfg = ScanConfig(image_path=img)
        cfg.validate_paths()


class TestScanConfigFormats:
    def test_empty_formats_means_all(self):
        cfg = ScanConfig(enabled_formats=[])
        assert cfg.enabled_formats == []

    def test_formats_stored(self):
        cfg = ScanConfig(enabled_formats=["jpeg", "png"])
        assert "jpeg" in cfg.enabled_formats
        assert "png" in cfg.enabled_formats
