# Module 2: GradCafe Web Scraping

## Name

**Rachael Mends**  
**JHED ID:** rmends1

## Module Info

**Module:** Module 2  
**Assignment:** Web Scraping  
**Due Date:** September 13, 2026

## Project Overview

This project collects publicly available graduate admissions results from GradCafe, structures the applicant data as JSON, and uses a locally hosted language model to standardize program and university names.

The scraper was designed to collect 50,000 applicant records. The assignment requires at least 30,000 records.

## Approach

This project uses a resumable hybrid web-scraping and local LLM cleaning workflow. The scraping portion collects publicly available GradCafe admissions results and preserves both structured fields and raw source text. The cleaning portion uses the locally hosted language model provided with the assignment to generate standardized program and university names without destructively modifying the original scraped values.

The implementation was designed around several practical issues encountered while accessing the live GradCafe website. Direct urllib/urllib3 requests returned HTTP 403 responses, while a Selenium-controlled browser could encounter repeated Cloudflare verification. Therefore, the scraper uses the hybrid Chrome capture approach described in the assignment update.

GradCafe is opened in a normal Google Chrome browser. Any required Cloudflare verification is completed manually by the user in the normal browser. Python then uses `subprocess` with macOS AppleScript to capture the rendered HTML from the open GradCafe survey tab. The HTML is parsed using BeautifulSoup, regular expressions, and Python string methods.

The scraper extracts applicant information into structured Python dictionaries, identifies the actual next-page URL from the rendered HTML, saves the resulting records as JSON, and stores pagination state so the process can resume after an interruption.

The scraper was intentionally run in batches rather than attempting to collect all 50,000 records in one uninterrupted execution. `MAX_PAGES_PER_RUN` controls the maximum number of pages processed during an individual run and was manually adjusted as needed during collection. Because the next-page state is saved in `scrape_state.json`, subsequent runs continue from the saved page rather than restarting the dataset.

After scraping, `clean.py` uses the provided local TinyLlama model as a first-pass standardizer. Before applying the model to the full dataset, I tested the LLM pipeline using a sample of 10 scraped applicant records. This test was used to verify that the local model executed correctly, determine how the provided LLM expected its input to be structured, and identify systematic errors that could be corrected through post-processing.

The final cleaning workflow preserves the original applicant data and adds separate LLM-generated standardized program and university fields.

## Project Structure

The primary files and directories used by this project are:

- `scrape.py` - collects and parses GradCafe applicant records.
- `clean.py` - runs the local LLM cleaning process and post-processing.
- `applicant_data.json` - scraped applicant dataset.
- `llm_extend_applicant_data.json` - dataset containing the LLM-generated standardized fields.
- `scrape_state.json` - stores scraper progress so interrupted scraping can resume.
- `llm_hosting/` - provided local LLM hosting code and supporting files.
- `requirements.txt` - Python dependencies required by the project.
- `screenshot.jpg` - evidence that GradCafe's `robots.txt` file was reviewed.

## Requirements

Python 3.10 or later is required.

Install the required Python packages with:

```bash
python -m pip install -r requirements.txt
```

The project uses the following third-party packages:

- BeautifulSoup
- urllib3
- Flask
- huggingface_hub
- llama-cpp-python

The remaining modules used by the project, including `json`, `re`, `subprocess`,
`time`, `pathlib`, `argparse`, `hashlib`, `os`, `shutil`, `sys`,
`concurrent.futures`, `difflib`, and `typing`, are part of the Python standard
library.

## Running the Scraper

From the Module 2 directory, run:

```bash
python scrape.py
```

The scraper saves applicant records to:

```text
applicant_data.json
```

The target for this project is 50,000 applicant records.

The scraper does not need to collect all 50,000 records in one execution. The
`MAX_PAGES_PER_RUN` setting in `scrape.py` controls how many GradCafe pages are
processed during an individual run. This value was manually adjusted during
data collection.

Progress is saved during scraping so that an interrupted or completed batch can
resume rather than restarting from the beginning. The saved pagination state is
stored in:

```text
scrape_state.json
```

Running:

```bash
python scrape.py
```

again causes the scraper to continue from the saved next page.

This batching and resume behavior was especially useful because collecting
50,000 records requires processing thousands of GradCafe result pages and a
single uninterrupted browser session is not required.

## GradCafe Hybrid Capture Approach

A normal urllib/urllib3 request to GradCafe may receive an HTTP 403 response,
and a Selenium-controlled browser may encounter repeated Cloudflare
verification. Therefore, this project uses the hybrid capture approach
described in the assignment update.

GradCafe is opened in a normal Google Chrome browser. Any Cloudflare
verification is completed manually by the user in the normal browser.

The scraper then uses a helper implemented with Python's `subprocess` module
and macOS AppleScript to capture the currently rendered HTML from the open
GradCafe survey page in Chrome. The captured HTML is passed to BeautifulSoup
for parsing.

The workflow is:

1. Open the public GradCafe admissions-results page in normal Chrome.
2. Complete any required browser verification manually.
3. Capture the rendered HTML from the GradCafe Chrome tab.
4. Parse the HTML using BeautifulSoup, Python string methods, and regular
   expressions.
