import sys
from pathlib import Path

import pytest


# ---------------------------------------------------------
# Import Module 4 source code
# ---------------------------------------------------------

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

from load_data import (
    clean_date,
    clean_float,
    clean_text,
    insert_applicant,
)


# ---------------------------------------------------------
# Fake database cursor
# ---------------------------------------------------------

class FakeCursor:
    """
    Small test double for a PostgreSQL cursor.

    This lets us test the loader without changing the real
    GradCafe database.
    """

    def __init__(self):
        self.executions = []
        self.inserted_urls = set()
        self.rows = []
        self.rowcount = 0
        self.query_result = None
        self.description = None

    def fetchone(self):
        return self.query_result

    def execute(self, sql, params=None):
        self.executions.append((sql, params))

        # SELECT query
        if sql.strip().upper().startswith("SELECT"):
            if self.rows:
                self.query_result = self.rows[0]

                self.description = [
                    ("program",),
                    ("comments",),
                    ("date_added",),
                    ("url",),
                    ("status",),
                    ("term",),
                    ("us_or_international",),
                    ("gpa",),
                    ("gre",),
                    ("gre_v",),
                    ("gre_aw",),
                    ("degree",),
                    ("llm_generated_program",),
                    ("llm_generated_university",),
                ]

                self.rowcount = 1
            else:
                self.query_result = None
                self.description = None
                self.rowcount = 0

            return

        # Ignore statements that do not contain applicant data.
        if params is None:
            self.rowcount = 0
            return

        # insert_applicant() sends the applicant URL as
        # parameter index 3.
        url = params[3]

        # Simulate:
        # ON CONFLICT (url) DO NOTHING
        if url in self.inserted_urls:
            self.rowcount = 0
            return

        self.inserted_urls.add(url)
        self.rows.append(params)
        self.rowcount = 1


# ---------------------------------------------------------
# Test applicant
# ---------------------------------------------------------

@pytest.fixture
def applicant():
    return {
        "university": "Johns Hopkins University",
        "program": "Computer Science",
        "comments": "Test applicant",
        "date_added": "Sep 20, 2026",
        "url": "https://example.com/test-applicant-1",
        "status": "Accepted",
        "term": "Fall 2026",
        "student_type": "American",
        "gpa": "3.90",
        "gre": "168",
        "gre_v": "162",
        "gre_aw": "4.5",
        "degree": "MS",
        "llm-generated-program": "Computer Science",
        "llm-generated-university": "Johns Hopkins University",
    }


# ---------------------------------------------------------
# Test 1: applicant can be inserted
# ---------------------------------------------------------

@pytest.mark.db
def test_insert_applicant_writes_record(applicant):
    cursor = FakeCursor()

    insert_applicant(cursor, applicant)

    assert cursor.rowcount == 1
    assert len(cursor.rows) == 1

    sql, params = cursor.executions[0]

    assert "INSERT INTO applicants" in sql
    assert "ON CONFLICT (url) DO NOTHING" in sql

    assert params[0] == (
        "Johns Hopkins University - Computer Science"
    )

    assert params[3] == (
        "https://example.com/test-applicant-1"
    )


# ---------------------------------------------------------
# Test 2: required Module 3 data is not null
# ---------------------------------------------------------

@pytest.mark.db
def test_required_fields_are_nonnull_after_insert(applicant):
    cursor = FakeCursor()

    insert_applicant(cursor, applicant)

    row = cursor.rows[0]

    # Parameter order comes directly from load_data.py.
    program = row[0]
    date_added = row[2]
    url = row[3]
    status = row[4]
    term = row[5]
    student_type = row[6]
    degree = row[11]

    assert program is not None
    assert date_added is not None
    assert url is not None
    assert status is not None
    assert term is not None
    assert student_type is not None
    assert degree is not None


# ---------------------------------------------------------
# Test 3: duplicate insert is idempotent
# ---------------------------------------------------------

@pytest.mark.db
def test_duplicate_insert_is_idempotent(applicant):
    cursor = FakeCursor()

    insert_applicant(cursor, applicant)

    assert cursor.rowcount == 1
    assert len(cursor.rows) == 1

    # Insert exact same applicant again.
    insert_applicant(cursor, applicant)

    # ON CONFLICT(url) DO NOTHING means no second row.
    assert cursor.rowcount == 0
    assert len(cursor.rows) == 1
    assert len(cursor.inserted_urls) == 1


# ---------------------------------------------------------
# Test 4: query data can be represented as a dictionary
# with the expected Module 3 fields
# ---------------------------------------------------------

@pytest.mark.db
def test_simple_query_returns_dict_with_expected_keys(applicant):
    cursor = FakeCursor()

    # Insert the applicant.
    insert_applicant(cursor, applicant)

    # Query the applicant back from the fake database.
    cursor.execute(
        """
        SELECT
            program,
            comments,
            date_added,
            url,
            status,
            term,
            us_or_international,
            gpa,
            gre,
            gre_v,
            gre_aw,
            degree,
            llm_generated_program,
            llm_generated_university
        FROM applicants
        LIMIT 1;
        """
    )

    row = cursor.fetchone()

    assert row is not None

    column_names = [
        column[0]
        for column in cursor.description
    ]

    result = dict(zip(column_names, row))

    expected_keys = {
        "program",
        "comments",
        "date_added",
        "url",
        "status",
        "term",
        "us_or_international",
        "gpa",
        "gre",
        "gre_v",
        "gre_aw",
        "degree",
        "llm_generated_program",
        "llm_generated_university",
    }

    # Requirement: query result is a dictionary.
    assert isinstance(result, dict)

    # Requirement: dictionary contains the required M3 fields.
    assert set(result.keys()) == expected_keys

    # Verify the queried values match the inserted applicant.
    assert result["program"] == (
        "Johns Hopkins University - Computer Science"
    )
    assert result["comments"] == applicant["comments"]
    assert result["date_added"].strftime("%b %d, %Y") == applicant["date_added"]
    assert result["url"] == applicant["url"]
    assert result["status"] == applicant["status"]
    assert result["term"] == applicant["term"]
    assert result["us_or_international"] == applicant["student_type"]
    assert result["gpa"] == float(applicant["gpa"])
    assert result["gre"] == float(applicant["gre"])
    assert result["gre_v"] == float(applicant["gre_v"])
    assert result["gre_aw"] == float(applicant["gre_aw"])
    assert result["degree"] == applicant["degree"]
    assert (
        result["llm_generated_program"]
        == applicant["llm-generated-program"]
    )
    assert (
        result["llm_generated_university"]
        == applicant["llm-generated-university"]
    )

# ---------------------------------------------------------
# Test 5: loader cleaning helpers
# ---------------------------------------------------------

@pytest.mark.db
def test_cleaning_helpers():
    assert clean_text("  Accepted  ") == "Accepted"
    assert clean_text("") is None
    assert clean_text(None) is None

    assert clean_float("3.75") == 3.75
    assert clean_float("") is None
    assert clean_float("not-a-number") is None

    assert str(clean_date("Sep 20, 2026")) == "2026-09-20"
    assert clean_date("") is None
    assert clean_date("invalid date") is None