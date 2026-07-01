"""Configuration, loaded from environment variables.

No secrets live in code. Copy .env.example to .env and fill it in, or export
the variables in your shell / deployment environment.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    # Reddit Ads identifiers
    account_id: str
    pixel_id: str

    # Auth: supply EITHER a conversion access token (simplest, long-lived)
    # OR OAuth2 client credentials. Access token wins if both are present.
    access_token: str | None = None
    client_id: str | None = None
    client_secret: str | None = None

    # Endpoints (verify against current Reddit Ads CAPI docs before production)
    api_base_url: str = "https://ads-api.reddit.com"
    api_version: str = "v2.0"  # VERIFY: confirm current version with API access
    # If set, this exact URL is used and api_base_url/api_version are ignored.
    capi_events_url: str | None = None
    oauth_token_url: str = "https://www.reddit.com/api/v1/access_token"

    # Behaviour
    test_mode: bool = True
    timeout_seconds: float = 10.0
    max_retries: int = 3

    @classmethod
    def from_env(cls) -> "Config":
        def req(key: str) -> str:
            val = os.environ.get(key)
            if not val:
                raise RuntimeError(f"Missing required environment variable: {key}")
            return val

        return cls(
            account_id=req("REDDIT_ACCOUNT_ID"),
            pixel_id=req("REDDIT_PIXEL_ID"),
            access_token=os.environ.get("REDDIT_ACCESS_TOKEN"),
            client_id=os.environ.get("REDDIT_CLIENT_ID"),
            client_secret=os.environ.get("REDDIT_CLIENT_SECRET"),
            api_base_url=os.environ.get("REDDIT_API_BASE_URL", cls.api_base_url),
            capi_events_url=os.environ.get("REDDIT_CAPI_EVENTS_URL"),
            test_mode=os.environ.get("CAPI_TEST_MODE", "true").lower() == "true",
        )

    def validate_auth(self) -> None:
        if self.access_token:
            return
        if self.client_id and self.client_secret:
            return
        raise RuntimeError(
            "No auth configured: set REDDIT_ACCESS_TOKEN, or both "
            "REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET."
        )
