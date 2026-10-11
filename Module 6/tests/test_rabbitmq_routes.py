"""Tests for Flask endpoints that publish RabbitMQ tasks."""

from unittest.mock import patch

import pika
import pytest

from app import create_app


@pytest.fixture
def client():
    """Create a Flask test client."""
    flask_app = create_app({"TESTING": True})
    return flask_app.test_client()


@pytest.mark.parametrize(
    ("endpoint", "task_kind"),
    [
        ("/pull-data", "scrape_new_data"),
        ("/update-analysis", "recompute_analytics"),
    ],
)
def test_endpoint_publishes_task(client, endpoint, task_kind):
    """A successful request publishes a task and returns HTTP 202."""
    with patch("app.publish_task") as mock_publish:
        response = client.post(endpoint)

    assert response.status_code == 202
    assert response.json["ok"] is True

    mock_publish.assert_called_once_with(
        kind=task_kind,
        payload={},
    )


@pytest.mark.parametrize(
    "endpoint",
    ["/pull-data", "/update-analysis"],
)
@pytest.mark.parametrize(
    "error",
    [
        OSError("Connection refused"),
        RuntimeError("Publish failed"),
        ValueError("Invalid message"),
        pika.exceptions.AMQPConnectionError(),
    ],
)
def test_endpoint_handles_publish_failure(client, endpoint, error):
    """Publishing failures return HTTP 503."""
    with patch("app.publish_task", side_effect=error):
        response = client.post(endpoint)

    assert response.status_code == 503
    assert response.json["ok"] is False
