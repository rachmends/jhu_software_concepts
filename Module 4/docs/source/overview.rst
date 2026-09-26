Overview and Setup
==================

Overview
--------

The Grad Café application collects graduate admissions data, cleans and
normalizes the collected records, stores the resulting data in PostgreSQL,
performs analysis queries, and displays the results through a Flask web
application.

The Module 4 implementation also includes an automated pytest test suite
and continuous integration through GitHub Actions.

Installation
------------

From the ``Module 4`` directory, install the required Python packages:

.. code-block:: bash

   pip install -r requirements.txt

The application uses Python 3.11.

Database Configuration
----------------------

The application uses PostgreSQL. Configure the database connection before
running the application.

The project uses the following environment variables:

``DATABASE_URL``
   SQLAlchemy database connection URL.

``DB_NAME``
   PostgreSQL database name used by scripts that connect directly with
   psycopg.

``DB_USER``
   PostgreSQL database user.

``DB_PASSWORD``
   PostgreSQL password where required by the database environment.

For example:

.. code-block:: bash

   export DB_NAME=gradcafe
   export DB_USER=postgres
   export DB_PASSWORD=postgres
   export DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/gradcafe"

Running the Flask Application
-----------------------------

From the ``Module 4`` directory:

.. code-block:: bash

   python src/app.py

The Flask application provides the analysis page and controls for pulling
new Grad Café data and refreshing the displayed analysis.

Running Tests
-------------

Run the complete test suite with:

.. code-block:: bash

   pytest

The assignment marker groups can be run with:

.. code-block:: bash

   pytest -m "web or buttons or analysis or db or integration"

Coverage is measured using ``pytest-cov``.