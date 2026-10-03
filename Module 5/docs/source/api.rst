API Reference
=============

This reference documents the primary modules and functions used by the
GradCafe application.

Scraper
-------

The :mod:`scrape` module retrieves GradCafe applicant records and checks for
newly available data.

.. automodule:: scrape
   :members:
   :undoc-members:
   :show-inheritance:


Cleaning
--------

The :mod:`clean` module cleans and normalizes the applicant data collected by
the scraper.

.. automodule:: clean
   :members:
   :undoc-members:
   :show-inheritance:


Database Loader
---------------

The :mod:`load_data` module prepares cleaned applicant records and loads them
into PostgreSQL.

.. automodule:: load_data
   :members:
   :undoc-members:
   :show-inheritance:


Raw SQL Queries
---------------

The :mod:`query_data` module connects to PostgreSQL and performs the raw SQL
analysis used by the GradCafe application.

.. automodule:: query_data
   :members:
   :undoc-members:
   :show-inheritance:


Flask Application and Routes
----------------------------

The :mod:`app` module implements the Flask web application and its routes.

Application Factory
~~~~~~~~~~~~~~~~~~~

.. autofunction:: app.create_app

The application factory creates and configures the Flask application and
registers the application routes.


Analysis Page
~~~~~~~~~~~~~

.. autofunction:: app.index

The analysis page displays the GradCafe analysis results. It is available
through the application's ``/`` and ``/analysis`` routes.


Pull Data
~~~~~~~~~

.. autofunction:: app.pull_data

The ``/pull-data`` route starts the workflow used to retrieve and process
newly available GradCafe applicant data. The application prevents another
data pull from starting while one is already running.


Update Analysis
~~~~~~~~~~~~~~~

.. autofunction:: app.update_analysis

The ``/update-analysis`` route refreshes the analysis using the applicant
records currently stored in PostgreSQL. An update is prevented while a data
pull is already in progress.


Analysis Results
~~~~~~~~~~~~~~~~

.. autofunction:: app.get_analysis_results

This function retrieves the database analysis results used to populate the
Flask analysis page.


Data Pull Workflow
~~~~~~~~~~~~~~~~~~

.. autofunction:: app.run_data_pull

This function performs the background data-pull workflow used by the
application.