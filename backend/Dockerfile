FROM python:3.11-slim-bookworm

WORKDIR /app

# Install system dependencies
# gcc and libpq-dev are needed for python packages
# Playwright needs additional libraries to run browsers in slim images
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user early
RUN useradd -m -u 1000 -s /bin/bash appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers and their system dependencies
RUN playwright install chromium && playwright install-deps chromium

# Copy source code
COPY . .

# Ensure data and logs directories exist with correct permissions
RUN mkdir -p /app/data /app/logs && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Run the application using Gunicorn for production
CMD ["gunicorn", "app.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--timeout", "120"]

