Architecture
============

The application is organized into three primary layers: the web layer,
ETL layer, and database/analysis layer.

Web Layer
---------

``app.py`` contains the Flask application.

The web layer is responsible for:

* Creating and configuring the Flask application.
* Serving the analysis page.
* Displaying analysis results.
* Handling the Pull Data action.
* Handling the Update Analysis action.
* Preventing conflicting operations while a data pull is running.

The application exposes a ``create_app()`` factory so that tests can create
a Flask application without starting the development server.

ETL Layer
---------

The ETL pipeline is primarily implemented by ``scrape.py``, ``clean.py``,
and ``load_data.py``.

``scrape.py``
   Retrieves Grad Café applicant records and converts the source data into
   structured applicant records.

``clean.py``
   Cleans and normalizes the collected data before database loading.

``load_data.py``
   Loads the processed applicant records into PostgreSQL while preserving
   the application's database schema and duplicate-handling behavior.

Database and Analysis Layer
---------------------------

PostgreSQL stores the Grad Café applicant records.

``models.py``
   Defines the SQLAlchemy representation of the applicant data and database
   session configuration.

``query_data.py``
   Performs the raw SQL analysis queries.

``orm_queries.py``
   Implements analysis using SQLAlchemy ORM operations.

The Flask application uses the database layer to calculate the values
displayed on the analysis page.

Data Flow
---------

The overall data flow is:

.. code-block:: text

   Grad Café
       |
       v
   scrape.py
       |
       v
   clean.py
       |
       v
   load_data.py
       |
       v
   PostgreSQL
       |
       +-------------------+
       |                   |
       v                   v
   query_data.py        app.py
                           |
                           v
                     Analysis Page