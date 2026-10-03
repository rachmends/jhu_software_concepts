"""Provide PostgreSQL configuration from environment variables."""

import os


def get_database_config():
    """Return validated PostgreSQL connection settings."""
    config = {
        "host": os.getenv("DB_HOST"),
        "port": os.getenv("DB_PORT"),
        "dbname": os.getenv("DB_NAME"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
    }

    missing = [
        name
        for name, value in config.items()
        if not value
    ]

    if missing:
        raise RuntimeError(
            "Database connection information is missing: "
            + ", ".join(missing)
            + "."
        )

    return config
