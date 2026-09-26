import runpy
import sys
from pathlib import Path

import pytest


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

import orm_queries


class FakeSession:
    def __init__(self, values):
        self.values = iter(values)
        self.scalar_count = 0

    def scalar(self, *args, **kwargs):
        self.scalar_count += 1
        return next(self.values)


class SessionContext:
    def __init__(self, session):
        self.session = session

    def __enter__(self):
        return self.session

    def __exit__(self, exc_type, exc_value, traceback):
        return False


def make_fake_session(values):
    session = FakeSession(values)
    context = SessionContext(session)
    return session, context


@pytest.mark.db
def test_main_runs_all_orm_queries(
    capsys,
    monkeypatch,
):
    fake_session, session_context = (
        make_fake_session(
            [
                33207,
                3.79,
                100,
                40,
                30,
                30,
                100,
                20,
                3.87,
            ]
        )
    )

    monkeypatch.setattr(
        orm_queries,
        "SessionLocal",
        lambda: session_context,
    )

    orm_queries.main()

    output = capsys.readouterr().out

    assert "Fall 2026 applicant count: 33207" in output

    assert (
        "Average GPA of American Fall 2026 applicants: 3.79"
        in output
    )

    assert (
        "Fall 2025 acceptance percentage: 40.00%"
        in output
    )

    assert "Original-field count: 30" in output
    assert "LLM-field count: 30" in output
    assert "Difference: +0" in output

    assert (
        "Princeton Fall 2026 acceptance percentage: 20.00%"
        in output
    )

    assert (
        "Average GPA of accepted Princeton Fall 2026 applicants: "
        "3.87"
        in output
    )

    assert fake_session.scalar_count == 9


@pytest.mark.db
def test_main_handles_zero_percentage_denominators(
    capsys,
    monkeypatch,
):
    fake_session, session_context = (
        make_fake_session(
            [
                33207,
                3.79,
                0,
                0,
                30,
                30,
                0,
                0,
                3.87,
            ]
        )
    )

    monkeypatch.setattr(
        orm_queries,
        "SessionLocal",
        lambda: session_context,
    )

    orm_queries.main()

    output = capsys.readouterr().out

    assert (
        "Fall 2025 acceptance percentage: 0.00%"
        in output
    )

    assert (
        "Princeton Fall 2026 acceptance percentage: 0.00%"
        in output
    )

    assert fake_session.scalar_count == 9


@pytest.mark.db
def test_orm_queries_script_entry_point(monkeypatch):
    fake_session, session_context = (
        make_fake_session(
            [
                33207,
                3.79,
                100,
                40,
                30,
                30,
                100,
                20,
                3.87,
            ]
        )
    )

    import models

    monkeypatch.setattr(
        models,
        "SessionLocal",
        lambda: session_context,
    )

    runpy.run_path(
        str(SRC_DIR / "orm_queries.py"),
        run_name="__main__",
    )

    assert fake_session.scalar_count == 9