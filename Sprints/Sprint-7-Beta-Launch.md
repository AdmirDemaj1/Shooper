# Sprint 7 — Beta Launch

**Duration:** Weeks 13–14
**Theme:** Closed beta with 50–100 external Albanian users. Real strangers, real searches, real money. The goal is to confirm the V1 success metrics are reachable before opening the floodgates.

---

## Goals

- Recruit 50–100 active Albanian beta users with at least one real search profile each.
- Hit success-metric trajectory:
  - 70%+ daily WhatsApp message open rate
  - 3+ user-initiated source-link clicks per week per user
  - <15% opt-out within 30 days
- Iterate daily on prompts, source adapters, and listing relevance based on real signals.
- Exit the sprint with go/no-go decision for public launch.

## Out of Scope

- Public launch (post-sprint, after buffer).
- New features beyond bug fixes and prompt tweaks.

---

## Workstreams

### Week 13 — Beta Recruitment & Onboarding

- [ ] **Recruitment channels** (target: 100 signups → ~60 active users):
  - Friends & family in Albania (target: 20)
  - Car enthusiast Facebook groups in Albania (with moderator permission; target: 30)
  - Reddit r/albania + local Discord communities (target: 20)
  - Internal team's personal networks (target: 30)
- [ ] **Beta landing page** at `beta.autoscout.al`:
  - One-line value prop in Albanian + English
  - "Apply for beta" form (name, phone, current car-shopping goal)
  - Privacy + ToS links
  - TestFlight + Play Internal Testing invite links sent after approval
- [ ] **Onboarding email/WhatsApp template:**
  - Welcome
  - Direct app download links
  - 60-second video walkthrough
  - Feedback link
- [ ] **Beta acceptance criteria:** users must be in Albania, have a WhatsApp number, actively shopping for a used car in the next 3 months.
- [ ] Cap initial accepts at 100; build a waitlist for overflow.

### Daily Operations (Week 13–14)

The team operates in a daily-rhythm cadence for two weeks:

**Morning standup (10 min):**
- Crawl success rates per source overnight
- Digests sent / delivered / read
- LLM spend yesterday
- New opt-outs (review reasons)
- Inbound support volume

**Evening review (30 min):**
- Sample 10 random digests from today; rate relevance manually
- Triage any new bugs filed
- Decide on prompt tweaks for tomorrow

### Metrics Dashboard (Beta)

Add to existing Mission Control dashboard:

- [ ] **Engagement:**
  - Daily Active Users (opened app)
  - Daily Active Recipients (received + opened digest)
  - Source-link click-through rate per user per week
  - "Save" / "Dismiss" action ratio on matches
- [ ] **Quality:**
  - Average match relevance score (LLM-assigned)
  - Manual relevance rating (sampled by team, 10/day)
  - Listings flagged "irrelevant" by users
- [ ] **Funnel:**
  - Signup → first profile created
  - First profile → first digest received
  - First digest → first source-link click
  - First digest → opt-out (target: <15% over 30 days)
- [ ] **Cohort analysis:** weekly cohorts by signup week; track retention curves.

### Rapid Iteration Loop

The team commits to fixing or improving based on real signal, not gut feel.

#### Prompt iteration

- [ ] Any time manual sampling finds a poor-quality digest, log it in `autoscout-prompts/beta-feedback/`.
- [ ] Twice a week, the AI/ML engineer reviews the log, proposes a prompt change, runs the regression suite, and ships if it passes.
- [ ] All prompt changes go through PR review; never live-edit prompts in prod.

#### Source iteration

- [ ] Track per-source contribution to delivered matches.
- [ ] If a source consistently produces <5% of matches AND has high maintenance cost, disable.
- [ ] If a source produces high-relevance matches, prioritize maintenance investment.
- [ ] **Add 1 extra Albanian source** if user feedback consistently mentions a site we don't cover (stretch goal — don't sacrifice stability).

#### User feedback loop

