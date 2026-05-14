# AutoScout Crawlers

Worker pool for scraping car listings from multiple sources. Playwright + httpx + Celery.

## Tech Stack

- **Language:** Python 3.12
- **Browser Automation:** Playwright
- **HTTP Client:** httpx
- **Job Queue:** Celery
- **Message Broker:** Redis
- **Proxies:** Bright Data / Oxylabs residential pools
- **Logging:** Structlog + JSON
- **Monitoring:** Prometheus metrics

## Local Development

### Prerequisites

- Python 3.12
- Poetry
- Docker (for Redis)
- Playwright browsers installed

### Setup

```bash
# Install dependencies
poetry install

# Install Playwright browsers
playwright install chromium

# Start Redis
docker-compose up -d redis

# Configure environment
cp .env.example .env.local

# Run a single crawler job (manual test)
poetry run python -m crawler.run --source=merrjep --profile=<test-profile-id>
```

## Project Structure

```
autoscout-crawlers/
├── crawler/
│   ├── __main__.py          # CLI entrypoint
│   ├── worker.py            # Celery worker
│   ├── settings.py
│   ├── sources/
│   │   ├── base.py          # SourceAdapter abstract base
│   │   ├── merrjep.py       # Tier 1: merrjep.al
│   │   ├── mobile.py        # Tier 1: mobile.al
│   │   ├── gjirafa.py       # Tier 2: gjirafa.com
│   │   └── njoftime.py      # Tier 2: njoftime.al
│   ├── normalization.py     # Canonical schema
│   ├── dedup.py             # Deduplication logic
│   ├── proxy.py             # Proxy rotation
│   ├── metrics.py           # Prometheus metrics
│   └── utils/
│       ├── browser.py
│       ├── http.py
│       └── parsing.py
├── tests/
│   ├── fixtures/            # Recorded HTML responses
│   └── test_sources/
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

## Source Adapter Interface

Every source must implement:

```python
from abc import ABC, abstractmethod
from typing import Iterator

class SourceAdapter(ABC):
    name: str
    country: str
    
    @abstractmethod
    async def search(self, profile: SearchProfile) -> Iterator[RawListing]:
        """Execute search against this source."""
        pass
    
    @abstractmethod
    def parse(self, raw: RawListing) -> NormalizedListing:
        """Parse raw source response into canonical schema."""
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """Quick health check for this source."""
        pass
```

## Running Crawls

### Manual (CLI)

```bash
# Crawl a single profile from a single source
poetry run python -m crawler.run --source=mobile --profile=<profile-id>

# Health check all sources
poetry run python -m crawler.health-check
```

### Via Celery (Production)

The backend scheduler enqueues tasks; workers pick them up from Redis:

```python
from crawler.tasks import crawl_profile_source

crawl_profile_source.delay(profile_id=123, source_name='merrjep')
```

## Environment Variables

```env
# Crawler config
CRAWLER_ENV=dev
CRAWLER_LOG_LEVEL=INFO

# Redis (Celery broker)
REDIS_URL=redis://localhost:6379/0

# Database (to persist listings)
DATABASE_URL=postgresql://...

# Proxies
BRIGHT_DATA_API_KEY=...
BRIGHT_DATA_ZONE=...

# Rate limiting
CRAWLER_MAX_CONCURRENT_PER_SOURCE=5
CRAWLER_REQUEST_TIMEOUT_SEC=90

# Metrics
PROMETHEUS_PUSHGATEWAY_URL=http://localhost:9091
```

## Testing

Fixtures (recorded HTML responses) are committed to `tests/fixtures/`. Tests run against these without hitting real sources.

```bash
poetry run pytest tests/ -v

# Update fixture (hits real source, slow)
pytest tests/test_sources/test_merrjep.py --update-fixtures
```

## Metrics & Monitoring

Per-source Prometheus metrics:

- `crawler_requests_total` — HTTP requests sent
- `crawler_requests_succeeded_total` — successful requests
- `crawler_listings_parsed_total` — listings extracted
- `crawler_deduplicated_total` — duplicates dropped
- `crawler_request_duration_seconds` — latency histogram

Scraped via Prometheus every 30s; visualized in Grafana.

## Anti-Blocking Best Practices

1. **Rotate residential proxies** — set `BRIGHT_DATA_API_KEY` and never reuse IPs.
2. **Randomize user-agent** — every request gets a random modern browser UA.
3. **Respect rate limits** — max 1 request per source per 3 seconds per IP.
4. **Honor robots.txt** — crawl delay respected even where not legally required.
5. **Circuit breaker** — after 5 consecutive failures, mark source unhealthy for 1h.

## Contributing

1. New source? Copy `sources/merrjep.py` as a template.
2. Add selector tests with fixtures in `tests/fixtures/`.
3. Never commit API keys or real credentials.
4. Update this README if you change the adapter interface.
