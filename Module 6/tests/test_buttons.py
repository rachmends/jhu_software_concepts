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
def test_pull_data_starts_when_not_busy(
    client,
    monkeypatch,
):
    """POST /pull-data should start a pull when the app is idle."""

    FakeThread.created.clear()
    FakeThread.started = 0

    monkeypatch.setattr(
        app_module.threading,
        "Thread",
        FakeThread,
    )

    response = client.post("/pull-data")

    assert response.status_code == 202
    assert response.get_json() == {
        "ok": True,
        "busy": False,
    }

    assert len(FakeThread.created) == 1
    assert FakeThread.started == 1

    assert app_module.pull_status["running"] is True


@pytest.mark.buttons
def test_update_analysis_when_not_busy(client):
    """POST /update-analysis should succeed when no pull is running."""

    response = client.post("/update-analysis")

    assert response.status_code == 200
    assert response.get_json() == {
        "ok": True,
        "busy": False,
    }


@pytest.mark.buttons
def test_update_analysis_returns_409_when_busy(client):
    """POST /update-analysis should be blocked during a data pull."""

    app_module.pull_status["running"] = True

    response = client.post("/update-analysis")

    assert response.status_code == 409
    assert response.get_json() == {
        "ok": False,
        "busy": True,
    }


@pytest.mark.buttons
def test_pull_data_returns_409_when_busy(client):
    """A second POST /pull-data should be blocked while pulling."""

    acquired = app_module.pull_lock.acquire(blocking=False)
    assert acquired is True

    app_module.pull_status["running"] = True

    response = client.post("/pull-data")

    assert response.status_code == 409
    assert response.get_json() == {
        "ok": False,
        "busy": True,
    }