"""Tests for RabbitMQ consumer behavior."""

import json
from unittest.mock import MagicMock

import pytest

from worker import consumer


def test_process_ingest_task(monkeypatch):
    """Dispatch a prepared-data ingestion task."""
    calls = []

    monkeypatch.setattr(
        consumer,
        "ingest_prepared_data",
        lambda: calls.append("ingest"),
    )

    consumer.process_task({"kind": "ingest_prepared_data"})

    assert calls == ["ingest"]


def test_process_analytics_task(monkeypatch):
    """Dispatch analytics using a caller-managed PostgreSQL transaction."""
    from unittest.mock import MagicMock

    connection = MagicMock()
    connection.__enter__.return_value = connection

    connect = MagicMock(return_value=connection)

    monkeypatch.setattr(consumer.psycopg, "connect", connect)
    monkeypatch.setattr(
        consumer,
        "get_database_config",
        lambda: {"dbname": "gradcafe"},
    )

    handler = MagicMock(return_value={"total_applicants": 50002})
    monkeypatch.setattr(
        consumer,
        "handle_recompute_analytics",
        handler,
    )

    result = consumer.process_task({
        "kind": "recompute_analytics",
        "payload": {},
    })

    assert result == {"total_applicants": 50002}
    connect.assert_called_once_with(dbname="gradcafe")
    handler.assert_called_once_with(connection, {})
    connection.commit.assert_called_once()


@pytest.mark.parametrize(
    "message",
    [
        None,
        [],
        {"kind": "unknown"},
        {},
    ],
)
def test_invalid_task(message):
    """Reject malformed or unsupported task types."""
    with pytest.raises(ValueError):
        consumer.process_task(message)


def test_successful_message_acknowledged(monkeypatch):
    """Acknowledge only after processing succeeds."""
    channel = MagicMock()
    method = MagicMock(delivery_tag=12)

    monkeypatch.setattr(
        consumer,
        "process_task",
        lambda message: None,
    )

    consumer.handle_message(
        channel,
        method,
        None,
        json.dumps({"kind": "recompute_analytics"}).encode(),
    )

    channel.basic_ack.assert_called_once_with(
        delivery_tag=12
    )
    channel.basic_nack.assert_not_called()


def test_invalid_message_rejected():
    """Reject malformed JSON without requeueing."""
    channel = MagicMock()
    method = MagicMock(delivery_tag=13)

    consumer.handle_message(
        channel,
        method,
        None,
        b"{invalid-json",
    )

    channel.basic_reject.assert_called_once_with(
        delivery_tag=13,
        requeue=False,
    )


def test_processing_failure_nacked(monkeypatch):
    """Nack a task when processing raises an exception."""
    channel = MagicMock()
    method = MagicMock(delivery_tag=14)

    def failing_task(message):
        raise RuntimeError("Database unavailable")

    monkeypatch.setattr(
        consumer,
        "process_task",
        failing_task,
    )

    consumer.handle_message(
        channel,
        method,
        None,
        json.dumps({"kind": "recompute_analytics"}).encode(),
    )

    channel.basic_nack.assert_called_once_with(
        delivery_tag=14,
        requeue=False,
    )


def test_create_connection(monkeypatch):
    """Delegate RabbitMQ connection creation to shared configuration."""
    connection = MagicMock()
    open_connection = MagicMock(return_value=connection)

    monkeypatch.setattr(
        consumer,
        "open_rabbitmq_connection",
        open_connection,
    )

    assert consumer.create_connection() is connection
    open_connection.assert_called_once_with()


def test_consumer_configuration(monkeypatch):
    """Declare durable messaging infrastructure and manual ACKs."""
    connection = MagicMock()
    channel = connection.channel.return_value

    monkeypatch.setattr(
        consumer,
        "create_connection",
        lambda: connection,
    )

    consumer.main()

    channel.exchange_declare.assert_called_once_with(
        exchange="tasks",
        exchange_type="direct",
        durable=True,
    )

    channel.queue_declare.assert_called_once_with(
        queue="tasks_q",
        durable=True,
    )

    channel.basic_qos.assert_called_once_with(
        prefetch_count=1
    )

    assert (
        channel.basic_consume.call_args.kwargs["auto_ack"]
        is False
    )

    connection.close.assert_called_once()


def test_worker_main_entry_point(monkeypatch):
    """Verify the worker entry point invokes main()."""
    import runpy
    from unittest.mock import MagicMock

    import pika

    mock_connection = MagicMock()
    mock_channel = mock_connection.channel.return_value

    # Prevent any real RabbitMQ connection.
    monkeypatch.setattr(
        pika,
        "BlockingConnection",
        lambda parameters: mock_connection,
    )

    runpy.run_module(
        "worker.consumer",
        run_name="__main__",
    )

    mock_channel.start_consuming.assert_called_once()
    mock_connection.close.assert_called_once()
