Testing Guide
=============

Test Suite
----------

The project uses pytest and pytest-cov. Tests are located in the
``Module 4/tests`` directory.

Run the complete suite from ``Module 4``:

.. code-block:: bash

   pytest

Marked Tests
------------

Every test uses at least one of the assignment's pytest markers:

``web``
   Flask application, route, and page behavior.

``buttons``
   Pull Data and Update Analysis behavior.

``analysis``
   Analysis output and formatting.

``db``
   Database behavior, loading, querying, and persistence.

``integration``
   Tests involving multiple application layers.

Run all assignment marker groups with:

.. code-block:: bash

   pytest -m "web or buttons or analysis or db or integration"

Individual groups can also be selected. For example:

.. code-block:: bash

   pytest -m web
   pytest -m buttons
   pytest -m db

Coverage
--------

Coverage is measured using pytest-cov. The Module 4 configuration requires
coverage of the source code under ``src``.

The terminal coverage report can be generated with:

.. code-block:: bash

   pytest -m "web or buttons or analysis or db or integration"

The committed terminal coverage summary is stored in
``coverage_summary.txt``.

Stable Page Selectors
---------------------

The Flask analysis page provides stable selectors for the primary actions.

The Pull Data button uses:

.. code-block:: text

   data-testid="pull-data-btn"

The Update Analysis button uses:

.. code-block:: text

   data-testid="update-analysis-btn"

Analysis results also use consistent ``Answer:`` labels so tests can verify
that analysis output is present.

Test Doubles and Fixtures
-------------------------

The test suite avoids live internet requests and long-running Grad Café
scrapes.

pytest's ``monkeypatch`` fixture is used to replace external dependencies
and isolate application behavior during testing.

``tmp_path`` is used where tests require temporary files without modifying
project data.

Small fake objects are used for dependencies such as database cursors,
database connections, SQLAlchemy sessions, threads, and subprocess results.
These test doubles allow error and success paths to be tested
deterministically without relying on external services.

Flask's test client and test request contexts are used to test routes and
rendering without requiring manual browser interaction.

Continuous Integration
----------------------

The repository contains a GitHub Actions workflow at
``.github/workflows/tests.yml``.

The workflow starts PostgreSQL, installs the Module 4 Python dependencies,
and runs the marked pytest suite automatically. This verifies the test suite
in a clean CI environment in addition to local testing.