Architecture
============

The GradCafe application is organized into three primary layers: the web
layer, the ETL layer, and the database and analysis layer. Together, these
layers collect GradCafe applicant data, process and store the records, and
display analysis results through the Flask application.

Web Layer
---------

The web layer is implemented in :mod:`app`.

The Flask application is responsible for displaying the GradCafe analysis
page, retrieving analysis results from the database, and handling user actions
from the web interface.

The application provides two primary user actions:

* **Pull Data** starts the process of retrieving and processing newly available
  GradCafe records.
* **Update Analysis** refreshes the displayed analysis using the records
  currently stored in PostgreSQL.

The application also prevents conflicting operations while a data pull is
already running.

The ``create_app()`` application factory allows the Flask application to be
created with different configurations, including configurations used by the
automated test suite.

ETL Layer
---------

The ETL layer is responsible for extracting, transforming, and loading
GradCafe applicant data.

The ETL process is divided among three primary modules:

* :mod:`scrape` retrieves GradCafe applicant records and checks for newly
  available results.
* :mod:`clean` cleans and normalizes the collected applicant records.
* :mod:`load_data` loads the processed applicant records into PostgreSQL.

Separating these responsibilities allows each stage of the data pipeline to be
tested independently. During automated testing, external behavior such as live
web requests is replaced with deterministic test doubles.

Database and Analysis Layer
---------------------------

PostgreSQL provides persistent storage for the processed GradCafe applicant
records.

The database and analysis functionality is divided among the following
modules:

* :mod:`models` defines the SQLAlchemy applicant model and database
  configuration.
* :mod:`query_data` performs analysis of the applicant data using raw SQL.
* :mod:`orm_queries` performs analysis using SQLAlchemy.

The Flask web layer uses the database and analysis functionality to generate
the results displayed on the analysis page.

Application Data Flow
---------------------

The overall application flow is:

.. code-block:: text

   GradCafe
       |
       v
   scrape
       |
       v
   clean
       |
       v
   load_data
       |
       v
   PostgreSQL
       |
       v
   query_data / SQLAlchemy
       |
       v
   Flask Application
       |
       v
   Analysis Page

The scraping layer retrieves applicant records, the cleaning layer transforms
the records into a consistent format, and the loading layer stores the
processed records in PostgreSQL. The analysis layer queries the stored data,
and the Flask web layer presents the resulting analysis to the user.

API Documentation
-----------------

Detailed API documentation for the application modules is available in the
:doc:`api` reference.