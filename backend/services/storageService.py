from collections import Counter

from sqlalchemy import desc
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException

from backend.db.database import get_session_factory
from backend.db.models import AnalysisModel
from backend.models.schemas import AnalysisRecord, AnalysisResult

_history: list[AnalysisRecord] = []
MAX_HISTORY = 20


def save_analysis(result: AnalysisResult, source: str, raw_logs: str) -> AnalysisRecord:
    record = AnalysisRecord(
        source=source,
        raw_log_preview=_preview(raw_logs),
        result=result,
    )

    session_factory = get_session_factory()
    if session_factory is not None:
        try:
            with session_factory() as session:
                db_record = AnalysisModel(
                    id=record.id,
                    created_at=record.created_at,
                    source=record.source,
                    raw_log_preview=record.raw_log_preview,
                    overall_health=record.result.overall_health,
                    high_severity_count=sum(
                        1 for finding in record.result.errors_found if finding.severity == "high"
                    ),
                    result=record.result.model_dump(mode="json"),
                )
                session.add(db_record)
                session.commit()
            return record
        except SQLAlchemyError as exc:
            raise HTTPException(
                status_code=500,
                detail=f"PostgreSQL save failed. Check DATABASE_URL and permissions: {exc}",
            ) from exc

    _history.insert(0, record)
    del _history[MAX_HISTORY:]
    return record


def get_history() -> list[AnalysisRecord]:
    session_factory = get_session_factory()
    if session_factory is not None:
        try:
            with session_factory() as session:
                rows = (
                    session.query(AnalysisModel)
                    .order_by(desc(AnalysisModel.created_at))
                    .limit(MAX_HISTORY)
                    .all()
                )
                return [_record_from_model(row) for row in rows]
        except SQLAlchemyError as exc:
            raise HTTPException(
                status_code=500,
                detail=f"PostgreSQL history read failed. Check DATABASE_URL and permissions: {exc}",
            ) from exc

    return list(_history)


def get_operational_overview() -> dict:
    records = get_history()
    if not records:
        return {
            "total_analyses": 0,
            "critical": 0,
            "warning": 0,
            "good": 0,
            "average_incident_score": 0,
            "top_services": [],
            "top_patterns": [],
        }

    health_counts = Counter(record.result.overall_health for record in records)
    service_counts: Counter[str] = Counter()
    pattern_counts: Counter[str] = Counter()

    for record in records:
        for service in record.result.impacted_services:
            service_counts[service.service] += service.impact_score
        for finding in record.result.errors_found:
            pattern_counts[finding.error] += finding.frequency

    average_score = round(
        sum(record.result.incident_score for record in records) / len(records),
        1,
    )

    return {
        "total_analyses": len(records),
        "critical": health_counts.get("critical", 0),
        "warning": health_counts.get("warning", 0),
        "good": health_counts.get("good", 0),
        "average_incident_score": average_score,
        "top_services": [
            {"name": name, "score": score}
            for name, score in service_counts.most_common(5)
        ],
        "top_patterns": [
            {"name": name, "count": count}
            for name, count in pattern_counts.most_common(5)
        ],
    }


def _preview(raw_logs: str) -> str:
    compact = " ".join(raw_logs.split())
    return compact[:220] + ("..." if len(compact) > 220 else "")


def _record_from_model(row: AnalysisModel) -> AnalysisRecord:
    return AnalysisRecord(
        id=row.id,
        created_at=row.created_at,
        source=row.source,
        raw_log_preview=row.raw_log_preview,
        result=AnalysisResult.model_validate(row.result),
    )
