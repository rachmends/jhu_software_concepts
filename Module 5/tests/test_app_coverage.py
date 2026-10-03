import runpy
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

import app as app_module


# ============================================================
# PYTEST-NATIVE FAKES
# ============================================================


class FakeSession:
    """Fake SQLAlchemy session returning scalar values in order."""

    def __init__(self, values):
        self.values = iter(values)
        self.scalar_count = 0

    def scalar(self, *args, **kwargs):
        self.scalar_count += 1
        return next(self.values)


class SessionContext:
    """Context manager returned by SessionLocal()."""

    def __init__(self, session):
        self.session = session

    def __enter__(self):
        return self.session

    def __exit__(self, exc_type, exc_value, traceback):
        return False


def make_fake_session(values):
    """Create a fake SQLAlchemy session and context manager."""

    fake_session = FakeSession(values)
    session_context = SessionContext(fake_session)

    return fake_session, session_context


def reset_pull_state():
    """Return the global pull state and lock to an idle state."""

    app_module.pull_status["running"] = False

    app_module.pull_status["message"] = (
        "No data pull is currently running."
    )

    if app_module.pull_lock.locked():
        app_module.pull_lock.release()


# ============================================================
# get_analysis_results()
# ============================================================


@pytest.mark.analysis
def test_get_analysis_results_with_data(monkeypatch):
    """Cover all analysis queries with normal nonzero data."""

    fake_session, session_context = make_fake_session(
        [
            33207,   # Q1
            100,     # Q2 usable nationality
            48,      # Q2 international
            3.76,    # Q3 GPA
            165.74,  # Q3 GRE quantitative
            160.37,  # Q3 GRE verbal
            4.33,    # Q3 analytical writing
            3.79,    # Q4
            100,     # Q5 Fall 2025 total
            40,      # Q5 Fall 2025 accepted
            3.76,    # Q6
            18,      # Q7
            30,      # Q8
            32,      # Q9
            100,     # Q10 Princeton total
            20,      # Q10 Princeton accepted
            3.87,    # Q11
        ]
    )

    monkeypatch.setattr(
        app_module,
        "SessionLocal",
        lambda: session_context,
    )

    results = app_module.get_analysis_results()

    assert results["q1"] == 33207
    assert results["q2"] == 48.0

    assert results["q3_gpa"] == 3.76
    assert results["q3_gre"] == 165.74
    assert results["q3_gre_v"] == 160.37
    assert results["q3_gre_aw"] == 4.33

    assert results["q4"] == 3.79
    assert results["q5"] == 40.0
    assert results["q6"] == 3.76
    assert results["q7"] == 18
    assert results["q8"] == 30
    assert results["q9"] == 32
    assert results["q9_difference"] == 2
    assert results["q10"] == 20.0
    assert results["q11"] == 3.87

    assert fake_session.scalar_count == 17


@pytest.mark.analysis
def test_get_analysis_results_zero_denominators(
    monkeypatch,
):
    """Cover zero-denominator branches for Q2, Q5, and Q10."""

    fake_session, session_context = make_fake_session(
        [
            0,    # Q1
            0,    # Q2 usable nationality
            0,    # Q2 international
            0.0,  # Q3 GPA
            0.0,  # Q3 GRE quantitative
            0.0,  # Q3 GRE verbal
            0.0,  # Q3 GRE analytical writing
            0.0,  # Q4
            0,    # Q5 total
            0,    # Q5 accepted
            0.0,  # Q6
            0,    # Q7
            0,    # Q8
            0,    # Q9
            0,    # Q10 total
            0,    # Q10 accepted
            0.0,  # Q11
        ]
    )

    monkeypatch.setattr(
        app_module,
        "SessionLocal",
        lambda: session_context,
    )

    results = app_module.get_analysis_results()

    assert results["q2"] == 0.0
    assert results["q5"] == 0.0
    assert results["q10"] == 0.0
    assert results["q9_difference"] == 0

    assert fake_session.scalar_count == 17


# ============================================================
# run_data_pull()
# ============================================================


@pytest.mark.buttons
def test_run_data_pull_no_new_records(monkeypatch):
    """Cover a successful pull where GradCafe has no new records."""

    reset_pull_state()

    app_module.pull_lock.acquire()
    app_module.pull_status["running"] = True

    monkeypatch.setattr(
        app_module,
        "pull_new_data",
        lambda: 0,
    )

    app_module.run_data_pull()

    assert app_module.pull_status["running"] is False
    assert app_module.pull_lock.locked() is False

    assert app_module.pull_status["message"] == (
        "Pull complete. No new GradCafe records were found."
    )


@pytest.mark.buttons
def test_run_data_pull_cleaning_failure(monkeypatch):
    """Cover failure of the cleaning pipeline."""

    reset_pull_state()

    app_module.pull_lock.acquire()
    app_module.pull_status["running"] = True

    clean_failure = SimpleNamespace(
        returncode=1,
        stderr="cleaning failed",
    )

    monkeypatch.setattr(
        app_module,
        "pull_new_data",
        lambda: 2,
    )

    monkeypatch.setattr(
        app_module.subprocess,
        "run",
        lambda *args, **kwargs: clean_failure,
    )

    app_module.run_data_pull()

    assert app_module.pull_status["running"] is False
    assert app_module.pull_lock.locked() is False

    assert app_module.pull_status["message"] == (
        "New records were found, but an error occurred "
        "while processing the data."
    )


