"""Unit tests for RabbitMQ task publishing."""

import json
from unittest.mock import MagicMock

import pytest

from web import publisher


def test_open_channel(monkeypatch):
    """Declare durable RabbitMQ entities and enable confirmations."""
    connection = MagicMock()
    channel = connection.channel.return_value

    monkeypatch.setattr(
        publisher.pika,
        "BlockingConnection",
        lambda parameters: connection,
    )

    returned_connection, returned_channel = publisher._open_channel()

    assert returned_connection is connection
    assert returned_channel is channel

    channel.exchange_declare.assert_called_once_with(
        exchange="tasks",
        exchange_type="direct",
        durable=True,
    )

    channel.queue_declare.assert_called_once_with(
        queue="tasks_q",
        durable=True,
    )

    channel.queue_bind.assert_called_once_with(
        exchange="tasks",
        queue="tasks_q",
        routing_key="tasks",
    )

    channel.confirm_delivery.assert_called_once()


def test_publish_task(monkeypatch):
    """Publish a persistent JSON message and close the connection."""
    connection = MagicMock()
    channel = MagicMock()

    monkeypatch.setattr(
        publisher,
        "_open_channel",
        lambda: (connection, channel),
    )

    publisher.publish_task(
        "scrape_new_data",
        payload={"source": "gradcafe"},
        headers={"request_id": "test-123"},
    )

    kwargs = channel.basic_publish.call_args.kwargs

    assert kwargs["exchange"] == "tasks"
    assert kwargs["routing_key"] == "tasks"
    assert kwargs["mandatory"] is True

    message = json.loads(kwargs["body"])

    assert message["kind"] == "scrape_new_data"
    assert message["payload"] == {"source": "gradcafe"}
    assert set(message) == {"kind", "ts", "payload"}

    from datetime import datetime, timezone

    timestamp = datetime.fromisoformat(message["ts"])
    assert timestamp.utcoffset() == timezone.utc.utcoffset(None)

    assert kwargs["properties"].delivery_mode == 2
    assert kwargs["properties"].headers == {
        "request_id": "test-123"
    }

    connection.close.assert_called_once()


def test_publish_task_rejects_empty_kind():
    """Reject invalid task names before connecting to RabbitMQ."""
    with pytest.raises(ValueError):
        publisher.publish_task("")


def test_publish_task_closes_on_failure(monkeypatch):
    """Close the RabbitMQ connection when publishing fails."""
    connection = MagicMock()
    channel = MagicMock()

    channel.basic_publish.side_effect = RuntimeError(
        "RabbitMQ publish failed"
    )

    monkeypatch.setattr(
        publisher,
        "_open_channel",
        lambda: (connection, channel),
    )

    with pytest.raises(RuntimeError):
        publisher.publish_task("recompute_analytics")

    connection.close.assert_called_once()


def test_open_channel_closes_on_setup_failure(monkeypatch):
    """Close the connection if RabbitMQ setup fails."""
    connection = MagicMock()
    connection.channel.side_effect = RuntimeError(
        "Channel unavailable"
    )

    monkeypatch.setattr(
        publisher.pika,
        "BlockingConnection",
        lambda parameters: connection,
    )

    with pytest.raises(RuntimeError):
        publisher._open_channel()

    connection.close.assert_called_once()
