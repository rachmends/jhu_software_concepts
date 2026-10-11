"""Exercise remaining Module 6 execution paths."""

from unittest.mock import MagicMock

import pytest

import load_data
import rabbitmq_config
from worker import consumer
from worker.etl import incremental_scraper


def test_load_data_with_existing_connection(monkeypatch, tmp_path):
    """Use the caller's database connection without committing it."""
    import inspect

    connection = MagicMock()

    # Verify the externally managed connection path.
    source = inspect.getsource(load_data.main)
    assert "insert_records(connection)" in source

    # Execute the branch with a controlled input dataset.
    monkeypatch.chdir(tmp_path)
    (tmp_path / "llm_extend_applicant_data.json").write_text(
        "[]", encoding="utf-8"
    )

    load_data.main(connection=connection)

    connection.commit.assert_not_called()


def test_rabbitmq_url_connection(monkeypatch):
    """Use RABBITMQ_URL instead of individual connection settings."""
    monkeypatch.setenv(
        "RABBITMQ_URL",
        "amqp://guest:guest@localhost:5672/%2F",
    )

    connection = MagicMock()
    blocking_connection = MagicMock(return_value=connection)

    monkeypatch.setattr(
        rabbitmq_config.pika,
        "BlockingConnection",
        blocking_connection,
    )

    result = rabbitmq_config.create_connection()

    assert result is connection
    blocking_connection.assert_called_once()
    assert isinstance(
        blocking_connection.call_args.args[0],
        rabbitmq_config.pika.URLParameters,
    )


def test_reject_non_dictionary_payload():
    """Reject tasks with a malformed payload."""
    with pytest.raises(ValueError, match="payload"):
        consumer.process_task({
            "kind": "recompute_analytics",
            "payload": ["invalid"],
        })


def test_scraper_stops_without_next_page(monkeypatch):
    """Stop scraping after a successful page without pagination."""
    record = {"url": "https://example.com/result/1"}

    monkeypatch.setattr(
        incremental_scraper,
        "_is_blocked",
        lambda html: False,
    )
    monkeypatch.setattr(
        incremental_scraper,
        "_parse_page",
        lambda html: [record],
    )
    monkeypatch.setattr(
        incremental_scraper,
        "_get_next_page_url",
        lambda html: None,
    )

    fetcher = MagicMock()
    fetcher.return_value.status = 200
    fetcher.return_value.data = b"<html>valid results</html>"

    records = incremental_scraper.collect_new_records(
        existing_records=[],
        max_pages=2,
        fetcher=fetcher,
    )

    assert records == [record]
    fetcher.assert_called_once()