5. Extract the applicant information into structured Python dictionaries.
6. Save the records to `applicant_data.json`.
7. Determine the real next-page URL from the rendered page.
8. Navigate Chrome to that next page.
9. Wait between pages so the next applicant table has time to render and rapid
   repeated page navigation is avoided.
10. Save the next-page state so scraping can resume after an interruption.
11. Continue until the configured maximum number of pages for that run is
    reached or the target number of records is collected.

The scraper does not automate completion of CAPTCHAs or other verification
mechanisms. If verification is required, it is completed manually in the normal
Chrome browser.

The use of the actual next-page URL is important because GradCafe pagination
does not rely solely on a simple `?page=` value. The scraper retrieves the
actual next-page URL from the rendered page before continuing.

## Scraped Fields

The structured applicant records include fields such as:

- program
- university
- comments
- date added
- applicant URL
- admission status
- decision date
- semester/year
- student type
- GRE
- GRE verbal
- GRE analytical writing
- degree
- GPA
- raw source text

Applicant fields that are not provided by the original GradCafe submission are
represented consistently as missing values rather than being inferred or
fabricated.

Raw source text is retained to provide traceability between the structured
record and the information extracted from GradCafe.

## Resume and Duplicate Handling

Each applicant result URL is used as the primary identifier when determining
whether a record has already been collected. This prevents records from being
duplicated when scraping is stopped and resumed.

The scraper also retains raw text for traceability.

After each successfully processed page, the current data and pagination state
are saved. If scraping stops because of a browser error, page-loading problem,
verification page, configured page limit, or another interruption, the scraper
can be run again:

```bash
python scrape.py
```

It then continues from the saved next page rather than intentionally restarting
the entire collection process.

This allowed the 50,000-record target to be collected across multiple scraping
runs. `MAX_PAGES_PER_RUN` was manually adjusted when longer or shorter scraping
batches were desired.

## robots.txt Compliance

Before scraping GradCafe, I reviewed the site's `robots.txt` file at:

`https://www.thegradcafe.com/robots.txt`

The `robots.txt` file permits access to the public site while identifying
restricted paths such as `/signin`, `/register`, `/forgot-password`,
`/reset-password`, `/confirm-password`, `/verify-email`, and `/profile`. The
scraper only collects data from the publicly accessible GradCafe
survey/admissions-results pages and does not access these restricted paths.

The scraper also uses a delay between page requests and does not attempt to
bypass CAPTCHAs, rate limits, authentication requirements, or other access
controls. If GradCafe presents a verification or blocking page, scraping is
stopped and any required verification is completed manually in the normal
browser before scraping resumes.

A screenshot of the `robots.txt` file is included in the repository as evidence
that the site's scraping directives were reviewed before data collection.

## Local LLM Cleaning

The scraped data is standardized using the local LLM-hosting implementation
provided with the assignment.

The local model performs a first-pass standardization of program and university
names. The results are then passed through additional post-processing rules to
correct systematic spelling, capitalization, and abbreviation issues observed
in the model output.

Run the cleaning process with:

```bash
python clean.py --workers 2
```

The number of workers can be changed, for example:

```bash
python clean.py --workers 4
```

The cleaning process supports resumable processing so that completed work does
not need to be intentionally repeated after an interruption.

The final cleaned dataset is written to:

```text
llm_extend_applicant_data.json
```

The original scraped fields remain in the output so the LLM-generated
standardizations can be compared with the original applicant-provided
information.

## 10-Record LLM Sample Test

Before running the local LLM against the complete scraped dataset, I created a
10-record sample of `applicant_data.json` and used it to test the provided
LLM-hosting pipeline.

This test served several purposes:

- Confirm that the provided TinyLlama model could be downloaded and executed
  locally.
- Confirm that `llm_hosting/app.py` could process the structure of the scraped
  JSON records.
- Verify the structure of the LLM-generated program and university fields.
- Identify how the provided prompt expected program and university information
  to be supplied.
- Identify systematic model errors before processing tens of thousands of
  records.
- Test the post-processing logic before running the full cleaning process.

The initial sample test showed that passing only the scraped `program` field
did not give the LLM enough information to reliably identify the university.
Inspection of the provided LLM prompt showed that it expected a single input
string containing both program and university information.

This led to the modification described below.

The sample also demonstrated that the lightweight model could produce small
spelling, capitalization, or standardization errors. These observations were
used to create targeted post-processing rules while preserving the original
scraped data.

## LLM Hosting Modifications

The provided `llm_hosting/app.py` was modified to support the structure of the
scraped GradCafe dataset.

The scraper stores `program` and `university` as separate fields, while the
provided local LLM prompt expects a single input string containing both the
program and university.

The LLM input construction was therefore updated in both relevant processing
paths in `app.py` to combine the existing fields before passing them to the
model:

```python
program = (row or {}).get("program") or ""
university = (row or {}).get("university") or ""

program_text = f"{program}, {university}".strip(", ")
result = _call_llm(program_text)
```

This modification was made in both relevant locations where rows are passed to
the local LLM.

