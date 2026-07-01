"""Authentication strategies.

Reddit supports two ways to authenticate CAPI calls:

1. Conversion access token — a long-lived, non-expiring token. Simplest.
2. OAuth2 client credentials — fetch a short-lived bearer token and refresh it
   when it expires. Included here to demonstrate the OAuth2 flow end to end.

The access token wins if both are configured.
"""
from __future__ import annotations

import time

import httpx

from .config import Config


class AccessTokenAuth:
    """Static, long-lived conversion access token."""

    def __init__(self, token: str):
        self._token = token

    def bearer(self) -> str:
        return self._token


class OAuth2ClientCredentials:
    """OAuth2 client-credentials grant with in-memory token caching + refresh."""

    def __init__(self, cfg: Config, client: httpx.Client | None = None):
        self._cfg = cfg
        self._client = client or httpx.Client(timeout=cfg.timeout_seconds)
        self._token: str | None = None
        self._expires_at: float = 0.0

    def _expired(self) -> bool:
        # refresh 60s early to avoid edge-of-expiry failures
        return self._token is None or time.time() >= (self._expires_at - 60)

    def _fetch(self) -> None:
        resp = self._client.post(
            self._cfg.oauth_token_url,
            data={"grant_type": "client_credentials"},
            auth=(self._cfg.client_id or "", self._cfg.client_secret or ""),
            headers={"User-Agent": "capi-connector/0.1"},
        )
        resp.raise_for_status()
        body = resp.json()
        self._token = body["access_token"]
        self._expires_at = time.time() + int(body.get("expires_in", 3600))

    def bearer(self) -> str:
        if self._expired():
            self._fetch()
        assert self._token is not None
        return self._token


def build_auth(cfg: Config):
    """Pick an auth strategy from config."""
    cfg.validate_auth()
    if cfg.access_token:
        return AccessTokenAuth(cfg.access_token)
    return OAuth2ClientCredentials(cfg)
