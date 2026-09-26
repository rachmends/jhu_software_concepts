import json
import runpy
import sys
from pathlib import Path

import pytest
import urllib3


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

import scrape


# ============================================================
# URLLIB3
# ============================================================


@pytest.mark.web
def test_urllib3_success(monkeypatch):
    class FakeResponse:
        status = 403

    monkeypatch.setattr(
        scrape.http,
        "request",
        lambda *args, **kwargs: FakeResponse(),
    )

    assert scrape._test_urllib3(scrape.RESULTS_URL) == 403


@pytest.mark.web
def test_urllib3_http_error(monkeypatch, capsys):
    def fail(*args, **kwargs):
        raise urllib3.exceptions.HTTPError("fake failure")

    monkeypatch.setattr(
        scrape.http,
        "request",
        fail,
    )

    assert scrape._test_urllib3(scrape.RESULTS_URL) is None
    assert "urllib3 error:" in capsys.readouterr().out


# ============================================================
# CHROME HELPERS
# ============================================================


@pytest.mark.web
def test_get_gradcafe_tab_info(monkeypatch):
    class Result:
        stdout = (
            "GradCafe | "
            "https://www.thegradcafe.com/survey?page=1\n"
        )

    monkeypatch.setattr(
        scrape.subprocess,
        "run",
        lambda *args, **kwargs: Result(),
    )

    assert scrape._get_gradcafe_tab_info() == (
        "GradCafe | "
        "https://www.thegradcafe.com/survey?page=1"
    )


@pytest.mark.web
def test_get_chrome_html(monkeypatch):
    class Result:
        stdout = "<html>hello</html>"

    monkeypatch.setattr(
        scrape.subprocess,
        "run",
        lambda *args, **kwargs: Result(),
    )

    assert scrape._get_chrome_html() == "<html>hello</html>"


@pytest.mark.web
def test_navigate_gradcafe_tab(monkeypatch):
    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs

    monkeypatch.setattr(
        scrape.subprocess,
        "run",
        fake_run,
    )

    url = "https://www.thegradcafe.com/survey?page=2"

    scrape._navigate_gradcafe_tab(url)

    assert url in captured["command"]
    assert captured["kwargs"]["check"] is True


# ============================================================
# HTML HELPERS
# ============================================================


@pytest.mark.web
def test_save_html(monkeypatch, tmp_path):
    target = tmp_path / "page.html"

    monkeypatch.setattr(
        scrape,
        "HTML_FILE",
        target,
    )

    scrape._save_html("<html>test</html>")

    assert target.read_text(
        encoding="utf-8"
    ) == "<html>test</html>"


@pytest.mark.web
def test_is_blocked_results_page():
    rows = "".join(
        "<tr><td>x</td></tr>"
        for _ in range(10)
    )

    html = (
        "<html>"
        "<head><title>Just a moment</title></head>"
        f"<body><table>{rows}</table></body>"
        "</html>"
    )

    assert scrape._is_blocked(html) is False


@pytest.mark.web
@pytest.mark.parametrize(
    "title",
    [
        "Just a moment",
        "Attention Required",
        "Access Denied",
    ],
)
def test_is_blocked_title(title):
    html = f"""
    <html>
        <head><title>{title}</title></head>
        <body>Something</body>
    </html>
    """

    assert scrape._is_blocked(html) is True


@pytest.mark.web
@pytest.mark.parametrize(
    "phrase",
    [
        "Verify you are human",
        "Checking your browser",
        "Performing security verification",
        "Enable JavaScript and cookies to continue",
    ],
)
def test_is_blocked_visible_text(phrase):
    html = f"""
    <html>
        <head><title>GradCafe</title></head>
        <body>{phrase}</body>
    </html>
    """

    assert scrape._is_blocked(html) is True


@pytest.mark.web
def test_is_blocked_normal_without_title():
    html = """
    <html>
        <body>Normal GradCafe content</body>
    </html>
    """

    assert scrape._is_blocked(html) is False


