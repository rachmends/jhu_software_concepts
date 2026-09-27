import os
import psycopg


def get_connection():
    """
    Create a PostgreSQL connection using environment configuration.

    Reads ``DB_NAME`` and ``DB_USER`` from the environment and uses them to
    establish the psycopg connection used by the raw SQL analysis.

    Returns:
        psycopg.Connection: Open PostgreSQL connection.

    Raises:
        RuntimeError: If ``DB_NAME`` or ``DB_USER`` is not configured.
    """
    db_name = os.getenv("DB_NAME")
    db_user = os.getenv("DB_USER")

    if not db_name or not db_user:
        raise RuntimeError(
            "Database connection information is missing. "
            "Set DB_NAME and DB_USER as environment variables."
        )

    return psycopg.connect(
        dbname=db_name,
        user=db_user
    )


def main():
    """
    Execute and display the GradCafe raw SQL analysis.

    Connects to PostgreSQL and executes the eleven analysis questions used by
    the GradCafe project. The analysis includes applicant counts, nationality
    percentages, GPA and GRE averages, acceptance percentages, Johns Hopkins
    Computer Science applicant counts, comparisons between original and
    LLM-generated fields, and the two Princeton Fall 2026 analyses.

    Percentage and average results are formatted for readable terminal output.
    PostgreSQL aggregate operations ignore missing values where appropriate,
    while GRE calculations restrict values to the valid ranges used by the
    analysis.
    """
    with get_connection() as conn:
        with conn.cursor() as cursor:

            # ---------------------------------------------------------
            # Question 1
            # How many entries are for Fall 2026?
            # ---------------------------------------------------------

            cursor.execute("""
                SELECT COUNT(*)
                FROM applicants
                WHERE LOWER(TRIM(term)) = 'fall 2026';
            """)

            q1 = cursor.fetchone()[0]

            print("Question 1")
            print(f"Fall 2026 applicant count: {q1}")
            print()


            # ---------------------------------------------------------
            # Question 2
            # Percentage of usable nationality classifications
            # that are international.
            #
            # American and Other are not international.
            # Missing/blank values are excluded from denominator.
            # ---------------------------------------------------------

            cursor.execute("""
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
            """)

            q2 = cursor.fetchone()[0]

            print("Question 2")
            print(f"Percent international: {q2:.2f}%")
            print()


            # ---------------------------------------------------------
            # Question 3
            # Average GPA and GRE metrics.
            #
            # PostgreSQL AVG ignores NULL values, so each metric is
            # averaged independently as required.
            # ---------------------------------------------------------

            cursor.execute("""
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
            """)

            q3_gpa, q3_gre, q3_gre_v, q3_gre_aw = cursor.fetchone()

            print("Question 3")
            print(f"Average GPA: {q3_gpa:.2f}")
            print(f"Average GRE Quantitative: {q3_gre:.2f}")
            print(f"Average GRE Verbal: {q3_gre_v:.2f}")
            print(f"Average GRE Analytical Writing: {q3_gre_aw:.2f}")
            print()


            # ---------------------------------------------------------
            # Question 4
            # Average GPA of American Fall 2026 applicants.
            # ---------------------------------------------------------

            cursor.execute("""
                SELECT AVG(gpa)
                FROM applicants
                WHERE LOWER(TRIM(term)) = 'fall 2026'
                  AND LOWER(TRIM(us_or_international)) = 'american'
                  AND gpa IS NOT NULL;
            """)

            q4 = cursor.fetchone()[0]

            print("Question 4")
            print(f"Average GPA of American Fall 2026 applicants: {q4:.2f}")
            print()


            # ---------------------------------------------------------
            # Question 5
            # Percentage of Fall 2025 entries that are acceptances.
            # ---------------------------------------------------------

            cursor.execute("""
                SELECT
                    100.0 *
                    COUNT(*) FILTER (
                        WHERE LOWER(TRIM(status)) LIKE 'accept%'
                    )
                    /
                    NULLIF(COUNT(*), 0)
                FROM applicants
                WHERE LOWER(TRIM(term)) = 'fall 2025';
            """)

            q5 = cursor.fetchone()[0]

            print("Question 5")
            print(f"Fall 2025 acceptance percentage: {q5:.2f}%")
            print()


            # ---------------------------------------------------------
            # Question 6
            # Average GPA of accepted Fall 2026 applicants.
            # ---------------------------------------------------------

            cursor.execute("""
                SELECT AVG(gpa)
                FROM applicants
                WHERE LOWER(TRIM(term)) = 'fall 2026'
                  AND LOWER(TRIM(status)) LIKE 'accept%'
                  AND gpa IS NOT NULL;
            """)

            q6 = cursor.fetchone()[0]

            print("Question 6")
            print(f"Average GPA of accepted Fall 2026 applicants: {q6:.2f}")
            print()


            # ---------------------------------------------------------
            # Question 7
            # Johns Hopkins master's Computer Science entries.
            #
            # The database program field contains the original
            # university + original program information.
            # ---------------------------------------------------------

            cursor.execute("""
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
            """)

            q7 = cursor.fetchone()[0]

            print("Question 7")
            print(
                "Johns Hopkins master's Computer Science "
                f"applicant count: {q7}"
            )
            print()


            # ---------------------------------------------------------
            # Question 8
            # Original-field count:
            # Accepted Fall 2026 CS PhD applicants at Georgetown,
            # MIT, Stanford, or Carnegie Mellon.
            # ---------------------------------------------------------

            cursor.execute("""
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
            """)

            q8 = cursor.fetchone()[0]

            print("Question 8")
            print(f"Original-field count: {q8}")
            print()


            # ---------------------------------------------------------
            # Question 9
            # Same analysis using LLM-generated university/program.
            # ---------------------------------------------------------

            cursor.execute("""
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
            """)

            q9 = cursor.fetchone()[0]

            difference = q9 - q8

            print("Question 9")
            print(f"Original-field count: {q8}")
            print(f"LLM-field count: {q9}")
            print(f"Difference: {difference:+d}")
            print()

            # ---------------------------------------------------------
            # Question 10
            # Among Princeton University Fall 2026 entries,
            # what percentage are acceptances?
            # ---------------------------------------------------------

            cursor.execute("""
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
            """)

            q10 = cursor.fetchone()[0]

            print("Question 10")
            print(
                "Princeton Fall 2026 acceptance percentage: "
                f"{q10:.2f}%"
            )
            print()
            
            # ---------------------------------------------------------
            # Question 11
            # Average GPA of accepted Princeton University
            # Fall 2026 applicants who reported a GPA.
            # ---------------------------------------------------------

            cursor.execute("""
                SELECT AVG(gpa)
                FROM applicants
                WHERE LOWER(TRIM(term)) = 'fall 2026'
                AND LOWER(program) LIKE '%princeton%'
                AND LOWER(TRIM(status)) LIKE 'accept%'
                AND gpa IS NOT NULL;
            """)

            q11 = cursor.fetchone()[0]

            print("Question 11")
            print(
                "Average GPA of accepted Princeton Fall 2026 applicants: "
                f"{q11:.2f}"
            )
            print()

if __name__ == "__main__":
    main()