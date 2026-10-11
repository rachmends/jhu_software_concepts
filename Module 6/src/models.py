"""Define SQLAlchemy database models for GradCafe applicant data."""

import os
from datetime import date

from sqlalchemy import create_engine, Float, Integer, Text, Date
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from db_config import get_database_config


# ---------------------------------------------------------
# Database connection
# ---------------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    database_config = get_database_config()
    DATABASE_URL = (
        "postgresql+psycopg://"
        f"{database_config['user']}:{database_config['password']}"
        f"@{database_config['host']}:{database_config['port']}"
        f"/{database_config['dbname']}"
    )


engine = create_engine(DATABASE_URL)


# ---------------------------------------------------------
# SQLAlchemy base class
# ---------------------------------------------------------

class Base(DeclarativeBase):
    """Base class for SQLAlchemy declarative models."""

    @classmethod
    def column_names(cls):
        """Return the names of columns defined for the model."""
        return [column.name for column in cls.__table__.columns]

    def to_dict(self):
        """Return the model instance as a dictionary."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }


# ---------------------------------------------------------
# Applicant model
# ---------------------------------------------------------

class Applicant(Base):
    """Represent a GradCafe applicant database record."""

    __tablename__ = "applicants"

    p_id: Mapped[int] = mapped_column(Integer, primary_key=True)

    program: Mapped[str | None] = mapped_column(Text)
    comments: Mapped[str | None] = mapped_column(Text)
    date_added: Mapped[date | None] = mapped_column(Date)
    url: Mapped[str | None] = mapped_column(Text, unique=True)
    status: Mapped[str | None] = mapped_column(Text)
    term: Mapped[str | None] = mapped_column(Text)
    us_or_international: Mapped[str | None] = mapped_column(Text)

    gpa: Mapped[float | None] = mapped_column(Float)
    gre: Mapped[float | None] = mapped_column(Float)
    gre_v: Mapped[float | None] = mapped_column(Float)
    gre_aw: Mapped[float | None] = mapped_column(Float)

    degree: Mapped[str | None] = mapped_column(Text)

    llm_generated_program: Mapped[str | None] = mapped_column(Text)
    llm_generated_university: Mapped[str | None] = mapped_column(Text)


# ---------------------------------------------------------
# Session configuration
# ---------------------------------------------------------

SESSION_LOCAL = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False
)