@pytest.mark.web
def test_next_url_rel_absolute():
    html = """
    <a rel="next"
       href="https://www.thegradcafe.com/survey?page=2">
       Next
    </a>
    """

    assert scrape._get_next_page_url(html) == (
        "https://www.thegradcafe.com/survey?page=2"
    )


@pytest.mark.web
def test_next_url_rel_relative():
    html = """
    <a rel="next" href="/survey?page=2">Next</a>
    """

    assert scrape._get_next_page_url(html) == (
        scrape.BASE_URL + "/survey?page=2"
    )


@pytest.mark.web
def test_next_url_text_relative():
    html = """
    <a href="/survey?page=3">Next page</a>
    """

    assert scrape._get_next_page_url(html) == (
        scrape.BASE_URL + "/survey?page=3"
    )


@pytest.mark.web
def test_next_url_text_absolute():
    html = """
    <a href="https://www.thegradcafe.com/survey?page=3">
        →
    </a>
    """

    assert scrape._get_next_page_url(html) == (
        "https://www.thegradcafe.com/survey?page=3"
    )


@pytest.mark.web
def test_next_url_aria_relative():
    html = """
    <a href="/survey?page=4" aria-label="Next results">
        More
    </a>
    """

    assert scrape._get_next_page_url(html) == (
        scrape.BASE_URL + "/survey?page=4"
    )


@pytest.mark.web
def test_next_url_none():
    assert scrape._get_next_page_url(
        '<a href="/previous">Previous</a>'
    ) is None


# ============================================================
# EXTRACTION HELPERS
# ============================================================


@pytest.mark.web
@pytest.mark.parametrize(
    "text, expected",
    [
        ("Computer Science PhD", "PhD"),
        ("Engineering MSc", "MSc"),
        ("Business MBA", "MBA"),
        ("No degree", None),
    ],
)
def test_extract_degree(text, expected):
    assert scrape._extract_degree(text) == expected


@pytest.mark.web
@pytest.mark.parametrize(
    "text, expected",
    [
        ("Added Sep 12, 2026", "Sep 12, 2026"),
        ("No date", None),
    ],
)
def test_extract_date_added(text, expected):
    assert scrape._extract_date_added(text) == expected


@pytest.mark.web
@pytest.mark.parametrize(
    "text, expected",
    [
        ("Accepted on Sep 11", "Accepted"),
        ("Rejected on Sep 11", "Rejected"),
        ("Wait listed on Sep 11", "Waitlisted"),
        ("Waitlisted on Sep 11", "Waitlisted"),
        ("Interview on Sep 11", "Interview"),
        ("Pending", None),
    ],
)
def test_extract_status(text, expected):
    assert scrape._extract_status(text) == expected


@pytest.mark.web
@pytest.mark.parametrize(
    "text, expected",
    [
        ("Accepted on Sep 11", "Sep 11"),
        ("Rejected on Jan 2", "Jan 2"),
        ("Waitlisted on Mar 3", "Mar 3"),
        ("Nothing", None),
    ],
)
def test_extract_decision_date(text, expected):
    assert scrape._extract_decision_date(text) == expected


@pytest.mark.web
@pytest.mark.parametrize(
    "text, expected",
    [
        ("Fall 2026", "Fall 2026"),
        ("Spring 2027", "Spring 2027"),
        ("No term", None),
    ],
)
def test_extract_term(text, expected):
    assert scrape._extract_term(text) == expected


@pytest.mark.web
@pytest.mark.parametrize(
    "text, expected",
    [
        ("International applicant", "International"),
        ("American applicant", "American"),
        ("Unknown applicant", None),
    ],
)
def test_extract_student_type(text, expected):
    assert scrape._extract_student_type(text) == expected


@pytest.mark.web
@pytest.mark.parametrize(
    "text, expected",
    [
        ("GPA 3.87", "3.87"),
        ("GPA 4", "4"),
        ("No GPA", None),
    ],
)
def test_extract_gpa(text, expected):
    assert scrape._extract_gpa(text) == expected


@pytest.mark.web
@pytest.mark.parametrize(
    "text, expected",
    [
        ("GRE 167", "167"),
        ("No GRE", None),
    ],
)
def test_extract_gre(text, expected):
    assert scrape._extract_gre(text) == expected


