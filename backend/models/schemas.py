from datetime import datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


Severity = Literal["low", "medium", "high"]
OverallHealth = Literal["good", "warning", "critical"]
Trend = Literal["stable", "rising", "falling", "spiky"]
IncidentPhase = Literal["detected", "correlated", "mitigating", "resolved"]
IncidentStatus = Literal["open", "investigating", "mitigating", "resolved"]
EnvironmentStatus = Literal["healthy", "degraded", "critical"]
AlertRuleStatus = Literal["enabled", "disabled"]


class ErrorFinding(BaseModel):
    error: str
    frequency: int = Field(ge=1)
    severity: Severity
    possible_cause: str
    suggested_fix: str


class MlSignal(BaseModel):
    name: str
    score: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    trend: Trend
    explanation: str


class IncidentEvent(BaseModel):
    time: str
    phase: IncidentPhase
    title: str
    detail: str


class ServiceImpact(BaseModel):
    service: str
    impact_score: int = Field(ge=0, le=100)
    evidence: str


class RunbookStep(BaseModel):
    title: str
    command: str | None = None
    rationale: str


class SloImpact(BaseModel):
    availability_risk: int = Field(ge=0, le=100)
    latency_risk: int = Field(ge=0, le=100)
    error_budget_burn: str
    customer_impact: str


class AnalysisResult(BaseModel):
    summary: str
    errors_found: list[ErrorFinding]
    root_cause_analysis: str
    overall_health: OverallHealth
    ai_engine: str = "local-ml"
    ai_model: str | None = None
    ai_provider_status: str = "local deterministic analysis"
    incident_score: int = Field(default=0, ge=0, le=100)
    ml_signals: list[MlSignal] = Field(default_factory=list)
    incident_timeline: list[IncidentEvent] = Field(default_factory=list)
    impacted_services: list[ServiceImpact] = Field(default_factory=list)
    runbook: list[RunbookStep] = Field(default_factory=list)
    slo_impact: SloImpact | None = None
    next_best_actions: list[str] = Field(default_factory=list)
    detection_notes: list[str] = Field(default_factory=list)


class AnalyzeRequest(BaseModel):
    logs: str = Field(min_length=1)
    source: str | None = None


class LoginRequest(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=1)


class UserProfile(BaseModel):
    email: str
    name: str
    role: str
    team: str


class AuthSession(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserProfile


class AuditEvent(BaseModel):
    created_at: datetime = Field(default_factory=datetime.utcnow)
    actor: str
    action: str
    detail: str


class Environment(BaseModel):
    id: str
    name: str
    status: EnvironmentStatus
    region: str
    risk_score: int = Field(ge=0, le=100)


class PlatformService(BaseModel):
    id: str
    name: str
    owner: str
    environment: str
    status: EnvironmentStatus
    risk_score: int = Field(ge=0, le=100)
    dependencies: list[str] = Field(default_factory=list)
    last_signal: str


class Incident(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    service: str
    environment: str = "production"
    severity: Severity
    status: IncidentStatus = "open"
    risk_score: int = Field(ge=0, le=100)
    owner: str = "Platform Engineering"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    summary: str
    recommended_action: str
    source_analysis_id: str | None = None


class AlertRule(BaseModel):
    id: str
    name: str
    service: str
    condition: str
    threshold: int
    status: AlertRuleStatus = "enabled"
    cooldown_minutes: int = Field(default=15, ge=1)


class DeployEvent(BaseModel):
    id: str
    service: str
    environment: str
    version: str
    actor: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    risk_note: str


class CopilotBrief(BaseModel):
    title: str
    summary: str
    priorities: list[str]
    recommended_owner: str


class PlatformOverview(BaseModel):
    environments: list[Environment]
    services: list[PlatformService]
    incidents: list[Incident]
    alert_rules: list[AlertRule]
    deployments: list[DeployEvent]
    copilot_brief: CopilotBrief


class AnalysisRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    source: str
    raw_log_preview: str
    result: AnalysisResult
