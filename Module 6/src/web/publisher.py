"""Publish durable GradCafe tasks to RabbitMQ."""

import json
from datetime import datetime, timezone

import pika


from rabbitmq_config import (
    EXCHANGE_NAME,
    ROUTING_KEY,
    create_connection,
    declare_tasks,
)


def _open_channel():
    """Connect to RabbitMQ and configure durable messaging."""
    connection = create_connection(default_host="localhost")
    try:
        channel = connection.channel()
        declare_tasks(channel)
        channel.confirm_delivery()
        return connection, channel
    except Exception:
        connection.close()
        raise


def publish_task(kind, payload=None, headers=None):
    """Publish a persistent task message to RabbitMQ."""
    if not isinstance(kind, str) or not kind.strip():
        raise ValueError("Task kind must be a nonempty string.")

    message = {
        "kind": kind,
        "ts": datetime.now(timezone.utc).isoformat(),
        "payload": payload if payload is not None else {},
    }

    connection, channel = _open_channel()

    try:
        channel.basic_publish(
            exchange=EXCHANGE_NAME,
            routing_key=ROUTING_KEY,
            body=json.dumps(message, separators=(",", ":")).encode("utf-8"),
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type="application/json",
                headers=headers or {},
            ),
            mandatory=True,
        )
    finally:
        connection.close()
