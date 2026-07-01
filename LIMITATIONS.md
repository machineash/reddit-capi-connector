# Limitations & What I'd Verify With Real API Access

This is a reference implementation I built to work through Reddit's Conversions API
end to end. It runs and is tested, but I want to be clear about what I could and
couldn't confirm without a live Reddit Ads account and API credentials.

## Would confirm against official docs / prod access

- **Exact endpoint path and API version.** I've made the events URL configurable
  (`REDDIT_CAPI_EVENTS_URL`) and defaulted to a documented-style path, but the
  precise version should be confirmed against current Reddit Ads API access.
- **`event_at` timestamp format.** I send milliseconds; I'd confirm whether the
  current API expects seconds, milliseconds, or ISO-8601.
- **Full standard-event enum.** I support standard + Custom events; I'd validate
  the complete list of standard `tracking_type` values against the live spec.

## Deliberate scope choices (would change for production)

- **Dedup is in-memory.** Fine for a single-process demo; at scale I'd back it
  with a shared store (Redis or a DB) so it survives restarts and works across
  workers.
- **Events send one request at a time.** I'd add batch mode (the API supports it)
  and move sending onto an async queue so a slow/failed call can't block callers.
- **No persistent retry/DLQ.** Retries are in-process with backoff; at scale I'd
  add a durable queue and a dead-letter path with alerting on repeated failures.
- **Observability is minimal.** I'd add structured logging + metrics (success
  rate, match-quality signal, latency) before trusting it in production.

## What I'm confident is correct

- SHA-256 hashing + normalization of PII (email, phone, external_id, IDFA, AAID),
  with a guard against double-hashing.
- Leaving click_id / conversion_id / uuid unhashed (hashing them breaks matching).
- Attribution validation (at least one signal required).
- Retry-on-429/5xx, fail-fast-on-4xx logic.
