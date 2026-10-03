import importlib.util
import sys
from pathlib import Path

import pytest


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))


@pytest.mark.db
def test_models_missing_database_environment(monkeypatch):
    """models.py raises an error when database configuration is missing."""

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DB_HOST", raising=False)
    monkeypatch.delenv("DB_PORT", raising=False)
    monkeypatch.delenv("DB_NAME", raising=False)
    monkeypatch.delenv("DB_USER", raising=False)
    monkeypatch.delenv("DB_PASSWORD", raising=False)

    models_path = SRC_DIR / "models.py"

    spec = importlib.util.spec_from_file_location(
        "models_without_database_env",
        models_path,
    )

    isolated_models = importlib.util.module_from_spec(spec)

    with pytest.raises(
        RuntimeError,
        match="Database connection information is missing",
    ):
        spec.loader.exec_module(isolated_models)

@pytest.mark.db
def test_applicant_column_names(monkeypatch):
    """Applicant exposes its mapped database column names."""
    monkeypatch.setenv(
        "DATABASE_URL",
        "sqlite:///:memory:",
    )

    import models

    columns = models.Applicant.column_names()

    assert "p_id" in columns
    assert "program" in columns
    assert "gpa" in columns


@pytest.mark.db
def test_applicant_to_dict(monkeypatch):
    """Applicant converts its mapped values to a dictionary."""
    monkeypatch.setenv(
        "DATABASE_URL",
        "sqlite:///:memory:",
    )

    import models

    applicant = models.Applicant(
        p_id=1,
        program="Computer Science",
        gpa=3.8,
    )

    result = applicant.to_dict()

    assert result["p_id"] == 1
    assert result["program"] == "Computer Science"
    assert result["gpa"] == 3.8
