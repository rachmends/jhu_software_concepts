import os
from datetime import date

from sqlalchemy import create_engine, Float, Integer, Text, Date
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


# ---------------------------------------------------------
# Database connection
# ---------------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    db_name = os.getenv("DB_NAME")
    db_user = os.getenv("DB_USER")

    if not db_name or not db_user:
        raise RuntimeError(
            "Database connection information is missing. "
            "Set DATABASE_URL or DB_NAME and DB_USER "
            "as environment variables."
        )

    DATABASE_URL = f"postgresql+psycopg://{db_user}@/{db_name}"

engine = create_engine(DATABASE_URL)


# ---------------------------------------------------------
# SQLAlchemy base class
# ---------------------------------------------------------

class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------
# Applicant model
# ---------------------------------------------------------

class Applicant(Base):
    __tablename__ = "applicants"

    p_id: Mapped[int] = mapped_column(Integer, primary_key=True)

    program: Mapped[str | None] = mapped_column(Text)
    comments: Mapped[str | None] = mapped_column(Text)
    date_added: Mapped[date | None] = mapped_column(Date)
    url: Mapped[str | None] = mapped_column(Text)
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

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False
)