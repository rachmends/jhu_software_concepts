import runpy
import sys
from pathlib import Path

import pytest


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

import load_data


# ============================================================
# PYTEST-NATIVE FAKES
# ============================================================


class FakeCursor:
    """Small fake psycopg cursor for deterministic tests."""

    def __init__(self, rowcount=1):
        self.rowcount = rowcount
        self.calls = []

    def execute(self, *args):
        self.calls.append(args)


class CursorContext:
    """Context manager returned by connection.cursor()."""

    def __init__(self, cursor):
        self.cursor = cursor

    def __enter__(self):
        return self.cursor

    def __exit__(self, exc_type, exc_value, traceback):
        return False


class FakeConnection:
    """Small fake psycopg connection."""

    def __init__(self, cursor):
        self.fake_cursor = cursor
        self.commit_count = 0

    def cursor(self):
        return CursorContext(self.fake_cursor)

    def commit(self):
        self.commit_count += 1


class ConnectionContext:
    """Context manager returned by psycopg.connect()."""

    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self.connection

    def __exit__(self, exc_type, exc_value, traceback):
        return False


# ============================================================
# CLEANING HELPERS
# ============================================================


@pytest.mark.db
def test_clean_text_empty_string():
    assert load_data.clean_text("   ") is None


@pytest.mark.db
def test_clean_float_invalid_values():
    assert load_data.clean_float("") is None
    assert load_data.clean_float("not-a-number") is None


@pytest.mark.db
def test_clean_date_invalid_values():
    assert load_data.clean_date("") is None
    assert load_data.clean_date("not-a-date") is None
    assert load_data.clean_date(12345) is None


# ============================================================
# JSON LOADING
# ============================================================


@pytest.mark.db
def test_load_data_reads_json(tmp_path):
    path = tmp_path / "fake.json"

    path.write_text(
        '[{"program": "Computer Science"}]',
        encoding="utf-8",
    )

    result = load_data.load_data(path)

    assert result == [
        {
            "program": "Computer Science",
        }
    ]


# ============================================================
# TABLE CREATION
# ============================================================


@pytest.mark.db
def test_create_table_executes_create_statement():
    cursor = FakeCursor()

    load_data.create_table(cursor)

    assert len(cursor.calls) == 1

    sql = cursor.calls[0][0]

    assert "CREATE TABLE IF NOT EXISTS applicants" in sql
    assert "p_id SERIAL PRIMARY KEY" in sql
    assert "url TEXT UNIQUE" in sql


# ============================================================
# INSERT APPLICANT
# ============================================================


@pytest.mark.db
def test_insert_applicant_program_name_branches():
    cursor = FakeCursor()

    # university + program
    load_data.insert_applicant(
        cursor,
        {
            "university": "Johns Hopkins University",
            "program": "Computer Science",
            "url": "https://example.com/1",
        },
    )

    params = cursor.calls[-1][1]

    assert params[0] == (
        "Johns Hopkins University - Computer Science"
    )

    # university only
    load_data.insert_applicant(
        cursor,
        {
            "university": "Johns Hopkins University",
            "program": None,
            "url": "https://example.com/2",
        },
    )

    params = cursor.calls[-1][1]

    assert params[0] == "Johns Hopkins University"

    # program only
    load_data.insert_applicant(
        cursor,
        {
            "university": None,
            "program": "Computer Science",
            "url": "https://example.com/3",
        },
    )

    params = cursor.calls[-1][1]

    assert params[0] == "Computer Science"

    # neither
    load_data.insert_applicant(
        cursor,
        {
            "university": None,
            "program": None,
            "url": "https://example.com/4",
        },
    )

    params = cursor.calls[-1][1]

    assert params[0] is None


# ============================================================
# main()
# ============================================================


@pytest.mark.db
def test_main_missing_database_environment(monkeypatch):
    monkeypatch.delenv(
        "DB_NAME",
        raising=False,
    )

    monkeypatch.delenv(
        "DB_USER",
        raising=False,
    )

    with pytest.raises(
        RuntimeError,
        match="Database connection information is missing",
    ):
        load_data.main()


@pytest.mark.db
def test_main_loads_records(monkeypatch):
    monkeypatch.setenv(
        "DB_NAME",
        "test_database",
    )

    monkeypatch.setenv(
        "DB_USER",
        "test_user",
    )

    applicants = [
        {
            "university": "Johns Hopkins University",
            "program": "Computer Science",
            "url": "https://example.com/1",
        },
        {
            "university": "Princeton University",
            "program": "Mathematics",
            "url": "https://example.com/2",
        },
    ]

    cursor = FakeCursor(rowcount=1)
    connection = FakeConnection(cursor)
    connection_context = ConnectionContext(connection)

    connect_calls = []

    def fake_connect(connection_string):
        connect_calls.append(connection_string)
        return connection_context

    monkeypatch.setattr(
        load_data,
        "load_data",
        lambda filename: applicants,
    )

    monkeypatch.setattr(
        load_data.psycopg,
        "connect",
        fake_connect,
    )

    load_data.main()

    assert connect_calls == [
        "dbname=test_database user=test_user"
    ]

    assert connection.commit_count == 1

    # create_table once + two INSERT statements
    assert len(cursor.calls) == 3


@pytest.mark.db
def test_main_progress_message(
    monkeypatch,
    capsys,
):
    monkeypatch.setenv(
        "DB_NAME",
        "test_database",
    )

    monkeypatch.setenv(
        "DB_USER",
        "test_user",
    )

    # Exactly 1000 records forces:
    # if processed % 1000 == 0
    applicants = [
        {
            "university": "Test University",
            "program": "Test Program",
            "url": f"https://example.com/{i}",
        }
        for i in range(1000)
    ]

    cursor = FakeCursor(rowcount=1)
    connection = FakeConnection(cursor)
    connection_context = ConnectionContext(connection)

    monkeypatch.setattr(
        load_data,
        "load_data",
        lambda filename: applicants,
    )

    monkeypatch.setattr(
        load_data.psycopg,
        "connect",
        lambda connection_string: connection_context,
    )

    load_data.main()

    output = capsys.readouterr().out

    assert (
        "Processed 1,000/1,000 records..."
        in output
    )

    assert connection.commit_count == 1

    # create_table + 1000 inserts
    assert len(cursor.calls) == 1001


# ============================================================
# SCRIPT ENTRY POINT
# ============================================================


@pytest.mark.db
def test_load_data_script_entry_point(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setenv(
        "DB_NAME",
        "test_database",
    )

    monkeypatch.setenv(
        "DB_USER",
        "test_user",
    )

    # load_data.py expects this filename when run directly.
    data_file = (
        tmp_path
        / "llm_extend_applicant_data.json"
    )

    data_file.write_text(
        "[]",
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)

    cursor = FakeCursor(rowcount=0)
    connection = FakeConnection(cursor)
    connection_context = ConnectionContext(connection)

    import psycopg

    monkeypatch.setattr(
        psycopg,
        "connect",
        lambda *args, **kwargs: connection_context,
    )

    runpy.run_path(
        str(SRC_DIR / "load_data.py"),
        run_name="__main__",
    )

    assert connection.commit_count == 1

    # Even with no applicants, create_table() should execute.
    assert len(cursor.calls) == 1