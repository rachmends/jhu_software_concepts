"""Collect and process graduate application data from GradCafe."""

import re
import subprocess
import time
from pathlib import Path

import urllib3
from bs4 import BeautifulSoup

from scrape_storage import (
    load_data as load_saved_data,
    load_state,
    save_data as save_saved_data,
    save_state,
)
from scrape_records import (
    deduplicate_records as _deduplicate_records,
    merge_records as _merge_records,
    record_key as _record_key,
)


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
MAX_PAGES_PER_RUN = 500

http = urllib3.PoolManager()

# ============================================================
# URLLIB3 TEST
# ============================================================

def _test_urllib3(url):
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

def _get_gradcafe_tab_info():
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


def _get_chrome_html():
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


def _navigate_gradcafe_tab(url):
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

def _save_html(html):
    """
    Save the most recently captured HTML for debugging.
    """

    HTML_FILE.write_text(
        html,
        encoding="utf-8"
    )


def _is_blocked(html):
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

def _get_next_page_url(html):
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

def _extract_degree(text):
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


def _extract_date_added(text):
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


def _extract_status(text):
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


def _extract_decision_date(text):
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


def _extract_term(text):
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


def _extract_student_type(text):
    """
    Determine International or American.
    """

    lowered = text.lower()

    if "international" in lowered:
        return "International"

    if "american" in lowered:
        return "American"

    return None


def _extract_gpa(text):
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


def _extract_gre(text):
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


def _extract_gre_v(text):
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


def _extract_gre_aw(text):
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

def _collect_extra_rows(rows, start_index):
    """Collect detail text and comments following an applicant row."""
    detail_parts = []
    comment_parts = []
    index = start_index

    while index < len(rows):
        extra_row = rows[index]

        if "tw-border-none" not in extra_row.get("class", []):
            break

        comment_element = extra_row.select_one(
            "p.tw-text-gray-500.tw-text-sm.tw-my-0"
        )

        if comment_element:
            comment_text = comment_element.get_text(" ", strip=True)
            if comment_text:
                comment_parts.append(comment_text)
        else:
            detail_text = extra_row.get_text(" ", strip=True)
            if detail_text:
                detail_parts.append(detail_text)

        index += 1

    detail_text = " ".join(detail_parts)
    comments = " ".join(comment_parts) or None

    return detail_text, comments, index


def _extract_program_info(row, degree):
    """Extract university and program values from an applicant row."""
    cells = [
        cell.get_text(" ", strip=True)
        for cell in row.find_all("td", recursive=False)
    ]

    university = cells[0] or None if cells else None
    program = cells[1] or None if len(cells) >= 2 else None

    if program and degree:
        program = re.sub(
            rf"\s+{re.escape(degree)}\s*$",
            "",
            program,
            flags=re.IGNORECASE,
        ).strip()

    return university, program


def _extract_applicant_url(row):
    """Extract the GradCafe applicant-result URL from a row."""
    for link in row.find_all("a", href=True):
        href = link.get("href", "")

        if "/result/" in href:
            if href.startswith("http"):
                return href
            return BASE_URL + href

    return None


def _build_record(row, main_text, detail_text, comments, status):
    """Build one GradCafe applicant record."""
    combined_text = f"{main_text} {detail_text}".strip()
    degree = _extract_degree(combined_text)
    university, program = _extract_program_info(row, degree)

    raw_text = " ".join(
        part
        for part in (main_text, detail_text, comments)
        if part
    ).strip()

    return {
        "program": program,
        "university": university,
        "comments": comments,
        "date_added": _extract_date_added(main_text),
        "url": _extract_applicant_url(row),
        "status": status,
        "decision_date": _extract_decision_date(combined_text),
        "term": _extract_term(detail_text),
        "student_type": _extract_student_type(detail_text),
        "gre": _extract_gre(detail_text),
        "gre_v": _extract_gre_v(detail_text),
        "gre_aw": _extract_gre_aw(detail_text),
        "gpa": _extract_gpa(detail_text),
        "degree": degree,
        "raw_text": raw_text,
        "raw_main_text": main_text,
        "raw_detail_text": detail_text,
    }


def _parse_page(html):
    """Parse applicant records from one GradCafe page."""
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.find_all("tr")
    records = []
    index = 0

    while index < len(rows):
        row = rows[index]

        if "tw-border-none" in row.get("class", []):
            index += 1
            continue

        main_text = row.get_text(" ", strip=True)

        detail_text, comments, next_index = _collect_extra_rows(
            rows,
            index + 1,
        )

        combined_text = f"{main_text} {detail_text}".strip()
        status = _extract_status(combined_text)

        if status is not None:
            records.append(
                _build_record(
                    row,
                    main_text,
                    detail_text,
                    comments,
                    status,
                )
            )

        index = next_index

    return records


def load_data():
    """Load applicant records from the configured output file."""
    return load_saved_data(OUTPUT_FILE)


def save_data(records):
    """Save applicant records to the configured output file."""
    save_saved_data(OUTPUT_FILE, records)


def _load_state():
    """Load scraper state from the configured state file."""
    return load_state(STATE_FILE)


def _save_state(next_url, record_count):
    """Save scraper state to the configured state file."""
    save_state(STATE_FILE, next_url, record_count)


# ============================================================
# DUPLICATE HANDLING
# ============================================================

def _inspect_page(html):
    """Print useful information about the captured page."""
    soup = BeautifulSoup(html, "html.parser")

    print("\n========== PAGE INSPECTION ==========")

    if soup.title:
        print(
            "PAGE TITLE:",
            soup.title.get_text(strip=True),
        )

    print("tr tags:", len(soup.find_all("tr")))
    print("div tags:", len(soup.find_all("div")))
    print("links:", len(soup.find_all("a")))
    print("=====================================\n")


