"""Testes da geração de relatórios."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from garimpo.recovery import RecoverySession
from garimpo.reports import write_reports
from garimpo.signatures import CarveResult, ValidationResult, ValidationStatus


def _make_session(tmp_path: Path, n_results: int = 2) -> RecoverySession:
    session = RecoverySession(
        image_path=tmp_path / "fake.img",
        output_dir=tmp_path / "out",
    )
    (tmp_path / "out" / "reports").mkdir(parents=True, exist_ok=True)

    for i in range(n_results):
        r = CarveResult(
            offset_start=i * 1000,
            offset_end=i * 1000 + 500,
            file_type="Imagem JPEG",
            extension=".jpg",
            size=500,
            index=i,
            validation=ValidationResult(
                status=ValidationStatus.VALID,
                confidence=0.95,
                notes="Test result",
            ),
            md5="a" * 32,
            sha1="b" * 40,
            sha256="c" * 64,
            output_path=tmp_path / "out" / f"carved_{i:06d}.jpg",
            has_footer=True,
        )
        session.results.append(r)
        session.total_carved += 1
        session.total_bytes_recovered += 500
        session.by_type["Imagem JPEG"] = session.by_type.get("Imagem JPEG", 0) + 1

    return session


class TestWriteReportsJSON:
    def test_json_created(self, tmp_path):
        session = _make_session(tmp_path)
        paths = write_reports(session, fmt="json")
        assert any(p.suffix == ".json" for p in paths)

    def test_json_valid_structure(self, tmp_path):
        session = _make_session(tmp_path, n_results=3)
        paths = write_reports(session, fmt="json")
        json_path = next(p for p in paths if p.suffix == ".json")
        data = json.loads(json_path.read_text(encoding="utf-8"))

        assert "garimpo_version" in data
        assert "generated_at" in data
        assert "summary" in data
        assert "evidence" in data
        assert len(data["evidence"]) == 3

    def test_json_evidence_fields(self, tmp_path):
        session = _make_session(tmp_path, n_results=1)
        paths = write_reports(session, fmt="json")
        json_path = next(p for p in paths if p.suffix == ".json")
        evidence = json.loads(json_path.read_text())["evidence"][0]

        required = {
            "index", "file_type", "extension",
            "offset_start", "offset_end", "size",
            "md5", "sha1", "sha256",
            "validation_status", "validation_confidence",
        }
        for field in required:
            assert field in evidence, f"Missing field: {field}"

    def test_json_summary_totals(self, tmp_path):
        session = _make_session(tmp_path, n_results=5)
        paths = write_reports(session, fmt="json")
        json_path = next(p for p in paths if p.suffix == ".json")
        summary = json.loads(json_path.read_text())["summary"]
        assert summary["total_recovered"] == 5
        assert summary["total_bytes_recovered"] == 2500


class TestWriteReportsCSV:
    def test_csv_created(self, tmp_path):
        session = _make_session(tmp_path)
        paths = write_reports(session, fmt="csv")
        assert any(p.suffix == ".csv" for p in paths)

    def test_csv_row_count(self, tmp_path):
        session = _make_session(tmp_path, n_results=4)
        paths = write_reports(session, fmt="csv")
        csv_path = next(p for p in paths if p.suffix == ".csv")
        rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
        assert len(rows) == 4

    def test_csv_has_required_columns(self, tmp_path):
        session = _make_session(tmp_path, n_results=1)
        paths = write_reports(session, fmt="csv")
        csv_path = next(p for p in paths if p.suffix == ".csv")
        reader = csv.DictReader(csv_path.open(encoding="utf-8"))
        fieldnames = set(reader.fieldnames or [])
        for col in ("index", "file_type", "md5", "sha256", "offset_start"):
            assert col in fieldnames

    def test_csv_data_integrity(self, tmp_path):
        session = _make_session(tmp_path, n_results=1)
        paths = write_reports(session, fmt="csv")
        csv_path = next(p for p in paths if p.suffix == ".csv")
        rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
        assert rows[0]["file_type"] == "Imagem JPEG"
        assert rows[0]["sha256"] == "c" * 64


class TestWriteReportsAll:
    def test_all_creates_both(self, tmp_path):
        session = _make_session(tmp_path)
        paths = write_reports(session, fmt="all")
        suffixes = {p.suffix for p in paths}
        assert ".json" in suffixes
        assert ".csv" in suffixes

    def test_none_creates_nothing(self, tmp_path):
        session = _make_session(tmp_path)
        paths = write_reports(session, fmt="none")
        assert paths == []


class TestEmptySession:
    def test_json_with_no_results(self, tmp_path):
        session = _make_session(tmp_path, n_results=0)
        paths = write_reports(session, fmt="json")
        json_path = next(p for p in paths if p.suffix == ".json")
        data = json.loads(json_path.read_text())
        assert data["evidence"] == []
        assert data["summary"]["total_recovered"] == 0
