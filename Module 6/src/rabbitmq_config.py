"""Shared RabbitMQ connection and durable queue configuration."""

import os

import pika


EXCHANGE_NAME = "tasks"
QUEUE_NAME = "tasks_q"
ROUTING_KEY = "tasks"


def create_connection(default_host="rabbitmq"):
    """Create a RabbitMQ connection from URL or environment settings."""
    rabbitmq_url = os.getenv("RABBITMQ_URL")
    if rabbitmq_url:
        parameters = pika.URLParameters(rabbitmq_url)
    else:
        credentials = pika.PlainCredentials(
            os.getenv("RABBITMQ_USER", "guest"),
            os.getenv("RABBITMQ_PASSWORD", "guest"),
        )
        parameters = pika.ConnectionParameters(
            host=os.getenv("RABBITMQ_HOST", default_host),
            port=int(os.getenv("RABBITMQ_PORT", "5672")),
            credentials=credentials,
            heartbeat=60,
            blocked_connection_timeout=30,
        )
    return pika.BlockingConnection(parameters)


def declare_tasks(channel):
    """Declare the durable task exchange, queue, and binding."""
    channel.exchange_declare(
        exchange=EXCHANGE_NAME,
        exchange_type="direct",
        durable=True,
    )
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    channel.queue_bind(
        exchange=EXCHANGE_NAME,
        queue=QUEUE_NAME,
        routing_key=ROUTING_KEY,
    )
