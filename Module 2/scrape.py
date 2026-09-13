import json
import re
import subprocess
import time
from pathlib import Path

import urllib3
from bs4 import BeautifulSoup


# ============================================================
# SETTINGS
# ============================================================

BASE_URL = "https://www.thegradcafe.com"
RESULTS_URL = "https://www.thegradcafe.com/survey"

TARGET_RECORDS = 50_000

OUTPUT_FILE = Path("applicant_data.json")
HTML_FILE = Path("gradcafe_page.html")
STATE_FILE = Path("scrape_state.json")

# Keep runs small while validating pagination/resume behavior.
MAX_PAGES_PER_RUN = 5

http = urllib3.PoolManager()

# ============================================================
# URLLIB3 TEST
# ============================================================

def test_urllib3(url):
    """
    Test whether GradCafe allows a direct urllib3 request.

    GradCafe currently returns HTTP 403, so the scraper uses
    the normal Chrome browser as the fallback.
    """

    try:
        response = http.request(
            "GET",
            url,
            timeout=urllib3.Timeout(
                connect=10.0,
                read=30.0
            ),
            retries=False
        )

        return response.status

    except urllib3.exceptions.HTTPError as error:
        print(f"urllib3 error: {error}")
        return None


# ============================================================
# CHROME FUNCTIONS
# ============================================================

def get_gradcafe_tab_info():
    """
    Find the GradCafe survey tab and return its title and URL.
    """

    applescript = '''
    tell application "Google Chrome"
        repeat with w in windows
            repeat with t in tabs of w
                if URL of t contains "thegradcafe.com/survey" then
                    return (title of t) & " | " & (URL of t)
                end if
            end repeat
        end repeat
    end tell
    '''

    result = subprocess.run(
        ["osascript", "-e", applescript],
        capture_output=True,
        text=True,
        check=True
    )

    return result.stdout.strip()


def get_chrome_html():
    """
    Capture the rendered HTML specifically from the
    GradCafe survey/results tab.
    """

    applescript = '''
    tell application "Google Chrome"
        repeat with w in windows
            repeat with t in tabs of w
                if URL of t contains "thegradcafe.com/survey" then
                    return execute t javascript "document.documentElement.outerHTML"
                end if
            end repeat
        end repeat
    end tell
    '''

    result = subprocess.run(
        ["osascript", "-e", applescript],
        capture_output=True,
        text=True,
        check=True
    )

    return result.stdout


def navigate_gradcafe_tab(url):
    """
    Navigate the existing GradCafe survey tab to another page.
    """

    applescript = '''
    on run argv
        set targetURL to item 1 of argv

        tell application "Google Chrome"
            repeat with w in windows
                repeat with t in tabs of w
                    if URL of t contains "thegradcafe.com/survey" then
                        set URL of t to targetURL
                        return
                    end if
                end repeat
            end repeat
        end tell
    end run
    '''

    subprocess.run(
        ["osascript", "-e", applescript, url],
        capture_output=True,
        text=True,
        check=True
    )


# ============================================================
# HTML FUNCTIONS
# ============================================================

def save_html(html):
    """
    Save the most recently captured HTML for debugging.
    """

    HTML_FILE.write_text(
        html,
        encoding="utf-8"
    )


def is_blocked(html):
    """
    Detect an actual blocking/verification page.

    Do not flag words that only appear inside JavaScript.
    """

    soup = BeautifulSoup(html, "html.parser")

    # If applicant table rows exist, this is almost certainly
    # the real results page.
    rows = soup.find_all("tr")

    if len(rows) >= 10:
        return False

    title = ""

    if soup.title:
        title = soup.title.get_text(
            " ",
            strip=True
        ).lower()

    visible_text = soup.get_text(
        " ",
        strip=True
    ).lower()

    blocking_titles = [
        "just a moment",
        "attention required",
        "access denied"
    ]

    blocking_phrases = [
        "verify you are human",
        "checking your browser",
        "performing security verification",
        "enable javascript and cookies to continue"
    ]

    if any(
        phrase in title
        for phrase in blocking_titles
    ):
        return True

    if any(
        phrase in visible_text
        for phrase in blocking_phrases
    ):
        return True

    return False

