"""Testes do motor de recuperação."""

from __future__ import annotations

from pathlib import Path

import pytest

from garimpo.config import ScanConfig
from garimpo.recovery import RecoveryEngine, RecoverySession


def _cfg(image_path: Path, output_dir: Path, **overrides) -> ScanConfig:
    defaults = dict(
        image_path=image_path,
        output_dir=output_dir,
        chunk_size=512,
        compute_hashes=True,
        validate=True,
        skip_duplicates=True,
    )
    defaults.update(overrides)
    return ScanConfig(**defaults)


class TestRecoveryEngine:
    def test_returns_session(self, synthetic_image, tmp_path):
        session = RecoveryEngine(_cfg(synthetic_image, tmp_path / "out")).run()
        assert isinstance(session, RecoverySession)

    def test_output_files_exist(self, synthetic_image, tmp_path):
        out = tmp_path / "out"
        session = RecoveryEngine(_cfg(synthetic_image, out)).run()
        assert session.total_bytes_recovered > 0
        carved_files = list(out.rglob("carved_*"))
        assert len(carved_files) >= 1

    def test_carved_files_are_valid(self, synthetic_image, tmp_path):
        out = tmp_path / "out"
        session = RecoveryEngine(_cfg(synthetic_image, out, enabled_formats=["jpeg", "png"])).run()
        for result in session.results:
            assert result.output_path.is_file()
            assert result.output_path.stat().st_size > 0

    def test_output_organised_by_type(self, synthetic_image, tmp_path):
        out = tmp_path / "out"
        session = RecoveryEngine(_cfg(synthetic_image, out)).run()
        for result in session.results:
            assert result.output_path.parent != out, (
                f"File not in a subdirectory: {result.output_path}"
            )

    def test_no_image_modification(self, synthetic_image, tmp_path):
        import hashlib
        original_digest = hashlib.sha256(synthetic_image.read_bytes()).hexdigest()
        RecoveryEngine(_cfg(synthetic_image, tmp_path / "out")).run()
        after_digest = hashlib.sha256(synthetic_image.read_bytes()).hexdigest()
        assert original_digest == after_digest, "A imagem foi modificada durante a varredura!"

    def test_duplicate_suppression(self, tmp_path, jpeg_bytes):
        img = tmp_path / "dup.img"
        img.write_bytes(b"\x00" * 64 + jpeg_bytes + b"\x00" * 64 + jpeg_bytes)
        out = tmp_path / "out"
        session = RecoveryEngine(_cfg(img, out, enabled_formats=["jpeg"])).run()
        assert session.total_duplicates >= 1
        unique_sha256s = {r.sha256 for r in session.results}
        assert len(unique_sha256s) == len(session.results)

    def test_max_carved_files_respected(self, synthetic_image, tmp_path):
        session = RecoveryEngine(_cfg(synthetic_image, tmp_path / "out", max_carved_files=1)).run()
        assert len(session.results) <= 1

    def test_session_by_type_populated(self, synthetic_image, tmp_path):
        session = RecoveryEngine(_cfg(synthetic_image, tmp_path / "out")).run()
        assert len(session.by_type) > 0

    def test_invalid_image_raises(self, tmp_path):
        cfg = ScanConfig(image_path=tmp_path / "nonexistent.img", output_dir=tmp_path / "out")
        with pytest.raises(ValueError, match="não encontrada"):
            RecoveryEngine(cfg).run()

    def test_empty_image_zero_results(self, tmp_path):
        img = tmp_path / "empty.img"
        img.write_bytes(b"\x00" * 4096)
        session = RecoveryEngine(_cfg(img, tmp_path / "out")).run()
        assert len(session.results) == 0
        assert session.total_bytes_recovered == 0

    def test_summary_string(self, synthetic_image, tmp_path):
        session = RecoveryEngine(_cfg(synthetic_image, tmp_path / "out")).run()
        summary = session.summary()
        assert "Recuperados" in summary
        assert "Dados" in summary

    def test_hashes_in_results(self, synthetic_image, tmp_path):
        session = RecoveryEngine(_cfg(synthetic_image, tmp_path / "out")).run()
        for result in session.results:
            assert len(result.md5) == 32
            assert len(result.sha256) == 64

    def test_image_with_spaces_in_path(self, tmp_path, jpeg_bytes):
        spaced_dir = tmp_path / "my images folder"
        spaced_dir.mkdir()
        img = spaced_dir / "disk image copy 01.img"
        img.write_bytes(b"\x00" * 128 + jpeg_bytes + b"\x00" * 128)
        out = tmp_path / "output folder"
        session = RecoveryEngine(_cfg(img, out, enabled_formats=["jpeg"])).run()
        assert len(session.results) >= 1
