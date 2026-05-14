# AutoScout Backend

FastAPI service for AutoScout AI. Handles auth, search profiles, listing management, matching, and WhatsApp integration.

## Tech Stack

- **Framework:** FastAPI 0.104+
- **Language:** Python 3.12
- **Database:** PostgreSQL 16 + PostGIS
- **Cache:** Redis 7
- **Job Queue:** Celery + Redis
- **LLM:** Anthropic Claude API
- **Logging:** Structlog + JSON output
- **Observability:** Sentry, Datadog APM

## Local Development

### Prerequisites

- Python 3.12
- Poetry (or pip + venv)
- Docker (for Postgres, Redis)
- Anthropic API key

### Setup

```bash
# Install dependencies
poetry install

# Start services (Postgres, Redis)
docker-compose up -d

# Run migrations
alembic upgrade head

# Start dev server
poetry run uvicorn autoscout.main:app --reload
```

The API will be available at `http://localhost:8000/docs` (Swagger UI).

## Project Structure

```
autoscout-backend/
├── autoscout/
│   ├── main.py              # FastAPI app
│   ├── settings.py          # Config (env-based)
│   ├── auth/
│   │   ├── firebase.py
│   │   └── models.py
│   ├── profiles/            # Search profile CRUD
│   ├── listings/            # Listing management
│   ├── matches/             # Matching & ranking
│   ├── notifications/       # Twilio WhatsApp (dev); channel-agnostic interface
│   ├── ai/                  # Claude integration, prompts
│   ├── db/
│   │   ├── models.py        # SQLAlchemy ORM
│   │   └── session.py
│   └── utils/
│       ├── logging.py
│       └── errors.py
├── migrations/              # Alembic migrations
├── tests/
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

**Note:** WhatsApp integration currently uses Twilio for development. See `../autoscout-docs/twilio-integration.md` for setup. The notification service interface is provider-agnostic, allowing easy migration to Meta Cloud API in production.

## Environment Variables

See `.env.example` for the full list. Key vars:

- `FASTAPI_ENV` — dev, staging, prod
- `DATABASE_URL` — Postgres connection
- `REDIS_URL` — Redis connection
- `FIREBASE_CREDENTIALS` — Firebase service account JSON
- `ANTHROPIC_API_KEY` — Claude API key
- `SENTRY_DSN` — error tracking
- `DATADOG_API_KEY` — metrics

## Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "add new column"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Testing

```bash
pytest tests/ -v
```

## Deployment

For V1, deployments are handled by Railway:
1. Connect your GitHub repo to Railway
2. Railway auto-detects `pyproject.toml` and builds/deploys on every push to `main`

See [RAILWAY-SETUP.md](../RAILWAY-SETUP.md) for setup instructions.

## API Documentation

Full API spec at `/docs` (Swagger) or `/redoc` (ReDoc) once the server is running.

Key endpoints:
- `POST /auth/sync` — sync user from Firebase
- `GET /me` — current user
- `POST /profiles` — create search profile
- `POST /profiles/parse` — natural-language profile parser
- `GET /profiles/{id}/matches` — profile match history
- `POST /webhooks/whatsapp` — inbound WhatsApp messages

## Contributing

1. Branch from `main`
2. Follow `black` formatting + `ruff` linting
3. Write tests for new endpoints
4. PR with test results + coverage report