@pytest.mark.web
@pytest.mark.parametrize(
    "text, expected",
    [
        ("GRE V 162", "162"),
        ("No GRE verbal", None),
    ],
)
def test_extract_gre_v(text, expected):
    assert scrape._extract_gre_v(text) == expected


@pytest.mark.web
@pytest.mark.parametrize(
    "text, expected",
    [
        ("GRE AW 4.5", "4.5"),
        ("No GRE AW", None),
    ],
)
def test_extract_gre_aw(text, expected):
    assert scrape._extract_gre_aw(text) == expected


# ============================================================
# PAGE PARSER
# ============================================================


@pytest.mark.web
def test_parse_page_full_record():
    html = """
    <table>
        <tr>
            <td>Johns Hopkins University</td>
            <td>Computer Science PhD</td>
            <td>
                <a href="/result/123">Result</a>
            </td>
            <td>
                Accepted on Sep 11
                Sep 12, 2026
            </td>
        </tr>

        <tr class="tw-border-none">
            <td>
                Fall 2026
                International
                GPA 3.87
                GRE 167
                GRE V 162
                GRE AW 4.5
            </td>
        </tr>

        <tr class="tw-border-none">
            <td>
                <p class="tw-text-gray-500 tw-text-sm tw-my-0">
                    Great program!
                </p>
            </td>
        </tr>
    </table>
    """

    records = scrape._parse_page(html)

    assert len(records) == 1

    record = records[0]

    assert record["university"] == (
        "Johns Hopkins University"
    )
    assert record["program"] == "Computer Science"
    assert record["comments"] == "Great program!"
    assert record["date_added"] == "Sep 12, 2026"
    assert record["url"] == (
        scrape.BASE_URL + "/result/123"
    )
    assert record["status"] == "Accepted"
    assert record["decision_date"] == "Sep 11"
    assert record["term"] == "Fall 2026"
    assert record["student_type"] == "International"
    assert record["gpa"] == "3.87"
    assert record["gre"] == "167"
    assert record["gre_v"] == "162"
    assert record["gre_aw"] == "4.5"
    assert record["degree"] == "PhD"
    assert "Great program!" in record["raw_text"]


@pytest.mark.web
def test_parse_page_absolute_result_url():
    html = """
    <table>
        <tr>
            <td>MIT</td>
            <td>Physics</td>
            <td>
                <a href="https://www.thegradcafe.com/result/999">
                    Result
                </a>
            </td>
            <td>Rejected on Jan 2</td>
        </tr>
    </table>
    """

    records = scrape._parse_page(html)

    assert len(records) == 1
    assert records[0]["url"] == (
        "https://www.thegradcafe.com/result/999"
    )
    assert records[0]["status"] == "Rejected"


@pytest.mark.web
def test_parse_page_header_and_detail_rows():
    html = """
    <table>
        <tr class="tw-border-none">
            <td>orphan detail</td>
        </tr>

        <tr>
            <th>University</th>
            <th>Program</th>
        </tr>

        <tr>
            <td>Stanford University</td>
            <td>Mathematics</td>
            <td>Interview on Feb 2</td>
        </tr>
    </table>
    """

    records = scrape._parse_page(html)

    assert len(records) == 1
    assert records[0]["status"] == "Interview"


@pytest.mark.web
def test_parse_page_empty_cells_and_empty_extra_rows():
    html = """
    <table>
        <tr>
            <td></td>
            <td></td>
            <td>Accepted on Apr 4</td>
        </tr>

        <tr class="tw-border-none">
            <td></td>
        </tr>

        <tr class="tw-border-none">
            <td>
                <p class="tw-text-gray-500 tw-text-sm tw-my-0">
                </p>
            </td>
        </tr>
    </table>
    """

    records = scrape._parse_page(html)

    assert len(records) == 1
    assert records[0]["university"] is None
    assert records[0]["program"] is None
    assert records[0]["comments"] is None


@pytest.mark.web
def test_parse_page_row_with_no_cells():
    html = """
    <table>
        <tr>
            Accepted on May 5
        </tr>
    </table>
    """

    records = scrape._parse_page(html)

    assert len(records) == 1
    assert records[0]["university"] is None
    assert records[0]["program"] is None


