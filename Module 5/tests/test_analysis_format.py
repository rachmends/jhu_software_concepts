import sys
from pathlib import Path

import pytest


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


@pytest.fixture
def fake_results():
    """Provide fake analysis results for formatting tests."""
    return {
        "q1": 33207,
        "q2": 47.89123,
        "q3_gpa": 3.756,
        "q3_gre": 165.744,
        "q3_gre_v": 160.366,
        "q3_gre_aw": 4.333,
        "q4": 3.789,
        "q5": 40.746,
        "q6": 3.755,
        "q7": 18,
        "q8": 30,
        "q9": 30,
        "q9_difference": 0,
        "q10": 20.777,
        "q11": 3.874,
    }


@pytest.mark.analysis
def test_analysis_contains_answer_labels(
    client,
    fake_results,
    monkeypatch,
):
    """Rendered analysis results should use Answer labels."""

    monkeypatch.setattr(
        "app.get_analysis_results",
        lambda: fake_results,
    )

    response = client.get("/analysis")

    assert response.status_code == 200

    page = response.get_data(as_text=True)

    assert "Answer:" in page
    assert page.count("Answer:") == 11


@pytest.mark.analysis
def test_percentages_have_exactly_two_decimal_places(
    client,
    fake_results,
    monkeypatch,
):
    """Percentage answers should display exactly two decimals."""

    monkeypatch.setattr(
        "app.get_analysis_results",
        lambda: fake_results,
    )

    response = client.get("/analysis")

    assert response.status_code == 200

    page = response.get_data(as_text=True)

    assert "47.89%" in page
    assert "40.75%" in page
    assert "20.78%" in page

    assert "47.89123%" not in page
    assert "40.746%" not in page
    assert "20.777%" not in page