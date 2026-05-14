AutoScout AI
AI-Powered Car Discovery via WhatsApp
Product & Engineering Plan
Version 1.0
May 2026
 
1. Executive Summary
AutoScout AI is a mobile-first service that lets users define what kind of used car they are looking for (price, model, location, mileage, year range, condition) and then runs autonomous AI agents every day to scan dozens of marketplaces, classifieds, and dealer sites across the web. Matching listings are delivered directly to the user's WhatsApp inbox with photos, key specs, price, location, seller contact, and a deep link back to the source.
The product replaces the painful daily ritual of manually browsing five or ten different car websites with a single conversational interface. The user sets their criteria once; the agents work continuously in the background.
Core Value Proposition
•	Set it and forget it: users define search criteria once and receive curated matches daily
•	Multi-source coverage: aggregates listings from sites the user would otherwise visit individually
•	WhatsApp-native delivery: no need to open an app to see new results; messages arrive where users already spend time
•	AI-driven filtering: relevance scoring removes obvious mismatches and duplicates
Target Users (V1)
•	Individual buyers actively shopping for a used car (1–3 month buying window)
•	Power buyers monitoring the market for a specific model or deal threshold
•	Resellers and small dealers sourcing inventory below market price
Success Metrics for V1 (First 90 Days Post-Launch)
•	500 active users with at least one active search profile
•	70%+ daily WhatsApp message open rate
•	Average 3+ user-initiated source-link clicks per week per user
•	Less than 15% unsubscribe rate within the first 30 days of signup
 
