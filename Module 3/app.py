from flask import Flask, render_template
from sqlalchemy import select, func, and_, or_

from models import Applicant, SessionLocal


app = Flask(__name__)


def get_analysis_results():
    """Retrieve all analysis results from PostgreSQL using SQLAlchemy."""

    with SessionLocal() as session:

        # Question 1
        q1 = session.scalar(
            select(func.count())
            .select_from(Applicant)
            .where(
                func.lower(func.trim(Applicant.term)) == "fall 2026"
            )
        )

        # Question 2
        usable_nationality = session.scalar(
            select(func.count())
            .select_from(Applicant)
            .where(
                Applicant.us_or_international.is_not(None),
                func.trim(Applicant.us_or_international) != "",
            )
        )

        international = session.scalar(
            select(func.count())
            .select_from(Applicant)
            .where(
                Applicant.us_or_international.is_not(None),
                func.trim(Applicant.us_or_international) != "",
                func.lower(
                    func.trim(Applicant.us_or_international)
                ).not_in(["american", "other"]),
            )
        )

        q2 = (
            100.0 * international / usable_nationality
            if usable_nationality
            else 0.0
        )

        # Question 3
        q3_gpa = session.scalar(
            select(func.avg(Applicant.gpa))
        )

        q3_gre = session.scalar(
            select(func.avg(Applicant.gre))
            .where(Applicant.gre.between(130, 170))
        )

        q3_gre_v = session.scalar(
            select(func.avg(Applicant.gre_v))
            .where(Applicant.gre_v.between(130, 170))
        )

        q3_gre_aw = session.scalar(
            select(func.avg(Applicant.gre_aw))
            .where(Applicant.gre_aw.between(0.0, 6.0))
        )

        # Question 4
        q4 = session.scalar(
            select(func.avg(Applicant.gpa))
            .where(
                func.lower(func.trim(Applicant.term)) == "fall 2026",
                func.lower(
                    func.trim(Applicant.us_or_international)
                ) == "american",
                Applicant.gpa.is_not(None),
            )
        )

        # Question 5
        fall_2025_total = session.scalar(
            select(func.count())
            .select_from(Applicant)
            .where(
                func.lower(func.trim(Applicant.term)) == "fall 2025"
            )
        )

        fall_2025_accepted = session.scalar(
            select(func.count())
            .select_from(Applicant)
            .where(
                func.lower(func.trim(Applicant.term)) == "fall 2025",
                func.lower(
                    func.trim(Applicant.status)
                ).like("accept%"),
            )
        )

        q5 = (
            100.0 * fall_2025_accepted / fall_2025_total
            if fall_2025_total
            else 0.0
        )

        # Question 6
        q6 = session.scalar(
            select(func.avg(Applicant.gpa))
            .where(
                func.lower(func.trim(Applicant.term)) == "fall 2026",
                func.lower(
                    func.trim(Applicant.status)
                ).like("accept%"),
                Applicant.gpa.is_not(None),
            )
        )

        # Question 7
        q7 = session.scalar(
            select(func.count())
            .select_from(Applicant)
            .where(
                or_(
                    func.lower(Applicant.program)
                    .like("%johns hopkins%"),
                    func.lower(Applicant.program).like("%jhu%"),
                ),
                func.lower(Applicant.program)
                .like("%computer science%"),
                or_(
                    func.lower(func.trim(Applicant.degree)).in_(
                        [
                            "ms",
                            "m.s.",
                            "msc",
                            "m.sc.",
                            "master",
                            "masters",
                            "master's",
                        ]
                    ),
                    func.lower(Applicant.degree)
                    .like("%master%"),
                ),
            )
        )

        # Shared PhD condition for Questions 8 and 9
        phd_condition = or_(
            func.lower(func.trim(Applicant.degree)).in_(
                ["phd", "ph.d.", "ph.d"]
            ),
            func.lower(Applicant.degree).like("%doctor%"),
        )

        # Question 8
        q8 = session.scalar(
            select(func.count())
            .select_from(Applicant)
            .where(
                func.lower(func.trim(Applicant.term)) == "fall 2026",
                func.lower(
                    func.trim(Applicant.status)
                ).like("accept%"),
                phd_condition,
                func.lower(Applicant.program)
                .like("%computer science%"),
                or_(
                    func.lower(Applicant.program)
                    .like("%georgetown%"),
                    func.lower(Applicant.program).like(
                        "%massachusetts institute of technology%"
                    ),
                    func.lower(Applicant.program).like("%mit%"),
                    func.lower(Applicant.program)
                    .like("%stanford%"),
                    func.lower(Applicant.program)
                    .like("%carnegie mellon%"),
                ),
            )
        )

        # Question 9
        q9 = session.scalar(
            select(func.count())
            .select_from(Applicant)
            .where(
                func.lower(func.trim(Applicant.term)) == "fall 2026",
                func.lower(
                    func.trim(Applicant.status)
                ).like("accept%"),
                phd_condition,
                func.lower(Applicant.llm_generated_program)
                .like("%computer science%"),
                or_(
                    func.lower(Applicant.llm_generated_university)
                    .like("%georgetown%"),
                    func.lower(Applicant.llm_generated_university)
                    .like(
                        "%massachusetts institute of technology%"
                    ),
                    func.lower(
                        Applicant.llm_generated_university
                    ) == "mit",
                    func.lower(Applicant.llm_generated_university)
                    .like("%stanford%"),
                    func.lower(Applicant.llm_generated_university)
                    .like("%carnegie mellon%"),
                ),
            )
        )

        # Question 10
        princeton_total = session.scalar(
            select(func.count())
            .select_from(Applicant)
            .where(
                func.lower(func.trim(Applicant.term)) == "fall 2026",
                func.lower(Applicant.program)
                .like("%princeton%"),
            )
        )

        princeton_accepted = session.scalar(
            select(func.count())
            .select_from(Applicant)
            .where(
                func.lower(func.trim(Applicant.term)) == "fall 2026",
                func.lower(Applicant.program)
                .like("%princeton%"),
                func.lower(
                    func.trim(Applicant.status)
                ).like("accept%"),
            )
        )

        q10 = (
            100.0 * princeton_accepted / princeton_total
            if princeton_total
            else 0.0
        )

        # Question 11
        q11 = session.scalar(
            select(func.avg(Applicant.gpa))
            .where(
                func.lower(func.trim(Applicant.term)) == "fall 2026",
                func.lower(Applicant.program)
                .like("%princeton%"),
                func.lower(
                    func.trim(Applicant.status)
                ).like("accept%"),
                Applicant.gpa.is_not(None),
            )
        )

        return {
            "q1": q1,
            "q2": q2,
            "q3_gpa": q3_gpa,
            "q3_gre": q3_gre,
            "q3_gre_v": q3_gre_v,
            "q3_gre_aw": q3_gre_aw,
            "q4": q4,
            "q5": q5,
            "q6": q6,
            "q7": q7,
            "q8": q8,
            "q9": q9,
            "q9_difference": q9 - q8,
            "q10": q10,
            "q11": q11,
        }


@app.route("/")
def index():
    results = get_analysis_results()
    return render_template("index.html", results=results)


if __name__ == "__main__":
    app.run(debug=True)