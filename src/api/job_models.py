from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class CreateJobRequest(BaseModel):
    title: str = Field(min_length=1)
    description: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)


class JobResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    report: Optional[Dict[str, Any]] = None
    status: str
    created_at: str
    updated_at: str
