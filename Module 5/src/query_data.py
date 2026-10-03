"""Analyze GradCafe applicant data using PostgreSQL queries."""

import os

import psycopg


def get_connection():
    """Create a PostgreSQL connection using environment configuration."""
    connection_config = {
        "dbname": os.getenv("DB_NAME"),
        "user": os.getenv("DB_USER"),
    }

    missing_settings = [
        name
        for name, value in connection_config.items()
        if not value
    ]

    if missing_settings:
        missing_names = ", ".join(missing_settings)
        raise RuntimeError(
            "Database connection information is missing: "
            f"{missing_names}."
        )

    return psycopg.connect(**connection_config)


def fetch_one(cursor, query):
    """Execute a query and return its first result row."""
    cursor.execute(query)
    return cursor.fetchone()


def print_result(question, label, value, format_spec="", suffix=""):
    """Print a formatted analysis result."""
    print(f"Question {question}")
    formatted_value = format(value, format_spec) if format_spec else value
    print(f"{label}{formatted_value}{suffix}")
    print()


def question_1(cursor):
    """Return the number of Fall 2026 applicant entries."""
    row = fetch_one(
        cursor,
        """
        SELECT COUNT(*)
        FROM applicants
        WHERE LOWER(TRIM(term)) = 'fall 2026';
        """,
    )
    return row[0]


def question_2(cursor):
    """Return the percentage of classified applicants who are international."""
    row = fetch_one(
        cursor,
        """
        SELECT
            100.0 *
            COUNT(*) FILTER (
                WHERE LOWER(TRIM(us_or_international))
                      NOT IN ('american', 'other')
            )
            /
            NULLIF(
                COUNT(*) FILTER (
                    WHERE us_or_international IS NOT NULL
                      AND TRIM(us_or_international) <> ''
                ),
                0
            )
        FROM applicants;
        """,
    )
    return row[0]


def question_3(cursor):
    """Return average GPA and valid GRE metrics."""
    return fetch_one(
        cursor,
        """
        SELECT
            AVG(gpa),
            AVG(gre) FILTER (
                WHERE gre BETWEEN 130 AND 170
            ),
            AVG(gre_v) FILTER (
                WHERE gre_v BETWEEN 130 AND 170
            ),
            AVG(gre_aw) FILTER (
                WHERE gre_aw BETWEEN 0.0 AND 6.0
            )
        FROM applicants;
        """,
    )


def question_4(cursor):
    """Return average GPA of American Fall 2026 applicants."""
    row = fetch_one(
        cursor,
        """
        SELECT AVG(gpa)
        FROM applicants
        WHERE LOWER(TRIM(term)) = 'fall 2026'
          AND LOWER(TRIM(us_or_international)) = 'american'
          AND gpa IS NOT NULL;
        """,
    )
    return row[0]


def question_5(cursor):
    """Return the Fall 2025 acceptance percentage."""
    row = fetch_one(
        cursor,
        """
        SELECT
            100.0 *
            COUNT(*) FILTER (
                WHERE LOWER(TRIM(status)) LIKE 'accept%'
            )
            /
            NULLIF(COUNT(*), 0)
        FROM applicants
        WHERE LOWER(TRIM(term)) = 'fall 2025';
        """,
    )
    return row[0]


def question_6(cursor):
    """Return average GPA of accepted Fall 2026 applicants."""
    row = fetch_one(
        cursor,
        """
        SELECT AVG(gpa)
        FROM applicants
        WHERE LOWER(TRIM(term)) = 'fall 2026'
          AND LOWER(TRIM(status)) LIKE 'accept%'
          AND gpa IS NOT NULL;
        """,
    )
    return row[0]


def question_7(cursor):
    """Return the Johns Hopkins master's Computer Science applicant count."""
    row = fetch_one(
        cursor,
        """
        SELECT COUNT(*)
        FROM applicants
        WHERE (
                LOWER(program) LIKE '%johns hopkins%'
                OR LOWER(program) LIKE '%jhu%'
              )
          AND LOWER(program) LIKE '%computer science%'
          AND (
                LOWER(TRIM(degree)) IN (
                    'ms',
                    'm.s.',
                    'msc',
                    'm.sc.',
                    'master',
                    'masters',
                    'master''s'
                )
                OR LOWER(degree) LIKE '%master%'
              );
        """,
    )
    return row[0]


def question_8(cursor):
    """Return the original-field count for accepted Fall 2026 CS PhDs."""
    row = fetch_one(
        cursor,
        """
        SELECT COUNT(*)
        FROM applicants
        WHERE LOWER(TRIM(term)) = 'fall 2026'
          AND LOWER(TRIM(status)) LIKE 'accept%'
          AND (
                LOWER(TRIM(degree)) IN (
                    'phd',
                    'ph.d.',
                    'ph.d'
                )
                OR LOWER(degree) LIKE '%doctor%'
              )
          AND LOWER(program) LIKE '%computer science%'
          AND (
                LOWER(program) LIKE '%georgetown%'
                OR LOWER(program) LIKE
                    '%massachusetts institute of technology%'
                OR LOWER(program) LIKE '%mit%'
                OR LOWER(program) LIKE '%stanford%'
                OR LOWER(program) LIKE '%carnegie mellon%'
              );
        """,
    )
    return row[0]


