from contextlib import asynccontextmanager
from typing import Callable, Optional

from fastapi import Depends, FastAPI, HTTPException, Path, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.api.auth import get_current_user
from src.api.domain_models import PortfolioRequest, PortfolioResponse, SubscriptionRequest, SubscriptionResponse
from src.api.job_models import CreateJobRequest, JobResponse
from src.api.models import HealthResponse, MarketSummaryResponse, StockResponse
from src.config.settings import get_settings
from src.services.audit_service import AuditService
from src.services.domain_repository import SQLiteDomainRepository
from src.services.domain_service import DomainService
from src.services.profile_service import ProfileService
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MarketServiceProtocol:
    def get_stock(self, symbol: str):
        raise NotImplementedError

    def get_market_summary(self):
        raise NotImplementedError


def create_app(
    service_factory: Optional[Callable[[], MarketServiceProtocol]] = None,
    persistence_service=None,
) -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info("backend_startup", extra={"app_env": settings.app_env, "auth_enabled": settings.auth_enabled})
        yield

    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

    service = service_factory() if service_factory else None
    persistence = persistence_service
    domain_repository = SQLiteDomainRepository()
    domain_service = DomainService(repository=domain_repository)
    profile_service = ProfileService()
    audit_service = AuditService()

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "type": "validation_error",
                    "message": "Request validation failed",
                    "details": exc.errors(),
                }
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail
        if isinstance(detail, dict):
            payload = detail
        else:
            payload = {"type": "http_error", "message": str(detail)}
        return JSONResponse(status_code=exc.status_code, content={"error": payload})

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_exception", extra={"path": request.url.path, "error": str(exc)})
        return JSONResponse(
            status_code=500,
            content={"error": {"type": "internal_error", "message": "Internal server error"}},
        )

    def get_service() -> MarketServiceProtocol:
        if service is None:
            raise RuntimeError("Service not configured")
        return service

    def require_portfolio_access(user: str) -> None:
        settings = get_settings()
        if settings.auth_enabled and not profile_service.can_access_portfolios(user):
            raise HTTPException(status_code=403, detail="premium access required")

    @app.get("/health", response_model=HealthResponse)
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/health/ready")
    def readiness() -> dict:
        return {"status": "ready", "app_env": settings.app_env}

    @app.get("/stocks/{symbol}", response_model=StockResponse)
    def get_stock(
        symbol: str = Path(..., min_length=1, description="Stock symbol to look up"),
        service: MarketServiceProtocol = Depends(get_service),
    ) -> dict:
        normalized_symbol = symbol.strip().upper()
        if not normalized_symbol:
            raise HTTPException(
                status_code=422,
                detail={"type": "validation_error", "message": "symbol must not be empty"},
            )

        payload = service.get_stock(normalized_symbol)
        if payload.get("success") is False:
            raise HTTPException(
                status_code=502,
                detail=payload.get("error", {}).get("message", "market data unavailable"),
            )
        return payload

    @app.get("/market/summary", response_model=MarketSummaryResponse)
    def get_market_summary(
        service: MarketServiceProtocol = Depends(get_service),
        user: str = Depends(get_current_user),
    ) -> dict:
        return service.get_market_summary()

    @app.post("/jobs", response_model=JobResponse)
    def create_job(
        request: CreateJobRequest,
        user: str = Depends(get_current_user),
    ) -> dict:
        if persistence is None:
            raise HTTPException(status_code=500, detail="persistence service unavailable")
        return persistence.create_job(request.title, request.description, request.payload)

    @app.get("/jobs/{job_id}", response_model=JobResponse)
    def get_job(job_id: str, user: str = Depends(get_current_user)) -> dict:
        if persistence is None:
            raise HTTPException(status_code=500, detail="persistence service unavailable")
        job = persistence.get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="job not found")
        return job

    @app.post("/profiles/me")
    def upsert_profile(request: dict, user: str = Depends(get_current_user)) -> dict:
        profile = profile_service.upsert_profile(
            username=user,
            plan=request.get("plan", "free"),
            status=request.get("status", "active"),
            features=list(request.get("features", [])),
        )
        return profile

    @app.get("/profiles/me")
    def get_profile(user: str = Depends(get_current_user)) -> dict:
        profile = profile_service.get_profile(user)
        if profile is None:
            raise HTTPException(status_code=404, detail="profile not found")
        return profile

    @app.post("/portfolios", response_model=PortfolioResponse)
    def create_portfolio(request: PortfolioRequest, user: str = Depends(get_current_user)) -> dict:
        require_portfolio_access(user)
        portfolio = domain_service.create_portfolio(request.name, list(request.symbols))
        audit_service.record(user, "create", "portfolio", request.name, {"symbols": list(request.symbols)})
        return portfolio

    @app.put("/portfolios/{name}", response_model=PortfolioResponse)
    def update_portfolio(name: str, request: PortfolioRequest, user: str = Depends(get_current_user)) -> dict:
        require_portfolio_access(user)
        portfolio = domain_service.update_portfolio(name, list(request.symbols))
        audit_service.record(user, "update", "portfolio", name, {"symbols": list(request.symbols)})
        return portfolio

    @app.get("/portfolios", response_model=list[PortfolioResponse])
    def list_portfolios(user: str = Depends(get_current_user)) -> list[dict]:
        require_portfolio_access(user)
        return domain_service.list_portfolios()

    @app.get("/portfolios/{name}", response_model=PortfolioResponse)
    def get_portfolio(name: str, user: str = Depends(get_current_user)) -> dict:
        portfolio = domain_service.get_portfolio(name)
        if portfolio is None:
            raise HTTPException(status_code=404, detail="portfolio not found")
        return portfolio

    @app.post("/subscriptions", response_model=SubscriptionResponse)
    def create_subscription(request: SubscriptionRequest, user: str = Depends(get_current_user)) -> dict:
        subscription = domain_service.create_subscription(
            plan=request.plan,
            customer_id=request.customer_id,
            status=request.status,
            features=list(request.features),
        )
        return subscription

    @app.get("/subscriptions/{customer_id}", response_model=SubscriptionResponse)
    def get_subscription(customer_id: str, user: str = Depends(get_current_user)) -> dict:
        subscription = domain_service.get_subscription(customer_id)
        if subscription is None:
            raise HTTPException(status_code=404, detail="subscription not found")
        return subscription

    @app.get("/watchlists/{portfolio_name}")
    def get_watchlist(portfolio_name: str, user: str = Depends(get_current_user)) -> dict:
        require_portfolio_access(user)
        portfolio = domain_service.get_portfolio(portfolio_name)
        if portfolio is None:
            raise HTTPException(status_code=404, detail="portfolio not found")
        return portfolio

    @app.post("/watchlists/{portfolio_name}/items")
    def add_watchlist_item(portfolio_name: str, request: dict, user: str = Depends(get_current_user)) -> dict:
        require_portfolio_access(user)
        portfolio = domain_service.get_portfolio(portfolio_name)
        if portfolio is None:
            raise HTTPException(status_code=404, detail="portfolio not found")
        symbols = list(portfolio.get("symbols", []))
        symbol = str(request.get("symbol", "")).strip().upper()
        if symbol and symbol not in symbols:
            symbols.append(symbol)
            domain_service.update_portfolio(portfolio_name, symbols)
        audit_service.record(user, "create", "watchlist_item", portfolio_name, {"symbol": symbol})
        return {"name": portfolio_name, "symbols": symbols}

    @app.get("/audit/logs")
    def get_audit_logs(user: str = Depends(get_current_user)) -> list[dict]:
        return audit_service.list_logs()

    return app


app = create_app()
