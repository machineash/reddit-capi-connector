"""Send one event through the client (requires env vars set).

    export REDDIT_ACCOUNT_ID=... REDDIT_PIXEL_ID=... REDDIT_ACCESS_TOKEN=...
    python examples/send_event.py
"""
from capi_connector.auth import build_auth
from capi_connector.client import CapiClient
from capi_connector.config import Config
from capi_connector.models import ConversionEvent, Product, UserData


def main() -> None:
    cfg = Config.from_env()
    client = CapiClient(cfg, build_auth(cfg))
    event = ConversionEvent(
        event_name="Purchase",
        user=UserData(
            email="buyer@example.com",
            click_id="rdt_cid_example_123",
            ip_address="203.0.113.7",
            user_agent="Mozilla/5.0",
            screen_width=390,
            screen_height=844,
        ),
        value=59.99,
        currency="USD",
        item_count=1,
        products=[Product(id="sku_hoodie_01", name="Logo Hoodie", category="Apparel")],
    )
    resp = client.send_one(event)
    print("sent:", resp.status_code, "conversion_id:", event.conversion_id)


if __name__ == "__main__":
    main()
