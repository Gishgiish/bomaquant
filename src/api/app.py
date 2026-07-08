from contextlib import asynccontextmanager
from typing import Callable, Optional

from fastapi import Depends, FastAPI, HTTPException, Path, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.api.auth import get_current_user
from src.api.job_models import CreateJobRequest, JobResponse
from src.api.models import HealthResponse, MarketSummaryResponse, StockResponse
from src.config.settings import get_settings
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

    return app


app = create_app()
