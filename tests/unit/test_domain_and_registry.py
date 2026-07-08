from src.services.domain_models import Portfolio, Subscription
from src.services.provider_registry import ProviderRegistry


def test_portfolio_tracks_symbols():
    portfolio = Portfolio(name="Growth", symbols=["SCOM", "EQTY"])

    portfolio.add_symbol("KCB")
    assert portfolio.symbols == ["SCOM", "EQTY", "KCB"]

    portfolio.remove_symbol("EQTY")
    assert portfolio.symbols == ["SCOM", "KCB"]


def test_subscription_serializes_cleanly():
    subscription = Subscription(plan="premium", customer_id="cust-001", status="active")

    payload = subscription.to_dict()

    assert payload["plan"] == "premium"
    assert payload["status"] == "active"
    assert payload["customer_id"] == "cust-001"


def test_provider_registry_resolves_named_provider():
    registry = ProviderRegistry()
    registry.register("demo", lambda settings=None: {"name": "demo"})

    provider = registry.get_provider("demo")

    assert provider["name"] == "demo"
    assert registry.list_providers() == ["demo"]
