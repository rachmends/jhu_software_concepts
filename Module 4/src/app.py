import os
import subprocess
import threading
import sys

from flask import Flask, render_template, redirect, url_for, request, jsonify
from sqlalchemy import select, func, and_, or_

from models import Applicant, SessionLocal
from scrape import pull_new_data


pull_lock = threading.Lock()

pull_status = {
    "running": False,
    "message": "No data pull is currently running."
}


def get_analysis_results():
    """
    Retrieve all GradCafe analysis results using SQLAlchemy.

    Executes the database queries required for Questions 1 through 11 on the
    analysis page. Results include applicant counts, international applicant
    percentages, GPA and GRE averages, acceptance percentages, field
    comparisons, and the Princeton Fall 2026 analyses.

    Returns:
        dict: Analysis results keyed by the question identifiers expected by
        the Flask analysis template.
    """

    with SessionLocal() as session:

        # Question 1
        q1 = session.scalar(
            select(func.count())
            .select_from(Applicant)
            .where(
                func.lower(func.trim(Applicant.term)) == "fall 2026"
            )
        )

        # Question 2
        usable_nationality = session.scalar(
            select(func.count())
            .select_from(Applicant)
            .where(
                Applicant.us_or_international.is_not(None),
                func.trim(Applicant.us_or_international) != "",
            )
        )

        international = session.scalar(
            select(func.count())
            .select_from(Applicant)
            .where(
                Applicant.us_or_international.is_not(None),
                func.trim(Applicant.us_or_international) != "",
                func.lower(
                    func.trim(Applicant.us_or_international)
                ).not_in(["american", "other"]),
            )
        )

        q2 = (
            100.0 * international / usable_nationality
            if usable_nationality
            else 0.0
        )

        # Question 3
        q3_gpa = session.scalar(
            select(func.avg(Applicant.gpa))
        )

        q3_gre = session.scalar(
            select(func.avg(Applicant.gre))
            .where(Applicant.gre.between(130, 170))
        )

        q3_gre_v = session.scalar(
            select(func.avg(Applicant.gre_v))
            .where(Applicant.gre_v.between(130, 170))
        )

        q3_gre_aw = session.scalar(
            select(func.avg(Applicant.gre_aw))
            .where(Applicant.gre_aw.between(0.0, 6.0))
        )

        # Question 4
        q4 = session.scalar(
            select(func.avg(Applicant.gpa))
            .where(
                func.lower(func.trim(Applicant.term)) == "fall 2026",
                func.lower(
                    func.trim(Applicant.us_or_international)
                ) == "american",
                Applicant.gpa.is_not(None),
            )
        )

        # Question 5
        fall_2025_total = session.scalar(
            select(func.count())
            .select_from(Applicant)
            .where(
                func.lower(func.trim(Applicant.term)) == "fall 2025"
            )
        )

        fall_2025_accepted = session.scalar(
            select(func.count())
            .select_from(Applicant)
            .where(
                func.lower(func.trim(Applicant.term)) == "fall 2025",
                func.lower(
                    func.trim(Applicant.status)
                ).like("accept%"),
            )
        )

        q5 = (
            100.0 * fall_2025_accepted / fall_2025_total
            if fall_2025_total
            else 0.0
        )

        # Question 6
        q6 = session.scalar(
            select(func.avg(Applicant.gpa))
            .where(
                func.lower(func.trim(Applicant.term)) == "fall 2026",
                func.lower(
                    func.trim(Applicant.status)
                ).like("accept%"),
                Applicant.gpa.is_not(None),
            )
        )

        # Question 7
        q7 = session.scalar(
            select(func.count())
            .select_from(Applicant)
            .where(
                or_(
                    func.lower(Applicant.program)
                    .like("%johns hopkins%"),
                    func.lower(Applicant.program).like("%jhu%"),
                ),
                func.lower(Applicant.program)
                .like("%computer science%"),
                or_(
                    func.lower(func.trim(Applicant.degree)).in_(
                        [
                            "ms",
                            "m.s.",
                            "msc",
                            "m.sc.",
                            "master",
                            "masters",
                            "master's",
                        ]
                    ),
                    func.lower(Applicant.degree)
                    .like("%master%"),
                ),
            )
        )

        # Shared PhD condition for Questions 8 and 9
        phd_condition = or_(
            func.lower(func.trim(Applicant.degree)).in_(
                ["phd", "ph.d.", "ph.d"]
            ),
            func.lower(Applicant.degree).like("%doctor%"),
        )

        # Question 8
        q8 = session.scalar(
            select(func.count())
            .select_from(Applicant)
            .where(
                func.lower(func.trim(Applicant.term)) == "fall 2026",
                func.lower(
                    func.trim(Applicant.status)
                ).like("accept%"),
                phd_condition,
                func.lower(Applicant.program)
                .like("%computer science%"),
                or_(
                    func.lower(Applicant.program)
                    .like("%georgetown%"),
                    func.lower(Applicant.program).like(
                        "%massachusetts institute of technology%"
                    ),
                    func.lower(Applicant.program).like("%mit%"),
                    func.lower(Applicant.program)
                    .like("%stanford%"),
                    func.lower(Applicant.program)
                    .like("%carnegie mellon%"),
                ),
            )
        )

        # Question 9
        q9 = session.scalar(
            select(func.count())
            .select_from(Applicant)
            .where(
                func.lower(func.trim(Applicant.term)) == "fall 2026",
                func.lower(
                    func.trim(Applicant.status)
                ).like("accept%"),
                phd_condition,
                func.lower(Applicant.llm_generated_program)
                .like("%computer science%"),
                or_(
                    func.lower(Applicant.llm_generated_university)
                    .like("%georgetown%"),
                    func.lower(Applicant.llm_generated_university)
                    .like(
                        "%massachusetts institute of technology%"
                    ),
                    func.lower(
                        Applicant.llm_generated_university
                    ) == "mit",
                    func.lower(Applicant.llm_generated_university)
                    .like("%stanford%"),
                    func.lower(Applicant.llm_generated_university)
                    .like("%carnegie mellon%"),
                ),
            )
        )

        # Question 10
        princeton_total = session.scalar(
            select(func.count())
            .select_from(Applicant)
            .where(
                func.lower(func.trim(Applicant.term)) == "fall 2026",
                func.lower(Applicant.program)
                .like("%princeton%"),
            )
        )

        princeton_accepted = session.scalar(
            select(func.count())
            .select_from(Applicant)
            .where(
                func.lower(func.trim(Applicant.term)) == "fall 2026",
                func.lower(Applicant.program)
                .like("%princeton%"),
                func.lower(
                    func.trim(Applicant.status)
                ).like("accept%"),
            )
        )

        q10 = (
            100.0 * princeton_accepted / princeton_total
            if princeton_total
            else 0.0
        )

        # Question 11
        q11 = session.scalar(
            select(func.avg(Applicant.gpa))
            .where(
                func.lower(func.trim(Applicant.term)) == "fall 2026",
                func.lower(Applicant.program)
                .like("%princeton%"),
                func.lower(
                    func.trim(Applicant.status)
                ).like("accept%"),
                Applicant.gpa.is_not(None),
            )
        )

        return {
            "q1": q1,
            "q2": q2,
            "q3_gpa": q3_gpa,
            "q3_gre": q3_gre,
            "q3_gre_v": q3_gre_v,
            "q3_gre_aw": q3_gre_aw,
            "q4": q4,
            "q5": q5,
            "q6": q6,
            "q7": q7,
            "q8": q8,
            "q9": q9,
            "q9_difference": q9 - q8,
            "q10": q10,
            "q11": q11,
        }

