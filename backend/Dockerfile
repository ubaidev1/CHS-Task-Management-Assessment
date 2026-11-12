FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# psycopg[binary] ships its own libpq, so no system build deps are needed.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

# Default command (compose overrides for the worker). Runs the WSGI server;
# migrations + seeding are run by the compose `command` before this.
CMD ["gunicorn", "taskflow.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