2. Product Scope
2.1 In Scope for V1
•	iOS and Android mobile app (React Native)
•	User authentication via phone number + OTP
•	Search profile creation and management (multiple profiles per user)
•	Daily automated crawling and filtering across 4–6 priority sources
•	WhatsApp Business API integration for daily digest delivery
•	Listing deduplication and persistence (so users don't see the same car twice)
•	Basic analytics dashboard for ops (internal tool, not user-facing)
•	Single country launch (recommend: country with strong used-car classifieds market and WhatsApp penetration, e.g. Brazil, Mexico, Spain, Portugal, Italy, or India). For now we will start with Albania only.
2.2 Out of Scope for V1
•	In-app messaging with sellers (users contact sellers directly via the source platform)
•	Payment processing or escrow
•	Vehicle history reports (Carfax/equivalent integration deferred to V2)
•	Price prediction or market analytics
•	New car listings (used only)
•	Web app (mobile-only at launch)
•	Multi-country support (single country launch, expand in V2)
2.3 Key Assumptions and Risks
Scraping legality and platform ToS: Several major sources (Facebook Marketplace in particular) prohibit automated scraping. We will mitigate via a tiered source strategy — start with sources that have public APIs or permissive terms, and treat ToS-restricted sources as optional enhancements requiring legal review.
WhatsApp Business API costs: Per-message and per-conversation pricing varies by country and message category. Marketing-template messages cost more than utility/service messages. The product is structured as a utility (user-requested, on-demand listings) to qualify for the lower-cost service tier.
LLM operating cost: Running an agent on every search every day will be expensive at scale. We will use classical scraping plus rule-based filtering for the bulk of the work, and only invoke the LLM for ranking, summarization, and ambiguous matches.
Source blocking: Marketplaces actively detect and block scrapers. Mitigated with rotating residential proxies, headless browsers, fingerprint randomization, and respectful rate limits.
 
3. System Architecture
3.1 High-Level Components
Mobile app (React Native): User-facing client for signup, search profile management, and viewing history. Communicates with backend via REST/GraphQL API.
API gateway and backend service: FastAPI (Python) service handling auth, search profile CRUD, user preferences, and admin endpoints.
Job scheduler: Celery Beat or Temporal triggers each user's search on a configurable cadence (default: once per day, randomized within a 4-hour window to spread load).
Crawler workers: Pool of containerized workers that execute searches against source sites. Each worker handles one source per job; uses Playwright for JS-heavy sites and direct HTTP for API-friendly sources.
AI agent layer: LLM-powered service (Claude API) that performs relevance scoring, deduplication via semantic similarity, listing summarization, and natural-language search parsing.
Notification service: Formats matched listings into WhatsApp templates and dispatches via the WhatsApp Business API.
Data stores: PostgreSQL for users/profiles/listings, Redis for job queues and caching, S3-compatible object storage for cached listing photos.
3.2 Data Flow
1.	User creates a search profile in the mobile app
2.	Profile is saved to PostgreSQL; scheduler picks it up on the next daily cycle
3.	Scheduler enqueues one job per (profile × source) combination in Redis
4.	Crawler workers pull jobs, execute searches against the source, and emit raw listings
5.	Raw listings flow into a normalization service that maps source-specific fields to a canonical schema
6.	Deduplication service hashes listings (VIN if available, otherwise location + price + make + model + year + photo perceptual hash) and discards duplicates
7.	AI agent scores each remaining listing against the user's profile (0–100 relevance score)
8.	Top N listings (configurable, default 5) are formatted into a WhatsApp template message
9.	Notification service dispatches the message; delivery status is logged
10.	User receives the WhatsApp digest with photos, summary, and source links
3.3 Deployment Architecture
•	Container orchestration: Kubernetes (managed: EKS, GKE, or DigitalOcean Kubernetes) for V1; consider managed serverless (Cloud Run, ECS Fargate) if team lacks Kubernetes experience
•	CI/CD: GitHub Actions with automated tests, container builds, and staged deployments (dev → staging → prod)
•	Observability: structured logs to Datadog or Grafana Loki; metrics in Prometheus; error tracking in Sentry
•	Secrets management: AWS Secrets Manager or HashiCorp Vault — no secrets in environment files committed to source control
 
4. Technology Stack
4.1 Stack Decision Table
Layer	Technology	Rationale
Mobile app	React Native + Expo	Single codebase for iOS and Android, large talent pool, Expo speeds up build and OTA updates
Mobile state	Zustand + React Query	Lightweight, simpler than Redux; React Query handles server cache and refetch logic
Backend API	Python 3.12 + FastAPI	Native async support, strong typing via Pydantic, ecosystem overlap with the AI/ML side
Database	PostgreSQL 16	JSONB for flexible listing payloads, full-text search for fallback queries, mature operationally
Cache and queue	Redis 7	Job queue (via Celery or RQ), rate-limit counters, hot-listing cache
Scheduler	Celery Beat (V1), evaluate Temporal for V2	Celery is sufficient for periodic jobs at V1 scale; Temporal becomes worth it when workflows grow
Crawling	Playwright + httpx	Playwright for JS-rendered pages, httpx for direct API calls; rotating residential proxies via Bright Data or Oxylabs
LLM / agents	Anthropic Claude API	Claude Sonnet for ranking/summarization; tool use for structured extraction; strong long-context handling
Vector search	pgvector extension	Embedding-based deduplication; avoids running a separate vector DB
WhatsApp delivery	Meta WhatsApp Business Platform (Cloud API)	Direct integration cheaper than BSPs at scale; Twilio as fallback for faster onboarding if needed
Auth	Firebase Auth (phone OTP) or Auth0	Battle-tested phone-OTP flow; saves weeks vs building in-house
Object storage	Cloudflare R2 or AWS S3	R2 has no egress fees, which matters for image-heavy WhatsApp messages
Hosting	AWS or GCP	Managed Kubernetes, RDS, secrets, monitoring — pick whichever the team has more experience with
Observability	Sentry + Datadog (or Grafana Cloud)	Sentry for errors; Datadog/Grafana for logs, traces, and metrics in one place
Analytics	PostHog (self-hosted or cloud)	Product analytics + feature flags + session replay in one tool
4.2 Why This Stack
The stack is deliberately conservative. Each technology is mature, has a large hiring pool, and has well-known failure modes. The most novel parts — the AI agent layer and the WhatsApp delivery — are the parts where we are willing to spend complexity. Everything else (auth, mobile app, backend, database) is built on rails that thousands of teams have shipped before.
The AI surface is intentionally narrow at V1. We do not use the LLM for crawling itself (too slow, too expensive); we use it for ranking and dedup, which are the parts where deterministic rules struggle.
 
5. Data Model
5.1 Core Entities
users
•	id (uuid, pk)
•	phone_number (e164 string, unique)
•	whatsapp_opt_in (boolean)
•	country (iso2)
•	locale (e.g. pt-BR, en-US)
•	created_at, updated_at
search_profiles
•	id (uuid, pk)
•	user_id (fk)
•	name (e.g. 'Honda Civic under 80k')
•	make, model (nullable; null = any)
•	year_min, year_max
•	price_min, price_max
•	mileage_max
•	location_lat, location_lng, radius_km
•	body_type, transmission, fuel_type (nullable)
•	free_text_criteria (e.g. 'no accidents, single owner preferred')
•	is_active (boolean)
•	delivery_time_local (hour of day to send digest, in user's timezone)
•	created_at, updated_at
sources
•	id, name, country, crawl_strategy (api|html|browser), is_enabled, last_crawl_at
listings
•	id (uuid, pk)
•	source_id (fk), source_listing_id (string)
•	source_url (text)
•	title, description
•	make, model, year, mileage, price, currency
•	location_lat, location_lng, location_text
•	photos (jsonb array of urls)
•	seller_name, seller_phone, seller_type (private|dealer)
•	raw_payload (jsonb, source-specific fields)
•	embedding (vector(384), for dedup)
•	dedup_hash (string, indexed)
•	first_seen_at, last_seen_at, is_active
matches
•	id, search_profile_id (fk), listing_id (fk)
•	relevance_score (0–100)
•	llm_reasoning (text, why this matched)
•	delivered_at, delivery_channel ('whatsapp'), delivery_status
•	user_action (null|clicked|dismissed|saved)
whatsapp_messages
•	id, user_id, template_name, payload (jsonb), provider_message_id, status, sent_at, delivered_at, read_at
5.2 Indexes That Matter
•	listings(dedup_hash) — unique, for fast dedup lookup
•	listings(source_id, source_listing_id) — unique, for upserts
•	matches(search_profile_id, delivered_at) — for 'has this user already seen this listing'
•	search_profiles(is_active, delivery_time_local) — for scheduler scans
•	pgvector index on listings.embedding for ANN dedup
 
6. Source Strategy
6.1 Tiered Approach
Tier 1 (build first): Sources with public APIs, RSS feeds, or permissive ToS. These are the foundation. Examples vary by country but typically include manufacturer-affiliated marketplaces, aggregator APIs, and government-run classified sites.
Tier 2 (build second): Major used-car marketplaces (e.g. AutoTrader, OLX, Mercado Libre, Standvirtual, Subito, CarDekho, depending on country) that can be scraped via standard HTML parsing without violating clear ToS prohibitions.
Tier 3 (legal review required): Facebook Marketplace, Craigslist in some jurisdictions, and similar platforms with explicit anti-scraping clauses. Treat these as optional V2+ work, contingent on legal review and risk acceptance by leadership.
6.2 Source Adapter Pattern
Each source is implemented as a class conforming to a common interface:
•	search(profile: SearchProfile) → list of raw listings
•	parse(raw_listing) → normalized Listing object
•	health_check() → boolean for the dashboard
This isolates source-specific logic. When a source changes its HTML structure (which will happen), only that one adapter breaks; the rest of the system is unaffected.
6.3 Anti-Blocking Measures
•	Rotating residential proxies (Bright Data, Oxylabs, or Smartproxy) — single biggest factor in scraper longevity
•	Realistic browser fingerprints via Playwright with stealth plugins
•	Human-like timing: randomized delays, mouse movements, scroll patterns on JS-heavy sites
•	Respectful rate limits: never more than one request per source per few seconds per IP
•	Honor robots.txt where it does not block the entire site (defensive posture, even where not legally required)
•	Monitor block rates per source; alert ops when a source's success rate drops below 80%
6.4 When a Source Breaks
Source breakage is when, not if. The runbook:
11.	Monitoring detects the success rate drop and pages on-call engineer
12.	Engineer reproduces the failure locally, identifies whether it is a DOM change, a block, or a CAPTCHA wall
13.	If DOM change: update the adapter's selectors, deploy
14.	If soft block: rotate proxy pool, increase delays
15.	If CAPTCHA wall: assess whether the source is still viable; if not, disable and notify product team
 
7. AI Agent Layer
7.1 Where the LLM Adds Value
Search query parsing: User types 'looking for a 2018-2020 Civic under $20k, manual transmission, near Austin' — LLM extracts structured fields and populates the search profile form. This is a one-shot operation per profile creation, so cost is negligible.
Relevance scoring: Given a search profile and a candidate listing, return a 0–100 relevance score and a short explanation. Bulk-batched (10–20 listings per LLM call) to keep cost low.
Listing summarization: Generate the short blurb that appears in the WhatsApp message ('2019 Civic, 45k miles, single owner, clean title, photos look excellent'). Cached so subsequent matches of the same listing reuse the summary.
Soft dedup: When the hash-based dedup is ambiguous (e.g. two listings with same make/model/year/location but slightly different prices), embeddings + LLM tiebreaker decide whether they are the same car re-listed or two different cars.
7.2 Where the LLM Does Not Add Value
•	Crawling pages — far too slow and expensive; classical scraping is orders of magnitude cheaper
•	Strict filtering (price, year, mileage bounds) — deterministic rules are faster, cheaper, and more predictable
•	Image processing — use a dedicated vision model or perceptual hashing, not a general LLM
7.3 Prompt Engineering Discipline
•	All prompts versioned in source control; never edited in production
•	Each prompt has a regression test suite of input/output pairs
•	LLM outputs constrained via JSON schema (tool use) — no free-form parsing
•	Token usage logged per call; daily cost reports per feature
•	Fall back to deterministic rules if the LLM is unavailable or rate-limited
7.4 Cost Budget Estimate
Rough envelope (Claude Sonnet pricing as of 2026, subject to change):
•	Relevance scoring: ~500 tokens per listing × 50 listings per user per day × $0.003/1k tokens = ~$0.08 per user per day
•	Summarization: cached aggressively; expect ~10% cache miss rate, ~$0.01 per user per day
•	Query parsing: one-time per profile creation, negligible
•	Total per active user per day: ~$0.10–$0.15 in LLM costs; design pricing accordingly
 
8. WhatsApp Integration
8.1 Provider Choice
Two viable paths:
Direct Meta WhatsApp Business Cloud API: Lowest per-message cost, full control. Requires more setup work (Business Manager verification, phone number provisioning, template approvals). Recommended for V1.
Business Solution Provider (Twilio, MessageBird, 360dialog): Higher per-message cost but faster onboarding and helpful tooling. Recommended only if the team wants to skip the Meta verification process initially.
8.2 Message Categories
•	Utility messages: triggered by user opt-in/action; lower cost; appropriate for daily digest sent at user's chosen time
•	Authentication messages: OTP for login; separate template category
•	Marketing messages: avoid — higher cost and stricter rules; not needed for V1
8.3 Template Examples
Templates require pre-approval by Meta. Plan for 24–48 hour review per template.
Daily Digest Template
Header: Image (top match's photo)
Body: 'Hi {{1}}, here are today's top {{2}} matches for your search "{{3}}":'
Buttons: 'View Listing' (URL button, dynamic), 'See All' (URL to app), 'Pause Alerts' (quick reply)
OTP Template
Body: 'Your AutoScout AI verification code is {{1}}. It expires in 10 minutes.'
8.4 Opt-In and Compliance
•	Explicit opt-in captured during signup with clear language about daily messages
•	Easy opt-out via 'Pause' or 'Stop' commands processed by an inbound webhook
•	Maintain a suppression list — never message a user who has opted out, regardless of new profile creation
•	Honor WhatsApp's 24-hour customer service window rules for free-form replies
 
9. Sprint Plan
The plan assumes a team of 5 engineers (1 mobile, 2 backend, 1 ML/AI, 1 full-stack/devops), 1 designer, 1 PM, and 2-week sprints. Total timeline to launch: 14 weeks (7 sprints) plus a 2-week beta and 2 weeks of buffer = roughly 4.5 months.
Note: Sprint estimates assume zero external blockers. WhatsApp template approval and any legal review on Tier 3 sources should be started as early as possible — both have wall-clock delays the team cannot compress.
Sprint 0 — Foundations (2 weeks, pre-development)
Goals
•	Project setup, hiring complete, all accounts provisioned
Deliverables
•	Cloud accounts (AWS or GCP) provisioned with billing alerts
•	Meta Business Manager account verified; WhatsApp Business API access requested
•	LLM provider accounts (Anthropic) with billing and rate limits configured
•	Proxy provider account (Bright Data or equivalent) with trial bandwidth
•	Repos created: mobile-app, backend, crawler-workers, infra (Terraform), docs
•	CI/CD pipelines for each repo (build, lint, test, deploy to dev)
•	Country selected for launch; legal review of Tier 1 and Tier 2 sources initiated
•	Design system started (Figma): brand, palette, typography, core components
Sprint 1 — Skeleton (Weeks 1–2)
Goals
•	Standing-up the minimum scaffold for everyone to work in parallel
Backend
•	FastAPI service with health endpoint, deployed to dev
•	PostgreSQL provisioned; initial migrations for users, search_profiles, listings, matches
•	Auth integration with Firebase Auth (phone OTP); /me endpoint working
Mobile
•	React Native + Expo project; onboarding flow with phone OTP
•	Bottom-tab navigation: Searches, History, Settings
•	Empty-state screens for each tab
Crawler
•	Worker container template; first source adapter (a Tier 1 source) returns listings end-to-end to dev DB
Definition of Done
•	A developer can sign up on the mobile app, log in, and see their user record in the DB
•	A manual trigger of the crawler populates listings for that source
Sprint 2 — Search Profile Creation (Weeks 3–4)
Backend
•	CRUD endpoints for search_profiles with validation
•	Natural-language search parsing endpoint (calls Claude API with tool-use schema)
•	Geographic search support (PostGIS extension; location + radius queries)
Mobile
•	Search profile creation flow: form-based AND natural language input
•	Search profile list, edit, delete, toggle active/inactive
•	Location picker with map and radius slider
Definition of Done
•	A user can create a search profile via the mobile app using natural language; it is correctly parsed into structured fields and saved
Sprint 3 — Multi-Source Crawling (Weeks 5–6)
Crawler
•	3 additional source adapters (mix of Tier 1 and Tier 2)
•	Proxy rotation and request retry logic
•	Source health monitoring; per-source success rate metrics in Prometheus
Backend
•	Listing normalization service: canonical schema, currency normalization, mileage units
•	Dedup service v1: hash-based dedup using make + model + year + location + price
•	Scheduler: Celery Beat job that scans active profiles and enqueues crawl jobs daily
Definition of Done
•	A search profile triggers crawls across 4 sources daily; deduplicated listings persisted; ops dashboard shows per-source success rates
Sprint 4 — Matching and Ranking (Weeks 7–8)
Backend
•	Strict filter pass: remove listings outside price/year/mileage/location bounds
•	LLM relevance scoring service (batched, with caching, with deterministic fallback)
•	Embedding-based soft dedup using pgvector
•	Match persistence: write to matches table with score, reasoning, and dedup status
Mobile
•	Search history screen: shows past matches per profile with relevance scores
•	Listing detail view with photos, specs, source link
AI/ML
•	Prompt regression test suite for ranking and summarization
•	Cost dashboard: LLM tokens per user per day
Definition of Done
•	Given a profile and a day's crawl, the system produces a ranked, deduplicated set of matches end-to-end
Sprint 5 — WhatsApp Integration (Weeks 9–10)
Backend
•	WhatsApp Business Cloud API integration
•	Template message dispatch with media (top match photo as header)
•	Inbound webhook for user replies (Pause, Stop, opt-out handling)
•	Delivery status tracking (sent / delivered / read / failed)
Mobile
•	Onboarding: explicit WhatsApp opt-in with clear copy
•	Settings: notification schedule (time of day), pause/resume per profile, opt-out
Ops
•	Submit all production templates for Meta approval (start of sprint — approval is the long pole)
Definition of Done
•	A user opted into WhatsApp receives a daily digest message with top matches, working source links, and a pause button
Sprint 6 — Polish, Hardening, Internal Dogfood (Weeks 11–12)
Cross-cutting
•	Error handling and graceful degradation throughout
•	Rate limiting on public API endpoints
•	Load testing the crawler and notification pipelines (10x expected V1 load)
•	Security audit: auth flows, data access patterns, secrets handling
•	Privacy review and policy: data retention, GDPR/LGPD compliance depending on country
•	Onboarding all internal staff as dogfood users; collecting feedback
Definition of Done
•	System runs unattended for 7 consecutive days with no human intervention required
•	Internal users report meaningfully relevant daily digests
Sprint 7 — Beta Launch (Weeks 13–14)
Goals
•	Closed beta with 50–100 external users in launch country
Activities
•	Recruitment: friends/family + targeted social posts in car-enthusiast communities
•	Daily monitoring of: crawl success rates, LLM costs per user, WhatsApp delivery rates, user-reported relevance
•	Rapid iteration on prompts and source adapters based on real usage
•	Weekly cohort analysis: engagement, opt-out rate, click-through to source listings
Definition of Done
•	Beta cohort metrics meet or exceed launch criteria (see Success Metrics)
•	No critical bugs unresolved for more than 48 hours
•	Public launch readiness: app store listings approved, support process documented
Buffer (Weeks 15–16)
Reserved for the things that always come up: app store review back-and-forth, a source breaking right before launch, a WhatsApp template rejection, a critical bug found in beta. Treat as non-negotiable — teams that skip the buffer ship late or broken.
 
10. Team and Roles
Role	Allocation	Responsibilities
Product Manager	Full-time	Roadmap, prioritization, stakeholder communication, beta program ownership
Tech Lead / Backend Engineer	Full-time	Architecture, API service, schema design, code review, technical roadmap
Backend Engineer (Crawling)	Full-time	Source adapters, anti-blocking, normalization, proxy infrastructure
AI/ML Engineer	Full-time	Prompt engineering, ranking pipeline, evaluation suite, cost optimization
Mobile Engineer	Full-time	React Native app, store submissions, mobile-side analytics integration
Full-stack / DevOps	Full-time	Infrastructure, CI/CD, monitoring, WhatsApp integration, admin tools
Product Designer	Full-time first 8 weeks, then half-time	Design system, onboarding, mobile screens, WhatsApp message templates
Legal counsel	On retainer	ToS review per source, privacy policy, terms of service, country-specific compliance
 
11. Cost Estimates
11.1 Pre-Launch Infrastructure (Months 1–4, per month)
•	Cloud compute and managed services (Kubernetes, RDS, Redis): $400–$700
•	LLM API spend during dev and testing: $200–$500
•	Proxy provider (residential, ~50GB/month during development): $300–$600
•	WhatsApp BSP fees or Cloud API setup: $0–$100
•	Observability tools (Sentry, Datadog free tier, PostHog cloud): $100–$300
•	Other (domains, code signing, app store accounts): $200 one-time
•	Approximate monthly burn during build phase: $1,000–$2,200
11.2 Per-Active-User Variable Cost (Steady State)
•	LLM (ranking + summarization): $0.10–$0.15 per active user per day = ~$3–$4.50 per month
•	Proxy bandwidth allocated per user: $0.20–$0.40 per month
•	WhatsApp utility messages (1 per day, country-dependent): $0.20–$1.00 per month
•	Compute and storage (amortized): ~$0.10–$0.20 per month
•	Total: roughly $4–$6 per active user per month in variable cost
11.3 Pricing Implications
To net positive margins, target either: a paid subscription at $9.99–$14.99/month (typical SaaS-style pricing), or a freemium model where free users get one search profile with weekly delivery, and paid users get unlimited profiles with daily delivery. The freemium path drives top-of-funnel but pushes more variable cost; the paid-only path is simpler to operate but harder to grow.
 
12. Risk Register
Risk	Likelihood	Impact	Mitigation
Major source blocks scrapers entirely	High	High	Tiered source strategy; build 4+ sources so no single block is fatal; rotating residential proxies; ongoing adapter maintenance budget
WhatsApp template rejected / account banned	Medium	High	Strict opt-in language; utility category only; multiple template versions in review; SMS fallback channel ready
LLM cost runs higher than estimated	Medium	Medium	Per-user cost dashboard; aggressive caching; deterministic fallback for ranking; cost alerts at 1.5x budget
Low relevance / users churn after first week	Medium	High	In-beta relevance grading; prompt iteration; user feedback buttons in WhatsApp message; cohort-by-cohort analysis
Legal action from a source platform	Low	Critical	Stay in Tier 1/2; document legal review; do not crawl Tier 3 sources without explicit signoff; respond to cease-and-desist within 24h
Mobile app rejected by app store	Low	Medium	Follow app store guidelines strictly; submit early in Sprint 7; have responses ready for common review questions about scraping/data use
Team velocity slower than planned	High	Medium	2-week buffer built in; weekly sprint review; ruthless V1 scope discipline (everything cuttable is in V2)
 
13. Beyond V1
Once V1 is live and the core loop is healthy, the following are strong candidates for V2 and beyond. None of them should distract V1 execution.
V2 Candidates (3–6 months post-launch)
•	Tier 3 source coverage (Facebook Marketplace, etc.) pending legal signoff
•	Vehicle history report integration (Carfax/equivalent) — high perceived value
•	Price prediction: 'this car is 12% below market' badges on listings
•	Saved listings and side-by-side comparison in the app
•	Multi-country expansion (one new country per quarter)
•	Web app for desktop search profile management
V3 Candidates (6–12 months post-launch)
•	Conversational search in WhatsApp itself ('show me more like the second one')
•	Dealer mode: B2B tier for small dealers sourcing inventory
•	Cross-vertical expansion: same engine, applied to motorcycles, then real estate, then jobs
•	Negotiation assist: draft initial outreach message to the seller from inside the app
13.1 Architectural Decisions That Enable Future Work
•	Source adapter pattern: adding a new country mostly means writing new adapters, not changing core logic
•	Canonical listing schema: extending to motorcycles or real estate means a new entity type, not a rewrite
•	LLM service abstraction: swapping providers or models requires changes in one place
•	WhatsApp-first, but the notification service is channel-agnostic — email, SMS, in-app push can be added with one adapter each
