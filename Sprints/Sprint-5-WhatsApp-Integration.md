# Sprint 6 — WhatsApp Integration

**Duration:** Weeks 9–10
**Theme:** Get the daily digest into users' WhatsApp inboxes. Handle replies (Pause, Stop). Treat Meta template approval as the long pole — submit on day 1.

---

## Goals

- Approved WhatsApp templates ready for production use.
- Daily digest dispatched at each profile's `delivery_time_local`.
- Inbound webhook handles Pause / Stop / unrecognized replies gracefully.
- Delivery, read, and failure status flow back into `matches.delivery_status`.
- A user can opt out from the app OR by replying "Stop" and never receives another message.

## Out of Scope

- Conversational search ("show me more like the second one") — V3.
- In-app messaging with sellers — explicitly out of V1.
- SMS fallback — built as the contingency channel only, not a feature.

## Development Approach

**For dev/test:** Using Twilio WhatsApp API for rapid iteration and cost control. See `autoscout-docs/twilio-integration.md` for setup and patterns.

**For production:** Consider migrating to Meta WhatsApp Business Cloud API for lower per-message costs at scale. The notification service interface is channel-agnostic, so the switch is a one-day refactor.

---

## Workstreams

### Day 1 (highest priority) — Submit Templates for Approval

Meta review takes 24–48 hours per template and rejections cost a full cycle. Submit immediately.

#### Templates to submit:

**1. `autoscout_otp` — Authentication category**
```
Body: Your AutoScout AI verification code is {{1}}. It expires in 10 minutes.
```

**2. `autoscout_daily_digest` — Utility category**
```
Header: Image (top match's photo)
Body: Hi {{1}}, here are today's top {{2}} matches for your search "{{3}}":

{{4}}

Reply STOP to stop receiving these messages.
Buttons:
  - URL: "View top match" → dynamic source listing URL
  - URL: "See all matches" → autoscout.al/m/{{5}}
  - Quick reply: "Pause for a week"
```
- `{{4}}` is a multi-line block of "• 2018 Golf 7 — 7.500€ — 145.000km — Tiranë"-style bullets.

**3. `autoscout_paused_confirmation` — Utility**
```
Body: Hi {{1}}, you've paused alerts for "{{2}}". Reply RESUME to start receiving matches again.
```

**4. `autoscout_resumed_confirmation` — Utility**
```
Body: Welcome back. You'll receive matches for "{{1}}" again starting tomorrow.
```

**Submit Albanian + English versions of each template** in case of mixed-locale users.

### Backend — WhatsApp Service

- [ ] Module `notifications.whatsapp` wrapping Meta's WhatsApp Business Cloud API.
- [ ] Outbound dispatch:
  - `send_template(to, template_name, locale, components)`
  - Idempotency key per message (UUID stored on `whatsapp_messages` to prevent double-sends on retry).
  - Exponential backoff retry on 5xx; immediate fail on 4xx with structured error logged.
- [ ] `whatsapp_messages` table:
  ```
  id, user_id, match_id (nullable),
  template_name, locale,
  payload (jsonb),
  provider_message_id,
  status (pending|sent|delivered|read|failed|rejected),
  status_history (jsonb array of {status, ts, reason}),
  sent_at, delivered_at, read_at, failed_at,
  error_code, error_message
  ```
- [ ] **Media handling for digest headers:**
  - Download top-match photo from source URL.
  - Resize to ~1MB JPEG (Meta has size limits).
  - Upload to Meta's media endpoint (24h TTL), keep `media_id`.
  - Pre-cache: do this in a separate worker queue 30 min before scheduled send, so the digest worker never blocks on photo upload.
  - Store original in R2 as backup.

### Backend — Inbound Webhook

- [ ] `POST /webhooks/whatsapp` — handles both message events and status callbacks.
- [ ] **Signature verification** using Meta's `X-Hub-Signature-256` HMAC.
- [ ] Message event routing (case-insensitive, accent-insensitive Albanian):
  - "STOP" / "STOPP" / "NDALO" → mark user `whatsapp_opt_in=false`, suppress all future sends, send last-message confirmation (utility category, before 24h window expires).
  - "PAUSE" / "PAUZË" / "PRIT" → set all profiles `is_active=false` for 7 days (cron re-enables), reply with `autoscout_paused_confirmation`.
  - "RESUME" / "VAZHDO" → re-enable profiles, reply with `autoscout_resumed_confirmation`.
  - Unrecognized free-form text → no auto-reply (avoids 24h window cost); log for product review.
