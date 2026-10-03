"""Analyze GradCafe applicant data using PostgreSQL queries."""

import psycopg
from psycopg import sql

from db_config import get_database_config


def get_connection():
    """Create a PostgreSQL connection using environment configuration."""
    return psycopg.connect(**get_database_config())


MAX_QUERY_LIMIT = 100


def clamp_limit(limit):
    """Clamp a query result limit to the permitted range of 1 through 100."""
    return max(1, min(int(limit), MAX_QUERY_LIMIT))


def fetch_one(cursor, statement, params=(), limit=MAX_QUERY_LIMIT):
    """Execute a bounded parameterized query and return its first result row."""
    bounded_limit = clamp_limit(limit)
    cursor.execute(statement, (*params, bounded_limit))
    return cursor.fetchone()


def print_result(question, label, value, format_spec="", suffix=""):
    """Print a formatted analysis result."""
    print(f"Question {question}")
    formatted_value = format(value, format_spec) if format_spec else value
    print(f"{label}{formatted_value}{suffix}")
    print()


def question_1(cursor, limit=MAX_QUERY_LIMIT):
    """Return the number of Fall 2026 applicant entries."""
    statement = sql.SQL("""
        SELECT COUNT(*)
        FROM {}
        WHERE LOWER(TRIM({})) = %s
        LIMIT %s
    """).format(
        sql.Identifier("applicants"),
        sql.Identifier("term"),
    )
    row = fetch_one(cursor, statement, ("fall 2026",), limit)
    return row[0]


def question_2(cursor, limit=MAX_QUERY_LIMIT):
    """Return the percentage of classified applicants who are international."""
    statement = sql.SQL("""
        SELECT
            100.0 *
            COUNT(*) FILTER (
                WHERE LOWER(TRIM({})) NOT IN (%s, %s)
            )
            /
            NULLIF(
                COUNT(*) FILTER (
                    WHERE {} IS NOT NULL
                      AND TRIM({}) <> %s
                ),
                0
            )
        FROM {}
        LIMIT %s
    """).format(
        sql.Identifier("us_or_international"),
        sql.Identifier("us_or_international"),
        sql.Identifier("us_or_international"),
        sql.Identifier("applicants"),
    )
    params = ("american", "other", "")
    row = fetch_one(cursor, statement, params, limit)
    return row[0]


def question_3(cursor, limit=MAX_QUERY_LIMIT):
    """Return average GPA and valid GRE metrics."""
    statement = sql.SQL("""
        SELECT
            AVG({}),
            AVG({}) FILTER (
                WHERE {} BETWEEN %s AND %s
            ),
            AVG({}) FILTER (
                WHERE {} BETWEEN %s AND %s
            ),
            AVG({}) FILTER (
                WHERE {} BETWEEN %s AND %s
            )
        FROM {}
        LIMIT %s
    """).format(
        sql.Identifier("gpa"),
        sql.Identifier("gre"),
        sql.Identifier("gre"),
        sql.Identifier("gre_v"),
        sql.Identifier("gre_v"),
        sql.Identifier("gre_aw"),
        sql.Identifier("gre_aw"),
        sql.Identifier("applicants"),
    )
    params = (130, 170, 130, 170, 0.0, 6.0)
    return fetch_one(cursor, statement, params, limit)


def question_4(cursor, limit=MAX_QUERY_LIMIT):
    """Return average GPA of American Fall 2026 applicants."""
    statement = sql.SQL("""
        SELECT AVG({})
        FROM {}
        WHERE LOWER(TRIM({})) = %s
          AND LOWER(TRIM({})) = %s
          AND {} IS NOT NULL
        LIMIT %s
    """).format(
        sql.Identifier("gpa"),
        sql.Identifier("applicants"),
        sql.Identifier("term"),
        sql.Identifier("us_or_international"),
        sql.Identifier("gpa"),
    )
    params = ("fall 2026", "american")
    row = fetch_one(cursor, statement, params, limit)
    return row[0]


def question_5(cursor, limit=MAX_QUERY_LIMIT):
    """Return the Fall 2025 acceptance percentage."""
    statement = sql.SQL("""
        SELECT
            100.0 *
            COUNT(*) FILTER (
                WHERE LOWER(TRIM({})) LIKE %s
            )
            /
            NULLIF(COUNT(*), 0)
        FROM {}
        WHERE LOWER(TRIM({})) = %s
        LIMIT %s
    """).format(
        sql.Identifier("status"),
        sql.Identifier("applicants"),
        sql.Identifier("term"),
    )
    params = ("accept%", "fall 2025")
    row = fetch_one(cursor, statement, params, limit)
    return row[0]


def question_6(cursor, limit=MAX_QUERY_LIMIT):
    """Return average GPA of accepted Fall 2026 applicants."""
    statement = sql.SQL("""
        SELECT AVG({})
        FROM {}
        WHERE LOWER(TRIM({})) = %s
          AND LOWER(TRIM({})) LIKE %s
          AND {} IS NOT NULL
        LIMIT %s
    """).format(
        sql.Identifier("gpa"),
        sql.Identifier("applicants"),
        sql.Identifier("term"),
        sql.Identifier("status"),
        sql.Identifier("gpa"),
    )
    params = ("fall 2026", "accept%")
    row = fetch_one(cursor, statement, params, limit)
    return row[0]


