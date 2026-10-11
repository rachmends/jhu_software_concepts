"""ETL operations executed by the RabbitMQ worker."""

import os
from pathlib import Path
from datetime import datetime, timezone

import psycopg

from db_config import get_database_config

from load_data import insert_applicant, main as load_applicants
from worker.etl.incremental_scraper import collect_new_records


def ingest_prepared_data():
    """Atomically ingest prepared records and advance the watermark."""
    data_dir = Path(os.environ.get("DATA_DIR", "/app/data"))
    cleaned_file = data_dir / "llm_extend_applicant_data.json"

    if not cleaned_file.is_file():
        raise FileNotFoundError(
            f"Prepared applicant dataset not found: {cleaned_file}"
        )

    previous_directory = Path.cwd()

    try:
        os.chdir(data_dir)

        with psycopg.connect(**get_database_config()) as connection:
            load_applicants(connection=connection)

            processed_at = datetime.now(timezone.utc)

            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO ingestion_watermarks
                        (source, last_processed_at, updated_at)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (source)
                    DO UPDATE SET
                        last_processed_at = EXCLUDED.last_processed_at,
                        updated_at = EXCLUDED.updated_at
                    """,
                    (
                        "gradcafe_prepared_json",
                        processed_at,
                        processed_at,
                    ),
                )

            connection.commit()

    finally:
        os.chdir(previous_directory)

    return {"status": "completed"}

def recompute_analytics():
    """Return the status of the analytics recomputation helper.

    The RabbitMQ worker's handle_recompute_analytics function
    persists refreshed results in the analytics_summary table.
    """
    return {"status": "ready"}



def handle_scrape_new_data(conn, payload):
    """Insert newly scraped GradCafe records and update the watermark.

    Args:
        conn: Caller-managed PostgreSQL connection.
        payload (dict): Optional scraping configuration, including
            ``max_pages``.

    Returns:
        dict: Counts of collected and inserted applicant records.

    Raises:
        ValueError: If a collected record lacks its unique URL.
        RuntimeError: If GradCafe blocks collection or parsing fails.

    Notes:
        The caller owns the transaction and must commit only after
        this function returns successfully.
    """
    source_name = "gradcafe_live"

    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT last_processed_url
            FROM ingestion_watermarks
            WHERE source = %s
            """,
            (source_name,),
        )
        watermark = cursor.fetchone()

        cursor.execute(
            "SELECT url FROM applicants WHERE url IS NOT NULL"
        )
        known_urls = [{"url": row[0]} for row in cursor.fetchall()]

    records = collect_new_records(
        existing_records=known_urls,
        max_pages=payload.get("max_pages"),
    )

    inserted = 0

    with conn.cursor() as cursor:
        for record in records:
            if not record.get("url"):
                raise ValueError("Scraped record is missing its URL")

            insert_applicant(cursor, record)
            inserted += cursor.rowcount

        processed_at = datetime.now(timezone.utc)
        latest_url = (
            records[0]["url"]
            if inserted > 0
            else (watermark[0] if watermark else None)
        )

        cursor.execute(
            """
            INSERT INTO ingestion_watermarks
                (source, last_processed_at,
                 last_processed_url, updated_at)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (source)
            DO UPDATE SET
                last_processed_at = EXCLUDED.last_processed_at,
                last_processed_url = EXCLUDED.last_processed_url,
                updated_at = EXCLUDED.updated_at
            """,
            (source_name, processed_at, latest_url, processed_at),
        )

    return {"inserted": inserted, "collected": len(records)}


def handle_recompute_analytics(conn, _payload):
    """Calculate current applicant statistics from PostgreSQL.

    Args:
        conn: Caller-managed PostgreSQL connection.
        payload (dict): Reserved for future analytics options.

    Returns:
        dict: Total applicants, mean GPA, mean quantitative GRE
        score, and accepted applicant count.

    Notes:
        This function does not commit or close the connection.
    """
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                COUNT(*),
                AVG(gpa),
                AVG(gre) FILTER (WHERE gre BETWEEN 130 AND 170),
                COUNT(*) FILTER (
                    WHERE status ILIKE 'accepted%'
                )
            FROM applicants
            """
        )
        total, average_gpa, average_gre, accepted = cursor.fetchone()

    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO analytics_summary (
                id,
                total_applicants,
                average_gpa,
                average_gre,
                accepted_count,
                updated_at
            )
            VALUES (1, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (id) DO UPDATE SET
                total_applicants = EXCLUDED.total_applicants,
                average_gpa = EXCLUDED.average_gpa,
                average_gre = EXCLUDED.average_gre,
                accepted_count = EXCLUDED.accepted_count,
                updated_at = CURRENT_TIMESTAMP
            """,
            (total, average_gpa, average_gre, accepted),
        )

    return {
        "total_applicants": total,
        "average_gpa": (
            float(average_gpa) if average_gpa is not None else None
        ),
        "average_gre": (
            float(average_gre) if average_gre is not None else None
        ),
        "accepted_count": accepted,
    }
