"""Typed models for conversion events and the Reddit CAPI payload they produce.

Field names follow Reddit's Conversions API shape as documented at build time.
Verify against the current official CAPI reference before production, since the
schema evolves (v3 at time of writing).
"""
from __future__ import annotations

import time
import uuid as uuidlib
from dataclasses import dataclass, field

from .hashing import maybe_hash_email, maybe_hash_generic, maybe_hash_phone


class AttributionError(ValueError):
    """Raised when an event carries no usable attribution signal."""


@dataclass
class UserData:
    email: str | None = None
    phone: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    screen_width: int | None = None
    screen_height: int | None = None
    idfa: str | None = None            # iOS advertising id
    aaid: str | None = None            # Android advertising id
    click_id: str | None = None        # rdt_cid — do NOT hash
    reddit_uuid: str | None = None     # _rdt_uuid cookie — do NOT hash
    external_id: str | None = None

    def has_attribution_signal(self) -> bool:
        """Reddit requires at least one: click id, email, IP+UA+screen, IDFA, AAID."""
        if self.click_id:
            return True
        if self.email:
            return True
        if self.ip_address and self.user_agent and self.screen_width and self.screen_height:
            return True
        if self.idfa or self.aaid:
            return True
        return False

    def to_payload(self) -> dict:
        out: dict = {}
        if self.email:
            out["email"] = maybe_hash_email(self.email)
        if self.phone:
            out["phone_number"] = maybe_hash_phone(self.phone)
        if self.ip_address:
            out["ip_address"] = self.ip_address
        if self.user_agent:
            out["user_agent"] = self.user_agent
        if self.screen_width and self.screen_height:
            out["screen_dimensions"] = {
                "width": self.screen_width,
                "height": self.screen_height,
            }
        if self.idfa:
            out["idfa"] = maybe_hash_generic(self.idfa)
        if self.aaid:
            out["aaid"] = maybe_hash_generic(self.aaid)
        if self.click_id:
            out["click_id"] = self.click_id          # unhashed by design
        if self.reddit_uuid:
            out["uuid"] = self.reddit_uuid            # unhashed by design
        if self.external_id:
            out["external_id"] = maybe_hash_generic(self.external_id)
        return out


@dataclass
class Product:
    id: str
    name: str | None = None
    category: str | None = None

    def to_payload(self) -> dict:
        p = {"id": self.id}
        if self.name:
            p["name"] = self.name
        if self.category:
            p["category"] = self.category
        return p


@dataclass
class ConversionEvent:
    event_name: str                                   # standard, e.g. "Purchase", or "Custom"
    user: UserData
    custom_event_name: str | None = None              # required when event_name == "Custom"
    conversion_id: str = field(default_factory=lambda: str(uuidlib.uuid4()))  # dedup key
    event_at_ms: int = field(default_factory=lambda: int(time.time() * 1000))
    value: float | None = None
    currency: str | None = None
    item_count: int | None = None
    products: list[Product] = field(default_factory=list)

    def validate(self) -> None:
        if not self.event_name:
            raise ValueError("event_name is required")
        if self.event_name == "Custom" and not self.custom_event_name:
            raise ValueError('custom_event_name is required when event_name is "Custom"')
        if not self.user.has_attribution_signal():
            raise AttributionError(
                "Event has no attribution signal. Provide at least one of: "
                "click_id, email, IP+user_agent+screen dimensions, IDFA, or AAID."
            )

    def to_payload(self) -> dict:
        self.validate()
        event_type: dict = {"tracking_type": self.event_name}
        if self.event_name == "Custom":
            event_type["custom_event_name"] = self.custom_event_name

        metadata: dict = {"conversion_id": self.conversion_id}
        if self.value is not None:
            metadata["value"] = self.value
        if self.currency:
            metadata["currency"] = self.currency
        if self.item_count is not None:
            metadata["item_count"] = self.item_count
        if self.products:
            metadata["products"] = [p.to_payload() for p in self.products]

        return {
            "event_type": event_type,
            "event_at_ms": self.event_at_ms,
            "user": self.user.to_payload(),
            "event_metadata": metadata,
        }
