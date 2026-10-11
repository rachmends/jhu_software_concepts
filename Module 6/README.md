# Module 6: Deploy Anywhere

## Name

**Rachael Mends**  
**JHED ID:** rmends1

## Module Info

**Module:** Module 6  
**Assignment:** Deploy Anywhere  
**Due Date:** October 12, 2026

## Project Overview

The GradCafe application collects graduate admissions results, cleans and processes applicant data, stores records in PostgreSQL, and presents statistical analyses through a Flask web application.

Module 6 extends the application from a locally executed Python project into a **containerized, asynchronous microservice architecture**. Docker Compose coordinates the Flask web application, PostgreSQL database, RabbitMQ message broker, and background worker as four independent services.

The principal architectural improvement is the separation of HTTP request handling from time-consuming data-processing operations. Rather than executing a GradCafe scrape or recalculating database statistics directly within a Flask request, the web service publishes a task to RabbitMQ. A dedicated worker consumes that task and performs the requested operation independently.

This approach allows the web interface to remain responsive while data processing occurs in the background. It also provides explicit message acknowledgment, database transaction handling, persistent storage, and a reproducible deployment environment.

The application allows a user to:

- View analyses of GradCafe graduate admissions data.
- Submit a task to retrieve newly available applicant records.
- Process and insert new records into PostgreSQL without duplicating existing records.
- Recalculate and persist analytical summaries.
- Observe task processing through worker logs and the RabbitMQ management interface.

## Requirements

The containerized application requires Docker Desktop or Docker Engine with the Docker Compose plugin.

For local development, automated testing, and documentation generation, the project uses Python 3.11.

The project declares dependencies in several files:

- `requirements.txt` — application and project dependencies.
- `requirements-dev.txt` — development, testing, linting, and documentation dependencies.
- `src/web/requirements.txt` — dependencies installed in the Flask web image.
- `src/worker/requirements.txt` — dependencies installed in the background worker image.

The web and worker services use separate Dockerfiles so that each container installs the dependencies required for its responsibilities.

## Docker Compose Architecture

Docker Compose defines and coordinates four application services.

### Web Service

The `web` service runs the Flask application and provides the GradCafe dashboard and analysis routes.

It is responsible for receiving HTTP requests, rendering application pages, reading persisted analytics, and publishing background tasks to RabbitMQ.

The web service does not need to perform a complete scrape or analytics recalculation before returning a response. Instead, it publishes a task and returns HTTP `202 Accepted` when the request has been successfully queued.

The Flask application listens on `0.0.0.0:8080` inside its container, making it accessible through the published host port.

### Worker Service

The `worker` service runs independently of Flask and consumes RabbitMQ messages.

It is responsible for executing incremental scraping operations, inserting newly discovered applicant records, updating ingestion progress, and recomputing analytical summaries.

Separating the worker from the web service prevents lengthy data-processing operations from blocking normal browser requests.

The worker uses explicit message acknowledgments and database transactions to coordinate successful task completion with persistent database changes.

### PostgreSQL Service

The `db` service provides relational storage for the application.

PostgreSQL stores the applicant dataset, ingestion watermark information, and persisted analytics summaries.

A named Docker volume preserves the database files across normal container restarts and recreation. This prevents the application from losing its accumulated data whenever the containers are stopped and restarted.

The Compose configuration also includes database readiness checks so that dependent services can wait for PostgreSQL to become available.

### RabbitMQ Service

The `rabbitmq` service provides asynchronous communication between the Flask web service and the worker.

RabbitMQ receives tasks from the publisher, places them in a queue, and delivers them to the worker for processing.

The application uses a durable direct exchange named `tasks`, a durable queue named `tasks_q`, and the routing key `tasks`.

Messages are published with persistent delivery mode so that queued tasks can survive an ordinary broker restart when RabbitMQ's persistent storage and durability requirements are satisfied.

The RabbitMQ management interface provides visibility into queue activity, message delivery, consumers, and broker status.

## Environment Configuration

The project includes `.env.example` to document the environment configuration used by the application.

A local `.env` file can be created from the template:

```bash
cp .env.example .env
```

Review the template and configure the database and RabbitMQ settings before deployment.

PostgreSQL connection settings include the database name, username, password, host, and port. The application can also use a `DATABASE_URL` connection string.

RabbitMQ connection settings identify the broker and provide the credentials required by the publisher and consumer.

Within Docker Compose, services communicate using their service names on the Compose network rather than relying on `localhost` to reach other containers.

The real `.env` file must not be committed to version control. Credentials should be supplied through environment configuration rather than embedded in application source code.

## Running the Application

From the `Module 6` directory, build and start the application:

```bash
docker compose up -d --build
```

This command builds the required images and starts the four services in detached mode.

Verify their status:

```bash
docker compose ps
```

The expected services are:

