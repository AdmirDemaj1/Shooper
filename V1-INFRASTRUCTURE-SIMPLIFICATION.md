# V1 Infrastructure Simplification: AWS/GCP → Railway

**TL;DR:** Removed all AWS/GCP/Kubernetes/Terraform references. V1 now uses **Railway** for hosting + **Twilio** for WhatsApp + **Anthropic** for AI. Total external accounts: 5. Total sprint cost: ~$50–100/month.

---

## What Changed

### Removed (Not Needed for V1)

❌ AWS or GCP cloud account
❌ Terraform (infrastructure-as-code)
❌ Kubernetes clusters, pods, deployments
❌ Helm charts
❌ VPCs, subnets, security groups
❌ IAM roles and policies
❌ Route53 / Cloud DNS (using Cloudflare instead)
❌ AWS Secrets Manager (using Railway env vars instead)
❌ ECR / Artifact Registry (Railway builds Docker images)
❌ RDS provisioning (Railway includes PostgreSQL)
❌ ElastiCache provisioning (Railway includes Redis)
❌ EKS/GKE provisioning (Railway runs containers)

### Added (For V1)

✅ **Railway** — all-in-one hosting (PostgreSQL, Redis, auto-deploy, $5–$50/month)
✅ **Twilio WhatsApp** — messaging (instead of Meta Business verification)
✅ **Anthropic Claude API** — AI/ranking (existing, unchanged)
✅ **Firebase** — auth (existing, unchanged)
✅ **Cloudflare** — DNS (free, replaced Route53)

---

## New Required External Accounts

| Account | Cost | Setup Time | Notes |
|---------|------|-----------|-------|
| **Railway** | $5–$50/mo | 5 min | Sign up via GitHub, add PostgreSQL + Redis plugins |
| **Twilio** | $3–$10/mo | 10 min | WhatsApp sandbox + API keys |
| **Anthropic** | $4–$10/mo | 2 min | API key, set spending limit |
| **Firebase** | Free | 5 min | Phone OTP for +355 |
| **Cloudflare** | Free | 5 min | Point domain to Railway |
| **GitHub** | Free | 1 min | Already have it |
| **Domain** | ~$1/mo | 2 min | e.g., autoscout.al on Namecheap |
| **Apple Dev** | $99/yr | 2 weeks | App store requirement |
| **Google Play** | $25 | 5 min | App store requirement |

**Total V1 setup cost:** ~$35–$75/month (excluding domain and app store, which are one-time/annual).

---

## Files Updated

### Sprint Documents

- ✅ **Sprint-0-Foundations.md**
  - Removed AWS/GCP workstream
  - Replaced with Railway setup
  - Simplified third-party accounts list

- ✅ **Sprint-1-Skeleton.md**
  - Changed "deploy to Kubernetes" → "deploy to Railway"
  - Removed Helm/Kustomize references

- ✅ **Sprint-5-WhatsApp-Integration.md**
  - Added note: "Dev: Twilio, Prod: consider Meta Cloud API"

### Guides & Documentation

- ✅ **SPRINT-0-SETUP.md**
  - Removed AWS/GCP accounts
  - Added Railway quick-start
  - Removed Terraform instructions

- ✅ **RAILWAY-SETUP.md** (new)
  - Complete Railway setup guide (10 minutes)
  - Add PostgreSQL + Redis plugins
  - Environment variables configuration
  - Custom domain setup
  - Spending limits
  - How to deploy crawlers as background workers
  - Cost breakdown

- ✅ **autoscout-docs/twilio-integration.md** (existing)
  - Already documents Twilio setup

- ✅ **autoscout-backend/.env.example**
  - Updated with Twilio vars, removed AWS SDK vars

- ✅ **autoscout-backend/pyproject.toml**
  - Added `twilio` dependency

- ✅ **GitHub Actions Workflow** (`.github/workflows/backend-ci.yml`)
  - Removed Docker build + push to ECR
  - Now just runs lint and tests
  - Railway auto-deploys on push to main


---

## Deployment Flow (V1)

**Old flow (AWS/GCP):**
1. Push code → GitHub
2. CI runs tests, builds Docker image
3. CI pushes image to ECR/Artifact Registry
4. CI updates Kubernetes deployment manifest
5. Kubernetes pulls image, scales pods
6. Load balancer routes traffic

**New flow (Railway):**
1. Push code → GitHub
2. Railway webhook triggered (auto)
3. Railway builds Dockerfile
4. Railway deploys container (auto-restart if needed)
5. Railway handles DNS, SSL, load balancing
6. Done ✅

**Total cycle:** ~2 minutes from git push to live.

---

## Scaling from V1 → V2

### When to Stay on Railway
- <1,000 active users
- Monthly spend <$200
- No exotic infrastructure needs (most teams don't have them)

### When to Migrate to AWS/GCP
- \>5,000 active users
- Monthly spend trending >$500
- Specific compliance requirements (e.g., data residency in EU)
- Need advanced observability, custom networking, etc.

**Migration cost:** Low. All code is containerized and portable. Just export DB dumps and update connection strings.

---

## Cost Protection

Set spending alerts on all services:

| Service | Alert Level |
|---------|------------|
| Railway | $100/month |
| Anthropic | $50/month (critical; LLM costs can spike) |
| Twilio | $20/month |
| All others | As-you-go |

These are 5-minute setups per service and will save you from runaway costs due to bugs.

---

## Summary

| Metric | Before | After |
|--------|--------|-------|
| **External accounts needed** | 10+ | 5–6 |
| **Setup time** | 3–4 weeks | 1–2 days |
| **Monthly infrastructure cost** | $500–$1,000 | $50–$100 |
| **DevOps complexity** | High (Terraform, K8s, IAM) | Low (buttons in web UI) |
| **Time to deploy** | 5–10 min (CI/CD) | 2 min (Railway auto-detects) |
| **Ability to scale** | Infinite but complex | Good for V1–V2, migrate later if needed |

**Verdict:** Railway is the right choice for V1. It removes weeks of DevOps work and hundreds of dollars in monthly costs, while keeping the door open to AWS/GCP when you actually need them.
