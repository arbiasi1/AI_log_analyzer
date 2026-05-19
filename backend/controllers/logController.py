from fastapi import File, Form, HTTPException, UploadFile

from backend.models.schemas import AnalyzeRequest, AnalysisRecord, AnalysisResult
from backend.services.aiService import analyze_logs
from backend.services.storageService import get_history, get_operational_overview, save_analysis

ALLOWED_EXTENSIONS = {".log", ".txt"}
MAX_LOG_CHARS = 80_000


async def analyze_controller(request: AnalyzeRequest) -> AnalysisRecord:
    logs = _validate_logs(request.logs)
    result = await analyze_logs(logs)
    return save_analysis(result=result, source=request.source or "manual paste", raw_logs=logs)


async def upload_logs_controller(
    file: UploadFile | None = File(default=None),
    text: str | None = Form(default=None),
) -> AnalysisRecord:
    raw_parts: list[str] = []
    source = "manual paste"

    if file is not None and file.filename:
        extension = _extension_for(file.filename)
        if extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail="Only .log and .txt files are supported.",
            )

        content = await file.read()
        try:
            raw_parts.append(content.decode("utf-8"))
        except UnicodeDecodeError as exc:
            raise HTTPException(
                status_code=400,
                detail="Could not decode file as UTF-8 text.",
            ) from exc
        source = file.filename

    if text and text.strip():
        raw_parts.append(text)
        if source == "manual paste":
            source = "manual paste"
        else:
            source = f"{source} + pasted logs"

    logs = _validate_logs("\n".join(raw_parts))
    result = await analyze_logs(logs)
    return save_analysis(result=result, source=source, raw_logs=logs)


async def history_controller() -> list[AnalysisRecord]:
    return get_history()


async def operational_overview_controller() -> dict:
    return get_operational_overview()


def sample_logs_controller() -> dict[str, str]:
    return {
        "logs": "\n".join(
            [
                "[ERROR] Database connection failed at 03:45",
                "[WARN] High memory usage detected",
                "[ERROR] Timeout connecting to auth service",
                "[INFO] Server restarted successfully",
                "[ERROR] Database connection failed at 03:47",
                "[WARN] Disk usage above 85%",
                "[CRITICAL] API gateway returned 504 for checkout-service",
                "[ERROR] checkout-service retry exhausted after auth-service timeout",
                "[WARN] Queue worker lag above threshold for billing jobs",
            ]
        )
    }


def _validate_logs(logs: str | None) -> str:
    normalized = (logs or "").strip()
    if not normalized:
        raise HTTPException(status_code=400, detail="Provide logs as a file or pasted text.")

    if len(normalized) > MAX_LOG_CHARS:
        raise HTTPException(
            status_code=413,
            detail=f"Logs are too large. Limit input to {MAX_LOG_CHARS} characters.",
        )

    return normalized


def _extension_for(filename: str) -> str:
    dot_index = filename.rfind(".")
    if dot_index == -1:
        return ""
    return filename[dot_index:].lower()
