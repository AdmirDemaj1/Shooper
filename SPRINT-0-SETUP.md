# Sprint 0 — Foundation Setup Complete

This document summarizes the foundational infrastructure and documentation created for AutoScout AI Sprint 0 (Foundations).

## What's Been Created

### 1. Sprint Documentation

See [Sprints/](Sprints/) for detailed implementation plans for all 8 sprints:

- **[Sprint-0-Foundations.md](Sprints/Sprint-0-Foundations.md)** — Accounts, repos, CI/CD, legal review
- **[Sprint-1-Skeleton.md](Sprints/Sprint-1-Skeleton.md)** — Auth, backend scaffold, first crawler
- **[Sprint-2-Search-Profile-Creation.md](Sprints/Sprint-2-Search-Profile-Creation.md)** — Profile CRUD + NLP parsing
- **[Sprint-3-Multi-Source-Crawling.md](Sprints/Sprint-3-Multi-Source-Crawling.md)** — 4 sources, scheduler, dedup
- **[Sprint-4-Matching-and-Ranking.md](Sprints/Sprint-4-Matching-and-Ranking.md)** — Filters, LLM ranking, soft dedup
- **[Sprint-5-WhatsApp-Integration.md](Sprints/Sprint-5-WhatsApp-Integration.md)** — Cloud API, digests, opt-out handling
- **[Sprint-6-Polish-Hardening-Dogfood.md](Sprints/Sprint-6-Polish-Hardening-Dogfood.md)** — Load test, security, 7-day run
- **[Sprint-7-Beta-Launch.md](Sprints/Sprint-7-Beta-Launch.md)** — 50–100 beta users, go/no-go decision

### 2. Repository Structure

#### Backend ([autoscout-backend/](autoscout-backend/))

- `README.md` — Setup, structure, environment variables
- `pyproject.toml` — Python dependencies (FastAPI, SQLAlchemy, Celery, etc.)
- `.env.example` — Sample environment variables
- `.gitignore` — Python-specific ignores

#### Mobile ([autoscout-mobile/](autoscout-mobile/))

- `README.md` — Expo setup, project structure, EAS build config
- `.env.example` — Firebase, Mapbox, API config
- `.gitignore` — Node/Expo ignores

#### Crawlers ([autoscout-crawlers/](autoscout-crawlers/))

- `README.md` — Worker pool, source adapter interface, testing
- Docstring guide for implementing source adapters


#### Documentation ([autoscout-docs/](autoscout-docs/))

- `README.md` — Structure for ADRs, runbooks, guides, retros, compliance

#### Prompts ([autoscout-prompts/](autoscout-prompts/))

- `README.md` — Versioned LLM prompts, test harness, regression suite workflow

### 3. CI/CD Pipelines

#### GitHub Actions ([.github/workflows/](../.github/workflows/))

- `backend-ci.yml` — Lint, test, build, push Docker image
  - Runs on PRs and merges to main
  - PostgreSQL + Redis services for testing
  - Coverage reporting via Codecov
  - Slack alerts on failure

## What You Need to Do Next (Completing Sprint 0)

### External Accounts (Must do manually)

**For hosting & infrastructure:**
- [ ] **Railway** account (sign up via GitHub) — includes PostgreSQL, Redis, auto-deploy
  - Set spending limit to $100/month in Railway project settings
  - Add domain `api.dev.autoscout.al` to Railway

**For messaging, AI, auth:**
- [ ] **Twilio** account for WhatsApp (see [autoscout-docs/twilio-integration.md](autoscout-docs/twilio-integration.md))
  - Set spending alerts in Twilio console
- [ ] **Anthropic Claude API** account + billing configured
  - **Critical:** Set spending limit (LLM bugs can be expensive)
- [ ] **Firebase** project created for +355 (Albania) phone OTP
- [ ] **GitHub** account + all code repos pushed

**For DNS & monitoring:**
- [ ] **Cloudflare** account (free) — for DNS management
- [ ] **Domain name** (~$12/year) — e.g., autoscout.al on Namecheap
- [ ] **Sentry** account (free tier) — optional but recommended for error tracking

**Before app store launch:**
- [ ] **Apple Developer** account ($99/year)
- [ ] **Google Play Console** account ($25 one-time)

### Repository Setup

- [ ] Initialize git repos from local directories (or push to GitHub)
- [ ] Create branch protection rules on `main` (require PR reviews, status checks)
- [ ] Add team members as collaborators
- [ ] **Connect Railway to GitHub:** Railway auto-detects Dockerfile or `pyproject.toml`/`package.json` and deploys on push to `main`

### Infrastructure with Railway

**No Terraform needed!** Railway handles everything:

- [ ] Create Railway project
- [ ] Add PostgreSQL plugin (Railway auto-provisions database)
- [ ] Add Redis plugin (Railway auto-provisions cache)
- [ ] Set environment variables in Railway dashboard: Twilio SID, Anthropic API key, Firebase credentials, etc.
- [ ] Point DNS (Cloudflare) to Railway's provided endpoint
- [ ] Test: push a commit to `main` branch → Railway auto-builds and deploys

### Legal & Compliance

- [ ] Engage external counsel familiar with Albanian commercial law
- [ ] Initiate legal review of Tier 1 and Tier 2 sources (merrjep.al, mobile.al, gjirafa.com, etc.)
- [ ] Draft privacy policy and terms of service
- [ ] Document data retention and compliance checklist

### Design System

- [ ] Finalize Figma library with brand, components, and token exports
- [ ] Export design tokens for mobile + web consumption

## Files Ready to Use

All READMEs include:

- **Project structure** — where to put code
- **Local dev setup** — how to install and run locally
- **Environment variables** — what secrets are needed (`.env.example` provided)
- **Testing** — how to run tests
- **Contributing** — PR and code quality standards

**Infrastructure:** Railway handles PostgreSQL, Redis, deploy, and secrets. No manual DevOps needed for V1.

## Next Steps: Sprint 1 Kickoff

Once Sprint 0 accounts are ready (most services instant, except Apple Developer approval):

1. Initialize git repos and push the skeleton code
2. Connect Railway to GitHub repositories
3. Add environment variables to Railway dashboard
4. Run `poetry install` in backend, `npm install` in mobile/crawlers
5. Push a test commit to `main` → Railway auto-deploys
6. Start Sprint 1 development on the [Sprint-1-Skeleton.md](Sprints/Sprint-1-Skeleton.md) tasks

## Questions?

Refer to the sprint documentation for detailed task breakdowns, definitions of done, and risk mitigations.