def run_data_pull():
    """
    Run the complete Pull Data workflow in the background.

    Checks GradCafe for newly submitted applicant records. If new records are
    found, the function runs the existing cleaning pipeline and then executes
    the database loader to add the processed records to PostgreSQL.

    The shared pull status is updated throughout the workflow so the web
    interface can report whether records are being retrieved, processed, or
    loaded. Cleaning and database-loading failures are reported without
    starting a conflicting operation.

    The running status is cleared and the pull lock is released when the
    workflow finishes.
    """

    try:
        pull_status["message"] = (
            "Checking GradCafe for newly submitted results..."
        )

        new_count = pull_new_data()

        if new_count == 0:
            pull_status["message"] = (
                "Pull complete. No new GradCafe records were found."
            )
            return

        pull_status["message"] = (
            f"Found {new_count} new records. "
            "Processing the new data..."
        )

        module_dir = os.path.dirname(
            os.path.abspath(__file__)
        )

        # Run the existing Module 2 cleaning/LLM pipeline.
        clean_result = subprocess.run(
            [
                sys.executable,
                "clean.py",
            ],
            cwd=module_dir,
            capture_output=True,
            text=True,
        )

        if clean_result.returncode != 0:
            print(clean_result.stderr)

            pull_status["message"] = (
                "New records were found, but an error occurred "
                "while processing the data."
            )
            return

        pull_status["message"] = (
            "Data processing complete. Adding new records "
            "to PostgreSQL..."
        )

        # Insert newly processed records into PostgreSQL.
        load_result = subprocess.run(
            [
                sys.executable,
                "load_data.py",
            ],
            cwd=module_dir,
            capture_output=True,
            text=True,
        )

        if load_result.returncode != 0:
            print(load_result.stderr)

            pull_status["message"] = (
                "The records were processed, but an error "
                "occurred while updating the database."
            )
            return

        pull_status["message"] = (
            f"Pull complete. {new_count} new GradCafe records "
            "were processed and the database was updated."
        )

    except Exception as error:
        print(f"Pull Data error: {error}")

        pull_status["message"] = (
            "The data pull encountered an unexpected error."
        )

    finally:
        pull_status["running"] = False
        pull_lock.release()

