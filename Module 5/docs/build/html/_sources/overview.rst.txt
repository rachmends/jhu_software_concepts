Overview and Setup
==================

Overview
--------

The GradCafe application collects graduate admissions data, cleans and
normalizes the collected records, stores the resulting data in PostgreSQL,
performs analysis queries, and displays the results through a Flask web
application.

The application consists of a web interface implemented in :mod:`app`, an ETL
pipeline implemented by :mod:`scrape`, :mod:`clean`, and :mod:`load_data`, and
database analysis functionality provided by :mod:`query_data`, :mod:`models`,
and :mod:`orm_queries`.

Module 4 also includes an automated pytest test suite, code coverage,
continuous integration through GitHub Actions, and Sphinx documentation.

Installation
------------

The project uses Python 3.11.

From the ``Module 4`` directory, install the required dependencies:

.. code-block:: bash

   pip install -r requirements.txt

Database Configuration
----------------------

The application uses PostgreSQL. PostgreSQL must be running before using
application functionality that requires the database.

Configure the database connection using the following environment variables:

``DB_NAME``
   PostgreSQL database name.

``DB_USER``
   PostgreSQL database user.

``DB_PASSWORD``
   PostgreSQL database password.

``DATABASE_URL``
   SQLAlchemy database connection URL.

For example:

.. code-block:: bash

   export DB_NAME=gradcafe
   export DB_USER=postgres
   export DB_PASSWORD=postgres
   export DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/gradcafe"

Running the Application
-----------------------

From the ``Module 4`` directory, start the Flask application with:

.. code-block:: bash

   python src/app.py

Open the local Flask address displayed in the terminal to access the GradCafe
analysis page.

The **Pull Data** button starts the process of retrieving and processing newly
available GradCafe records.

The **Update Analysis** button refreshes the displayed analysis using the
records currently stored in PostgreSQL.

Running the Tests
-----------------

Run the complete pytest suite from the ``Module 4`` directory with:

.. code-block:: bash

   pytest

The assignment test groups can be run with:

.. code-block:: bash

   pytest -m "web or buttons or analysis or db or integration"

The project uses ``pytest-cov`` to measure source-code coverage.

Additional testing information, including markers, selectors, fixtures, and
test doubles, is available in the :doc:`testing` guide.

API Reference
-------------

Detailed documentation generated from the application's Python modules is
available in the :doc:`api` reference.