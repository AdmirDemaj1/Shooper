# Sprint 0 — Foundations

**Duration:** 2 weeks (pre-development)
**Theme:** Get every account, repo, and pipeline in place so Sprint 1 can start without external blockers.
**Launch country:** Albania

---

## Goals

- Unblock all dependencies (external accounts, repos, CI/CD, design system) before code work begins.
- Set up Railway for hosting (no AWS/GCP overhead for V1).
- Ensure every engineer can push code and see it deploy automatically to `api.dev.autoscout.al` on day 1 of Sprint 1.

## Out of Scope

- Any product feature work
- Source adapter implementation
- LLM prompt engineering

---

## Workstreams

### 1. Hosting & Infrastructure

**For V1, skip AWS/GCP entirely.** Use Railway for hosting, PostgreSQL, and Redis. [See Railway docs](https://docs.railway.app/).

- [ ] **Railway account** — sign up via GitHub, create a new project.
- [ ] **PostgreSQL plugin** — Railway > Add > Postgres; database auto-provisioned.
- [ ] **Redis plugin** — Railway > Add > Redis; cache auto-provisioned.
- [ ] **Environment variables** — Railway dashboard; add all secrets here (Twilio, Anthropic, Firebase keys).
- [ ] **Spending alerts** — Railway project settings > Usage limits; set monthly cap ($100 recommended for dev).
- [ ] **Custom domain** — Railway > Domain; point to your autoscout.al via Cloudflare DNS.

### 2. Third-Party Accounts

**Required:**
- [ ] **GitHub** (free) — all code goes here.
- [ ] **Twilio** — WhatsApp messaging for dev. [Setup guide](../../autoscout-docs/twilio-integration.md). Add spending alerts in Twilio console.
- [ ] **Anthropic Claude API** — AI ranking and parsing. Set spending limit (critical — LLM bugs can be expensive). [Billing](https://console.anthropic.com).
- [ ] **Firebase** — phone OTP login. Create project, enable phone auth for +355 (Albania).
- [ ] **Cloudflare** (free) — DNS for your domain (autoscout.al).
- [ ] **Domain name** (~$12/year) — Namecheap or equivalent.

**Before launch (app store):**
- [ ] **Apple Developer Program** ($99/year) — required for iOS app store.
- [ ] **Google Play Console** ($25 one-time) — required for Android app store.
- [ ] **Meta Business Manager** (free) — for WhatsApp sender verification. See [Sprint 5 notes](Sprint-5-WhatsApp-Integration.md).

**Optional but useful:**
- [ ] **Sentry** (free tier) — error tracking and alerts.
- [ ] **PostHog** (free tier) — product analytics and session replay.

### 3. Repositories

Create one repo per service with branch protection on `main`:

- [ ] `autoscout-mobile` — React Native + Expo app
- [ ] `autoscout-backend` — FastAPI service
- [ ] `autoscout-crawlers` — worker pool + source adapters
- [ ] `autoscout-docs` — architecture decision records, runbooks
- [ ] `autoscout-prompts` — versioned LLM prompts + regression test suite

**Note:** For V1, no `autoscout-infra` repo needed. Railway handles everything (database, Redis, deploy, secrets).

Each repo needs:
- [ ] README with local dev setup
- [ ] `.editorconfig`, language-specific linter config
- [ ] PR template referencing checklist (tests, migrations, observability)
- [ ] CODEOWNERS file

### 4. CI/CD Pipelines (GitHub Actions)

For every repo:
- [ ] Lint job (ruff/eslint/etc.)
- [ ] Unit test job
- [ ] Auto-deploy to Railway on merge to `main` (Railway auto-builds and deploys via GitHub integration)

**Note:** Railway auto-detects your service (Dockerfile or `package.json` / `pyproject.toml`), builds, and deploys. No manual container pushes needed.

### 5. Legal & Compliance

- [ ] Engage external counsel familiar with Albanian commercial / data protection law.
- [ ] Initiate legal review of all Tier 1 and Tier 2 source ToS (target list: see Sprint 3 backlog).
- [ ] Draft privacy policy v0 (data retention, GDPR alignment — Albania has DPA Law 9887).
- [ ] Draft Terms of Service v0.
- [ ] Document Tier 3 source policy: no crawl without written legal sign-off.

### 6. Design System

- [ ] Brand: name, logo, color palette, typography.
- [ ] Figma library: buttons, inputs, cards, list rows, empty states.
- [ ] Onboarding flow wireframes (low-fi).
- [ ] WhatsApp message mockups (image + body + button layout).

### 7. Team Readiness

- [ ] All 5 engineers onboarded with access to all accounts and repos.
- [ ] Sprint cadence agreed (2-week sprints, planning Mon, demo Fri).
- [ ] On-call rotation drafted (even though not active yet).
- [ ] Communication channels: #autoscout-eng, #autoscout-product, #autoscout-alerts.

---

## Deliverables Checklist

- [ ] Every engineer can push a branch and watch CI run green on GitHub.
- [ ] Backend deployed to Railway and reachable at `api.dev.autoscout.al`.
- [ ] Crawlers and scheduler deployed as Railway background workers.
- [ ] PostgreSQL + Redis provisioned in Railway and accessible from services.
- [ ] All secret environment variables configured in Railway dashboard.
- [ ] Spending alerts set on Anthropic, Twilio, and Railway.
- [ ] Legal review kicked off for Tier 1 + Tier 2 Albanian sources.
- [ ] Figma design system v0 reviewed by team.

---

## Definition of Done

Sprint 0 is complete when **Sprint 1 can start on Monday with no blockers besides code**. If Meta verification or legal review is still pending, that's expected — but every account that *can* be ready, is ready.

---

## Risks & Watch-Outs

- **Railway quota exceeded.** Monitor spending from day 1. If dev environment hits $100/month, switch from `hobby` to `pro` tier or optimize resource usage (scale down worker concurrency, reduce test frequency).
- **Anthropic rate limit hits.** Claude API has rate limits per minute. Set `max_retries` and `timeout` in the SDK; use exponential backoff in your code. Set a spending limit so a runaway loop doesn't cost hundreds.
- **Legal review of Albanian sources may surface unexpected ToS restrictions.** Adjust source priority list as findings come in.
- **Apple Developer account approval** can take 1–2 weeks for organizational accounts — start day 1.

---

## Next Sprint Preview

[Sprint 1 — Skeleton](Sprint-1-Skeleton.md): stand up the minimum scaffold so all 5 engineers can work in parallel.
