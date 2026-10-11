import sys
from pathlib import Path

import pytest


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

import app as app_module
from app import create_app

class FakeThread:
    created = []
    started = 0

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        FakeThread.created.append(self)

    def start(self):
        FakeThread.started += 1

@pytest.fixture
def app():
    """Create a Flask application configured for testing."""
    return create_app({
        "TESTING": True,
    })


@pytest.fixture
def client(app):
    """Create a Flask test client."""
    return app.test_client()


@pytest.fixture(autouse=True)
def reset_pull_state():
    """Reset shared pull state before and after every test."""
    app_module.pull_status["running"] = False
    app_module.pull_status["message"] = (
        "No data pull is currently running."
    )

    if app_module.pull_lock.locked():
        app_module.pull_lock.release()

    yield

    app_module.pull_status["running"] = False

    if app_module.pull_lock.locked():
        app_module.pull_lock.release()


@pytest.mark.buttons
def test_pull_data_starts_when_not_busy(client, monkeypatch):
    """POST /pull-data queues an ingestion task."""
    published = []

    monkeypatch.setattr(
        app_module,
        "publish_task",
        lambda **kwargs: published.append(kwargs),
    )

    response = client.post("/pull-data")

    assert response.status_code == 202
    assert response.get_json()["ok"] is True
    assert published == [
        {"kind": "scrape_new_data", "payload": {}}
    ]


@pytest.mark.buttons
def test_update_analysis_when_not_busy(client, monkeypatch):
    """POST /update-analysis queues an analytics task."""
    published = []

    monkeypatch.setattr(
        app_module,
        "publish_task",
        lambda **kwargs: published.append(kwargs),
    )

    response = client.post("/update-analysis")

    assert response.status_code == 202
    assert response.get_json()["ok"] is True
    assert published == [
        {"kind": "recompute_analytics", "payload": {}}
    ]


@pytest.mark.buttons
def test_update_analysis_returns_409_when_busy(client, monkeypatch):
    """A local pull flag does not prevent analytics task publishing."""
    published = []

    monkeypatch.setattr(
        app_module,
        "publish_task",
        lambda **kwargs: published.append(kwargs),
    )

    app_module.pull_status["running"] = True

    response = client.post("/update-analysis")

    assert response.status_code == 202
    assert response.get_json()["ok"] is True
    assert published == [
        {"kind": "recompute_analytics", "payload": {}}
    ]


@pytest.mark.buttons
def test_pull_data_returns_409_when_busy(client, monkeypatch):
    """A local pull lock does not prevent queueing another task."""
    published = []

    monkeypatch.setattr(
        app_module,
        "publish_task",
        lambda **kwargs: published.append(kwargs),
    )

    acquired = app_module.pull_lock.acquire(blocking=False)
    assert acquired is True

    app_module.pull_status["running"] = True

    response = client.post("/pull-data")

    assert response.status_code == 202
    assert response.get_json()["ok"] is True
    assert published == [
        {"kind": "scrape_new_data", "payload": {}}
    ]
