FROM python:3.11-slim

WORKDIR /app

COPY src/web/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ /app/src/

ENV PYTHONPATH=/app/src
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

RUN useradd --create-home --uid 1000 appuser
USER appuser

EXPOSE 8080

CMD ["sh", "-c", "python -m db.init_db && exec python src/web/run.py"]
