from sqlalchemy import select, func, and_, or_

from models import Applicant, SessionLocal


def main():
    with SessionLocal() as session:

        # ---------------------------------------------------------
        # Question 1
        # How many entries are for Fall 2026?
        # ---------------------------------------------------------

        q1_statement = (
            select(func.count())
            .select_from(Applicant)
            .where(
                func.lower(func.trim(Applicant.term)) == "fall 2026"
            )
        )

        q1 = session.scalar(q1_statement)

        print("Question 1")
        print(f"Fall 2026 applicant count: {q1}")
        print()


        # ---------------------------------------------------------
        # Question 4
        # Average GPA of American Fall 2026 applicants.
        # ---------------------------------------------------------

        q4_statement = (
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

        q4 = session.scalar(q4_statement)

        print("Question 4")
        print(
            "Average GPA of American Fall 2026 applicants: "
            f"{q4:.2f}"
        )
        print()


        # ---------------------------------------------------------
        # Question 5
        # Percentage of Fall 2025 entries that are acceptances.
        # ---------------------------------------------------------

        q5_total_statement = (
            select(func.count())
            .select_from(Applicant)
            .where(
                func.lower(func.trim(Applicant.term)) == "fall 2025"
            )
        )

        q5_accepted_statement = (
            select(func.count())
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

        q5_total = session.scalar(q5_total_statement)
        q5_accepted = session.scalar(q5_accepted_statement)

        q5 = (
            100.0 * q5_accepted / q5_total
            if q5_total
            else 0.0
        )

        print("Question 5")
        print(f"Fall 2025 acceptance percentage: {q5:.2f}%")
        print()


        # ---------------------------------------------------------
        # Question 8
        # Original-field count:
        # Accepted Fall 2026 CS PhD applicants at Georgetown,
        # MIT, Stanford, or Carnegie Mellon.
        # ---------------------------------------------------------

        degree_condition = or_(
            func.lower(func.trim(Applicant.degree)).in_(
                ["phd", "ph.d.", "ph.d"]
            ),
            func.lower(Applicant.degree).like("%doctor%"),
        )

        original_university_condition = or_(
            func.lower(Applicant.program).like("%georgetown%"),
            func.lower(Applicant.program).like(
                "%massachusetts institute of technology%"
            ),
            func.lower(Applicant.program).like("%mit%"),
            func.lower(Applicant.program).like("%stanford%"),
            func.lower(Applicant.program).like("%carnegie mellon%"),
        )

        q8_statement = (
            select(func.count())
            .select_from(Applicant)
            .where(
                and_(
                    func.lower(func.trim(Applicant.term))
                    == "fall 2026",
                    func.lower(func.trim(Applicant.status))
                    .like("accept%"),
                    degree_condition,
                    func.lower(Applicant.program)
                    .like("%computer science%"),
                    original_university_condition,
                )
            )
        )

        q8 = session.scalar(q8_statement)

        print("Question 8")
        print(f"Original-field count: {q8}")
        print()


        # ---------------------------------------------------------
        # Question 9
        # Repeat Question 8 using LLM-generated university/program.
        # ---------------------------------------------------------

        llm_university_condition = or_(
            func.lower(Applicant.llm_generated_university)
            .like("%georgetown%"),
            func.lower(Applicant.llm_generated_university)
            .like("%massachusetts institute of technology%"),
            func.lower(Applicant.llm_generated_university) == "mit",
            func.lower(Applicant.llm_generated_university)
            .like("%stanford%"),
            func.lower(Applicant.llm_generated_university)
            .like("%carnegie mellon%"),
        )

        q9_statement = (
            select(func.count())
            .select_from(Applicant)
            .where(
                and_(
                    func.lower(func.trim(Applicant.term))
                    == "fall 2026",
                    func.lower(func.trim(Applicant.status))
                    .like("accept%"),
                    degree_condition,
                    func.lower(Applicant.llm_generated_program)
                    .like("%computer science%"),
                    llm_university_condition,
                )
            )
        )

        q9 = session.scalar(q9_statement)
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

        princeton_condition = (
            func.lower(Applicant.program).like("%princeton%")
        )

        q10_total_statement = (
            select(func.count())
            .select_from(Applicant)
            .where(
                and_(
                    func.lower(func.trim(Applicant.term))
                    == "fall 2026",
                    princeton_condition,
                )
            )
        )

        q10_accepted_statement = (
            select(func.count())
            .select_from(Applicant)
            .where(
                and_(
                    func.lower(func.trim(Applicant.term))
                    == "fall 2026",
                    princeton_condition,
                    func.lower(func.trim(Applicant.status))
                    .like("accept%"),
                )
            )
        )

        q10_total = session.scalar(q10_total_statement)
        q10_accepted = session.scalar(q10_accepted_statement)

        q10 = (
            100.0 * q10_accepted / q10_total
            if q10_total
            else 0.0
        )

        print("Question 10")
        print(
            "Princeton Fall 2026 acceptance percentage: "
            f"{q10:.2f}%"
        )
        print()


        ## USED FOR MY READ ME, LOL ##
        # ---------------------------------------------------------
        # Question 11
        # Average GPA of accepted Princeton University
        # Fall 2026 applicants who reported a GPA.
        # ---------------------------------------------------------

        q11_statement = (
            select(func.avg(Applicant.gpa))
            .where(
                and_(
                    func.lower(func.trim(Applicant.term)) == "fall 2026",
                    func.lower(Applicant.program).like("%princeton%"),
                    func.lower(func.trim(Applicant.status)).like("accept%"),
                    Applicant.gpa.is_not(None),
                )
            )
        )

        q11 = session.scalar(q11_statement)

        print("Question 11")
        print(
            "Average GPA of accepted Princeton Fall 2026 applicants: "
            f"{q11:.2f}"
        )
        print()

if __name__ == "__main__":
    main()