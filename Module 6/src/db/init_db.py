"""Initialize the PostgreSQL schema for Module 6."""

from sqlalchemy import text
from models import Base, engine


def initialize_database():
    """Create application tables and ingestion tracking."""
    Base.metadata.create_all(bind=engine)

    with engine.begin() as connection:
        connection.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS
                applicants_url_unique_idx
            ON applicants (url)
        """))

        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS ingestion_watermarks (
                source TEXT PRIMARY KEY,
                last_processed_at TIMESTAMPTZ,
                last_processed_url TEXT,
                updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            )
        """))

    with engine.begin() as connection:
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS analytics_summary (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                total_applicants BIGINT NOT NULL,
                average_gpa DOUBLE PRECISION,
                average_gre DOUBLE PRECISION,
                accepted_count BIGINT NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL
                    DEFAULT CURRENT_TIMESTAMP
            )
        """))

    print("Database schema initialized successfully.")


if __name__ == "__main__":
    initialize_database()