- [ ] In-app "Was this digest useful?" thumbs-up/down on each digest summary screen (writes to `digest_feedback` table).
- [ ] WhatsApp reply with "GOOD" or "BAD" → captured as match-level feedback.
- [ ] Weekly Typeform NPS survey to all beta users.
- [ ] **Office hours:** PM holds 30-min open WhatsApp office hours twice a week.

### Go / No-Go Criteria for Public Launch

Documented decision framework, evaluated at end of Sprint 7:

| Metric | Target | Acceptable | Block Launch If |
|--------|--------|------------|-----------------|
| 7-day digest open rate | 70%+ | 60%+ | <50% |
| Source-link clicks per user per week | 3+ | 2+ | <1 |
| 14-day opt-out rate | <10% | <15% | >25% |
| User-reported relevance ("useful?") | >60% positive | >50% positive | <40% |
| Crawl success rate per source | >90% | >80% | <70% on majority of sources |
| LLM cost per active user per day | <$0.15 | <$0.25 | >$0.40 |
| WhatsApp delivery rate | >98% | >95% | <90% |
| Critical bugs unresolved >48h | 0 | 0 | ≥1 |

If any "Acceptable" row breaks: extend beta by 2 weeks (eats into buffer).
If any "Block Launch If" row breaks: extend beta indefinitely, escalate to leadership.

### Incident Readiness

- [ ] **On-call rotation** active 24/7 during beta (one engineer per week).
- [ ] Pager budget: <2 alerts per week per engineer; more than that means the system isn't ready.
- [ ] **Incident response template** in `autoscout-docs`:
  - Detection time
  - Mitigation steps
  - User impact
  - Post-mortem within 48h
- [ ] Public status page (`status.autoscout.al`) updated within 10 min of any user-impacting incident.

### Compliance Loose Ends

- [ ] Final legal sign-off on operating in Albania with Tier 1 + Tier 2 sources.
- [ ] Terms of Service v1 published; users accept on signup.
- [ ] Cookie policy (web landing page only).
- [ ] **App store approval** secured (Apple + Google) — done by end of week 13 ideally so week 14 isn't a fire drill.

---

## Definition of Done

1. **50+ external Albanian beta users** active for at least 7 days.
2. **Engagement metrics meet or exceed the "Acceptable" column** of the go/no-go table.
3. **Zero critical bugs unresolved >48 hours.**
4. **App store listings approved** on both stores.
5. **Public launch readiness review meeting** held with leadership; documented decision and any conditions for launch.
6. **Post-sprint retrospective** held; lessons captured in `autoscout-docs/retros/`.

---

## Risks & Watch-Outs

- **Recruitment is harder than estimated.** Start outreach in Sprint 6 so applications are flowing on day 1 of Sprint 7.
- **Real users will find creative ways to break things.** Reserve ~30% of engineering capacity for unplanned beta-driven work.
- **App store rejection** late in week 14 is the classic ship-delay scenario. Submit early (week 13 ideally), keep the review notes thorough, have a fast iteration loop with the review team.
- **WhatsApp account quality** can drop fast if opt-outs spike. Watch the daily metric; if it goes from "high" to "medium," pause new signups and investigate.
- **Source attribution disputes.** A major Albanian classified might notice the traffic and request changes. Have the legal review documentation ready; respond within 24h.

---

## Dependencies

- All prior sprints complete.
- Apple + Google app store reviews submitted (started end of Sprint 6).

---

## Post-Sprint: Buffer Weeks (Weeks 15–16)

Reserved for the things that always come up. Treat as non-negotiable.

Typical buffer use:
- App store review back-and-forth
- A source breaking right before launch
- A WhatsApp template revision
- A critical bug found late in beta
- Marketing site polish
- Last-minute legal questions

**If the buffer is unused, the team takes time off. Do not pull V2 work forward to fill it.**

---

## Looking Forward — V2 Candidates (3–6 months post-launch)

Documented now so the team can deprioritize cleanly during beta:

- Tier 3 sources (Facebook Marketplace) pending legal review
- Vehicle history reports integration
- Price prediction badges
- Saved listings + side-by-side comparison
- Multi-country expansion (next country: Kosovo or North Macedonia, both Albanian-language adjacent)
- Web app for desktop search management