# ============================================================
# MAIN PROGRAM
# ============================================================

def _capture_page_records():
    """Capture and validate applicant records from the current page."""
    html = _get_chrome_html()

    if not html:
        print("No HTML was captured. Stopping.")
        return None, None

    _save_html(html)

    if _is_blocked(html):
        print(
            "GradCafe is showing a verification/blocking page. "
            "Complete it manually in Chrome, then rerun."
        )
        return None, None

    page_records = _parse_page(html)

    if not page_records:
        print("No applicant records found. Stopping.")
        return None, None

    return html, page_records


def _store_page_records(all_records, page_records, html):
    """Merge, save, and report records collected from one page."""
    before = len(all_records)
    all_records.extend(page_records)
    all_records = _deduplicate_records(all_records)
    added = len(all_records) - before

    save_data(all_records)

    next_url = _get_next_page_url(html)
    _save_state(next_url, len(all_records))

    return all_records, added, next_url


def _page_limit_reached(pages_processed):
    """Return whether the configured per-run page limit was reached."""
    return (
        MAX_PAGES_PER_RUN is not None
        and pages_processed >= MAX_PAGES_PER_RUN
    )


def scrape_data():
    """Run the main paginated GradCafe collection process."""
    all_records = _deduplicate_records(load_data())
    start_count = len(all_records)
    tab_info = _get_gradcafe_tab_info()

    if not tab_info:
        print(f"Open {RESULTS_URL} in normal Google Chrome, then rerun.")
        return

    status = _test_urllib3(RESULTS_URL)
    print(f"urllib3 status: {status}")

    saved_url = _load_state().get("next_url")
    browser_url = tab_info.rsplit(" | ", 1)[-1].strip()
    current_url = saved_url or browser_url or RESULTS_URL

    if browser_url != current_url:
        _navigate_gradcafe_tab(current_url)
        time.sleep(12)

    print(f"Starting records: {start_count:,}")

    if saved_url:
        print("Resume state found; continuing from the saved next page.")

    pages_processed = 0

    while len(all_records) < TARGET_RECORDS:
        if _page_limit_reached(pages_processed):
            break

        html, page_records = _capture_page_records()

        if page_records is None:
            break

        all_records, added, next_url = _store_page_records(
            all_records,
            page_records,
            html,
        )

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

        if _page_limit_reached(pages_processed):
            break

        _navigate_gradcafe_tab(next_url)
        current_url = next_url
        time.sleep(12)

    print(
        f"Finished: {len(all_records):,}/{TARGET_RECORDS:,} records "
        f"({len(all_records) - start_count:+,} this run)."
    )
    print(f"Data: {OUTPUT_FILE} | Resume state: {STATE_FILE}")


def pull_new_data():
    """
    Retrieve newly available GradCafe applicant records.

    Loads the existing applicant dataset and creates keys for the records that
    have already been collected. The scraper then begins with the newest
    GradCafe results, captures the current page through Chrome, parses the
    applicant records, and compares them with the existing dataset.

    New records are added to ``applicant_data.json`` while previously
    collected records are skipped. Pagination continues until the scraper
    reaches a page containing only records that are already present, no usable
    records are found, GradCafe displays a verification page, or no next page
    is available.

    The function is used by the Flask application's Pull Data workflow.

    Returns:
        int: Number of newly collected applicant records.
    """

    all_records = _deduplicate_records(load_data())
    existing_keys = {
        _record_key(record)
        for record in all_records
    }

    tab_info = _get_gradcafe_tab_info()

    if not tab_info:
        print(
            f"Open {RESULTS_URL} in normal Google Chrome, "
            "then try again."
        )
        return 0

    status = _test_urllib3(RESULTS_URL)
    print(f"urllib3 status: {status}")

    # Part 9 always checks the newest GradCafe results.
    current_url = RESULTS_URL
    _navigate_gradcafe_tab(current_url)
    time.sleep(12)

    pages_processed = 0
    total_new = 0

    while True:

        html = _get_chrome_html()

        if not html:
            print("No HTML was captured. Stopping.")
            break

        _save_html(html)

        if _is_blocked(html):
            print(
                "GradCafe is showing a verification/blocking "
                "page. Complete it manually in Chrome."
            )
            break

        page_records = _parse_page(html)

        if not page_records:
            print("No applicant records found. Stopping.")
            break

        new_records = [
            record
            for record in page_records
            if _record_key(record) not in existing_keys
        ]

        print(
            f"Page {pages_processed + 1}: "
            f"{len(page_records)} records found, "
            f"{len(new_records)} new."
        )

        # If the entire page is already in our dataset,
        # we have reached previously collected data.
        if not new_records:
            print(
                "Reached records already in the dataset. "
                "No older pages need to be checked."
            )
            break

        for record in new_records:
            existing_keys.add(
                _record_key(record)
            )

        all_records = _merge_records(
            all_records,
            new_records
        )

        total_new += len(new_records)
        pages_processed += 1

        save_data(all_records)

        next_url = _get_next_page_url(html)

        if not next_url:
            print("No next-page link found. Stopping.")
            break

        if next_url == current_url:
            print("Next-page URL did not change. Stopping.")
            break

        _navigate_gradcafe_tab(next_url)
        current_url = next_url
        time.sleep(12)

    print(
        f"Pull complete: {total_new} new records found. "
        f"Dataset now contains {len(all_records):,} records."
    )

    return total_new

def main():
    """
    Run the GradCafe scraper from the command line.

    Serves as the command-line entry point for the scraping module and starts
    the primary GradCafe data collection workflow.
    """
    scrape_data()


if __name__ == "__main__":
    main()
