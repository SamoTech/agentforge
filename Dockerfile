FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl git && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]"

COPY . .

ENV PYTHONUNBUFFERED=1 PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "agentforge.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
