import sys
from pathlib import Path

import pytest


# Allow tests to import modules from Module 4/src.
SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

from app import create_app


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


@pytest.mark.web
def test_app_factory_creates_required_routes(app):
    """The application factory should create all required routes."""
    routes = {rule.rule for rule in app.url_map.iter_rules()}

    assert "/" in routes
    assert "/analysis" in routes
    assert "/pull-data" in routes
    assert "/update-analysis" in routes


@pytest.mark.web
def test_analysis_page_loads(client, monkeypatch):
    """GET /analysis should render the required Analysis page."""

    fake_results = {
        "q1": 33207,
        "q2": 47.89,
        "q3_gpa": 3.76,
        "q3_gre": 165.74,
        "q3_gre_v": 160.37,
        "q3_gre_aw": 4.33,
        "q4": 3.79,
        "q5": 40.74,
        "q6": 3.76,
        "q7": 18,
        "q8": 30,
        "q9": 30,
        "q9_difference": 0,
        "q10": 20.77,
        "q11": 3.87,
    }

    monkeypatch.setattr(
        "app.get_analysis_results",
        lambda: fake_results,
    )

    response = client.get("/analysis")

    assert response.status_code == 200

    page = response.get_data(as_text=True)

    assert "Analysis" in page
    assert "Pull Data" in page
    assert "Update Analysis" in page
    assert "Answer:" in page