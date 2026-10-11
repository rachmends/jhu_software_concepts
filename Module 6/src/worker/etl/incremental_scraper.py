"""Collect incremental GradCafe records in a Linux-compatible worker."""

import os

import urllib3

from scrape import (
    RESULTS_URL,
    _get_next_page_url,
    _is_blocked,
    _parse_page,
)
from scrape_records import deduplicate_records, record_key


def fetch_page(url, http=None):
    """Fetch HTML, raising an error on blocked or unsuccessful responses."""
    client = http if http is not None else urllib3.PoolManager()

    response = client.request(
        "GET",
        url,
        timeout=urllib3.Timeout(connect=10.0, read=30.0),
        retries=False,
    )

    if response.status != 200:
        raise RuntimeError(
            f"GradCafe request failed: HTTP {response.status} for {url}"
        )

    html = response.data.decode("utf-8")

    if _is_blocked(html):
        raise RuntimeError(
            "GradCafe returned a verification page; "
            "automated collection cannot continue."
        )

    return html


def collect_new_records(existing_records, max_pages=None, fetcher=None):
    """Collect records until previously collected results are encountered."""
    if max_pages is None:
        max_pages = int(os.getenv("SCRAPE_MAX_PAGES", "10"))

    if max_pages < 1:
        raise ValueError("max_pages must be positive")

    get_html = fetcher if fetcher is not None else fetch_page

    known_keys = {
        record_key(record)
        for record in existing_records
    }

    new_records = []
    current_url = RESULTS_URL
    visited_urls = set()

    for _ in range(max_pages):
        if current_url in visited_urls:
            raise RuntimeError("GradCafe pagination loop detected")

        visited_urls.add(current_url)

        html = get_html(current_url)
        page_records = _parse_page(html)

        if not page_records:
            raise RuntimeError(
                "GradCafe returned no recognizable applicant records"
            )

        page_new = [
            record
            for record in page_records
            if record_key(record) not in known_keys
        ]

        if not page_new:
            break

        for record in page_new:
            known_keys.add(record_key(record))

        new_records.extend(page_new)

        next_url = _get_next_page_url(html)

        if not next_url:
            break

        current_url = next_url

    return deduplicate_records(new_records)
