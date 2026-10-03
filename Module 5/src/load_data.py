"""Load cleaned GradCafe applicant data into PostgreSQL."""

import json
import os
from datetime import datetime

import psycopg


DATA_FILE = "llm_extend_applicant_data.json"


def clean_text(value):
    """
    Normalize a text value before database insertion.

    Args:
        value: Value to normalize.

    Returns:
        str or None: Cleaned text value, or ``None`` when the value is missing
        or contains only whitespace.
    """
    if value is None:
        return None

    value = str(value).strip()

    if value == "":
        return None

    return value


def clean_float(value):
    """
    Convert an applicant value to a floating-point number.

    Args:
        value: Value to convert.

    Returns:
        float or None: Converted numeric value. Missing values and values that
        cannot be converted are returned as ``None``.
    """
    if value is None or value == "":
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def clean_date(value):
    """
    Convert a GradCafe decision-date value to a Python date.

    Args:
        value: GradCafe date value to convert.

    Returns:
        date or None: Parsed date when the value is valid; otherwise ``None``.
    """
    if value is None or value == "":
        return None

    try:
        return datetime.strptime(value.strip(), "%b %d, %Y").date()
    except (ValueError, AttributeError):
        return None

def load_data(filename):
    """
    Load cleaned applicant records from a JSON file.

    Args:
        filename (str): Path to the cleaned GradCafe JSON dataset.

    Returns:
        list: Applicant dictionaries read from the file.
    """
    with open(filename, "r", encoding="utf-8") as file:
        return json.load(file)


def create_table(cursor):
    """
    Create the PostgreSQL ``applicants`` table when it does not already exist.

    The table follows the applicant schema used by the GradCafe analysis
    application. It includes a serial primary key and a unique URL field used
    to identify individual GradCafe applicant records.

    Args:
        cursor: Active psycopg database cursor used to execute the table
            creation statement.
    """

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS applicants (
            p_id SERIAL PRIMARY KEY,
            program TEXT,
            comments TEXT,
            date_added DATE,
            url TEXT UNIQUE,
            status TEXT,
            term TEXT,
            us_or_international TEXT,
            gpa DOUBLE PRECISION,
            gre DOUBLE PRECISION,
            gre_v DOUBLE PRECISION,
            gre_aw DOUBLE PRECISION,
            degree TEXT,
            llm_generated_program TEXT,
            llm_generated_university TEXT
        );
    """)


def insert_applicant(cursor, applicant):
    """
    Insert one cleaned GradCafe applicant record into PostgreSQL.

    Builds the stored program name from the available university and program
    values, normalizes database fields, and inserts the applicant using the
    Module 3 database schema. The applicant URL provides the uniqueness
    constraint used to prevent duplicate GradCafe records from being stored.

    Args:
        cursor: Active psycopg database cursor used for the INSERT operation.
        applicant (dict): Cleaned applicant record containing the values to
            store in PostgreSQL.
    """

    university = clean_text(applicant.get("university"))
    program = clean_text(applicant.get("program"))

    # The assignment defines program as:
    # "University and Department/Program"
    if university and program:
        full_program = f"{university} - {program}"
    else:
        full_program = university or program

    cursor.execute(
        """
        INSERT INTO applicants (
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
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (url) DO NOTHING;
        """,
        (
            full_program,
            clean_text(applicant.get("comments")),
            clean_date(applicant.get("date_added")),
            clean_text(applicant.get("url")),
            clean_text(applicant.get("status")),
            clean_text(applicant.get("term")),
            clean_text(applicant.get("student_type")),
            clean_float(applicant.get("gpa")),
            clean_float(applicant.get("gre")),
            clean_float(applicant.get("gre_v")),
            clean_float(applicant.get("gre_aw")),
            clean_text(applicant.get("degree")),
            clean_text(applicant.get("llm-generated-program")),
            clean_text(applicant.get("llm-generated-university")),
        ),
    )


def main():

    """
    Load the cleaned GradCafe dataset into PostgreSQL.

    Reads the database name and user from the ``DB_NAME`` and ``DB_USER``
    environment variables, loads the cleaned applicant JSON data, creates the
    ``applicants`` table when necessary, and inserts the applicant records.

    Database changes are committed after processing. Progress is reported
    during large loads.

    Raises:
        RuntimeError: If the required database environment variables are not
            configured.
    """

    # Database credentials come from environment variables.
    # Nothing secret is stored in this file.
    db_name = os.getenv("DB_NAME")
    db_user = os.getenv("DB_USER")

    if not db_name or not db_user:
        raise RuntimeError(
            "Database connection information is missing. "
            "Set DB_NAME and DB_USER as environment variables."
        )

    print(f"Reading {DATA_FILE}...")

    applicants = load_data(DATA_FILE)

    print(f"Found {len(applicants):,} applicant records.")

    connection_string = (
        f"dbname={db_name} "
        f"user={db_user}"
    )

    with psycopg.connect(connection_string) as connection:

        with connection.cursor() as cursor:

            print("Creating applicants table if necessary...")
            create_table(cursor)

            print("Loading applicant data into PostgreSQL...")

            inserted = 0
            processed = 0

            for applicant in applicants:

                insert_applicant(cursor, applicant)

                processed += 1
                inserted += cursor.rowcount

                if processed % 1000 == 0:
                    print(
                        f"Processed {processed:,}/{len(applicants):,} "
                        f"records..."
                    )

        connection.commit()

    print()
    print("Database load complete.")
    print(f"Records processed: {processed:,}")
    print(f"New records inserted: {inserted:,}")
    print(f"Duplicates skipped: {processed - inserted:,}")


if __name__ == "__main__":
    main()
