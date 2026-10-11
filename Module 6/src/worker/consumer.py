"""RabbitMQ consumer for GradCafe background tasks."""

import json

import psycopg

from db_config import get_database_config
from rabbitmq_config import (
    QUEUE_NAME,
    create_connection as open_rabbitmq_connection,
    declare_tasks,
)

from worker.etl.pipeline import (
    ingest_prepared_data,
    handle_scrape_new_data,
    handle_recompute_analytics,
)



def process_task(message):
    """Validate and execute a background task transactionally.

    Dispatches supported RabbitMQ task kinds to their corresponding
    ETL handlers. Database-backed tasks share a single PostgreSQL
    connection and commit only after the handler completes.

    Args:
        message (dict): Decoded RabbitMQ message containing a task
            ``kind`` and optional dictionary ``payload``.

    Returns:
        dict: Result returned by the completed task handler.

    Raises:
        ValueError: If the message structure or task kind is invalid.
        Exception: If database connection or task execution fails.
            Such failures propagate to the RabbitMQ callback.
    """
    if not isinstance(message, dict):
        raise ValueError("Task must be a JSON object.")

    kind = message.get("kind")
    payload = message.get("payload", {})

    if not isinstance(payload, dict):
        raise ValueError("Task payload must be a JSON object.")

    if kind == "ingest_prepared_data":
        return ingest_prepared_data()

    handlers = {
        "scrape_new_data": handle_scrape_new_data,
        "recompute_analytics": handle_recompute_analytics,
    }

    if kind not in handlers:
        raise ValueError(f"Unsupported task kind: {kind!r}")

    with psycopg.connect(**get_database_config()) as connection:
        result = handlers[kind](connection, payload)
        connection.commit()

    return result


def handle_message(channel, method, _properties, body):
    """Process a delivery and acknowledge or reject it."""
    try:
        message = json.loads(body)
        result = process_task(message)

    except (ValueError, UnicodeDecodeError) as error:
        print(f"Invalid task: {error}")
        channel.basic_reject(
            delivery_tag=method.delivery_tag,
            requeue=False,
        )

    except Exception as error:  # pylint: disable=broad-exception-caught
        print(f"Worker task failed: {error}")
        channel.basic_nack(
            delivery_tag=method.delivery_tag,
            requeue=False,
        )
        # Failed tasks are discarded unless a dead-letter queue
        # is configured. We will add retry/dead-letter handling later.

    else:
        print(f"Worker task completed: {result}", flush=True)
        channel.basic_ack(
            delivery_tag=method.delivery_tag,
        )


def create_connection():
    """Create the RabbitMQ consumer connection."""
    return open_rabbitmq_connection()



def main():
    """Consume durable tasks with manual acknowledgments."""
    connection = create_connection()

    try:
        channel = connection.channel()

        declare_tasks(channel)

        channel.basic_qos(prefetch_count=1)

        channel.basic_consume(
            queue=QUEUE_NAME,
            on_message_callback=handle_message,
            auto_ack=False,
        )

        print("Worker waiting for RabbitMQ tasks...")
        channel.start_consuming()

    finally:
        connection.close()


if __name__ == "__main__":
    main()