def question_7(cursor, limit=MAX_QUERY_LIMIT):
    """Return the Johns Hopkins master's Computer Science applicant count."""
    statement = sql.SQL("""
        SELECT COUNT(*)
        FROM {}
        WHERE (
                LOWER({}) LIKE %s
                OR LOWER({}) LIKE %s
              )
          AND LOWER({}) LIKE %s
          AND (
                LOWER(TRIM({})) IN (
                    %s, %s, %s, %s, %s, %s, %s
                )
                OR LOWER({}) LIKE %s
              )
        LIMIT %s
    """).format(
        sql.Identifier("applicants"),
        sql.Identifier("program"),
        sql.Identifier("program"),
        sql.Identifier("program"),
        sql.Identifier("degree"),
        sql.Identifier("degree"),
    )
    params = (
        "%johns hopkins%",
        "%jhu%",
        "%computer science%",
        "ms",
        "m.s.",
        "msc",
        "m.sc.",
        "master",
        "masters",
        "master's",
        "%master%",
    )
    row = fetch_one(cursor, statement, params, limit)
    return row[0]


def question_8(cursor, limit=MAX_QUERY_LIMIT):
    """Return the original-field count for accepted Fall 2026 CS PhDs."""
    statement = sql.SQL("""
        SELECT COUNT(*)
        FROM {}
        WHERE LOWER(TRIM({})) = %s
          AND LOWER(TRIM({})) LIKE %s
          AND (
                LOWER(TRIM({})) IN (%s, %s, %s)
                OR LOWER({}) LIKE %s
              )
          AND LOWER({}) LIKE %s
          AND (
                LOWER({}) LIKE %s
                OR LOWER({}) LIKE %s
                OR LOWER({}) LIKE %s
                OR LOWER({}) LIKE %s
                OR LOWER({}) LIKE %s
              )
        LIMIT %s
    """).format(
        sql.Identifier("applicants"),
        sql.Identifier("term"),
        sql.Identifier("status"),
        sql.Identifier("degree"),
        sql.Identifier("degree"),
        sql.Identifier("program"),
        sql.Identifier("program"),
        sql.Identifier("program"),
        sql.Identifier("program"),
        sql.Identifier("program"),
        sql.Identifier("program"),
    )
    params = (
        "fall 2026",
        "accept%",
        "phd",
        "ph.d.",
        "ph.d",
        "%doctor%",
        "%computer science%",
        "%georgetown%",
        "%massachusetts institute of technology%",
        "%mit%",
        "%stanford%",
        "%carnegie mellon%",
    )
    row = fetch_one(cursor, statement, params, limit)
    return row[0]


def question_9(cursor, limit=MAX_QUERY_LIMIT):
    """Return the LLM-field count for accepted Fall 2026 CS PhDs."""
    statement = sql.SQL("""
        SELECT COUNT(*)
        FROM {}
        WHERE LOWER(TRIM({})) = %s
          AND LOWER(TRIM({})) LIKE %s
          AND (
                LOWER(TRIM({})) IN (%s, %s, %s)
                OR LOWER({}) LIKE %s
              )
          AND LOWER({}) LIKE %s
          AND (
                LOWER({}) LIKE %s
                OR LOWER({}) LIKE %s
                OR LOWER({}) = %s
                OR LOWER({}) LIKE %s
                OR LOWER({}) LIKE %s
              )
        LIMIT %s
    """).format(
        sql.Identifier("applicants"),
        sql.Identifier("term"),
        sql.Identifier("status"),
        sql.Identifier("degree"),
        sql.Identifier("degree"),
        sql.Identifier("llm_generated_program"),
        sql.Identifier("llm_generated_university"),
        sql.Identifier("llm_generated_university"),
        sql.Identifier("llm_generated_university"),
        sql.Identifier("llm_generated_university"),
        sql.Identifier("llm_generated_university"),
    )
    params = (
        "fall 2026",
        "accept%",
        "phd",
        "ph.d.",
        "ph.d",
        "%doctor%",
        "%computer science%",
        "%georgetown%",
        "%massachusetts institute of technology%",
        "mit",
        "%stanford%",
        "%carnegie mellon%",
    )
    row = fetch_one(cursor, statement, params, limit)
    return row[0]


def question_10(cursor, limit=MAX_QUERY_LIMIT):
    """Return the Princeton Fall 2026 acceptance percentage."""
    statement = sql.SQL("""
        SELECT
            100.0 *
            COUNT(*) FILTER (
                WHERE LOWER(TRIM({})) LIKE %s
            )
            /
            NULLIF(COUNT(*), 0)
        FROM {}
        WHERE LOWER(TRIM({})) = %s
          AND LOWER({}) LIKE %s
        LIMIT %s
    """).format(
        sql.Identifier("status"),
        sql.Identifier("applicants"),
        sql.Identifier("term"),
        sql.Identifier("program"),
    )
    params = ("accept%", "fall 2026", "%princeton%")
    row = fetch_one(cursor, statement, params, limit)
    return row[0]


def question_11(cursor, limit=MAX_QUERY_LIMIT):
    """Return average GPA of accepted Princeton Fall 2026 applicants."""
    statement = sql.SQL("""
        SELECT AVG({})
        FROM {}
        WHERE LOWER(TRIM({})) = %s
          AND LOWER({}) LIKE %s
          AND LOWER(TRIM({})) LIKE %s
          AND {} IS NOT NULL
        LIMIT %s
    """).format(
        sql.Identifier("gpa"),
        sql.Identifier("applicants"),
        sql.Identifier("term"),
        sql.Identifier("program"),
        sql.Identifier("status"),
        sql.Identifier("gpa"),
    )
    params = ("fall 2026", "%princeton%", "accept%")
    row = fetch_one(cursor, statement, params, limit)
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
