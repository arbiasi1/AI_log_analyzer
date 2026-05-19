from datetime import datetime

from backend.models.schemas import (
    AlertRule,
    AnalysisRecord,
    CopilotBrief,
    DeployEvent,
    Environment,
    Incident,
    PlatformOverview,
    PlatformService,
)


_incidents: list[Incident] = []
_alert_rules: list[AlertRule] = [
    AlertRule(
        id="rule-critical-recurrence",
        name="Critical recurrence guard",
        service="all-services",
        condition="Create incident when critical findings repeat",
        threshold=2,
        cooldown_minutes=10,
    ),
    AlertRule(
        id="rule-gateway-5xx",
        name="Gateway 5xx pressure",
        service="api-gateway",
        condition="Risk score above threshold for gateway or timeout signals",
        threshold=65,
        cooldown_minutes=15,
    ),
    AlertRule(
        id="rule-db-availability",
        name="Database availability risk",
        service="database",
        condition="Database signal appears in high-severity analysis",
        threshold=55,
        cooldown_minutes=20,
    ),
]

_deployments: list[DeployEvent] = [
    DeployEvent(
        id="deploy-api-2026-05-19",
        service="api-gateway",
        environment="production",
        version="api-gateway@2026.05.19",
        actor="release-bot",
        risk_note="Recent gateway release should be checked when 502/504 patterns appear.",
    ),
    DeployEvent(
        id="deploy-auth-2026-05-18",
        service="auth-service",
        environment="production",
        version="auth-service@2026.05.18",
        actor="platform-team",
        risk_note="Auth changes can explain 401/403, token, or timeout cascades.",
    ),
]


def get_platform_overview() -> PlatformOverview:
    services = _services_from_incidents()
    environments = _environments_from_services(services)
    return PlatformOverview(
        environments=environments,
        services=services,
        incidents=list(_incidents[:25]),
        alert_rules=list(_alert_rules),
        deployments=list(_deployments),
        copilot_brief=_copilot_brief(services),
    )


def get_incidents() -> list[Incident]:
    return list(_incidents)


def get_alert_rules() -> list[AlertRule]:
    return list(_alert_rules)


def record_analysis_incident(record: AnalysisRecord) -> Incident | None:
    result = record.result
    if result.overall_health != "critical" and result.incident_score < 70:
        return None

    service = (
        result.impacted_services[0].service
        if result.impacted_services
        else "unknown-service"
    )
    title = f"{service} incident from {record.source}"
    existing = next(
        (
            item
            for item in _incidents
            if item.service == service
            and item.status != "resolved"
            and item.source_analysis_id == record.id
        ),
        None,
    )
    if existing:
        return existing

    top_action = result.next_best_actions[0] if result.next_best_actions else "Investigate the highest severity signal."
    incident = Incident(
        title=title,
        service=service,
        severity="high",
        status="open",
        risk_score=result.incident_score,
        summary=result.summary,
        recommended_action=top_action,
        source_analysis_id=record.id,
    )
    _incidents.insert(0, incident)
    del _incidents[50:]
    return incident


def resolve_incident(incident_id: str) -> Incident | None:
    for incident in _incidents:
        if incident.id == incident_id:
            incident.status = "resolved"
            incident.updated_at = datetime.utcnow()
            return incident
    return None


def _services_from_incidents() -> list[PlatformService]:
    base = {
        "api-gateway": PlatformService(
            id="svc-api-gateway",
            name="api-gateway",
            owner="Platform Engineering",
            environment="production",
            status="healthy",
            risk_score=18,
            dependencies=["auth-service", "checkout-service"],
            last_signal="No active gateway pressure.",
        ),
        "auth-service": PlatformService(
            id="svc-auth-service",
            name="auth-service",
            owner="Identity Team",
            environment="production",
            status="healthy",
            risk_score=22,
            dependencies=["database"],
            last_signal="Token validation stable.",
        ),
        "database": PlatformService(
            id="svc-database",
            name="database",
            owner="Data Platform",
            environment="production",
            status="healthy",
            risk_score=20,
            dependencies=[],
            last_signal="Connection pool stable.",
        ),
        "worker": PlatformService(
            id="svc-worker",
            name="worker",
            owner="Backend Team",
            environment="production",
            status="healthy",
            risk_score=16,
            dependencies=["database", "queue"],
            last_signal="Job throughput normal.",
        ),
        "storage": PlatformService(
            id="svc-storage",
            name="storage",
            owner="Infrastructure",
            environment="production",
            status="healthy",
            risk_score=14,
            dependencies=[],
            last_signal="Volumes under threshold.",
        ),
    }

    for incident in _incidents:
        service = base.get(incident.service)
        if service is None:
            service = PlatformService(
                id=f"svc-{incident.service}",
                name=incident.service,
                owner=incident.owner,
                environment=incident.environment,
                status="degraded",
                risk_score=incident.risk_score,
                dependencies=[],
                last_signal=incident.summary,
            )
            base[incident.service] = service
        service.risk_score = max(service.risk_score, incident.risk_score)
        service.status = "critical" if incident.risk_score >= 75 else "degraded"
        service.last_signal = incident.summary

    return sorted(base.values(), key=lambda item: item.risk_score, reverse=True)


def _environments_from_services(services: list[PlatformService]) -> list[Environment]:
    prod_risk = max((service.risk_score for service in services), default=0)
    prod_status = "critical" if prod_risk >= 75 else "degraded" if prod_risk >= 45 else "healthy"
    return [
        Environment(
            id="env-production",
            name="production",
            status=prod_status,
            region="eu-central-1",
            risk_score=prod_risk,
        ),
        Environment(
            id="env-staging",
            name="staging",
            status="healthy",
            region="eu-central-1",
            risk_score=12,
        ),
    ]


def _copilot_brief(services: list[PlatformService]) -> CopilotBrief:
    active = [incident for incident in _incidents if incident.status != "resolved"]
    top_service = services[0] if services else None
    priorities = [
        "Review active critical incidents before starting new analysis.",
        "Correlate high-risk services with recent deployments.",
        "Keep OpenAI enabled for richer root-cause narratives when investigating production events.",
    ]
    if active:
        priorities.insert(0, f"Own {active[0].title} and move it to investigating.")
    return CopilotBrief(
        title="AIOps command brief",
        summary=(
            f"{len(active)} active incident{'' if len(active) == 1 else 's'}."
            if active
            else "No active production incidents. Services are being monitored through local ML and optional OpenAI reasoning."
        ),
        priorities=priorities[:4],
        recommended_owner=top_service.owner if top_service else "Platform Engineering",
    )
