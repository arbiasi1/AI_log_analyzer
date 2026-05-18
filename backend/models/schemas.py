from datetime import datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


Severity = Literal["low", "medium", "high"]
OverallHealth = Literal["good", "warning", "critical"]


class ErrorFinding(BaseModel):
    error: str
    frequency: int = Field(ge=1)
    severity: Severity
    possible_cause: str
    suggested_fix: str


class AnalysisResult(BaseModel):
    summary: str
    errors_found: list[ErrorFinding]
    root_cause_analysis: str
    overall_health: OverallHealth


class AnalyzeRequest(BaseModel):
    logs: str = Field(min_length=1)
    source: str | None = None


class AnalysisRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    source: str
    raw_log_preview: str
    result: AnalysisResult
