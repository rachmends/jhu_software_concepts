"""Analyze GradCafe applicant data using SQLAlchemy ORM queries."""

from sqlalchemy import and_, func, or_, select
from sqlalchemy.sql.functions import count

from models import Applicant, SessionLocal


def fall_2026_applicant_count(session):
    """Return the number of applicant entries for Fall 2026."""
    statement = (
        select(count())
        .select_from(Applicant)
        .where(
            func.lower(func.trim(Applicant.term)) == "fall 2026"
        )
    )
    return session.scalar(statement)


def american_fall_2026_average_gpa(session):
    """Return the average GPA of American Fall 2026 applicants."""
    statement = (
        select(func.avg(Applicant.gpa))
        .where(
            and_(
                func.lower(func.trim(Applicant.term)) == "fall 2026",
                func.lower(
                    func.trim(Applicant.us_or_international)
                ) == "american",
                Applicant.gpa.is_not(None),
            )
        )
    )
    return session.scalar(statement)


def fall_2025_acceptance_percentage(session):
    """Return the acceptance percentage for Fall 2025 entries."""
    total_statement = (
        select(count())
        .select_from(Applicant)
        .where(
            func.lower(func.trim(Applicant.term)) == "fall 2025"
        )
    )

    accepted_statement = (
        select(count())
        .select_from(Applicant)
        .where(
            and_(
                func.lower(func.trim(Applicant.term)) == "fall 2025",
                func.lower(
                    func.trim(Applicant.status)
                ).like("accept%"),
            )
        )
    )

    total = session.scalar(total_statement)
    accepted = session.scalar(accepted_statement)

    return 100.0 * accepted / total if total else 0.0


def doctoral_degree_condition():
    """Return the SQL condition identifying doctoral degrees."""
    return or_(
        func.lower(func.trim(Applicant.degree)).in_(
            ["phd", "ph.d.", "ph.d"]
        ),
        func.lower(Applicant.degree).like("%doctor%"),
    )


def original_university_condition():
    """Return the university condition used for Question 8."""
    return or_(
        func.lower(Applicant.program).like("%georgetown%"),
        func.lower(Applicant.program).like(
            "%massachusetts institute of technology%"
        ),
        func.lower(Applicant.program).like("%mit%"),
        func.lower(Applicant.program).like("%stanford%"),
        func.lower(Applicant.program).like("%carnegie mellon%"),
    )


def original_field_count(session):
    """Return the original-field applicant count for Question 8."""
    statement = (
        select(count())
        .select_from(Applicant)
        .where(
            and_(
                func.lower(func.trim(Applicant.term)) == "fall 2026",
                func.lower(
                    func.trim(Applicant.status)
                ).like("accept%"),
                doctoral_degree_condition(),
                func.lower(Applicant.program).like(
                    "%computer science%"
                ),
                original_university_condition(),
            )
        )
    )
    return session.scalar(statement)


def llm_university_condition():
    """Return the LLM university condition used for Question 9."""
    return or_(
        func.lower(Applicant.llm_generated_university).like(
            "%georgetown%"
        ),
        func.lower(Applicant.llm_generated_university).like(
            "%massachusetts institute of technology%"
        ),
        func.lower(Applicant.llm_generated_university) == "mit",
        func.lower(Applicant.llm_generated_university).like(
            "%stanford%"
        ),
        func.lower(Applicant.llm_generated_university).like(
            "%carnegie mellon%"
        ),
    )


def llm_field_count(session):
    """Return the LLM-field applicant count for Question 9."""
    statement = (
        select(count())
        .select_from(Applicant)
        .where(
            and_(
                func.lower(func.trim(Applicant.term)) == "fall 2026",
                func.lower(
                    func.trim(Applicant.status)
                ).like("accept%"),
                doctoral_degree_condition(),
                func.lower(
                    Applicant.llm_generated_program
                ).like("%computer science%"),
                llm_university_condition(),
            )
        )
    )
    return session.scalar(statement)


def princeton_condition():
    """Return the SQL condition identifying Princeton entries."""
    return func.lower(Applicant.program).like("%princeton%")


def princeton_acceptance_percentage(session):
    """Return the Fall 2026 Princeton acceptance percentage."""
    total_statement = (
        select(count())
        .select_from(Applicant)
        .where(
            and_(
                func.lower(func.trim(Applicant.term)) == "fall 2026",
                princeton_condition(),
            )
        )
    )

    accepted_statement = (
        select(count())
        .select_from(Applicant)
        .where(
            and_(
                func.lower(func.trim(Applicant.term)) == "fall 2026",
                princeton_condition(),
                func.lower(
                    func.trim(Applicant.status)
                ).like("accept%"),
            )
        )
    )

    total = session.scalar(total_statement)
    accepted = session.scalar(accepted_statement)

    return 100.0 * accepted / total if total else 0.0


def accepted_princeton_average_gpa(session):
    """Return average GPA for accepted Princeton Fall 2026 applicants."""
    statement = (
        select(func.avg(Applicant.gpa))
        .where(
            and_(
                func.lower(func.trim(Applicant.term)) == "fall 2026",
                func.lower(Applicant.program).like("%princeton%"),
                func.lower(
                    func.trim(Applicant.status)
                ).like("accept%"),
                Applicant.gpa.is_not(None),
            )
        )
    )
    return session.scalar(statement)


def main():
    """Run the ORM analysis queries and print their results."""
    with SessionLocal() as session:
        fall_2026_count = fall_2026_applicant_count(session)
        american_average_gpa = american_fall_2026_average_gpa(session)
        fall_2025_percentage = fall_2025_acceptance_percentage(session)
        original_count = original_field_count(session)
        llm_count = llm_field_count(session)
        difference = llm_count - original_count
        princeton_percentage = princeton_acceptance_percentage(session)
        princeton_average_gpa = accepted_princeton_average_gpa(session)

        print("Question 1")
        print(f"Fall 2026 applicant count: {fall_2026_count}")
        print()

        print("Question 4")
        print(
            "Average GPA of American Fall 2026 applicants: "
            f"{american_average_gpa:.2f}"
        )
        print()

        print("Question 5")
        print(
            "Fall 2025 acceptance percentage: "
            f"{fall_2025_percentage:.2f}%"
        )
        print()

        print("Question 8")
        print(f"Original-field count: {original_count}")
        print()

        print("Question 9")
        print(f"Original-field count: {original_count}")
        print(f"LLM-field count: {llm_count}")
        print(f"Difference: {difference:+d}")
        print()

        print("Question 10")
        print(
            "Princeton Fall 2026 acceptance percentage: "
            f"{princeton_percentage:.2f}%"
        )
        print()

        print("Question 11")
        print(
            "Average GPA of accepted Princeton Fall 2026 applicants: "
            f"{princeton_average_gpa:.2f}"
        )
        print()


if __name__ == "__main__":
    main()
