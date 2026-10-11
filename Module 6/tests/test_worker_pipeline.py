"""Tests for worker ETL pipeline functions."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from worker.etl import pipeline


def test_ingest_prepared_data(monkeypatch, tmp_path):
    """A prepared dataset is passed to the existing loader."""
    cleaned_file = tmp_path / "llm_extend_applicant_data.json"
    cleaned_file.write_text("[]", encoding="utf-8")

    calls = []

    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setattr(
        pipeline,
        "load_applicants",
        lambda connection=None: calls.append(Path.cwd()),
    )

    # Mock the watermark transaction so this unit test
    # does not depend on a running PostgreSQL database.
    mock_engine = MagicMock()
    monkeypatch.setattr(
        pipeline.psycopg,
        "connect",
        lambda **kwargs: mock_engine,
    )
    monkeypatch.setattr(
        pipeline,
        "get_database_config",
        lambda: {"dbname": "gradcafe"},
    )
    mock_engine.__enter__.return_value = mock_engine

    original_directory = Path.cwd()

    pipeline.ingest_prepared_data()

    mock_engine.commit.assert_called_once()

    assert calls == [tmp_path]
    assert Path.cwd() == original_directory


def test_ingest_requires_prepared_dataset(monkeypatch, tmp_path):
    """Missing input data raises an exception."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))

    with pytest.raises(FileNotFoundError):
        pipeline.ingest_prepared_data()


def test_ingest_restores_directory_on_failure(monkeypatch, tmp_path):
    """Restore the working directory when loading fails."""
    cleaned_file = tmp_path / "llm_extend_applicant_data.json"
    cleaned_file.write_text("[]", encoding="utf-8")

    monkeypatch.setenv("DATA_DIR", str(tmp_path))

    def failing_loader(connection=None):
        raise RuntimeError("Database unavailable")

    monkeypatch.setattr(
        pipeline,
        "load_applicants",
        failing_loader,
    )

    mock_connection = MagicMock()
    mock_connection.__enter__.return_value = mock_connection

    monkeypatch.setattr(
        pipeline.psycopg,
        "connect",
        lambda **kwargs: mock_connection,
    )
    monkeypatch.setattr(
        pipeline,
        "get_database_config",
        lambda: {"dbname": "gradcafe"},
    )

    original_directory = Path.cwd()

    with pytest.raises(RuntimeError, match="Database unavailable"):
        pipeline.ingest_prepared_data()

    assert Path.cwd() == original_directory


def test_recompute_analytics():
    """Analytics status is returned."""
    assert pipeline.recompute_analytics() == {
        "status": "ready"
    }