# ============================================================
# JSON FUNCTIONS
# ============================================================


@pytest.mark.web
def test_load_data_missing(monkeypatch, tmp_path):
    path = tmp_path / "missing.json"

    monkeypatch.setattr(
        scrape,
        "OUTPUT_FILE",
        path,
    )

    assert scrape.load_data() == []


@pytest.mark.web
def test_load_data_empty(monkeypatch, tmp_path):
    path = tmp_path / "data.json"
    path.write_text("", encoding="utf-8")

    monkeypatch.setattr(
        scrape,
        "OUTPUT_FILE",
        path,
    )

    assert scrape.load_data() == []


@pytest.mark.web
def test_load_data_valid_list(monkeypatch, tmp_path):
    path = tmp_path / "data.json"

    path.write_text(
        json.dumps([{"url": "one"}]),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        scrape,
        "OUTPUT_FILE",
        path,
    )

    assert scrape.load_data() == [{"url": "one"}]


@pytest.mark.web
def test_load_data_non_list(monkeypatch, tmp_path):
    path = tmp_path / "data.json"

    path.write_text(
        json.dumps({"url": "one"}),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        scrape,
        "OUTPUT_FILE",
        path,
    )

    assert scrape.load_data() == []


@pytest.mark.web
def test_load_data_invalid_json(
    monkeypatch,
    tmp_path,
    capsys,
):
    path = tmp_path / "data.json"
    path.write_text("{bad json", encoding="utf-8")

    monkeypatch.setattr(
        scrape,
        "OUTPUT_FILE",
        path,
    )

    assert scrape.load_data() == []

    assert "invalid" in (
        capsys.readouterr().out.lower()
    )


@pytest.mark.web
def test_save_data(monkeypatch, tmp_path):
    path = tmp_path / "data.json"

    monkeypatch.setattr(
        scrape,
        "OUTPUT_FILE",
        path,
    )

    records = [{"url": "one"}]

    scrape.save_data(records)

    assert json.loads(
        path.read_text(encoding="utf-8")
    ) == records


# ============================================================
# RESUME STATE
# ============================================================


@pytest.mark.web
def test_load_state_missing(monkeypatch, tmp_path):
    path = tmp_path / "state.json"

    monkeypatch.setattr(
        scrape,
        "STATE_FILE",
        path,
    )

    assert scrape._load_state() == {}


@pytest.mark.web
def test_load_state_empty(monkeypatch, tmp_path):
    path = tmp_path / "state.json"
    path.write_text("", encoding="utf-8")

    monkeypatch.setattr(
        scrape,
        "STATE_FILE",
        path,
    )

    assert scrape._load_state() == {}


@pytest.mark.web
def test_load_state_valid(monkeypatch, tmp_path):
    path = tmp_path / "state.json"

    state = {
        "next_url": "page2",
        "records_collected": 20,
    }

    path.write_text(
        json.dumps(state),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        scrape,
        "STATE_FILE",
        path,
    )

    assert scrape._load_state() == state


@pytest.mark.web
def test_load_state_non_dict(monkeypatch, tmp_path):
    path = tmp_path / "state.json"

    path.write_text(
        json.dumps(["wrong"]),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        scrape,
        "STATE_FILE",
        path,
    )

    assert scrape._load_state() == {}


@pytest.mark.web
def test_load_state_invalid_json(monkeypatch, tmp_path):
    path = tmp_path / "state.json"
    path.write_text("{bad", encoding="utf-8")

    monkeypatch.setattr(
        scrape,
        "STATE_FILE",
        path,
    )

    assert scrape._load_state() == {}


@pytest.mark.web
def test_save_state(monkeypatch, tmp_path):
    path = tmp_path / "state.json"

    monkeypatch.setattr(
        scrape,
        "STATE_FILE",
        path,
    )

    scrape._save_state("page2", 42)

    state = json.loads(
        path.read_text(encoding="utf-8")
    )

    assert state == {
        "next_url": "page2",
        "records_collected": 42,
    }


