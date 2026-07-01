# Reddit Conversions API (CAPI) Connector

A small, server-side reference implementation for sending conversion events to the
**Reddit Conversions API**. It exists because browser-based tracking (the Reddit
Pixel) loses signal to ad blockers, ITP/ATT, and cookie restrictions — sending
events **server-to-server** recovers that signal and improves measurement and
campaign optimization.

This is the kind of proof-of-concept a partner/solutions engineer builds to get an
advertiser integrated quickly. It is intentionally small, readable, and tested.

> **Scope & honesty note:** This is a reference implementation, not an official
> Reddit SDK. Field names follow Reddit's documented CAPI shape at the time of
> writing; the endpoint path/version is configurable and should be confirmed
> against live API access. **Verify against the current official CAPI reference
> before production**, since the schema evolves. `CAPI_TEST_MODE=true`
> is the default so you can validate in Reddit Events Manager before going live.
> See [LIMITATIONS.md](LIMITATIONS.md) for what I'd confirm with real API access.

## What it demonstrates

- **OAuth2** client-credentials auth (with token caching + refresh), *and* the
  simpler long-lived conversion-access-token path — pick either via config.
- **PII hashing** done correctly: email/phone are normalized and SHA-256 hashed;
  attribution/dedup identifiers (click id, Reddit uuid, conversion id) are sent
  **unhashed by design**, because hashing them breaks matching.
- **Attribution validation**: an event is rejected unless it carries at least one
  usable signal (click id, email, IP+UA+screen, IDFA, or AAID).
- **Deduplication**: every event carries a `conversion_id` so Reddit can dedupe
  CAPI events against matching Pixel events; the client also guards against
  re-sending the same id in-process.
- **Resilient delivery**: 429/5xx retried with exponential backoff; other 4xx
  fail fast as caller errors.

## Architecture

```
your backend ──POST /conversions──▶  FastAPI receiver (server.py)
                                        │  normalize + hash PII (hashing.py)
                                        │  validate attribution (models.py)
                                        │  auth: OAuth2 or access token (auth.py)
                                        ▼
                                 Reddit Conversions API  (client.py: retries, dedup)
```

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env          # fill in your Reddit Ads values
pytest                        # 14 tests, no network needed

# run the receiver
uvicorn capi_connector.server:app --reload
# then POST examples/sample_event.json to http://127.0.0.1:8000/conversions
```

Send one event directly (no server):

```bash
export REDDIT_ACCOUNT_ID=... REDDIT_PIXEL_ID=... REDDIT_ACCESS_TOKEN=...
python examples/send_event.py
```

## Layout

| Path | What it does |
|------|--------------|
| `src/capi_connector/config.py`  | Env-based config; no secrets in code |
| `src/capi_connector/auth.py`    | OAuth2 client-credentials + access-token strategies |
| `src/capi_connector/hashing.py` | Normalize + SHA-256 PII (Reddit Advanced Matching) |
| `src/capi_connector/models.py`  | Event/user models, payload build, attribution rules |
| `src/capi_connector/client.py`  | Send with retries, backoff, dedup |
| `src/capi_connector/server.py`  | FastAPI receiver that forwards server-side |
| `tests/`                        | Hashing, models/attribution, client (mocked HTTP) |
| `docs/INTEGRATION.md`           | Partner integration guide |

## Why server-side (the AdTech context)

Client-side pixels miss events when a browser blocks scripts or strips cookies.
The Conversions API sends events from your server using first-party data, which
is more durable, improves match rates, and keeps measurement working as privacy
rules tighten. Pixel + CAPI are typically run **together**, with `conversion_id`
deduplicating the overlap.

## License

MIT — see [LICENSE](LICENSE).
