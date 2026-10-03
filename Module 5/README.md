# Module 5: Software Assurance + Secure SQL

## Name

**Rachael Mends**  
**JHED ID:** rmends1

## Module Info

**Module:** Module 5  
**Assignment:** Software Assurance + Secure SQL (SQLi Defense)  
**Due Date:** October 4, 2026

## Project Overview

This application collects graduate admissions results from GradCafe, cleans and
processes the applicant data, stores the records in PostgreSQL, and displays
summary analyses through a Flask web application.

Module 5 extends the application with software assurance and secure SQL
practices, including SQL injection defenses, parameterized queries, query
limits, least-privilege database access, dependency analysis, reproducible
environment configuration, packaging, and automated security checks.

The application allows a user to:

- View analyses of GradCafe admissions data.
- Pull newly available GradCafe records.
- Process and load new records into PostgreSQL.
- Refresh the analysis using the latest data stored in the database.

## Requirements

This project uses Python 3.11 and PostgreSQL.

The Python dependencies are declared in:

```text
requirements.txt
```

The project uses packages including Flask, SQLAlchemy, psycopg, urllib3,
Beautiful Soup, pytest, pytest-cov, Pylint, and pydeps.

## PostgreSQL Setup

PostgreSQL must be running before starting the application.

The application uses environment variables for the database connection. Set
the following variables in your terminal:

```bash
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=gradcafe
export DB_USER=gradcafe_app
export DB_PASSWORD="your_database_password"
```

The database used for this project is:

```text
gradcafe
```

Database credentials are supplied through environment variables rather than
stored in the application source code. The `.env.example` file documents the
required environment variables. The real `.env` file is excluded from version
control and should not be committed.

The `gradcafe_app` PostgreSQL role is the application's least-privilege
database account. It is not a PostgreSQL superuser and has only the database
permissions required by the application.

## Fresh Install

Module 5 can be installed from a fresh environment using either **pip** or
**uv**.

### Option 1: pip

From the `Module 5` directory, create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

Upgrade pip and install all dependencies declared in `requirements.txt`:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Install the Module 5 project in editable mode:

```bash
pip install -e .
```

Verify the package installation:

```bash
pip show jhu-software-concepts-module5
```

### Option 2: uv

Create and activate a fresh virtual environment using uv:

```bash
uv venv
source .venv/bin/activate
```

Synchronize the environment with the dependencies declared in
`requirements.txt`:

```bash
uv pip sync requirements.txt
```

Install the Module 5 project in editable mode:

```bash
uv pip install -e .
```

Using `uv pip sync` makes the environment match the declared requirements,
which improves reproducibility.

Both the pip and uv fresh-install workflows were independently verified for
Module 5.

## Running the Application

After completing either installation method, configuring the PostgreSQL
environment variables, and ensuring PostgreSQL is running, start the Flask
application from the `Module 5` directory:

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

The scraping functionality is additionally separated into
`scrape_records.py` and `scrape_storage.py`.

The Flask application queries the PostgreSQL data and displays the analysis
results.

## SQL Injection Defenses

Module 5 uses psycopg SQL composition and parameterized values to defend
against SQL injection.

SQL statements are constructed using `psycopg.sql.SQL`. Dynamic table and
column identifiers are composed using `psycopg.sql.Identifier`, while values
are supplied separately using `%s` placeholders and query parameters rather
than being inserted directly into SQL strings.

SQL statement construction is kept separate from execution and parameter
binding. Queries are therefore executed using a composed statement and a
separate parameter collection rather than SQL strings constructed with
user-supplied values.

The application also enforces bounded query limits. SELECT queries include an
inherent parameterized `LIMIT`, and application logic constrains requested
limits to the permitted range of 1 through 100.

## Database Security

Module 5 uses a dedicated PostgreSQL application role named `gradcafe_app`
rather than running the application through a PostgreSQL superuser.

The role is configured without superuser, database-creation, or role-creation
privileges. It has only the permissions required for the application's normal
database operations:

- `CONNECT` on the `gradcafe` database.
- `USAGE` on the `public` schema.
- `SELECT` and `INSERT` on the `applicants` table.
- `USAGE` and `SELECT` on the `applicants_p_id_seq` sequence.

Schema creation is not performed by the application's normal data-loading
path, so the application role does not require schema-management privileges
such as `DROP`, `ALTER`, or object ownership.

Database credentials are provided through `DB_HOST`, `DB_PORT`, `DB_NAME`,
`DB_USER`, and `DB_PASSWORD` rather than being hard-coded in source code.

## Packaging

The project includes `setup.py` to make Module 5 installable as
`jhu-software-concepts-module5`.

The project can be installed in editable mode using pip:

```bash
pip install -e .
```

or uv:

```bash
uv pip install -e .
```

Packaging provides a consistent installation mechanism for local development,
testing, and continuous integration. Editable installation also reduces
path-related environment problems while allowing source changes to remain
immediately available during development.

## Verify the Installation

Run the complete test suite with:

```bash
pytest
```

The verified Module 5 test suite contains 179 tests and achieves 100% coverage
across the ten source modules.

## Pylint

Pylint is used to check all Python files inside the `src` directory.

Run:

```bash
pylint src
```

The completed Module 5 source code achieves a Pylint score of **10.00/10**
with no warnings or errors.

## Dependency Graph

The project's Python module dependencies were analyzed using pydeps and
Graphviz.

The generated dependency graph is saved in the Module 5 directory as:

```text
dependency.svg
```

The graph represents the project's internal source modules together with its
major external dependency families, including Flask, SQLAlchemy, psycopg,
Beautiful Soup, and urllib3. Low-level SQLAlchemy and psycopg implementation
modules were filtered from the final visualization to preserve meaningful
dependency detail while keeping the graph readable.

The required 5–7 sentence analysis of the dependency graph is included in the
final Module 5 PDF report.

## Security Analysis

Step 6 uses Snyk to scan the application's dependencies for known security
vulnerabilities.

The dependency scan is run with:

```bash
snyk test
```

The required Snyk scan evidence will be saved as:

```text
snyk-analysis.png
```

The final documentation will describe any vulnerabilities identified by the
scan and any remediation performed.

## Continuous Integration

Step 7 uses GitHub Actions to automate the required Module 5 software
assurance checks on pushes and pull requests.

The workflow is located at:

```text
.github/workflows/ci.yml
```

The required workflow is configured to perform four separate checks:

- Run Pylint and fail if the score is below 10.00/10.
- Generate and validate `dependency.svg` using pydeps and Graphviz.
- Run the Snyk dependency scan.
- Run the pytest test suite and fail if any tests fail.

A screenshot of the successful GitHub Actions workflow run will be included
in the final Module 5 PDF report after the workflow has been executed
successfully.

## Documentation

The final Module 5 documentation covers:

- Fresh installation and execution using pip and uv.
- Why packaging and `setup.py` are used.
- Dependency graph analysis.
- SQL injection defenses.
- Least-privilege PostgreSQL configuration.
- SQL LIMIT enforcement and safe statement composition/parameterization.
- Snyk dependency-security analysis.
- GitHub Actions continuous integration.

The primary Module 5 deliverables include:

```text
dependency.svg
setup.py
requirements.txt
.env.example
snyk-analysis.png
.github/workflows/ci.yml
module_5_report.pdf
```