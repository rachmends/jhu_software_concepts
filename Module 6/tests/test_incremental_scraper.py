"""Tests for the container-compatible incremental scraper."""

from unittest.mock import Mock

import pytest

from worker.etl import incremental_scraper as scraper


def make_page(urls, next_url=None):
    """Build a representative GradCafe-style results page."""
    rows = "".join(
        f'<tr><td><a href="{url}">Accepted</a></td></tr>'
        for url in urls
    )
    next_link = (
        f'<a rel="next" href="{next_url}">Next</a>'
        if next_url else ""
    )
    return f"<html><body><table>{rows}</table>{next_link}</body></html>"


def test_fetch_page_success():
    response = Mock(status=200, data=b"<html><body>Results</body></html>")
    client = Mock()
    client.request.return_value = response

    result = scraper.fetch_page("https://example.com", http=client)

    assert "Results" in result


def test_fetch_page_http_error():
    client = Mock()
    client.request.return_value = Mock(status=403)

    with pytest.raises(RuntimeError, match="HTTP 403"):
        scraper.fetch_page("https://example.com", http=client)


def test_fetch_page_verification():
    client = Mock()
    client.request.return_value = Mock(
        status=200,
        data=b"<html><title>Just a moment</title></html>",
    )

    with pytest.raises(RuntimeError, match="verification"):
        scraper.fetch_page("https://example.com", http=client)


def test_collect_new_records(monkeypatch):
    monkeypatch.setattr(
        scraper,
        "_parse_page",
        lambda html: (
            [{"url": "/new"}, {"url": "/existing"}]
            if html == "first"
            else [{"url": "/existing"}]
        ),
    )
    monkeypatch.setattr(
        scraper,
        "_get_next_page_url",
        lambda html: "https://example.com/page2"
        if html == "first" else None,
    )

    pages = iter(["first", "second"])

    result = scraper.collect_new_records(
        [{"url": "/existing"}],
        max_pages=2,
        fetcher=lambda url: next(pages),
    )

    assert result == [{"url": "/new"}]


def test_collect_rejects_empty_page(monkeypatch):
    monkeypatch.setattr(scraper, "_parse_page", lambda html: [])

    with pytest.raises(RuntimeError, match="no recognizable"):
        scraper.collect_new_records([], fetcher=lambda url: "<html/>")


def test_collect_rejects_invalid_limit():
    with pytest.raises(ValueError, match="positive"):
        scraper.collect_new_records([], max_pages=0)


def test_collect_detects_pagination_loop(monkeypatch):
    monkeypatch.setattr(
        scraper,
        "_parse_page",
        lambda html: [{"url": html}],
    )
    monkeypatch.setattr(
        scraper,
        "_get_next_page_url",
        lambda html: scraper.RESULTS_URL,
    )

    with pytest.raises(RuntimeError, match="pagination loop"):
        scraper.collect_new_records(
            [],
            max_pages=2,
            fetcher=lambda url: "new-record",
        )
