FROM python:3.11-slim

WORKDIR /app
COPY apps/backend/pyproject.toml ./
COPY apps/backend/app ./app
COPY apps/backend/migrations ./migrations

RUN pip install --no-cache-dir .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