- [ ] Status callback routing: update `whatsapp_messages.status` and propagate to `matches.delivery_status`.

### Backend — Suppression List

- [ ] Table `whatsapp_suppressions`:
  ```
  phone_number (e164, pk)
  reason (opt_out|template_rejection|bounce|manual)
  suppressed_at
  ```
- [ ] Every outbound send checks suppression before dispatching.
- [ ] **A user re-signing up does NOT clear suppression** — they must explicitly opt back in via the app's settings (legal requirement).

### Backend — Delivery Scheduling

- [ ] New Celery Beat job: every 15 minutes, scan `matches` where `selected_for_delivery=true AND delivered_at IS NULL` AND profile's `delivery_time_local` window matches now in the user's timezone.
- [ ] Group by user × profile, build digest, dispatch.
- [ ] Rate limit: max 1 digest per user per profile per day (hard idempotency by `(profile_id, date_in_user_tz)`).

### Mobile — Onboarding & Settings

- [ ] **Onboarding step** (post-OTP, pre-first-profile): explicit WhatsApp opt-in screen:
  - Clear copy: "We'll send you up to one daily message per search with your top matches. You can pause or stop anytime by replying or in Settings."
  - Toggle, "Continue" disabled until toggle on.
  - Records `whatsapp_opt_in=true` with timestamp + IP (compliance trail).
- [ ] **Settings → Notifications:**
  - Master "WhatsApp notifications" toggle.
  - Per-profile: pause for a week, pause indefinitely, change delivery time.
- [ ] **Settings → Privacy:**
  - "Stop all messages and delete my account" — hard opt-out that adds to suppression list.

### Ops

- [ ] **Test mode** before live launch: 24-hour test period where digests only send to a hardcoded internal allow-list, even though scheduling is fully live. Catches dispatch logic bugs without spamming users.
- [ ] Grafana dashboard:
  - Digests sent per day
  - Delivery rate (target: >95%)
  - Read rate (target: >70% per success metric)
  - Opt-out rate per cohort (alert if any daily cohort >5%)
  - Inbound message volume + breakdown by intent
- [ ] Runbook: "WhatsApp template was rejected." Linked from on-call docs.
- [ ] Runbook: "Account quality rating dropped." (Meta downgrades sending throughput if opt-outs spike.)

### SMS Fallback Skeleton

- [ ] Behind a feature flag, wire a Twilio SMS channel using the same `notifications` interface.
- [ ] Goal is **not** to launch SMS as a feature in V1 — only to have a switch we can flip if WhatsApp templates get banned. Document the activation runbook.

---

## Definition of Done

1. Templates submitted on day 1 of the sprint are approved by end of week 1.
2. An internal test user with one active search profile receives a daily WhatsApp digest at their chosen time, with:
   - A photo of the top match in the header.
   - 3–5 bulleted match summaries.
   - A working "View top match" deep link.
   - A working "See all matches" link to the app.
3. Replying "STOP" stops messages immediately and adds to suppression.
4. Replying "PAUSE" pauses all profiles for 7 days.
5. Delivery status (sent / delivered / read) is reflected in `matches.delivery_status` within seconds.
6. The opt-out flow from Settings produces the same suppression result.
7. Grafana shows >95% delivery success across 50+ test messages.

---

## Risks & Watch-Outs

- **Template rejection is the most common Sprint 5 setback.** Have backup wording ready. Common Meta concerns: overly promotional tone, missing opt-out language, ambiguous variables. The bullet `Reply STOP to stop receiving these messages` line is non-negotiable for utility approval.
- **24-hour customer service window** — free-form replies (outside templates) cost nothing within 24h of a user's last message, but a fee outside it. Build dispatch to prefer templates always; free-form only for support handling.
- **Image upload size limits** — Meta caps headers at 5MB; resize aggressively. JPEG quality ~80 is a good default.
- **Albanian phone-number formatting** — Meta is strict about E.164; double-check `+355` formatting end-to-end.
- **Quality rating downgrade.** If opt-out rate spikes early in beta, Meta will throttle sending. Watch the dashboard daily.

---

## Dependencies

- Sprint 4 producing ranked matches with summaries and photos.
- Meta Business verification complete (from Sprint 0).
- WhatsApp phone number provisioned and verified.

---

## Next Sprint Preview

[Sprint 6 — Polish, Hardening, Internal Dogfood](Sprint-6-Polish-Hardening-Dogfood.md): error handling, load tests, security review, and all internal staff onboarded as dogfood users.
