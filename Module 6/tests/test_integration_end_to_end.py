import sys
from pathlib import Path

import pytest


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

import app as app_module
from app import create_app
from load_data import insert_applicant


# ---------------------------------------------------------
# Fake database cursor and thread
# ---------------------------------------------------------

class FakeCursor:
    """In-memory cursor used for the end-to-end integration tests."""

    def __init__(self):
        self.rows = []
        self.inserted_urls = set()
        self.rowcount = 0

    def execute(self, sql, params=None):
        if params is None:
            self.rowcount = 0
            return

        # URL is parameter index 3 in insert_applicant().
        url = params[3]

        # Simulate ON CONFLICT (url) DO NOTHING.
        if url in self.inserted_urls:
            self.rowcount = 0
            return

        self.inserted_urls.add(url)
        self.rows.append(params)
        self.rowcount = 1

class FakeThread:
    started = 0

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def start(self):
        FakeThread.started += 1

# ---------------------------------------------------------
# Fixtures
# ---------------------------------------------------------

@pytest.fixture
def app():
    return create_app({"TESTING": True})


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def reset_pull_state():
    """Make sure integration tests do not share pull state."""

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


@pytest.fixture
def fake_scraper_rows():
    """Multiple fake records returned by the scraper."""

    return [
        {
            "university": "Johns Hopkins University",
            "program": "Computer Science",
            "comments": "First test applicant",
            "date_added": "Sep 20, 2026",
            "url": "https://example.com/integration-1",
            "status": "Accepted",
            "term": "Fall 2026",
            "student_type": "American",
            "gpa": "3.90",
            "gre": "168",
            "gre_v": "162",
            "gre_aw": "4.5",
            "degree": "MS",
            "llm-generated-program": "Computer Science",
            "llm-generated-university": (
                "Johns Hopkins University"
            ),
        },
        {
            "university": "Princeton University",
            "program": "Computer Science",
            "comments": "Second test applicant",
            "date_added": "Sep 21, 2026",
            "url": "https://example.com/integration-2",
            "status": "Accepted",
            "term": "Fall 2026",
            "student_type": "International",
            "gpa": "3.85",
            "gre": "170",
            "gre_v": "165",
            "gre_aw": "5.0",
            "degree": "PhD",
            "llm-generated-program": "Computer Science",
            "llm-generated-university": "Princeton University",
        },
    ]


# ---------------------------------------------------------
# Integration test 1
# fake scraper -> pull -> DB -> update -> analysis page
# ---------------------------------------------------------

@pytest.mark.integration
def test_end_to_end_pull_update_and_analysis(
    client,
    fake_scraper_rows,
    monkeypatch,
):
    cursor = FakeCursor()

    published_tasks = []

    monkeypatch.setattr(
        app_module,
        "publish_task",
        lambda **kwargs: published_tasks.append(kwargs),
    )

    pull_response = client.post("/pull-data")

    assert pull_response.status_code == 202
    assert pull_response.get_json()["ok"] is True
    assert published_tasks == [
        {"kind": "scrape_new_data", "payload": {}}
    ]

    for applicant in fake_scraper_rows:
        insert_applicant(cursor, applicant)

    assert len(cursor.rows) == 2

    app_module.pull_status["running"] = False

    if app_module.pull_lock.locked():
        app_module.pull_lock.release()

    update_response = client.post("/update-analysis")

    assert update_response.status_code == 202
    assert update_response.get_json()["ok"] is True
    assert published_tasks == [
        {"kind": "scrape_new_data", "payload": {}},
        {"kind": "recompute_analytics", "payload": {}},
    ]

    fake_analysis = {
        "q1": 2,
        "q2": 50.00,
        "q3_gpa": 3.88,
        "q3_gre": 169.00,
        "q3_gre_v": 163.50,
        "q3_gre_aw": 4.75,
        "q4": 3.90,
        "q5": 0.00,
        "q6": 3.88,
        "q7": 1,
        "q8": 0,
        "q9": 0,
        "q9_difference": 0,
        "q10": 100.00,
        "q11": 3.85,
    }

    monkeypatch.setattr(
        app_module,
        "get_analysis_results",
        lambda: fake_analysis,
    )

    analysis_response = client.get("/analysis")

    assert analysis_response.status_code == 200

    page = analysis_response.get_data(as_text=True)

    assert "Analysis" in page
    assert "Answer:" in page
    assert "Pull Data" in page
    assert "Update Analysis" in page
    assert "50.00%" in page
    assert "100.00%" in page


# ---------------------------------------------------------
# Integration test 2
# overlapping pulls remain consistent
# ---------------------------------------------------------

@pytest.mark.integration
def test_multiple_pulls_with_overlapping_records_remain_consistent(
    fake_scraper_rows,
):
    cursor = FakeCursor()

    first_pull = fake_scraper_rows

    # Second pull contains one existing record and one new record.
    second_pull = [
        fake_scraper_rows[1],
        {
            "university": "Stanford University",
            "program": "Computer Science",
            "comments": "Third test applicant",
            "date_added": "Sep 22, 2026",
            "url": "https://example.com/integration-3",
            "status": "Rejected",
            "term": "Fall 2026",
            "student_type": "American",
            "gpa": "3.80",
            "gre": "167",
            "gre_v": "160",
            "gre_aw": "4.0",
            "degree": "PhD",
            "llm-generated-program": "Computer Science",
            "llm-generated-university": "Stanford University",
        },
    ]

    # First pull inserts two records.
    for applicant in first_pull:
        insert_applicant(cursor, applicant)

    assert len(cursor.rows) == 2

    # Second pull contains one duplicate + one new applicant.
    for applicant in second_pull:
        insert_applicant(cursor, applicant)

    # We should have only three unique database rows,
    # not four.
    assert len(cursor.rows) == 3
    assert len(cursor.inserted_urls) == 3

    urls = [row[3] for row in cursor.rows]

    assert urls.count(
        "https://example.com/integration-2"
    ) == 1

    assert (
        "https://example.com/integration-3"
        in urls
    )