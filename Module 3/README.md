# Module 3: Database Queries Assignment 

## Name

**Rachael Mends**  
**JHED ID:** rmends1

## Module Info

**Module:** Module 3  
**Assignment:** Database Queries Assignment   
**Due Date:** September 20, 2026

## Project Overview

This assignment will introduce you to querying relational databases using SQL and interacting with those databases using an Object-Relational Mapper (ORM)

### Prerequisites

- Python 3.11.10
- PostgreSQL
- Google Chrome

## Setup and Run Instructions

### 1. Install Required Python Packages

Install the project dependencies using the provided `requirements.txt` file:

```bash
python -m pip install -r requirements.txt
```

This project uses PostgreSQL for database storage, `psycopg` for the raw SQL portions of the assignment, SQLAlchemy for ORM-based database access, and Flask for the web application.

### 2. PostgreSQL Database Setup

This project uses a local PostgreSQL database named `gradcafe`. PostgreSQL must be installed and running before the database scripts or Flask application are executed.

Create the database from the terminal:

```bash
createdb gradcafe
```

The database name and PostgreSQL user are supplied to the Python programs through environment variables rather than being hard-coded into the source files. Set the variables before running the project:

```bash
export DB_NAME="gradcafe"
export DB_USER="<your_postgresql_username>"
```

For example, my local PostgreSQL username is `rachrachmendmends`, so my local configuration is:

```bash
export DB_NAME="gradcafe"
export DB_USER="rachrachmendmends"
```

No database password or other credential is stored in the repository.

### 3. Load the Applicant Data into PostgreSQL

The cleaned applicant data is stored in `llm_extend_applicant_data.json`. To create the `applicants` table if necessary and load the cleaned records into PostgreSQL, run:

```bash
python load_data.py
```

`load_data.py` connects to the `gradcafe` PostgreSQL database using `psycopg`, creates the required `applicants` table when necessary, and inserts the cleaned applicant records. Existing records are identified by their unique URLs so that repeatedly running the loader does not create duplicate records.

The number of records currently stored in PostgreSQL can be checked with:

```bash
psql -d gradcafe -c "SELECT COUNT(*) FROM applicants;"
```

### 4. Run the Raw SQL Analysis

The raw SQL analysis for the assignment is contained in `query_data.py`. After PostgreSQL is running, the database has been populated, and the environment variables have been set, run:

```bash
python query_data.py
```

This script connects to PostgreSQL using `psycopg` and executes the SQL queries used to answer the assignment analysis questions. The resulting counts, percentages, and averages are printed in the terminal.

### 5. Run the SQLAlchemy ORM Analysis

`models.py` defines the SQLAlchemy `Applicant` model that maps to the existing PostgreSQL `applicants` table and configures the SQLAlchemy engine and session.

The ORM versions of the selected analysis questions are contained in `orm_queries.py`. Run them with:

```bash
python orm_queries.py
```

These queries use SQLAlchemy expressions and the `Applicant` model rather than handwritten SQL or a database cursor.

### 6. Run the GradCafe Scraper

The GradCafe scraping functionality from Module 2 is contained in `scrape.py`. The scraper uses `urllib3` for its direct request/status check and the existing Google Chrome session for retrieving and parsing the rendered GradCafe results pages.

Before running the scraper, open the GradCafe survey/results page in a normal Google Chrome tab.

The original Module 2 scraper can be run directly with:

```bash
python scrape.py
```

The Flask application's **Pull Data** feature uses the incremental `pull_new_data()` functionality from `scrape.py` instead of starting the original full collection process. Pull Data begins with the newest GradCafe results, compares the retrieved records with those already stored in `applicant_data.json`, and continues through pages until it reaches results already present in the dataset. Existing records are preserved rather than overwritten or duplicated.

When new records are discovered, the Flask application runs the existing cleaning and local LLM processing pipeline through `clean.py`. The resulting records are stored in `llm_extend_applicant_data.json`, after which `load_data.py` adds the usable new records to PostgreSQL.

### 7. Run the Flask Analysis Application

Make sure PostgreSQL is running and that `DB_NAME` and `DB_USER` have been set in the terminal. Then start the Flask application with:

```bash
python app.py
```

Open the local address displayed by Flask in a web browser. The analysis webpage queries the PostgreSQL database using SQLAlchemy and dynamically displays the current analysis results.

The webpage provides two data-management controls:

**Pull Data** checks GradCafe for newly submitted application results. Because the scraper reuses the Chrome-based workflow from Module 2, the GradCafe results page should be open in Google Chrome before this button is used. Only records that are not already present in the collected dataset are added. While a pull is running, another Pull Data request cannot be started, and the webpage displays the current status of the operation.

**Update Analysis** does not initiate a GradCafe scrape. It re-queries the PostgreSQL database and refreshes the analysis using the records currently available in the database. If Pull Data is still retrieving and processing new records, Update Analysis does not interrupt that process and informs the user that new data is currently being retrieved. Once the new records have been processed and loaded into PostgreSQL, updating the analysis incorporates those records into the displayed results.

### 8. Recommended Run Order

For a new local setup, the project can be run in the following order:

```bash
python -m pip install -r requirements.txt

createdb gradcafe

export DB_NAME="gradcafe"
export DB_USER="<your_postgresql_username>"

python load_data.py
python query_data.py
python orm_queries.py
python app.py
```

After the Flask application is running, **Pull Data** and **Update Analysis** can be used directly from the webpage. The GradCafe results page must be open in Google Chrome before using Pull Data.

## SQL vs. SQLAlchemy Comparison

For this comparison, I used Question 11: **What is the average GPA of accepted Princeton University applicants for Fall 2026 who reported a GPA?**

Both approaches produced an average GPA of **3.87**.

### Raw SQL

```sql
SELECT AVG(gpa)
FROM applicants
WHERE LOWER(TRIM(term)) = 'fall 2026'
  AND LOWER(program) LIKE '%princeton%'
  AND LOWER(TRIM(status)) LIKE 'accept%'
  AND gpa IS NOT NULL;
```

### SQLAlchemy

```python
q11_statement = (
    select(func.avg(Applicant.gpa))
    .where(
        and_(
            func.lower(func.trim(Applicant.term)) == "fall 2026",
            func.lower(Applicant.program).like("%princeton%"),
            func.lower(func.trim(Applicant.status)).like("accept%"),
            Applicant.gpa.is_not(None),
        )
    )
)

q11 = session.scalar(q11_statement)
```

### Comparison

Both the raw SQL and SQLAlchemy queries perform the same filtering and aggregation and produce the same average GPA of 3.87, but they express the database operation differently. Raw SQL is more concise and provides direct visibility into the query being executed, which can make straightforward database operations easier to read and debug and gives the programmer precise control over the resulting SQL. SQLAlchemy provides greater abstraction by representing the database through Python classes and attributes, such as `Applicant.gpa`, `Applicant.term`, and `Applicant.status`, rather than requiring the application to work directly with table and column syntax. This abstraction can improve maintainability and portability in larger Python applications because database operations can be constructed and reused using the same Python-based interface as the rest of the application. Therefore, raw SQL offers advantages in conciseness, transparency, and direct control, while SQLAlchemy offers advantages in abstraction, application integration, and maintainability.
