from fastapi import APIRouter, File, Form, UploadFile

from backend.controllers.logController import (
    analyze_controller,
    history_controller,
    sample_logs_controller,
    upload_logs_controller,
)
from backend.models.schemas import AnalyzeRequest, AnalysisRecord

router = APIRouter(tags=["logs"])


@router.post("/analyze", response_model=AnalysisRecord)
async def analyze(request: AnalyzeRequest):
    return await analyze_controller(request)


@router.post("/upload-logs", response_model=AnalysisRecord)
async def upload_logs(
    file: UploadFile | None = File(default=None),
    text: str | None = Form(default=None),
):
    return await upload_logs_controller(file=file, text=text)


@router.get("/history", response_model=list[AnalysisRecord])
async def history():
    return await history_controller()


@router.get("/sample-logs")
async def sample_logs():
    return sample_logs_controller()