@pytest.mark.buttons
def test_run_data_pull_database_failure(monkeypatch):
    """Cover successful cleaning followed by database-load failure."""

    reset_pull_state()

    app_module.pull_lock.acquire()
    app_module.pull_status["running"] = True

    clean_success = SimpleNamespace(
        returncode=0,
        stderr="",
    )

    load_failure = SimpleNamespace(
        returncode=1,
        stderr="database load failed",
    )

    subprocess_results = iter(
        [
            clean_success,
            load_failure,
        ]
    )

    monkeypatch.setattr(
        app_module,
        "pull_new_data",
        lambda: 2,
    )

    monkeypatch.setattr(
        app_module.subprocess,
        "run",
        lambda *args, **kwargs: next(
            subprocess_results
        ),
    )

    app_module.run_data_pull()

    assert app_module.pull_status["running"] is False
    assert app_module.pull_lock.locked() is False

    assert app_module.pull_status["message"] == (
        "The records were processed, but an error "
        "occurred while updating the database."
    )


@pytest.mark.buttons
def test_run_data_pull_success(monkeypatch):
    """Cover the complete successful data-pull pipeline."""

    reset_pull_state()

    app_module.pull_lock.acquire()
    app_module.pull_status["running"] = True

    success = SimpleNamespace(
        returncode=0,
        stderr="",
    )

    subprocess_results = iter(
        [
            success,
            success,
        ]
    )

    subprocess_calls = []

    def fake_subprocess_run(*args, **kwargs):
        subprocess_calls.append(
            (args, kwargs)
        )

        return next(subprocess_results)

    monkeypatch.setattr(
        app_module,
        "pull_new_data",
        lambda: 2,
    )

    monkeypatch.setattr(
        app_module.subprocess,
        "run",
        fake_subprocess_run,
    )

    app_module.run_data_pull()

    assert len(subprocess_calls) == 2

    assert app_module.pull_status["running"] is False
    assert app_module.pull_lock.locked() is False

    assert app_module.pull_status["message"] == (
        "Pull complete. 2 new GradCafe records "
        "were processed and the database was updated."
    )


@pytest.mark.buttons
def test_run_data_pull_unexpected_exception(
    monkeypatch,
):
    """Cover the unexpected-error handler."""

    reset_pull_state()

    app_module.pull_lock.acquire()
    app_module.pull_status["running"] = True

    def fail():
        raise RuntimeError("test failure")

    monkeypatch.setattr(
        app_module,
        "pull_new_data",
        fail,
    )

    app_module.run_data_pull()

    assert app_module.pull_status["running"] is False
    assert app_module.pull_lock.locked() is False

    assert app_module.pull_status["message"] == (
        "The data pull encountered an unexpected error."
    )


# ============================================================
# index() status branches
# ============================================================


@pytest.mark.web
def test_index_updated_analysis_message(monkeypatch):
    """Cover the analysis_status=updated branch."""

    flask_app = app_module.create_app(
        {
            "TESTING": True,
        }
    )

    fake_results = {
        "q1": 1,
    }

    captured = {}

    def fake_render_template(
        template,
        **kwargs,
    ):
        captured["template"] = template
        captured.update(kwargs)
        return "rendered"

    monkeypatch.setattr(
        app_module,
        "get_analysis_results",
        lambda: fake_results,
    )

    monkeypatch.setattr(
        app_module,
        "render_template",
        fake_render_template,
    )

    with flask_app.test_request_context(
        "/analysis?analysis_status=updated"
    ):
        response = app_module.index()

    assert response == "rendered"

    assert captured["analysis_message"] == (
        "Analysis updated using the most current "
        "data available in PostgreSQL."
    )


@pytest.mark.web
def test_index_pull_running_analysis_message(
    monkeypatch,
):
    """Cover the analysis_status=pull_running branch."""

    flask_app = app_module.create_app(
        {
            "TESTING": True,
        }
    )

    fake_results = {
        "q1": 1,
    }

    captured = {}

    def fake_render_template(
        template,
        **kwargs,
    ):
        captured["template"] = template
        captured.update(kwargs)
        return "rendered"

    monkeypatch.setattr(
        app_module,
        "get_analysis_results",
        lambda: fake_results,
    )

    monkeypatch.setattr(
        app_module,
        "render_template",
        fake_render_template,
    )

    with flask_app.test_request_context(
        "/analysis?analysis_status=pull_running"
    ):
        response = app_module.index()

    assert response == "rendered"

    assert captured["analysis_message"] == (
        "New data is currently being retrieved. "
        "The analysis has been refreshed using the "
        "records currently available in PostgreSQL."
    )


# ============================================================
# SCRIPT ENTRY POINT
# ============================================================


@pytest.mark.web
def test_app_script_entry_point(monkeypatch):
    """Cover running app.py directly."""

    import flask

    run_calls = []

    def fake_run(self, **kwargs):
        run_calls.append(kwargs)

    monkeypatch.setattr(
        flask.Flask,
        "run",
        fake_run,
    )

    runpy.run_path(
        str(SRC_DIR / "app.py"),
        run_name="__main__",
    )

    assert run_calls == [
        {
            "debug": True,
        }
    ]