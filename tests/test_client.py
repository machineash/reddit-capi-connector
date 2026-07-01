import httpx
import pytest

from capi_connector.auth import AccessTokenAuth
from capi_connector.client import CapiClient, CapiError
from capi_connector.config import Config
from capi_connector.models import ConversionEvent, UserData


def make_client(handler) -> CapiClient:
    cfg = Config(account_id="acc1", pixel_id="px1", access_token="tok", max_retries=3)
    transport = httpx.MockTransport(handler)
    http = httpx.Client(transport=transport)
    return CapiClient(cfg, AccessTokenAuth("tok"), client=http)


def test_send_success_builds_expected_body():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json={"ok": True})

    client = make_client(handler)
    event = ConversionEvent(event_name="Purchase", user=UserData(click_id="c1"))
    resp = client.send_one(event)

    assert resp.status_code == 200
    assert "/conversions/events/acc1" in captured["url"]
    assert captured["auth"] == "Bearer tok"


def test_retries_on_500_then_succeeds():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(503, text="try again")
        return httpx.Response(200, json={"ok": True})

    client = make_client(handler)
    event = ConversionEvent(event_name="Purchase", user=UserData(click_id="c1"))
    resp = client.send_one(event)
    assert resp.status_code == 200
    assert calls["n"] == 3


def test_non_retryable_400_fails_fast():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, text="bad field")

    client = make_client(handler)
    event = ConversionEvent(event_name="Purchase", user=UserData(click_id="c1"))
    with pytest.raises(CapiError):
        client.send_one(event)


def test_local_dedup_blocks_repeated_conversion_id():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True})

    client = make_client(handler)
    e1 = ConversionEvent(event_name="Purchase", user=UserData(click_id="c1"), conversion_id="dup")
    e2 = ConversionEvent(event_name="Purchase", user=UserData(click_id="c1"), conversion_id="dup")
    client.send_one(e1)
    with pytest.raises(CapiError):
        client.send_one(e2)  # same conversion_id -> nothing new to send