def get_next_page_url(html):
    """
    Find GradCafe's actual next-page URL from the rendered HTML.
    """

    soup = BeautifulSoup(html, "html.parser")

    # First try rel="next"
    next_link = soup.find("a", rel="next")

    if next_link and next_link.get("href"):
        href = next_link["href"]

        if href.startswith("http"):
            return href

        return BASE_URL + href

    # Then search links by visible text / aria-label
    for link in soup.find_all("a", href=True):

        text = link.get_text(
            " ",
            strip=True
        ).lower()

        aria_label = link.get(
            "aria-label",
            ""
        ).lower()

        if (
            text in ["next", "next page", "›", "→"]
            or "next" in aria_label
        ):
            href = link["href"]

            if href.startswith("http"):
                return href

            if href.startswith("/"):
                return BASE_URL + href

    return None

# ============================================================
# PARSING HELPERS
# ============================================================

def extract_degree(text):
    """
    Extract degree type.
    """

    match = re.search(
        r"\b(PhD|MFA|MBA|MSc|MS|MA|MPH|MEd|EdD|JD|"
        r"Masters|Master's)\b",
        text,
        re.IGNORECASE
    )

    if match:
        return match.group(1)

    return None


def extract_date_added(text):
    """
    Extract date such as Sep 12, 2026.
    """

    match = re.search(
        r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|"
        r"Oct|Nov|Dec)\s+\d{1,2},\s+\d{4}\b",
        text
    )

    if match:
        return match.group(0)

    return None


def extract_status(text):
    """
    Extract applicant decision status.
    """

    lowered = text.lower()

    if "accepted" in lowered:
        return "Accepted"

    if "rejected" in lowered:
        return "Rejected"

    if "wait listed" in lowered or "waitlisted" in lowered:
        return "Waitlisted"

    if "interview" in lowered:
        return "Interview"

    return None


def extract_decision_date(text):
    """
    Extract decision date such as Sep 11.
    """

    match = re.search(
        r"(?:Accepted|Rejected|Wait listed|Waitlisted|Interview)"
        r"\s+on\s+"
        r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
        r"\s+\d{1,2})",
        text,
        re.IGNORECASE
    )

    if match:
        return match.group(1)

    return None


def extract_term(text):
    """
    Extract semester/year such as Spring 2027.
    """

    match = re.search(
        r"\b(Fall|Spring|Summer|Winter)\s+\d{4}\b",
        text,
        re.IGNORECASE
    )

    if match:
        return match.group(0)

    return None


def extract_student_type(text):
    """
    Determine International or American.
    """

    lowered = text.lower()

    if "international" in lowered:
        return "International"

    if "american" in lowered:
        return "American"

    return None


def extract_gpa(text):
    """
    Extract GPA.
    """

    match = re.search(
        r"\bGPA\s+([0-4](?:\.\d+)?)",
        text,
        re.IGNORECASE
    )

    if match:
        return match.group(1)

    return None


def extract_gre(text):
    """
    Extract GRE quantitative/general score shown as GRE.
    """

    match = re.search(
        r"\bGRE\s+(\d{2,3})\b",
        text,
        re.IGNORECASE
    )

    if match:
        return match.group(1)

    return None


def extract_gre_v(text):
    """
    Extract GRE verbal score.
    """

    match = re.search(
        r"\bGRE V\s+(\d{2,3})\b",
        text,
        re.IGNORECASE
    )

    if match:
        return match.group(1)

    return None


def extract_gre_aw(text):
    """
    Extract GRE analytical-writing score.
    """

    match = re.search(
        r"\bGRE AW\s+([\d.]+)",
        text,
        re.IGNORECASE
    )

    if match:
        return match.group(1)

    return None


# ============================================================
# PAGE PARSER
# ============================================================

