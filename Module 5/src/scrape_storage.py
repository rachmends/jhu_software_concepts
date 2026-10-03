"""Persist GradCafe scraper data and resume state."""

import json


def load_data(output_file):
    """Load previously collected GradCafe applicant records."""
    if not output_file.exists() or output_file.stat().st_size == 0:
        return []

    try:
        with output_file.open("r", encoding="utf-8") as file_handle:
            data = json.load(file_handle)
    except json.JSONDecodeError:
        print(
            "Existing applicant_data.json is invalid. "
            "Starting with an empty dataset."
        )
        return []

    return data if isinstance(data, list) else []


def save_data(output_file, records):
    """Save GradCafe applicant records as formatted UTF-8 JSON."""
    with output_file.open("w", encoding="utf-8") as file_handle:
        json.dump(
            records,
            file_handle,
            indent=2,
            ensure_ascii=False,
        )


def load_state(state_file):
    """Load saved scraper resume state."""
    if not state_file.exists() or state_file.stat().st_size == 0:
        return {}

    try:
        with state_file.open("r", encoding="utf-8") as file_handle:
            state = json.load(file_handle)
    except json.JSONDecodeError:
        return {}

    return state if isinstance(state, dict) else {}


def save_state(state_file, next_url, record_count):
    """Save enough information to resume after the current page."""
    state = {
        "next_url": next_url,
        "records_collected": record_count,
    }

    with state_file.open("w", encoding="utf-8") as file_handle:
        json.dump(state, file_handle, indent=2)
