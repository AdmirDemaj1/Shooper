FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml poetry.lock* ./
RUN pip install poetry && poetry install --only main

COPY . .

CMD ["poetry", "run", "celery", "-A", "crawler.worker", "worker", "--loglevel=info"]
