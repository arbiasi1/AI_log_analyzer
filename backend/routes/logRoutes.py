from fastapi import APIRouter, Depends, File, Form, UploadFile

from backend.controllers.logController import (
    analyze_controller,
    history_controller,
    operational_overview_controller,
    sample_logs_controller,
    upload_logs_controller,
)
from backend.models.schemas import AnalyzeRequest, AnalysisRecord, UserProfile
from backend.services.authService import record_audit, require_user
from backend.services.platformService import record_analysis_incident

router = APIRouter(tags=["logs"])


@router.post("/analyze", response_model=AnalysisRecord)
async def analyze(request: AnalyzeRequest, user: UserProfile = Depends(require_user)):
    record = await analyze_controller(request)
    record_audit(user.email, "analyze_logs", f"Analyzed {record.source}.")
    incident = record_analysis_incident(record)
    if incident is not None:
        record_audit(user.email, "incident_created", f"Created {incident.title}.")
    return record


@router.post("/upload-logs", response_model=AnalysisRecord)
async def upload_logs(
    file: UploadFile | None = File(default=None),
    text: str | None = Form(default=None),
    user: UserProfile = Depends(require_user),
):
    record = await upload_logs_controller(file=file, text=text)
    record_audit(user.email, "upload_logs", f"Uploaded and analyzed {record.source}.")
    incident = record_analysis_incident(record)
    if incident is not None:
        record_audit(user.email, "incident_created", f"Created {incident.title}.")
    return record


@router.get("/history", response_model=list[AnalysisRecord])
async def history(_: UserProfile = Depends(require_user)):
    return await history_controller()


@router.get("/ops/overview")
async def operational_overview(_: UserProfile = Depends(require_user)):
    return await operational_overview_controller()


@router.get("/sample-logs")
async def sample_logs():
    return sample_logs_controller()
