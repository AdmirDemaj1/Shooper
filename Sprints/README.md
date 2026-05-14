# AutoScout AI — Sprint Plan

Detailed implementation files for the sprints defined in [Planner.md](../Planner.md) §9.

**Team:** 5 engineers (1 mobile, 2 backend, 1 ML/AI, 1 full-stack/DevOps), 1 designer, 1 PM
**Cadence:** 2-week sprints
**Total timeline:** 14 weeks of sprints + 2 weeks beta + 2 weeks buffer ≈ 4.5 months
**Launch country:** Albania

## Sprint Index

| # | Sprint | Weeks | Focus |
|---|--------|-------|-------|
| 0 | [Foundations](Sprint-0-Foundations.md) | pre-dev | Accounts, repos, CI/CD, legal review kickoff |
| 1 | [Skeleton](Sprint-1-Skeleton.md) | 1–2 | Auth, backend skeleton, first crawler adapter |
| 2 | [Search Profile Creation](Sprint-2-Search-Profile-Creation.md) | 3–4 | Profile CRUD + natural-language parsing |
| 3 | [Multi-Source Crawling](Sprint-3-Multi-Source-Crawling.md) | 5–6 | 4 source adapters, scheduler, hash dedup |
| 4 | [Matching and Ranking](Sprint-4-Matching-and-Ranking.md) | 7–8 | Strict filters + LLM ranking + soft dedup |
| 5 | [WhatsApp Integration](Sprint-5-WhatsApp-Integration.md) | 9–10 | Cloud API, templates, daily digest delivery |
| 6 | [Polish, Hardening, Dogfood](Sprint-6-Polish-Hardening-Dogfood.md) | 11–12 | Load test, security review, 7-day unattended run |
| 7 | [Beta Launch](Sprint-7-Beta-Launch.md) | 13–14 | 50–100 external Albanian users, go/no-go decision |
|   | Buffer | 15–16 | Reserved for app store reviews, late bugs, source breakage |

## How These Documents Relate to Planner.md

`Planner.md` is the single source of truth for product scope, architecture, tech stack, data model, and risk register. Each sprint document **expands** the corresponding entry in Planner §9 with task-level detail: workstreams per role, explicit definition-of-done, dependencies, and watch-outs.

If a sprint document conflicts with `Planner.md`, the planner wins — open an issue and reconcile.