- `web`
- `worker`
- `db`
- `rabbitmq`

The application interfaces are available at:

| Interface | URL |
|---|---|
| Flask dashboard | http://localhost:8080 |
| Analysis page | http://localhost:8080/analysis |
| RabbitMQ management | http://localhost:15672 |

For a local development deployment configured with RabbitMQ's default credentials, the management username and password are `guest` and `guest`.

### Viewing Container Logs

Docker Compose provides access to individual service logs:

```bash
docker compose logs --tail=100 web
docker compose logs --tail=100 worker
docker compose logs --tail=100 db
docker compose logs --tail=100 rabbitmq
```

The worker logs are particularly useful for confirming that tasks were received, processed, and committed successfully.

### Stopping the Application

Stop and remove the running containers with:

```bash
docker compose down
```

This preserves the named PostgreSQL volume.

The command `docker compose down -v` additionally removes named volumes and should not be used unless deleting the persistent application data is intentional.

## Using the Application

### Pull Data

The **Pull Data** button initiates an asynchronous request to retrieve newly available GradCafe applicant records.

When the user clicks the button, Flask publishes a `scrape_new_data` task to RabbitMQ.

The HTTP endpoint returns `202 Accepted` after successful task publication, allowing the browser to remain responsive.

The worker subsequently consumes the task and executes the incremental scraping pipeline.

The pipeline checks for newly available records, cleans and normalizes applicant information, and inserts eligible records into PostgreSQL.

An ingestion watermark records the application's progress so that subsequent runs can identify previously processed data.

Duplicate protection prevents the same applicant records from being inserted repeatedly.

If no new records are available, the worker can complete successfully without inserting additional applicants.

### Update Analysis

The **Update Analysis** button initiates an asynchronous analytics refresh.

Flask publishes a `recompute_analytics` task to RabbitMQ and returns `202 Accepted` when the task has been queued.

The worker reads the applicant data stored in PostgreSQL, performs the required calculations, and persists the resulting analytical summary.

The Flask application can then retrieve the updated statistics from PostgreSQL for display on the analysis page.

Separating this calculation from the HTTP request allows the application to process analytical updates without requiring the browser to wait for the database operation to finish.

## RabbitMQ Message Processing

RabbitMQ is the communication mechanism between the web service and the worker.

The publisher creates a task message containing three principal fields:

- `kind` — identifies the requested operation.
- `ts` — records the task timestamp.
- `payload` — carries task-specific information.

The supported task kinds are `scrape_new_data` and `recompute_analytics`.

The publisher sends persistent messages through the durable `tasks` exchange to the `tasks_q` queue using the `tasks` routing key.

The worker declares the corresponding RabbitMQ entities and consumes messages using a prefetch count of one.

This configuration limits the number of unacknowledged messages delivered to the worker at a time.

### Transaction Handling and Acknowledgment

The worker processes database modifications inside transactions.

For successful processing, database changes are committed before the worker acknowledges the RabbitMQ message.

This ordering prevents the worker from acknowledging successful completion before its database changes have been persisted.

If processing fails, the worker rolls back the database transaction and rejects the message without automatically requeuing it indefinitely.

These mechanisms support predictable task handling and reduce the risk of inconsistent database state.

## Data Pipeline

The original GradCafe application includes extraction, cleaning, database loading, and statistical analysis.

Module 6 adapts those operations for execution by a dedicated background worker.

### Incremental Scraping

The worker's incremental scraper retrieves available GradCafe records and identifies records that have not already been processed.

The application uses ingestion watermark information to track progress between scraping runs.

The pipeline normalizes applicant information before insertion and applies duplicate protection at the database layer.

Incremental processing reduces unnecessary repeated work and helps preserve consistency across repeated task submissions.

### Database Loading

PostgreSQL stores the processed applicant records.

The project includes database initialization and loading functionality for the prepared applicant dataset.

Database operations use parameterized SQL rather than interpolating untrusted values directly into executable SQL statements.

The application maintains applicant data, ingestion watermarks, and persisted analytical results as separate logical responsibilities.

### Analytics

The application performs statistical analysis on the stored graduate admissions records.

The existing GradCafe analysis includes admission-related summaries and descriptive statistics.

Module 6 adds persisted analytical summaries so that recalculated results can be stored and subsequently retrieved by the web service.

The dashboard continues to present the application's analysis questions and results.

## SQL Injection Defenses

The application retains the secure SQL practices developed in Module 5.

Database statements use psycopg parameter binding to separate SQL commands from user-controlled values.

Where SQL identifiers must be composed dynamically, the application uses psycopg's SQL composition utilities rather than directly concatenating untrusted text into statements.

Parameterized statements reduce the risk that input values will be interpreted as executable SQL.

The Module 6 worker also performs its database modifications within explicit transactions, providing additional control over the consistency of inserted records and updated summaries.