# ============================================================
# DUPLICATION / MERGING
# ============================================================


@pytest.mark.web
def test_record_key_url():
    assert scrape._record_key(
        {"url": "  abc  "}
    ) == (
        "url",
        "abc",
    )


@pytest.mark.web
def test_record_key_raw_text():
    assert scrape._record_key(
        {
            "url": None,
            "raw_text": "  HELLO    WORLD ",
        }
    ) == (
        "text",
        "hello world",
    )


@pytest.mark.web
def test_deduplicate_records():
    first = {
        "url": "one",
        "raw_text": "first",
    }

    duplicate = {
        "url": "one",
        "raw_text": "different",
    }

    second = {
        "url": None,
        "raw_text": "Second Applicant",
    }

    second_duplicate = {
        "url": None,
        "raw_text": " second   applicant ",
    }

    result = scrape._deduplicate_records(
        [
            first,
            duplicate,
            second,
            second_duplicate,
        ]
    )

    assert result == [
        first,
        second,
    ]


@pytest.mark.web
def test_merge_records_adds_and_updates():
    existing = [
        {
            "url": "one",
            "program": "Math",
            "comments": None,
        }
    ]

    new = [
        {
            "url": "one",
            "program": "",
            "comments": "New comment",
        },
        {
            "url": "two",
            "program": "Physics",
            "comments": None,
        },
    ]

    result = scrape._merge_records(
        existing,
        new,
    )

    assert len(result) == 2

    first = next(
        item
        for item in result
        if item["url"] == "one"
    )

    assert first["program"] == "Math"
    assert first["comments"] == "New comment"

    assert any(
        item["url"] == "two"
        for item in result
    )


# ============================================================
# PAGE INSPECTION
# ============================================================


@pytest.mark.web
def test_inspect_page_with_title(capsys):
    html = """
    <html>
        <head><title>GradCafe</title></head>
        <body>
            <div>One</div>
            <table>
                <tr><td>Test</td></tr>
            </table>
            <a href="/test">Link</a>
        </body>
    </html>
    """

    scrape._inspect_page(html)

    output = capsys.readouterr().out

    assert "PAGE TITLE:" in output
    assert "GradCafe" in output
    assert "tr tags:" in output
    assert "div tags:" in output
    assert "links:" in output


@pytest.mark.web
def test_inspect_page_without_title(capsys):
    scrape._inspect_page(
        "<html><body>test</body></html>"
    )

    output = capsys.readouterr().out

    assert "PAGE INSPECTION" in output
    assert "tr tags:" in output


# ============================================================
# scrape_data()
# ============================================================


def configure_scrape_data(
    monkeypatch,
    *,
    existing=None,
    tab_info=(
        "GradCafe | "
        "https://www.thegradcafe.com/survey"
    ),
    state=None,
    html="<html>page</html>",
    blocked=False,
    records=None,
    next_url=None,
):
    if existing is None:
        existing = []

    if state is None:
        state = {}

    if records is None:
        records = [
            {
                "url": "new",
                "raw_text": "new",
            }
        ]

    monkeypatch.setattr(
        scrape,
        "load_data",
        lambda: existing,
    )

    monkeypatch.setattr(
        scrape,
        "_get_gradcafe_tab_info",
        lambda: tab_info,
    )

    monkeypatch.setattr(
        scrape,
        "_test_urllib3",
        lambda url: 403,
    )

    monkeypatch.setattr(
        scrape,
        "_load_state",
        lambda: state,
    )

    monkeypatch.setattr(
        scrape,
        "_get_chrome_html",
        lambda: html,
    )

    monkeypatch.setattr(
        scrape,
        "_save_html",
        lambda html: None,
    )

    monkeypatch.setattr(
        scrape,
        "_is_blocked",
        lambda html: blocked,
    )

    monkeypatch.setattr(
        scrape,
        "_parse_page",
        lambda html: records,
    )

    monkeypatch.setattr(
        scrape,
        "_get_next_page_url",
        lambda html: next_url,
    )

    monkeypatch.setattr(
        scrape,
        "save_data",
        lambda records: None,
    )

    monkeypatch.setattr(
        scrape,
        "_save_state",
        lambda url, count: None,
    )

    monkeypatch.setattr(
        scrape,
        "_navigate_gradcafe_tab",
        lambda url: None,
    )

    monkeypatch.setattr(
        scrape.time,
        "sleep",
        lambda seconds: None,
    )

    monkeypatch.setattr(
        scrape,
        "TARGET_RECORDS",
        50_000,
    )

    monkeypatch.setattr(
        scrape,
        "MAX_PAGES_PER_RUN",
        500,
    )


