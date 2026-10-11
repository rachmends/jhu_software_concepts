FROM python:3.11-slim

WORKDIR /app

COPY src/worker/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ /app/src/

ENV PYTHONPATH=/app/src
ENV DATA_DIR=/app/data
ENV PYTHONUNBUFFERED=1

RUN useradd --create-home --uid 1000 workeruser
USER workeruser

CMD ["python", "-m", "worker.consumer"]