def parse_page(html):
    """
    Parse applicant records from one GradCafe page.

    Each applicant consists of:
        1. Main row
        2. Detail row
        3. Optional comment row

    Detail/comment rows use class "tw-border-none".
    """

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    records = []
    rows = soup.find_all("tr")

    i = 0

    while i < len(rows):

        row = rows[i]

        classes = row.get(
            "class",
            []
        )

        # Never start a record from a detail/comment row.
        if "tw-border-none" in classes:
            i += 1
            continue

        main_text = row.get_text(
            " ",
            strip=True
        )

        # ----------------------------------------------------
        # Collect detail rows + optional comment row
        # ----------------------------------------------------

        detail_text_parts = []
        comment_texts = []

        j = i + 1

        while j < len(rows):

            extra_row = rows[j]

            extra_classes = extra_row.get(
                "class",
                []
            )

            if "tw-border-none" not in extra_classes:
                break

            # Comment rows contain this <p>
            comment_element = extra_row.select_one(
                "p.tw-text-gray-500.tw-text-sm.tw-my-0"
            )

            if comment_element:

                comment_text = comment_element.get_text(
                    " ",
                    strip=True
                )

                if comment_text:
                    comment_texts.append(
                        comment_text
                    )

            else:

                extra_text = extra_row.get_text(
                    " ",
                    strip=True
                )

                if extra_text:
                    detail_text_parts.append(
                        extra_text
                    )

            j += 1

        detail_text = " ".join(
            detail_text_parts
        )

        comments = None

        if comment_texts:
            comments = " ".join(
                comment_texts
            )

        combined_text = (
            main_text + " " + detail_text
        ).strip()

        # ----------------------------------------------------
        # Status
        # ----------------------------------------------------

        status = extract_status(
            combined_text
        )

        # Header/unrelated row.
        if status is None:
            i = j
            continue

        # ----------------------------------------------------
        # Main table cells
        # ----------------------------------------------------

        cells = [
            td.get_text(
                " ",
                strip=True
            )
            for td in row.find_all(
                "td",
                recursive=False
            )
        ]

        university = None
        program = None

        if len(cells) >= 1:
            university = cells[0] or None

        if len(cells) >= 2:
            program = cells[1] or None

        # ----------------------------------------------------
        # Degree
        # ----------------------------------------------------

        degree = extract_degree(
            combined_text
        )

        if program and degree:

            program = re.sub(
                rf"\s+{re.escape(degree)}\s*$",
                "",
                program,
                flags=re.IGNORECASE
            ).strip()

        # ----------------------------------------------------
        # Applicant URL
        # ----------------------------------------------------

        applicant_url = None

        for link in row.find_all(
            "a",
            href=True
        ):

            href = link.get(
                "href",
                ""
            )

            if "/result/" in href:

                if href.startswith("http"):
                    applicant_url = href
                else:
                    applicant_url = BASE_URL + href

                break

        # ----------------------------------------------------
        # Final record
        # ----------------------------------------------------

        record = {
            "program": program,
            "university": university,
            "comments": comments,
            "date_added": extract_date_added(
                main_text
            ),
            "url": applicant_url,
            "status": status,
            "decision_date": extract_decision_date(
                combined_text
            ),
            "term": extract_term(
                detail_text
            ),
            "student_type": extract_student_type(
                detail_text
            ),
            "gre": extract_gre(
                detail_text
            ),
            "gre_v": extract_gre_v(
                detail_text
            ),
            "gre_aw": extract_gre_aw(
                detail_text
            ),
            "gpa": extract_gpa(
                detail_text
            ),
            "degree": degree,
            "raw_text": (
                main_text
                + " "
                + detail_text
                + (
                    " " + comments
                    if comments
                    else ""
                )
            ).strip(),
            "raw_main_text": main_text,
            "raw_detail_text": detail_text
        }

        records.append(
            record
        )

        # Jump directly to the next applicant row.
        i = j

    return records

# ============================================================
# JSON FUNCTIONS
# ============================================================

def load_data():
    """
    Load existing JSON records.
    """

    if not OUTPUT_FILE.exists():
        return []

    if OUTPUT_FILE.stat().st_size == 0:
        return []

    try:

        with OUTPUT_FILE.open(
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        if isinstance(data, list):
            return data

        return []

    except json.JSONDecodeError:

        print(
            "Existing applicant_data.json is invalid. "
            "Starting with an empty dataset."
        )

        return []


def save_data(records):
    """
    Save records as formatted JSON.
    """

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            records,
            file,
            indent=2,
            ensure_ascii=False
        )


# ============================================================
# RESUME STATE
# ============================================================

def load_state():
    """Load the saved next-page URL, if one exists."""
    if not STATE_FILE.exists() or STATE_FILE.stat().st_size == 0:
        return {}

    try:
        with STATE_FILE.open("r", encoding="utf-8") as file:
            state = json.load(file)
        return state if isinstance(state, dict) else {}
    except json.JSONDecodeError:
        return {}


def save_state(next_url, record_count):
    """Save enough information to resume after the current page."""
    state = {
        "next_url": next_url,
        "records_collected": record_count
    }

    with STATE_FILE.open("w", encoding="utf-8") as file:
        json.dump(state, file, indent=2)


# ============================================================
# DUPLICATE HANDLING
# ============================================================

def record_key(record):
    """
    Create a stable key used to identify duplicate records.

    Prefer the applicant URL. If there is no individual URL,
    use the normalized raw text.
    """

    url = record.get("url")

    if url:
        return (
            "url",
            url.strip()
        )

    raw_text = record.get(
        "raw_text",
        ""
    )

    normalized_text = " ".join(
        raw_text.split()
    ).lower()

    return (
        "text",
        normalized_text
    )