@pytest.mark.web
def test_scrape_data_no_tab(monkeypatch, capsys):
    configure_scrape_data(
        monkeypatch,
        tab_info="",
    )

    scrape.scrape_data()

    assert "Open" in capsys.readouterr().out


@pytest.mark.web
def test_scrape_data_resume_and_no_html(
    monkeypatch,
    capsys,
):
    navigated = []

    configure_scrape_data(
        monkeypatch,
        tab_info=(
            "GradCafe | "
            "https://www.thegradcafe.com/survey"
        ),
        state={
            "next_url":
                "https://www.thegradcafe.com/survey?page=2"
        },
        html="",
    )

    monkeypatch.setattr(
        scrape,
        "_navigate_gradcafe_tab",
        lambda url: navigated.append(url),
    )

    scrape.scrape_data()

    output = capsys.readouterr().out

    assert navigated == [
        "https://www.thegradcafe.com/survey?page=2"
    ]
    assert "Resume state found" in output
    assert "No HTML was captured" in output


@pytest.mark.web
def test_scrape_data_blocked(monkeypatch, capsys):
    configure_scrape_data(
        monkeypatch,
        blocked=True,
    )

    scrape.scrape_data()

    assert "verification/blocking" in (
        capsys.readouterr().out
    )


@pytest.mark.web
def test_scrape_data_no_records(monkeypatch, capsys):
    configure_scrape_data(
        monkeypatch,
        records=[],
    )

    scrape.scrape_data()

    assert "No applicant records found" in (
        capsys.readouterr().out
    )


@pytest.mark.web
def test_scrape_data_no_next_url(
    monkeypatch,
    capsys,
):
    saved = []

    configure_scrape_data(
        monkeypatch,
        records=[
            {
                "url": "new",
                "raw_text": "new",
            }
        ],
        next_url=None,
    )

    monkeypatch.setattr(
        scrape,
        "save_data",
        lambda records: saved.append(
            list(records)
        ),
    )

    scrape.scrape_data()

    output = capsys.readouterr().out

    assert saved
    assert "Page 1:" in output
    assert "No next-page link found" in output
    assert "Finished:" in output


@pytest.mark.web
def test_scrape_data_same_next_url(
    monkeypatch,
    capsys,
):
    current = scrape.RESULTS_URL

    configure_scrape_data(
        monkeypatch,
        tab_info=f"GradCafe | {current}",
        next_url=current,
    )

    scrape.scrape_data()

    assert "Next-page URL did not change" in (
        capsys.readouterr().out
    )


@pytest.mark.web
def test_scrape_data_reaches_target(
    monkeypatch,
    capsys,
):
    configure_scrape_data(
        monkeypatch,
        records=[
            {
                "url": "new",
                "raw_text": "new",
            }
        ],
        next_url="page2",
    )

    monkeypatch.setattr(
        scrape,
        "TARGET_RECORDS",
        1,
    )

    scrape.scrape_data()

    assert "Finished: 1/1" in (
        capsys.readouterr().out
    )


@pytest.mark.web
def test_scrape_data_page_limit_before_loop(
    monkeypatch,
):
    configure_scrape_data(
        monkeypatch,
    )

    monkeypatch.setattr(
        scrape,
        "MAX_PAGES_PER_RUN",
        0,
    )

    scrape.scrape_data()