This modification does not destructively modify the original scraped `program`
or `university` fields. The combined string is used only as input to the local
LLM so that the model has both pieces of information when generating its
standardized values.

The standardized values are stored separately from the original scraped
values, including the fields:

```text
llm-generated-program
llm-generated-university
```

This preserves the original applicant-provided information for reproducibility
and traceability.

## LLM Post-Processing

The local LLM is used as a first-pass standardizer rather than being assumed to
produce perfect output.

During the 10-record sample test, systematic model errors were identified and
corrected through post-processing in `clean.py`.

For example:

```text
Ellectrical Engineering And Computer Science
```

is corrected to:

```text
Electrical Engineering and Computer Science
```

and:

```text
Friedrich-Schiller Universität Jenna
```

is corrected to:

```text
Friedrich-Schiller Universität Jena
```

Abbreviation/capitalization corrections are also applied where appropriate,
including forms such as `UPF` and `BUET`.

The canonical lists supplied with the assignment are retained. Additional
post-processing rules can be added when systematic model errors are identified.

Because the local LLM is a lightweight first-pass standardizer, some imperfect
standardizations may remain. The original scraped fields are therefore
preserved alongside the generated standardized fields.

## Parallel and Resumable LLM Processing

Processing tens of thousands of applicant records through a local LLM can take
a significant amount of time. `clean.py` therefore supports parallel and
resumable processing.

The number of workers can be selected from the command line:

```bash
python clean.py --workers 2
```

or, when additional system resources are available:

```bash
python clean.py --workers 4
```

The dataset is divided into chunks for the worker processes. Progress is
tracked during processing, and completed work can be retained between runs.

The cleaning workflow also checks previously cleaned records so that when the
raw dataset has grown through additional scraping, already cleaned records do
not need to be intentionally processed again. Remaining records can then be
processed and merged with the previously cleaned prefix.

After processing, the chunks are merged back into their original order,
post-processing corrections are applied, and the final dataset is written to
`llm_extend_applicant_data.json`.

## Data Validation

The scraped JSON data can be validated directly from the terminal without
requiring a separate validation script.

To verify the total number of records, number of unique URLs, duplicate URLs,
missing required keys, missing values, comment count, invalid GPA values, and
preservation of raw text, run:

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

A successful validation should confirm that the dataset contains unique
applicant URLs, all required JSON keys are present, raw source text is retained
for traceability, and numeric GPA values fall within the expected range.

Missing values for optional applicant-submitted fields such as GRE scores or
comments may occur when the original GradCafe record does not provide those
values.

## Final Cleaned-Data Validation

After `clean.py` finishes, the raw and LLM-extended datasets can be checked with:

```bash
python - <<'PY'
import json

with open("applicant_data.json", "r", encoding="utf-8") as f:
    raw = json.load(f)

with open(
    "llm_extend_applicant_data.json",
    "r",
    encoding="utf-8"
) as f:
    cleaned = json.load(f)

print("Raw records:", len(raw))
print("Cleaned records:", len(cleaned))
print("Counts match:", len(raw) == len(cleaned))

print(
    "Missing LLM program:",
    sum(
        not row.get("llm-generated-program")
        for row in cleaned
    )
)

print(
    "Missing LLM university:",
    sum(
        not row.get("llm-generated-university")
        for row in cleaned
    )
)

print(
    "Missing original program:",
    sum(
        "program" not in row
        for row in cleaned
    )
)

print(
    "Missing original university:",
    sum(
        "university" not in row
        for row in cleaned
    )
)
PY
```

For the completed project, `applicant_data.json` and
`llm_extend_applicant_data.json` should contain the same number of records, and
the cleaned dataset should preserve the original program and university fields
while adding the LLM-generated standardized fields.

## Known Bugs and Limitations

No known bug currently prevents the scraper from collecting and structuring
the required applicant records.

The hybrid capture process depends on an open Google Chrome GradCafe survey tab
and macOS AppleScript. Occasionally, Chrome may fail to return the rendered
HTML or a GradCafe page may not finish rendering before the scraper attempts to
capture it. The scraper saves its progress continuously, so if this occurs it
can be restarted from the saved next page without discarding the records
already collected.

A possible future improvement would be to add additional checks or retry logic
around Chrome HTML capture so that a temporary AppleScript or page-rendering
failure does not require restarting the scraper process.

The use of `MAX_PAGES_PER_RUN` is intentional and is not a correctness bug.
The complete dataset was collected through multiple resumable runs rather than
requiring a single uninterrupted scrape. The maximum number of pages per run
was manually adjusted during collection.

GradCafe applicant information is user-submitted, so individual records do not
always contain every possible field. Missing GRE scores, GPA values, comments,
student type, or other optional information may therefore represent missing
source data rather than a scraping error.

The local TinyLlama model is intentionally lightweight and does not perfectly
standardize every program or university name. The 10-record sample test was
used to identify systematic errors before full processing, and recurring
issues identified during testing were addressed through post-processing.
Additional uncommon standardization errors may remain in the LLM-generated
fields.

The original program and university values and raw scraped text are retained so
that generated standardized values can be inspected, reproduced, or improved
later.