## Container Security

The web and worker Docker images are configured to execute application processes as non-root users.

Running application processes without root privileges reduces the permissions available to those processes inside their containers.

The services install their required Python dependencies from their respective pinned requirements files.

The worker receives application data through a read-only mount, preventing the worker from modifying the mounted source dataset.

Docker Compose provides an internal network for service-to-service communication and defines service dependencies and health checks.

The application also keeps runtime configuration separate from source code through environment variables.

## Docker Hub Publication

The Module 6 web and worker images have been published to Docker Hub.

Both repositories are public and use the `v1` tag.

### Web Image

Repository:

https://hub.docker.com/r/rachmends/module_6-web/tags

Pull command:

```bash
docker pull rachmends/module_6-web:v1
```

### Worker Image

Repository:

https://hub.docker.com/r/rachmends/module_6-worker/tags

Pull command:

```bash
docker pull rachmends/module_6-worker:v1
```

The published images provide reusable versions of the two application services.

They are intended to operate with the PostgreSQL and RabbitMQ services defined in Docker Compose.

## Packaging

The project includes `setup.py` to support installation of the Python application in editable mode.

Editable installation allows the source code to be imported during local development and automated testing without rebuilding the package after every source change.

From the `Module 6` directory:

```bash
python -m pip install -e .
```

The Docker deployment uses service-specific Dockerfiles and requirements files, while editable installation supports the local development and testing workflow.

## Verify the Installation

### Docker Verification

Start the complete application:

```bash
docker compose up -d --build
```

Confirm service status:

```bash
docker compose ps
```

Verify that the Flask application responds:

```bash
curl -I http://localhost:8080/
curl -I http://localhost:8080/analysis
```

Submit the two asynchronous tasks:

```bash
curl -i -X POST http://localhost:8080/pull-data
curl -i -X POST http://localhost:8080/update-analysis
```

Successful task publication should return HTTP `202 Accepted`.

Inspect the worker logs:

```bash
docker compose logs --tail=100 worker
```

The worker output can be used to confirm that the requested operations were processed.

The RabbitMQ management interface provides additional evidence that the broker is running and that the worker is connected.

### Automated Tests

Run the complete Module 6 test suite:

```bash
PYTHONPATH=src python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=100
```

The required coverage threshold is **100%**.

The test suite covers application routes, RabbitMQ publishing, worker consumption, transaction handling, incremental scraping, database operations, and integration behavior.

## Pylint

Pylint checks the Python source code for code-quality issues and violations of configured lint rules.

Run:

```bash
PYTHONPATH=src python -m pylint --fail-under=10 --persistent=n src
```

The required final score is **10.00/10**.

The GitHub Actions workflow enforces this threshold so that a lint regression causes the corresponding CI job to fail.

## Continuous Integration

The repository uses GitHub Actions to execute automated quality checks.

The workflow is located at the repository root:

```text
.github/workflows/ci.yml
```

The Module 6 Pylint job installs the project dependencies and runs Pylint against the Module 6 source directory.

The Module 6 Pytest job runs the complete test suite and enforces the 100% coverage requirement.

These checks are configured to run on repository pushes and pull requests.

The existing dependency-graph and Snyk jobs remain associated with the earlier Module 5 implementation.

Successful GitHub Actions execution provides additional verification that the project can be installed and tested in a clean environment.

## Sphinx Documentation

The project uses Sphinx to generate HTML documentation from reStructuredText files and Python docstrings.

The documentation source files are located in:

```text
docs/source/
```

The documentation includes:

- Application overview and setup instructions.
- Four-service Docker Compose architecture.
- RabbitMQ publishing and consumption workflow.
- PostgreSQL persistence and incremental processing.
- Python API reference.
- Automated testing and deployment verification.

Build the documentation from the Module 6 directory:

```bash
python -m sphinx -b html -W --keep-going docs/source docs/build/html
```

The `-W` option treats documentation warnings as errors, allowing documentation problems to be identified before submission.

The generated documentation can be opened at:

```text
docs/build/html/index.html
```

## Final Deliverables

The Module 6 submission consists of the completed project, its repository, and the required documentation.

The deliverables include:

- A ZIP archive containing the Module 6 project.
- A link to the private GitHub repository containing the committed Module 6 implementation.
- The Docker Compose configuration and service Dockerfiles.
- The web publisher, RabbitMQ worker, incremental scraper, and PostgreSQL initialization code.
- Updated README and Sphinx documentation.
- GitHub Actions configuration enforcing Pylint 10/10 and Pytest 100% coverage.
- Public Docker Hub links for the web and worker images.
- A PDF report describing the architecture, message flow, database initialization, worker behavior, and verification procedures.
- Screenshots showing the running Flask website and RabbitMQ management interface.

The final archive should be created after the application, documentation, and automated checks have been verified.