def index():
    """
    Render the GradCafe analysis page.

    Retrieves the current SQLAlchemy analysis results and passes them to the
    Flask template along with the current Pull Data status. The optional
    ``analysis_status`` query parameter controls the status message displayed
    after an analysis refresh or while a data pull is running.

    Returns:
        Response: Rendered GradCafe analysis page.
    """
    results = get_analysis_results()

    analysis_status = request.args.get(
        "analysis_status"
    )

    if analysis_status == "updated":
        analysis_message = (
            "Analysis updated using the most current "
            "data available in PostgreSQL."
        )

    elif analysis_status == "pull_running":
        analysis_message = (
            "New data is currently being retrieved. "
            "The analysis has been refreshed using the "
            "records currently available in PostgreSQL."
        )

    else:
        analysis_message = None

    return render_template(
        "index.html",
        results=results,
        pull_status=pull_status,
        analysis_message=analysis_message,
    )

def pull_data():
    """
    Start a background GradCafe data pull.

    Attempts to acquire the application data-pull lock. If another pull is
    already running, the route returns HTTP 409 with ``busy`` set to true.

    When the application is available, the route marks the pull as running,
    starts :func:`run_data_pull` in a background thread, and immediately
    returns HTTP 202 so the web request does not wait for the complete ETL
    workflow.

    Returns:
        Response: JSON response with HTTP 202 when the pull starts, or HTTP
        409 when another pull is already running.
    """

    if not pull_lock.acquire(blocking=False):
        pull_status["message"] = (
            "A data pull is already running. "
            "Please wait for it to finish."
        )

        return jsonify({
            "ok": False,
            "busy": True
        }), 409

    pull_status["running"] = True
    pull_status["message"] = (
        "Starting GradCafe data pull..."
    )

    thread = threading.Thread(
        target=run_data_pull,
        daemon=True,
    )

    thread.start()

    return jsonify({
        "ok": True,
        "busy": False
    }), 202

def update_analysis():
    """
    Request an analysis refresh using the current PostgreSQL data.

    The analysis cannot be refreshed while a GradCafe data pull is running.
    In that case, the route returns HTTP 409 with ``busy`` set to true.
    Otherwise, it returns HTTP 200 so the client can refresh the analysis
    using the most current database contents.

    Returns:
        Response: JSON response with HTTP 200 when an update is available, or
        HTTP 409 while a data pull is in progress.
    """


    if pull_status["running"]:
        pull_status["message"] = (
            "New GradCafe data is currently being retrieved. "
            "The analysis below reflects the data currently "
            "available in PostgreSQL."
        )

        return jsonify({
            "ok": False,
            "busy": True
        }), 409

    return jsonify({
        "ok": True,
        "busy": False
    }), 200

def create_app(test_config=None):
    """
    Create and configure the Flask application.

    Creates the Flask application, applies an optional configuration
    dictionary, and registers the analysis, Pull Data, and Update Analysis
    routes.

    Args:
        test_config (dict, optional): Configuration values used to override
            the application's defaults, particularly during automated tests.

    Returns:
        Flask: Configured Flask application.
    """
    app = Flask(__name__)

    if test_config:
        app.config.update(test_config)

    app.add_url_rule("/", endpoint="index", view_func=index)
    app.add_url_rule("/analysis", endpoint="analysis", view_func=index)

    app.add_url_rule(
        "/pull-data",
        endpoint="pull_data",
        view_func=pull_data,
        methods=["POST"],
    )

    app.add_url_rule(
        "/update-analysis",
        endpoint="update_analysis",
        view_func=update_analysis,
        methods=["POST"],
    )

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)