from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PortfolioRequest(BaseModel):
    name: str = Field(min_length=1)
    symbols: List[str] = Field(default_factory=list)


class PortfolioResponse(BaseModel):
    name: str
    symbols: List[str] = Field(default_factory=list)


class SubscriptionRequest(BaseModel):
    plan: str = Field(min_length=1)
    customer_id: str = Field(min_length=1)
    status: str = Field(default="active")
    features: List[str] = Field(default_factory=list)


class SubscriptionResponse(BaseModel):
    plan: str
    customer_id: str
    status: str = "active"
    features: List[str] = Field(default_factory=list)
