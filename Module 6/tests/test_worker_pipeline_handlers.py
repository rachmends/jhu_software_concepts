"""Tests for transactional scraping and analytics worker handlers."""

from unittest.mock import MagicMock

import pytest

from worker.etl import pipeline


def make_connection():
    """Create a mock PostgreSQL connection and cursor."""
    connection = MagicMock()
    cursor = MagicMock()
    connection.cursor.return_value.__enter__.return_value = cursor
    return connection, cursor


def test_scrape_inserts_new_records(monkeypatch):
    """Insert collected records and update the ingestion watermark."""
    connection, cursor = make_connection()

    cursor.fetchone.return_value = None
    cursor.fetchall.return_value = [
        ("https://example.com/existing",),
    ]
    cursor.rowcount = 1

    records = [
        {"url": "https://example.com/new-1"},
        {"url": "https://example.com/new-2"},
    ]

    collect = MagicMock(return_value=records)
    insert = MagicMock()

    monkeypatch.setattr(pipeline, "collect_new_records", collect)
    monkeypatch.setattr(pipeline, "insert_applicant", insert)

    result = pipeline.handle_scrape_new_data(
        connection,
        {"max_pages": 2},
    )

    assert result == {"inserted": 2, "collected": 2}
    assert insert.call_count == 2
    collect.assert_called_once_with(
        existing_records=[{"url": "https://example.com/existing"}],
        max_pages=2,
    )

    sql_statements = [
        call.args[0]
        for call in cursor.execute.call_args_list
    ]
    assert any("INSERT INTO ingestion_watermarks" in sql
               for sql in sql_statements)


def test_scrape_without_new_records(monkeypatch):
    """Preserve the existing URL watermark when nothing new is found."""
    connection, cursor = make_connection()

    existing_url = "https://example.com/previous"
    cursor.fetchone.return_value = (existing_url,)
    cursor.fetchall.return_value = []

    monkeypatch.setattr(
        pipeline,
        "collect_new_records",
        lambda **kwargs: [],
    )

    insert = MagicMock()
    monkeypatch.setattr(pipeline, "insert_applicant", insert)

    result = pipeline.handle_scrape_new_data(connection, {})

    assert result == {"inserted": 0, "collected": 0}
    insert.assert_not_called()

    watermark_call = cursor.execute.call_args
    assert watermark_call.args[1][2] == existing_url


def test_scrape_missing_url(monkeypatch):
    """Reject invalid scraped records before advancing the watermark."""
    connection, cursor = make_connection()

    cursor.fetchone.return_value = None
    cursor.fetchall.return_value = []

    monkeypatch.setattr(
        pipeline,
        "collect_new_records",
        lambda **kwargs: [{"program": "Chemistry"}],
    )

    with pytest.raises(ValueError, match="missing its URL"):
        pipeline.handle_scrape_new_data(connection, {})

    sql_statements = [
        call.args[0]
        for call in cursor.execute.call_args_list
    ]
    assert not any(
        "INSERT INTO ingestion_watermarks" in sql
        for sql in sql_statements
    )


def test_recompute_analytics_with_values():
    """Calculate analytics from PostgreSQL aggregate results."""
    connection, cursor = make_connection()
    cursor.fetchone.return_value = (50025, 3.76, 165.74, 20000)

    result = pipeline.handle_recompute_analytics(connection, {})

    assert result == {
        "total_applicants": 50025,
        "average_gpa": 3.76,
        "average_gre": 165.74,
        "accepted_count": 20000,
    }
    statements = [
        call.args[0]
        for call in cursor.execute.call_args_list
    ]
    assert any("AVG(gpa)" in sql for sql in statements)
    assert any("INSERT INTO analytics_summary" in sql for sql in statements)

    insert_call = next(
        call for call in cursor.execute.call_args_list
        if "INSERT INTO analytics_summary" in call.args[0]
    )
    assert insert_call.args[1] == (50025, 3.76, 165.74, 20000)


def test_recompute_analytics_with_null_averages():
    """Handle an empty dataset without invalid float conversions."""
    connection, cursor = make_connection()
    cursor.fetchone.return_value = (0, None, None, 0)

    result = pipeline.handle_recompute_analytics(connection, {})

    assert result == {
        "total_applicants": 0,
        "average_gpa": None,
        "average_gre": None,
        "accepted_count": 0,
    }


def test_scrape_duplicate_records_preserves_watermark(monkeypatch):
    """Do not advance the URL watermark when all inserts conflict."""
    connection, cursor = make_connection()

    existing_url = "https://example.com/previous"
    duplicate_url = "https://example.com/duplicate"

    cursor.fetchone.return_value = (existing_url,)
    cursor.fetchall.return_value = []
    cursor.rowcount = 0

    monkeypatch.setattr(
        pipeline,
        "collect_new_records",
        lambda **kwargs: [{"url": duplicate_url}],
    )

    insert = MagicMock()
    monkeypatch.setattr(pipeline, "insert_applicant", insert)

    result = pipeline.handle_scrape_new_data(connection, {})

    assert result == {"inserted": 0, "collected": 1}
    insert.assert_called_once_with(
        cursor,
        {"url": duplicate_url},
    )

    watermark_call = cursor.execute.call_args
    assert "INSERT INTO ingestion_watermarks" in watermark_call.args[0]
    assert watermark_call.args[1][2] == existing_url
