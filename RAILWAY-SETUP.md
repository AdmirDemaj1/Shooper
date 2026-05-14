# Railway Setup for AutoScout AI (V1 Hosting)

Railway replaces AWS/GCP for V1. It's the simplest, cheapest way to launch: PostgreSQL, Redis, auto-deploy, and environment variables all built in.

## Quick Start (10 minutes)

### 1. Create a Railway Account

1. Go to [railway.app](https://railway.app)
2. Click "Start a new project"
3. Sign in with GitHub (Railway auto-connects to your repos)

### 2. Create a Project

1. Click "New Project"
2. Select "Deploy from GitHub"
3. Authorize Railway to access your GitHub account
4. Select `autoscout-backend` repo

Railway will:
- Auto-detect `pyproject.toml`
- Create a Dockerfile (or you can provide your own)
- Deploy on every push to `main`

### 3. Add PostgreSQL

1. In Railway dashboard: Click "Add" (bottom left)
2. Select "Add from Marketplace"
3. Choose "PostgreSQL"
4. Railway provisions a database instance
5. Environment variables are auto-injected: `DATABASE_URL`, `DATABASE_HOST`, etc.

### 4. Add Redis

1. Click "Add" again
2. Select "Redis" from Marketplace
3. Railway provisions a cache instance
4. Environment variables: `REDIS_URL`, `REDIS_HOST`, etc.

### 5. Add Service Env Variables

For each service (backend, crawlers), add these to Railway dashboard:

**Backend:**
```
FASTAPI_ENV=dev
ANTHROPIC_API_KEY=sk-ant-...
TWILIO_ACCOUNT_SID=ACxxxxxxxx
TWILIO_AUTH_TOKEN=your_token
TWILIO_WHATSAPP_PHONE_NUMBER=+1415...
FIREBASE_CREDENTIALS={...}
SENTRY_DSN=https://...
```

**Crawlers (background workers):**
```
FASTAPI_ENV=dev
CRAWLER_LOG_LEVEL=INFO
BRIGHT_DATA_API_KEY=...
BRIGHT_DATA_ZONE=...
```

Railway auto-injects `DATABASE_URL` and `REDIS_URL` from the plugins.

### 6. Add Custom Domain

1. Railway > Domain
2. Enter `api.dev.autoscout.al`
3. Railway gives you a CNAME or A record to point at
4. In Cloudflare (your DNS): add the CNAME
5. Wait a few minutes for propagation

### 7. Set Spending Limits

**Critical:** Protect against runaway costs.

1. Railway > Project Settings > Usage limits
2. Set a monthly limit: `$100` for dev, `$500` for staging
3. Railway stops deployments if you hit the limit

---

## How Railway Works

### Auto-Deploy

Push to `main` → GitHub webhook → Railway builds from Dockerfile → Railway deploys.

Railway detects:
- `Dockerfile` → uses it as-is
- `pyproject.toml` → generates a Dockerfile
- `package.json` → generates a Dockerfile

### Environment Variables

Railway provides:
- System vars: `DATABASE_URL`, `REDIS_URL` (from plugins)
- Custom vars: anything you set in the dashboard
- All injected into container at runtime

### Logs

1. Railway > Deployments > click the latest
2. View real-time logs from your service
3. Search by keyword, filter by timestamp

### Metrics

1. Railway > Monitoring
2. View CPU, memory, disk usage
3. Set alerts (paid feature, optional)

---

## Multiple Services (Backend + Crawlers)

Railway can host multiple services in one project:

1. **Backend service:** deployed as a web service (port 8000)
2. **Crawlers service:** deployed as a worker (no port exposed)

### Deploy Crawlers as Background Workers

Crawlers (Celery workers) don't need a public port. Deploy as a "worker" service:

```bash
# In autoscout-crawlers/Dockerfile
FROM python:3.12

WORKDIR /app
COPY . .
RUN pip install -r requirements.txt

# Run Celery worker instead of a web server
CMD ["celery", "-A", "crawler.worker", "worker", "--loglevel=info"]
```

In Railway:
1. Create a new service from `autoscout-crawlers` repo
2. Railway auto-detects it as a worker (no port)
3. It connects to the same `DATABASE_URL` and `REDIS_URL`
4. Workers consume jobs from Redis queue

---

## Migrating Away from Railway (Later)

If you ever outgrow Railway (5,000+ users, costs >$500/month), the migration is straightforward:

1. **Database:** Export PostgreSQL dump from Railway, import to AWS RDS/GCP Cloud SQL
2. **Cache:** Export Redis dump, import to AWS ElastiCache/GCP Memorystore
3. **Services:** Containers are portable — deploy to AWS ECS/Fargate or GKE
4. **Secrets:** Copy env vars from Railway dashboard to AWS Secrets Manager or similar

The code changes are minimal — just update `DATABASE_URL` and `REDIS_URL` connection strings.

---

## Cost Breakdown (V1 Estimates)

| Service | Monthly Cost | Notes |
|---------|--------------|-------|
| **Railway base** | $5–$20 | includes 500 GB-month compute |
| **PostgreSQL** | $5–$15 | small instance, auto-scaling |
| **Redis** | $3–$10 | small instance, auto-scaling |
| **Bandwidth** | $0 | free egress |
| **Total Railway** | ~$15–$45/month | scales with usage |
| **Twilio** | ~$3–$10/month | $0.005–$0.015 per message, ~500 users × 1 message/day |
| **Anthropic** | ~$4–$10/month | ~$0.10–$0.15 per active user per day |
| **Domain** | ~$1/month | $12/year divided by 12 |
| **Apple Dev** | ~$8/month | $99/year divided by 12 |
| **Google Play** | ~$2/month | $25 one-time, amortized |
| **Total V1 burn** | ~$35–$75/month | add 20% buffer for growth |

At launch, target <$100/month. No AWS bill, no Kubernetes bill, no DevOps overhead.

---

## Debugging

### Logs

```bash
# View live logs in Railway dashboard, or via CLI:
railway logs
```

### Shell into Container

```bash
railway shell
# Now you're in the container; can run commands, inspect files
```

### Environmental Variable Issues

If a service can't start:

1. Check Railway logs for the error message
2. Verify all `ANTHROPIC_API_KEY`, `TWILIO_ACCOUNT_SID`, etc. are set
3. Test env vars locally: `python -c "import os; print(os.getenv('ANTHROPIC_API_KEY'))"`

### Database Connection Issues

```bash
# In railway shell:
psql $DATABASE_URL -c "SELECT 1"  # Test Postgres connection
redis-cli -u $REDIS_URL ping       # Test Redis connection
```

---

## More Info

- [Railway Docs](https://docs.railway.app)
- [PostgreSQL Plugin](https://docs.railway.app/plugins/postgresql)
- [Redis Plugin](https://docs.railway.app/plugins/redis)
- [Environment Variables](https://docs.railway.app/guides/variables)
- [Deploying a Python App](https://docs.railway.app/guides/python)
