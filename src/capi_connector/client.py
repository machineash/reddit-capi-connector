"""The Conversions API client: build the request, retry sensibly, send.

Design notes
------------
- Dedup: every event carries a conversion_id. Reddit dedupes CAPI events against
  matching Pixel events by (conversion_id, event_name). This client also guards
  against accidentally sending the *same* conversion_id twice in one process.
- Retries: 429 and 5xx are retried with exponential backoff; 4xx (other than 429)
  fail fast because they are caller errors, not transient ones.
"""
from __future__ import annotations

import time
from typing import Iterable

import httpx

from .config import Config
from .models import ConversionEvent


class CapiError(RuntimeError):
    pass


class CapiClient:
    def __init__(self, cfg: Config, auth, client: httpx.Client | None = None):
        self._cfg = cfg
        self._auth = auth
        self._client = client or httpx.Client(timeout=cfg.timeout_seconds)
        self._seen_conversion_ids: set[str] = set()

    # ---- payload -----------------------------------------------------------
    def _endpoint(self) -> str:
        # The exact path/version must be confirmed against Reddit's official CAPI
        # docs with real API access. Override with REDDIT_CAPI_EVENTS_URL when known.
        if self._cfg.capi_events_url:
            return self._cfg.capi_events_url
        return (
            f"{self._cfg.api_base_url}/api/{self._cfg.api_version}"
            f"/conversions/events/{self._cfg.account_id}"
        )

    def build_body(self, events: Iterable[ConversionEvent]) -> dict:
        return {
            "test_mode": self._cfg.test_mode,
            "events": [e.to_payload() for e in events],
            "pixel_id": self._cfg.pixel_id,
        }

    # ---- sending -----------------------------------------------------------
    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._auth.bearer()}",
            "Content-Type": "application/json",
            "User-Agent": "capi-connector/0.1",
        }

    def send(self, events: list[ConversionEvent]) -> httpx.Response:
        # local dedup guard
        deduped: list[ConversionEvent] = []
        for e in events:
            if e.conversion_id in self._seen_conversion_ids:
                continue
            self._seen_conversion_ids.add(e.conversion_id)
            deduped.append(e)
        if not deduped:
            raise CapiError("No new events to send (all conversion_ids already seen).")

        body = self.build_body(deduped)
        url = self._endpoint()

        backoff = 0.5
        last_exc: Exception | None = None
        for attempt in range(1, self._cfg.max_retries + 1):
            try:
                resp = self._client.post(url, json=body, headers=self._headers())
            except httpx.TransportError as exc:  # network blip
                last_exc = exc
                time.sleep(backoff)
                backoff *= 2
                continue

            if resp.status_code < 300:
                return resp
            if resp.status_code == 429 or resp.status_code >= 500:
                last_exc = CapiError(f"Retryable status {resp.status_code}: {resp.text}")
                time.sleep(backoff)
                backoff *= 2
                continue
            # non-retryable client error
            raise CapiError(f"CAPI rejected event ({resp.status_code}): {resp.text}")

        raise CapiError(f"Exhausted retries sending to CAPI: {last_exc}")

    def send_one(self, event: ConversionEvent) -> httpx.Response:
        return self.send([event])
