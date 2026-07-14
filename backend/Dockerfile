# Use the official lightweight Python image.
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    POETRY_VERSION=2.4.1

# Install system dependencies (build tools for packages if needed, libpq for Postgres connection)
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir "poetry==$POETRY_VERSION"

# Configure Poetry: install dependencies globally in the container
RUN poetry config virtualenvs.create false

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Install main dependencies only (skipping dev dependencies)
RUN poetry install --no-interaction --no-ansi --no-root --only main

# Copy application files
COPY . .

# Make startup script executable
RUN chmod +x start.sh

# Expose API port
EXPOSE 8000

# Start application via startup script
CMD ["./start.sh"]
