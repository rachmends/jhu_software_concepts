"""Manage duplicate and updated GradCafe applicant records."""


def record_key(record):
    """Create a stable key used to identify duplicate records."""
    url = record.get("url")

    if url:
        return "url", url.strip()

    raw_text = record.get("raw_text", "")
    normalized_text = " ".join(raw_text.split()).lower()

    return "text", normalized_text


def deduplicate_records(records):
    """Remove duplicate applicant records."""
    unique_records = []
    seen = set()

    for record in records:
        key = record_key(record)

        if key in seen:
            continue

        seen.add(key)
        unique_records.append(record)

    return unique_records


def merge_records(existing_records, new_records):
    """Merge records while retaining new nonempty field values."""
    records_by_key = {
        record_key(record): record
        for record in existing_records
    }

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
