"""A thin server-side receiver.

Your app/backend POSTs a conversion here; this service normalizes, hashes PII,
and forwards it to Reddit CAPI. Keeping this server-side is the whole point:
it survives ad blockers and browser signal loss that break the client Pixel.

Run locally:
    uvicorn capi_connector.server:app --reload
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .auth import build_auth
from .client import CapiClient, CapiError
from .config import Config
from .models import AttributionError, ConversionEvent, Product, UserData

app = FastAPI(title="Reddit CAPI Connector", version="0.1.0")


class UserIn(BaseModel):
    email: str | None = None
    phone: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    screen_width: int | None = None
    screen_height: int | None = None
    idfa: str | None = None
    aaid: str | None = None
    click_id: str | None = None
    reddit_uuid: str | None = None
    external_id: str | None = None


class ProductIn(BaseModel):
    id: str
    name: str | None = None
    category: str | None = None


class EventIn(BaseModel):
    event_name: str = Field(..., examples=["Purchase"])
    custom_event_name: str | None = None
    conversion_id: str | None = None
    value: float | None = None
    currency: str | None = None
    item_count: int | None = None
    user: UserIn
    products: list[ProductIn] = []


def _to_domain(payload: EventIn) -> ConversionEvent:
    user = UserData(**payload.user.model_dump())
    kwargs = dict(
        event_name=payload.event_name,
        user=user,
        custom_event_name=payload.custom_event_name,
        value=payload.value,
        currency=payload.currency,
        item_count=payload.item_count,
        products=[Product(**p.model_dump()) for p in payload.products],
    )
    if payload.conversion_id:
        kwargs["conversion_id"] = payload.conversion_id
    return ConversionEvent(**kwargs)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/conversions")
def forward_conversion(payload: EventIn) -> dict:
    cfg = Config.from_env()
    client = CapiClient(cfg, build_auth(cfg))
    event = _to_domain(payload)
    try:
        resp = client.send_one(event)
    except AttributionError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except CapiError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return {"forwarded": True, "conversion_id": event.conversion_id, "status": resp.status_code}
