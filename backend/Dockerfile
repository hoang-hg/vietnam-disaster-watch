FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
# gcc and libpq-dev are often needed for python packages like psycopg2 or others
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Ensure data and logs directories exist
RUN mkdir -p /app/data /app/logs

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
