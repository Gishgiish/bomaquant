from src.services.domain_repository import SQLiteDomainRepository
from src.services.domain_service import DomainService


def test_domain_service_creates_and_retrieves_portfolio_and_subscription(tmp_path):
    repository = SQLiteDomainRepository(storage_path=str(tmp_path / "domain.sqlite3"))
    service = DomainService(repository=repository)

    portfolio = service.create_portfolio("Growth", ["SCOM", "EQTY"])
    assert portfolio["name"] == "Growth"
    assert portfolio["symbols"] == ["SCOM", "EQTY"]

    fetched_portfolio = service.get_portfolio("Growth")
    assert fetched_portfolio is not None
    assert fetched_portfolio["symbols"] == ["SCOM", "EQTY"]

    subscription = service.create_subscription("premium", "cust-001", status="active", features=["alerts"])
    assert subscription["customer_id"] == "cust-001"

    fetched_subscription = service.get_subscription("cust-001")
    assert fetched_subscription is not None
    assert fetched_subscription["plan"] == "premium"
