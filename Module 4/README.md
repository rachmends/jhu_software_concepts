# Module 4: Testing and Documentation

## Name

**Rachael Mends**  
**JHED ID:** rmends1

## Module Info

**Module:** Module 4  
**Assignment:** Testing and Documentation  
**Due Date:** September 27, 2026

## Project Overview

This application collects graduate admissions results from GradCafe, cleans and
processes the applicant data, stores the records in PostgreSQL, and displays
summary analyses through a Flask web application.

The application allows a user to:

- View analyses of GradCafe admissions data.
- Pull newly available GradCafe records.
- Process and load new records into PostgreSQL.
- Refresh the analysis using the latest data stored in the database.

## Requirements

This project uses Python 3.11 and PostgreSQL.

Install the required Python packages from the `Module 4` directory:

```bash
pip install -r requirements.txt
```

The project uses packages including Flask, SQLAlchemy, psycopg, urllib3,
BeautifulSoup, pytest, pytest-cov, and Sphinx.

## PostgreSQL Setup

PostgreSQL must be running before starting the application.

The application uses environment variables for the database connection. Set
the following variables in your terminal:

```bash
export DB_NAME=gradcafe
export DB_USER=YOUR_POSTGRES_USER
export DB_PASSWORD=YOUR_POSTGRES_PASSWORD
export DATABASE_URL="postgresql+psycopg://YOUR_POSTGRES_USER:YOUR_POSTGRES_PASSWORD@localhost:5432/gradcafe"
```

Replace the username and password with the credentials for your local
PostgreSQL installation.

The database name used for this project is:

```text
gradcafe
```

## Running the Application

From the `Module 4` directory, start the Flask application with:

```bash
python src/app.py
```

Open the local Flask address displayed in the terminal in a web browser.

The application displays the GradCafe analysis page containing the analysis
questions and their current results.

## Using the Application

### Pull Data

Click **Pull Data** to check GradCafe for newly available applicant records.

The application checks for new records, processes the retrieved data, and loads
the processed records into PostgreSQL.

Only one data pull can run at a time. If a pull is already running, the
application prevents another pull from starting.

### Update Analysis

Click **Update Analysis** to recalculate the displayed analysis using the
records currently stored in PostgreSQL.

If a data pull is currently running, the application prevents an analysis
update until the pull has completed.

## Data Pipeline

The application's data pipeline consists of three main stages:

1. `scrape.py` retrieves GradCafe applicant records.
2. `clean.py` cleans and normalizes the collected records.
3. `load_data.py` loads the processed records into PostgreSQL.

The Flask application then queries the PostgreSQL data and displays the
analysis results.

## Running the Tests

The automated test suite uses pytest.

From the `Module 4` directory, run the complete test suite with:

```bash
pytest
```

Tests are organized using the following markers:

- `web` — Flask pages and routes
- `buttons` — Pull Data and Update Analysis behavior
- `analysis` — analysis output and formatting
- `db` — database operations
- `integration` — end-to-end application behavior

To run all assignment test groups:

```bash
pytest -m "web or buttons or analysis or db or integration"
```

To run a specific group, use its marker. For example:

```bash
pytest -m db
```

or:

```bash
pytest -m web
```

## Test Coverage

The project uses `pytest-cov` to measure source-code coverage.

Running:

```bash
pytest
```

also produces the configured coverage report.

The committed terminal coverage summary is available in:

```text
coverage_summary.txt
```

## Continuous Integration

The repository uses GitHub Actions to automatically run the pytest suite in a
clean environment with a PostgreSQL service.

The workflow is located at:

```text
.github/workflows/tests.yml
```

Evidence of a successful GitHub Actions run is included in:

```text
actions_success.png
```

## Documentation

Full application documentation is generated with Sphinx and published using
Read the Docs.

The documentation includes:

- Application setup and environment variables
- Web, ETL, and database architecture
- API documentation generated from the Python source code
- Testing instructions, markers, selectors, fixtures, and test doubles

### Published Documentation

**[GradCafe Application Documentation][(https://jhu-software-concepts-rmends.readthedocs.io)]**

To build the documentation locally from the `Module 4` directory:

```bash
sphinx-build -b html docs/source docs/build/html
```

Then open:

```text
docs/build/html/index.html
```