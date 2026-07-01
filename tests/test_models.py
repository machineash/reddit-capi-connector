import pytest

from capi_connector.hashing import is_sha256_hex
from capi_connector.models import (
    AttributionError,
    ConversionEvent,
    Product,
    UserData,
)


def test_attribution_requires_a_signal():
    event = ConversionEvent(event_name="Purchase", user=UserData())
    with pytest.raises(AttributionError):
        event.to_payload()


def test_click_id_alone_is_sufficient_attribution():
    event = ConversionEvent(event_name="Purchase", user=UserData(click_id="abc123"))
    payload = event.to_payload()
    assert payload["user"]["click_id"] == "abc123"  # unhashed by design


def test_email_is_hashed_but_click_id_is_not():
    event = ConversionEvent(
        event_name="Purchase",
        user=UserData(email="buyer@example.com", click_id="rdt_cid_1"),
    )
    payload = event.to_payload()
    assert is_sha256_hex(payload["user"]["email"])
    assert payload["user"]["click_id"] == "rdt_cid_1"


def test_ip_needs_ua_and_screen_to_count():
    only_ip = ConversionEvent(event_name="ViewContent", user=UserData(ip_address="1.2.3.4"))
    with pytest.raises(AttributionError):
        only_ip.to_payload()

    full = ConversionEvent(
        event_name="ViewContent",
        user=UserData(
            ip_address="1.2.3.4", user_agent="Mozilla/5.0",
            screen_width=390, screen_height=844,
        ),
    )
    full.to_payload()  # should not raise


def test_metadata_and_products_serialize():
    event = ConversionEvent(
        event_name="Purchase",
        user=UserData(click_id="c1"),
        value=42.5,
        currency="USD",
        item_count=2,
        products=[Product(id="sku_1", name="Hoodie", category="Apparel")],
    )
    payload = event.to_payload()
    md = payload["event_metadata"]
    assert md["value"] == 42.5
    assert md["currency"] == "USD"
    assert md["conversion_id"]  # auto-generated
    assert md["products"][0]["id"] == "sku_1"


def test_idfa_aaid_external_id_are_hashed():
    event = ConversionEvent(
        event_name="Purchase",
        user=UserData(click_id="c1", idfa="ABC-123", aaid="xyz-789", external_id="cust_42"),
    )
    u = event.to_payload()["user"]
    assert is_sha256_hex(u["idfa"])
    assert is_sha256_hex(u["aaid"])
    assert is_sha256_hex(u["external_id"])


def test_custom_event_requires_custom_name():
    bad = ConversionEvent(event_name="Custom", user=UserData(click_id="c1"))
    with pytest.raises(ValueError):
        bad.to_payload()

    good = ConversionEvent(
        event_name="Custom", custom_event_name="waitlist_join", user=UserData(click_id="c1")
    )
    et = good.to_payload()["event_type"]
    assert et["tracking_type"] == "Custom"
    assert et["custom_event_name"] == "waitlist_join"
