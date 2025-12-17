FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY app /app/app
RUN mkdir -p /app/data

ENV APP_DB_URL=sqlite:///./data/app.db
ENV CRAWL_INTERVAL_MINUTES=10
ENV APP_TIMEZONE=Asia/Ho_Chi_Minh

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
