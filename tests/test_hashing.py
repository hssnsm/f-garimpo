"""Testes do cálculo de hashes."""

from __future__ import annotations

import hashlib

from garimpo.hashing import hash_bytes, hash_file, EMPTY_HASHES, FileHashes


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _md5(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


class TestHashBytes:
    def test_known_md5_empty(self):
        h = hash_bytes(b"")
        assert h.md5 == _md5(b"")

    def test_sha256_matches_stdlib(self):
        data = b"abc"
        h = hash_bytes(data)
        assert h.sha256 == _sha256(data)

    def test_sha256_longer_data(self):
        data = b"The quick brown fox jumps over the lazy dog"
        h = hash_bytes(data)
        assert h.sha256 == _sha256(data)

    def test_md5_matches_stdlib(self):
        data = b"garimpo"
        h = hash_bytes(data)
        assert h.md5 == _md5(data)

    def test_returns_filehashes(self):
        h = hash_bytes(b"garimpo")
        assert isinstance(h, FileHashes)
        assert len(h.md5) == 32
        assert len(h.sha1) == 40
        assert len(h.sha256) == 64

    def test_as_dict(self):
        h = hash_bytes(b"test")
        d = h.as_dict()
        assert set(d.keys()) == {"md5", "sha1", "sha256"}

    def test_empty_bytes_returns_valid_hashes(self):
        h = hash_bytes(b"")
        assert len(h.md5) == 32
        assert len(h.sha1) == 40
        assert len(h.sha256) == 64


class TestHashFile:
    def test_hash_file(self, tmp_path):
        p = tmp_path / "sample.bin"
        p.write_bytes(b"hello world")
        h = hash_file(p)
        expected = hash_bytes(b"hello world")
        assert h.md5 == expected.md5
        assert h.sha1 == expected.sha1
        assert h.sha256 == expected.sha256

    def test_empty_file(self, tmp_path):
        p = tmp_path / "empty.bin"
        p.write_bytes(b"")
        h = hash_file(p)
        assert h.md5 == _md5(b"")
        assert len(h.sha256) == 64


class TestEmptyHashes:
    def test_empty_hashes_all_empty_strings(self):
        assert EMPTY_HASHES.md5 == ""
        assert EMPTY_HASHES.sha1 == ""
        assert EMPTY_HASHES.sha256 == ""
