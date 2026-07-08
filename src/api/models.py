from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator


class HealthResponse(BaseModel):
    status: str = Field(default="ok")


class ErrorResponse(BaseModel):
    success: bool = False
    error: Dict[str, Any] = Field(default_factory=dict)


class StockResponse(BaseModel):
    symbol: str
    price: Optional[float] = None
    currency: Optional[str] = None
    success: bool = True
    cached: bool = False

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, value: str) -> str:
        cleaned = value.strip().upper()
        if not cleaned:
            raise ValueError("symbol must not be empty")
        return cleaned


class MarketSummaryResponse(BaseModel):
    index_name: Optional[str] = None
    value: Optional[float] = None
    success: bool = True
    cached: bool = False