def deduplicate_records(records):
    """
    Remove duplicate applicants.
    """

    unique_records = []

    seen = set()

    for record in records:

        key = record_key(
            record
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        unique_records.append(
            record
        )

    return unique_records


# ============================================================
# DEBUG OUTPUT
# ============================================================

def inspect_page(html):
    """
    Print useful information about the captured page.
    """

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    print("\n========== PAGE INSPECTION ==========")

    if soup.title:
        print(
            "PAGE TITLE:",
            soup.title.get_text(
                strip=True
            )
        )

    print(
        "tr tags:",
        len(soup.find_all("tr"))
    )

    print(
        "div tags:",
        len(soup.find_all("div"))
    )

    print(
        "links:",
        len(soup.find_all("a"))
    )

    print(
        "=====================================\n"
    )

def merge_records(existing_records, new_records):
    """
    Merge records using the applicant URL.

    Existing records are preserved, but new non-null comment
    values can fill in fields that were previously missing.
    
    Added because I realized my first 2k data did not pull comments from GradCafe during my first few scrapes
    
    This block in def main() was edited to call upon def merge_records() when rescraping was done:
    
    before = len(all_records)
        all_records.extend(page_records)
        all_records = deduplicate_records(all_records)
        added = len(all_records) - before
    
    """

    records_by_key = {}

    for record in existing_records:
        key = record_key(record)
        records_by_key[key] = record

    for new_record in new_records:
        key = record_key(new_record)

        if key not in records_by_key:
            records_by_key[key] = new_record
            continue

        old_record = records_by_key[key]

        for field, new_value in new_record.items():

            if new_value not in (None, "", []):
                old_record[field] = new_value

    return list(records_by_key.values())

# ============================================================
# MAIN PROGRAM
# ============================================================

def main():
    all_records = deduplicate_records(load_data())
    start_count = len(all_records)

    tab_info = get_gradcafe_tab_info()
    if not tab_info:
        print(f"Open {RESULTS_URL} in normal Google Chrome, then rerun.")
        return

    # Keep the urllib3 check required by the assignment, but do not
    # attempt to bypass a 403 response.
    status = test_urllib3(RESULTS_URL)
    print(f"urllib3 status: {status}")

    state = load_state()
    saved_url = state.get("next_url")
    browser_url = tab_info.rsplit(" | ", 1)[-1].strip()

    # If resume state exists, it wins. Otherwise start from the page
    # already open in Chrome so an existing session is not discarded.
    current_url = saved_url or browser_url or RESULTS_URL

    if browser_url != current_url:
        navigate_gradcafe_tab(current_url)
        time.sleep(5)

    print(f"Starting records: {start_count:,}")
    if saved_url:
        print("Resume state found; continuing from the saved next page.")

    pages_processed = 0

    while len(all_records) < TARGET_RECORDS:
        if (
            MAX_PAGES_PER_RUN is not None
            and pages_processed >= MAX_PAGES_PER_RUN
        ):
            break

        html = get_chrome_html()
        if not html:
            print("No HTML was captured. Stopping.")
            break

        save_html(html)

        if is_blocked(html):
            print(
                "GradCafe is showing a verification/blocking page. "
                "Complete it manually in Chrome, then rerun."
            )
            break

        page_records = parse_page(html)
        if not page_records:
            print("No applicant records found. Stopping.")
            break

        before = len(all_records)
        all_records.extend(page_records)
        all_records = deduplicate_records(all_records)
        added = len(all_records) - before

        save_data(all_records)

        # Capture the site's actual cursor-based next page and save it
        # immediately so an interrupted run can resume here.
        next_url = get_next_page_url(html)
        save_state(next_url, len(all_records))

        pages_processed += 1
        print(
            f"Page {pages_processed}: "
            f"parsed {len(page_records)}, "
            f"new {added}, "
            f"total {len(all_records):,}"
        )

        if len(all_records) >= TARGET_RECORDS:
            break

        if not next_url:
            print("No next-page link found. Stopping.")
            break

        if next_url == current_url:
            print("Next-page URL did not change. Stopping.")
            break

        if (
            MAX_PAGES_PER_RUN is not None
            and pages_processed >= MAX_PAGES_PER_RUN
        ):
            break

        navigate_gradcafe_tab(next_url)
        current_url = next_url
        time.sleep(5)

    print(
        f"Finished: {len(all_records):,}/{TARGET_RECORDS:,} records "
        f"({len(all_records) - start_count:+,} this run)."
    )
    print(f"Data: {OUTPUT_FILE} | Resume state: {STATE_FILE}")


if __name__ == "__main__":
    main()
