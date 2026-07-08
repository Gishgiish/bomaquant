from src.api.app import create_app
from src.services.market_service import MarketService


app = create_app(service_factory=MarketService)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
