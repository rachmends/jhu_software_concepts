import runpy
import sys
from pathlib import Path

import pytest


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

import query_data


class FakeCursor:
    def __init__(self, results):
        self.results = iter(results)
        self.execute_count = 0
        self.fetchone_count = 0

    def execute(self, *args, **kwargs):
        self.execute_count += 1

    def fetchone(self):
        self.fetchone_count += 1
        return next(self.results)


class CursorContext:
    def __init__(self, cursor):
        self.cursor = cursor

    def __enter__(self):
        return self.cursor

    def __exit__(self, exc_type, exc_value, traceback):
        return False


class FakeConnection:
    def __init__(self, cursor):
        self.fake_cursor = cursor

    def cursor(self):
        return CursorContext(self.fake_cursor)


class ConnectionContext:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self.connection

    def __exit__(self, exc_type, exc_value, traceback):
        return False


def make_fake_connection(results):
    cursor = FakeCursor(results)
    connection = FakeConnection(cursor)
    context = ConnectionContext(connection)
    return cursor, context


@pytest.mark.db
def test_get_connection_uses_environment_variables(
    monkeypatch,
):
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_NAME", "test_database")
    monkeypatch.setenv("DB_USER", "test_user")
    monkeypatch.setenv("DB_PASSWORD", "test_password")

    received = {}

    def fake_connect(**kwargs):
        received.update(kwargs)
        return object()

    monkeypatch.setattr(
        query_data.psycopg,
        "connect",
        fake_connect,
    )

    query_data.get_connection()

    assert received == {
        "host": "localhost",
        "port": "5432",
        "dbname": "test_database",
        "user": "test_user",
        "password": "test_password",
    }


@pytest.mark.db
def test_get_connection_missing_database_environment(
    monkeypatch,
):
    monkeypatch.delenv("DB_HOST", raising=False)
    monkeypatch.delenv("DB_PORT", raising=False)
    monkeypatch.delenv("DB_NAME", raising=False)
    monkeypatch.delenv("DB_USER", raising=False)
    monkeypatch.delenv("DB_PASSWORD", raising=False)

    with pytest.raises(
        RuntimeError,
        match="Database connection information is missing",
    ):
        query_data.get_connection()


@pytest.mark.db
def test_main_runs_all_raw_sql_queries(
    capsys,
    monkeypatch,
):
    fake_cursor, connection_context = (
        make_fake_connection(
            [
                (33207,),
                (47.89,),
                (3.76, 165.74, 160.37, 4.33),
                (3.79,),
                (40.74,),
                (3.76,),
                (18,),
                (30,),
                (30,),
                (20.77,),
                (3.87,),
            ]
        )
    )

    monkeypatch.setattr(
        query_data,
        "get_connection",
        lambda: connection_context,
    )

    query_data.main()

    output = capsys.readouterr().out

    assert "Fall 2026 applicant count: 33207" in output
    assert "Percent international: 47.89%" in output
    assert "Average GPA: 3.76" in output
    assert "Average GRE Quantitative: 165.74" in output
    assert "Average GRE Verbal: 160.37" in output
    assert "Average GRE Analytical Writing: 4.33" in output

    assert (
        "Average GPA of American Fall 2026 applicants: 3.79"
        in output
    )

    assert (
        "Fall 2025 acceptance percentage: 40.74%"
        in output
    )

    assert (
        "Average GPA of accepted Fall 2026 applicants: 3.76"
        in output
    )

    assert (
        "Johns Hopkins master's Computer Science "
        "applicant count: 18"
        in output
    )

    assert "Original-field count: 30" in output
    assert "LLM-field count: 30" in output
    assert "Difference: +0" in output

    assert (
        "Princeton Fall 2026 acceptance percentage: 20.77%"
        in output
    )

    assert (
        "Average GPA of accepted Princeton Fall 2026 applicants: "
        "3.87"
        in output
    )

    assert fake_cursor.execute_count == 11
    assert fake_cursor.fetchone_count == 11


@pytest.mark.db
def test_query_data_script_entry_point(monkeypatch):
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_NAME", "test_database")
    monkeypatch.setenv("DB_USER", "test_user")
    monkeypatch.setenv("DB_PASSWORD", "test_password")

    fake_cursor, connection_context = (
        make_fake_connection(
            [
                (33207,),
                (47.89,),
                (3.76, 165.74, 160.37, 4.33),
                (3.79,),
                (40.74,),
                (3.76,),
                (18,),
                (30,),
                (30,),
                (20.77,),
                (3.87,),
            ]
        )
    )

    import psycopg

    monkeypatch.setattr(
        psycopg,
        "connect",
        lambda *args, **kwargs: connection_context,
    )

    runpy.run_path(
        str(SRC_DIR / "query_data.py"),
        run_name="__main__",
    )

    assert fake_cursor.execute_count == 11
    assert fake_cursor.fetchone_count == 11