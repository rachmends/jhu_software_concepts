"""Verify the required RabbitMQ message timestamp."""

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock

from web import publisher


def test_published_message_contains_utc_timestamp(monkeypatch):
    """Published tasks contain kind, UTC timestamp, and payload."""
    connection = MagicMock()
    channel = MagicMock()

    monkeypatch.setattr(
        publisher,
        "_open_channel",
        lambda: (connection, channel),
    )

    publisher.publish_task(
        "recompute_analytics",
        {"source": "gradcafe"},
    )

    message = json.loads(
        channel.basic_publish.call_args.kwargs["body"]
    )

    assert set(message) == {"kind", "ts", "payload"}
    assert message["kind"] == "recompute_analytics"
    assert message["payload"] == {"source": "gradcafe"}

    timestamp = datetime.fromisoformat(message["ts"])
    assert timestamp.tzinfo is not None
    assert timestamp.utcoffset() == timezone.utc.utcoffset(None)

    connection.close.assert_called_once()
