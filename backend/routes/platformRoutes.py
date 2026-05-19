from fastapi import APIRouter, Depends, HTTPException

from backend.models.schemas import AlertRule, Incident, PlatformOverview, UserProfile
from backend.services.authService import record_audit, require_user
from backend.services.platformService import (
    get_alert_rules,
    get_incidents,
    get_platform_overview,
    resolve_incident,
)


router = APIRouter(prefix="/platform", tags=["platform"])


@router.get("/overview", response_model=PlatformOverview)
async def platform_overview(_: UserProfile = Depends(require_user)):
    return get_platform_overview()


@router.get("/incidents", response_model=list[Incident])
async def incidents(_: UserProfile = Depends(require_user)):
    return get_incidents()


@router.post("/incidents/{incident_id}/resolve", response_model=Incident)
async def resolve_incident_route(
    incident_id: str,
    user: UserProfile = Depends(require_user),
):
    incident = resolve_incident(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found.")
    record_audit(user.email, "resolve_incident", f"Resolved {incident.title}.")
    return incident


@router.get("/alert-rules", response_model=list[AlertRule])
async def alert_rules(_: UserProfile = Depends(require_user)):
    return get_alert_rules()