def question_9(cursor):
    """Return the LLM-field count for accepted Fall 2026 CS PhDs."""
    row = fetch_one(
        cursor,
        """
        SELECT COUNT(*)
        FROM applicants
        WHERE LOWER(TRIM(term)) = 'fall 2026'
          AND LOWER(TRIM(status)) LIKE 'accept%'
          AND (
                LOWER(TRIM(degree)) IN (
                    'phd',
                    'ph.d.',
                    'ph.d'
                )
                OR LOWER(degree) LIKE '%doctor%'
              )
          AND LOWER(llm_generated_program)
              LIKE '%computer science%'
          AND (
                LOWER(llm_generated_university)
                    LIKE '%georgetown%'
                OR LOWER(llm_generated_university)
                    LIKE '%massachusetts institute of technology%'
                OR LOWER(llm_generated_university) = 'mit'
                OR LOWER(llm_generated_university)
                    LIKE '%stanford%'
                OR LOWER(llm_generated_university)
                    LIKE '%carnegie mellon%'
              );
        """,
    )
    return row[0]


def question_10(cursor):
    """Return the Princeton Fall 2026 acceptance percentage."""
    row = fetch_one(
        cursor,
        """
        SELECT
            100.0 *
            COUNT(*) FILTER (
                WHERE LOWER(TRIM(status)) LIKE 'accept%'
            )
            /
            NULLIF(COUNT(*), 0)
        FROM applicants
        WHERE LOWER(TRIM(term)) = 'fall 2026'
          AND LOWER(program) LIKE '%princeton%';
        """,
    )
    return row[0]


def question_11(cursor):
    """Return average GPA of accepted Princeton Fall 2026 applicants."""
    row = fetch_one(
        cursor,
        """
        SELECT AVG(gpa)
        FROM applicants
        WHERE LOWER(TRIM(term)) = 'fall 2026'
          AND LOWER(program) LIKE '%princeton%'
          AND LOWER(TRIM(status)) LIKE 'accept%'
          AND gpa IS NOT NULL;
        """,
    )
    return row[0]


def display_question_3(results):
    """Display the four average values returned by Question 3."""
    average_gpa, average_gre, average_gre_v, average_gre_aw = results

    print("Question 3")
    print(f"Average GPA: {average_gpa:.2f}")
    print(f"Average GRE Quantitative: {average_gre:.2f}")
    print(f"Average GRE Verbal: {average_gre_v:.2f}")
    print(f"Average GRE Analytical Writing: {average_gre_aw:.2f}")
    print()


def display_question_9(original_count, llm_count):
    """Display the original and LLM field counts and their difference."""
    difference = llm_count - original_count

    print_result(
        9,
        "Original-field count: ",
        original_count,
    )
    print(f"LLM-field count: {llm_count}")
    print(f"Difference: {difference:+d}")
    print()


def run_analysis(cursor):
    """Execute and display all GradCafe analysis questions."""
    fall_2026_count = question_1(cursor)
    print_result(
        1,
        "Fall 2026 applicant count: ",
        fall_2026_count,
    )

    international_percentage = question_2(cursor)
    print_result(
        2,
        "Percent international: ",
        international_percentage,
        ".2f",
        "%",
    )

    display_question_3(question_3(cursor))

    american_average_gpa = question_4(cursor)
    print_result(
        4,
        "Average GPA of American Fall 2026 applicants: ",
        american_average_gpa,
        ".2f",
    )

    fall_2025_acceptance = question_5(cursor)
    print_result(
        5,
        "Fall 2025 acceptance percentage: ",
        fall_2025_acceptance,
        ".2f",
        "%",
    )

    accepted_average_gpa = question_6(cursor)
    print_result(
        6,
        "Average GPA of accepted Fall 2026 applicants: ",
        accepted_average_gpa,
        ".2f",
    )

    johns_hopkins_count = question_7(cursor)
    print_result(
        7,
        "Johns Hopkins master's Computer Science applicant count: ",
        johns_hopkins_count,
    )

    original_field_count = question_8(cursor)
    print_result(
        8,
        "Original-field count: ",
        original_field_count,
    )

    llm_field_count = question_9(cursor)
    display_question_9(original_field_count, llm_field_count)

    princeton_acceptance = question_10(cursor)
    print_result(
        10,
        "Princeton Fall 2026 acceptance percentage: ",
        princeton_acceptance,
        ".2f",
        "%",
    )

    princeton_average_gpa = question_11(cursor)
    print_result(
        11,
        "Average GPA of accepted Princeton Fall 2026 applicants: ",
        princeton_average_gpa,
        ".2f",
    )


def main():
    """Execute and display the GradCafe raw SQL analysis."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            run_analysis(cursor)


if __name__ == "__main__":
    main()
