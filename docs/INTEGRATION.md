# Partner Integration Guide

A step-by-step guide for an advertiser or partner integrating server-side
conversions with Reddit via this connector. Written the way a solutions/business
engineer would hand it to a partner's dev team.

## 1. Prerequisites

- A Reddit Ads account with a **Pixel** created (Events Manager → Pixel).
- Either a **Conversion Access Token** (Events Manager → Conversions API →
  Generate Access Token) or **OAuth2 client credentials**.
- Your **ad account id** and **pixel id**.

## 2. Decide what to send

Start with your highest-value conversion (usually `Purchase`), then add funnel
events (`AddToCart`, `ViewContent`, `SignUp`). For each event you will need:

- An **attribution signal** — at minimum one of: `click_id` (from `rdt_cid` on
  the landing URL), hashed `email`, `IP + user_agent + screen dimensions`,
  `IDFA`, or `AAID`. More signals = better match quality.
- A **`conversion_id`** — a unique id per event, used for deduplication.

## 3. Deduplication (important)

If you run the **Pixel and CAPI together** (recommended), send the **same**
`conversion_id` and event name from both sources for the same user action. Reddit
collapses the pair so the conversion is counted once. Do **not** reuse one
`conversion_id` across different events — that suppresses real conversions.

## 4. Handling PII

Never send raw email/phone off your servers. This connector hashes them with
SHA-256 after normalizing (lowercase/trim email; digits-only phone). Do **not**
hash `click_id`, `conversion_id`, or the Reddit `uuid` — those must stay raw to
match.

## 5. Rollout

1. Keep `CAPI_TEST_MODE=true`. Fire test events.
2. Confirm they appear in **Reddit Events Manager** and check the
   **Match Quality Score**.
3. Flip `CAPI_TEST_MODE=false` once events look correct.
4. Monitor delivery; add retry alerting on repeated 5xx/429.

## 6. Payload shape (illustrative)

See `examples/sample_event.json`. The connector converts that into Reddit's CAPI
event structure (`event_type.tracking_type`, `event_at_ms`, hashed `user`,
`event_metadata` with `conversion_id`, value, currency, products).

> Verify exact field names and the endpoint version against Reddit's current
> official CAPI documentation before going live.