@pytest.mark.web
def test_scrape_data_page_limit_after_page(
    monkeypatch,
):
    navigated = []

    configure_scrape_data(
        monkeypatch,
        next_url="page2",
    )

    monkeypatch.setattr(
        scrape,
        "MAX_PAGES_PER_RUN",
        1,
    )

    monkeypatch.setattr(
        scrape,
        "_navigate_gradcafe_tab",
        lambda url: navigated.append(url),
    )

    scrape.scrape_data()

    assert navigated == []


@pytest.mark.web
def test_scrape_data_navigates_next_page(
    monkeypatch,
):
    html_values = iter(
        [
            "<html>page1</html>",
            "",
        ]
    )

    navigated = []

    configure_scrape_data(
        monkeypatch,
        next_url="page2",
    )

    monkeypatch.setattr(
        scrape,
        "_get_chrome_html",
        lambda: next(html_values),
    )

    next_values = iter(
        [
            "page2",
            None,
        ]
    )

    monkeypatch.setattr(
        scrape,
        "_get_next_page_url",
        lambda html: next(next_values),
    )

    monkeypatch.setattr(
        scrape,
        "_navigate_gradcafe_tab",
        lambda url: navigated.append(url),
    )

    scrape.scrape_data()

    assert navigated == ["page2"]


@pytest.mark.web
def test_scrape_data_duplicate_adds_zero(
    monkeypatch,
    capsys,
):
    existing = [
        {
            "url": "same",
            "raw_text": "same",
        }
    ]

    configure_scrape_data(
        monkeypatch,
        existing=existing,
        records=[
            {
                "url": "same",
                "raw_text": "same",
            }
        ],
        next_url=None,
    )

    scrape.scrape_data()

    assert "new 0" in capsys.readouterr().out


# ============================================================
# pull_new_data()
# ============================================================


def configure_pull_new_data(
    monkeypatch,
    *,
    existing=None,
    tab_info=(
        "GradCafe | "
        "https://www.thegradcafe.com/survey"
    ),
    html="<html>page</html>",
    blocked=False,
    records=None,
    next_url=None,
):
    if existing is None:
        existing = []

    if records is None:
        records = [
            {
                "url": "new",
                "raw_text": "new",
            }
        ]

    monkeypatch.setattr(
        scrape,
        "load_data",
        lambda: existing,
    )

    monkeypatch.setattr(
        scrape,
        "_get_gradcafe_tab_info",
        lambda: tab_info,
    )

    monkeypatch.setattr(
        scrape,
        "_test_urllib3",
        lambda url: 403,
    )

    monkeypatch.setattr(
        scrape,
        "_navigate_gradcafe_tab",
        lambda url: None,
    )

    monkeypatch.setattr(
        scrape.time,
        "sleep",
        lambda seconds: None,
    )

    monkeypatch.setattr(
        scrape,
        "_get_chrome_html",
        lambda: html,
    )

    monkeypatch.setattr(
        scrape,
        "_save_html",
        lambda html: None,
    )

    monkeypatch.setattr(
        scrape,
        "_is_blocked",
        lambda html: blocked,
    )

    monkeypatch.setattr(
        scrape,
        "_parse_page",
        lambda html: records,
    )

    monkeypatch.setattr(
        scrape,
        "_get_next_page_url",
        lambda html: next_url,
    )

    monkeypatch.setattr(
        scrape,
        "save_data",
        lambda records: None,
    )


@pytest.mark.web
def test_pull_new_data_no_tab(
    monkeypatch,
    capsys,
):
    configure_pull_new_data(
        monkeypatch,
        tab_info="",
    )

    result = scrape.pull_new_data()

    assert result == 0
    assert "Open" in capsys.readouterr().out


@pytest.mark.web
def test_pull_new_data_no_html(
    monkeypatch,
    capsys,
):
    configure_pull_new_data(
        monkeypatch,
        html="",
    )

    result = scrape.pull_new_data()

    assert result == 0
    assert "No HTML was captured" in (
        capsys.readouterr().out
    )


@pytest.mark.web
def test_pull_new_data_blocked(
    monkeypatch,
    capsys,
):
    configure_pull_new_data(
        monkeypatch,
        blocked=True,
    )

    result = scrape.pull_new_data()

    assert result == 0
    assert "verification/blocking" in (
        capsys.readouterr().out
    )


