## robots.txt Compliance

Before scraping GradCafe, I reviewed the site's `robots.txt` file at:

`https://www.thegradcafe.com/robots.txt`

The `robots.txt` file permits access to the public site while identifying restricted paths such as `/signin`, `/register`, `/forgot-password`, `/reset-password`, `/confirm-password`, `/verify-email`, and `/profile`. The scraper only collects data from the publicly accessible GradCafe survey/admissions-results pages and does not access these restricted paths.

The scraper also uses a delay between page requests and does not attempt to bypass CAPTCHAs, rate limits, authentication requirements, or other access controls. If GradCafe presents a verification or blocking page, scraping is stopped and any required verification is completed manually in the normal browser before scraping resumes.

A screenshot of the `robots.txt` file is included in the repository as evidence that the site's scraping directives were reviewed before data collection.

## Data Validation

The scraped JSON data can be validated directly from the terminal without requiring a separate validation script.

To verify the total number of records, number of unique URLs, duplicate URLs, missing required keys, missing values, comment count, invalid GPA values, and preservation of raw text, run:

```bash
python - <<'PY'
import json
from collections import Counter

with open("applicant_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

required_keys = [
    "program",
    "university",
    "comments",
    "date_added",
    "url",
    "status",
    "decision_date",
    "term",
    "student_type",
    "gre",
    "gre_v",
    "degree",
    "gpa",
    "gre_aw",
    "raw_text",
]

urls = [
    record.get("url")
    for record in data
    if record.get("url")
]

print("TOTAL RECORDS:", len(data))
print("RECORDS WITH URL:", len(urls))
print("UNIQUE URLS:", len(set(urls)))
print("DUPLICATE URLS:", len(urls) - len(set(urls)))

print("\nMISSING VALUES:")
for key in required_keys:
    missing = sum(
        record.get(key) in (None, "")
        for record in data
    )
    print(f"{key:18} {missing} / {len(data)}")

print("\nMISSING KEYS:")
for key in required_keys:
    missing = sum(
        key not in record
        for record in data
    )
    print(f"{key:18} {missing}")

print("\nSTATUS COUNTS:")
print(
    Counter(
        record.get("status")
        for record in data
    )
)

print("\nDEGREE COUNTS:")
print(
    Counter(
        record.get("degree")
        for record in data
    )
)

print(
    "\nRECORDS WITH COMMENTS:",
    sum(
        bool(record.get("comments"))
        for record in data
    )
)

bad_gpa = []

for record in data:
    gpa = record.get("gpa")

    if gpa not in (None, ""):
        try:
            value = float(gpa)

            if value < 0 or value > 4.0:
                bad_gpa.append(record)

        except (TypeError, ValueError):
            bad_gpa.append(record)

print("\nBAD GPA VALUES:", len(bad_gpa))

print(
    "MISSING RAW TEXT:",
    sum(
        not record.get("raw_text")
        for record in data
    )
)
PY
```

A successful validation should confirm that the dataset contains unique applicant URLs, all required JSON keys are present, raw source text is retained for traceability, and numeric GPA values fall within the expected range. Missing values for optional applicant-submitted fields such as GRE scores or comments may occur when the original GradCafe record does not provide those values.