@pytest.mark.web
def test_pull_new_data_no_records(
    monkeypatch,
    capsys,
):
    configure_pull_new_data(
        monkeypatch,
        records=[],
    )

    result = scrape.pull_new_data()

    assert result == 0
    assert "No applicant records found" in (
        capsys.readouterr().out
    )


@pytest.mark.web
def test_pull_new_data_existing_page(
    monkeypatch,
    capsys,
):
    existing = [
        {
            "url": "same",
            "raw_text": "same",
        }
    ]

    configure_pull_new_data(
        monkeypatch,
        existing=existing,
        records=[
            {
                "url": "same",
                "raw_text": "same",
            }
        ],
    )

    result = scrape.pull_new_data()

    assert result == 0

    output = capsys.readouterr().out

    assert "0 new" in output
    assert "Reached records already" in output


@pytest.mark.web
def test_pull_new_data_adds_new_records_no_next(
    monkeypatch,
    capsys,
):
    saved = []

    configure_pull_new_data(
        monkeypatch,
        existing=[
            {
                "url": "old",
                "raw_text": "old",
            }
        ],
        records=[
            {
                "url": "new",
                "raw_text": "new",
            }
        ],
        next_url=None,
    )

    monkeypatch.setattr(
        scrape,
        "save_data",
        lambda records: saved.append(
            list(records)
        ),
    )

    result = scrape.pull_new_data()

    assert result == 1
    assert len(saved[-1]) == 2

    output = capsys.readouterr().out

    assert "1 new" in output
    assert "No next-page link found" in output
    assert "Pull complete: 1 new records" in output


@pytest.mark.web
def test_pull_new_data_same_next_url(
    monkeypatch,
    capsys,
):
    configure_pull_new_data(
        monkeypatch,
        records=[
            {
                "url": "new",
                "raw_text": "new",
            }
        ],
        next_url=scrape.RESULTS_URL,
    )

    result = scrape.pull_new_data()

    assert result == 1
    assert "Next-page URL did not change" in (
        capsys.readouterr().out
    )


@pytest.mark.web
def test_pull_new_data_navigates_next_page(
    monkeypatch,
):
    html_values = iter(
        [
            "<html>page1</html>",
            "<html>page2</html>",
        ]
    )

    record_values = iter(
        [
            [
                {
                    "url": "new",
                    "raw_text": "new",
                }
            ],
            [
                {
                    "url": "new",
                    "raw_text": "new",
                }
            ],
        ]
    )

    navigated = []

    configure_pull_new_data(
        monkeypatch,
    )

    monkeypatch.setattr(
        scrape,
        "_get_chrome_html",
        lambda: next(html_values),
    )

    monkeypatch.setattr(
        scrape,
        "_parse_page",
        lambda html: next(record_values),
    )

    monkeypatch.setattr(
        scrape,
        "_get_next_page_url",
        lambda html: "page2",
    )

    monkeypatch.setattr(
        scrape,
        "_navigate_gradcafe_tab",
        lambda url: navigated.append(url),
    )

    result = scrape.pull_new_data()

    assert result == 1

    # Initial navigation to newest results + page 2.
    assert navigated == [
        scrape.RESULTS_URL,
        "page2",
    ]


# ============================================================
# main() / SCRIPT ENTRY
# ============================================================


@pytest.mark.web
def test_main(monkeypatch):
    called = {
        "value": False,
    }

    def fake_scrape_data():
        called["value"] = True

    monkeypatch.setattr(
        scrape,
        "scrape_data",
        fake_scrape_data,
    )

    scrape.main()

    assert called["value"] is True


@pytest.mark.web
def test_script_entry_point(monkeypatch):
    # runpy executes scrape.py in a fresh __main__ namespace.
    # Replace scrape_data after the module globals are created by
    # making the main loop terminate immediately through its first
    # dependency.
    def stop_immediately(self):
        raise SystemExit

    monkeypatch.setattr(
        Path,
        "exists",
        stop_immediately,
    )

    with pytest.raises(SystemExit):
        runpy.run_path(
            str(SRC_DIR / "scrape.py"),
            run_name="__main__",
        )