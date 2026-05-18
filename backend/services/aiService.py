import json
import os
import re
from collections import Counter
from typing import Any

from backend.models.schemas import AnalysisResult, ErrorFinding


ERROR_PATTERNS = {
    "database": {
        "keywords": ("database", "db", "postgres", "mysql", "mongo", "connection refused"),
        "cause": "The application could not reach its database or the database rejected connections.",
        "fix": "Check database health, network access, credentials, connection pool limits, and recent deploy or secret changes.",
    },
    "auth service": {
        "keywords": ("auth", "oauth", "jwt", "401", "403", "permission", "unauthorized"),
        "cause": "Authentication or authorization dependencies are failing or rejecting requests.",
        "fix": "Verify auth service availability, tokens, client secrets, clock skew, and service-to-service permissions.",
    },
    "timeout": {
        "keywords": ("timeout", "timed out", "deadline exceeded", "504", "gateway timeout"),
        "cause": "A dependency is too slow, unavailable, or overloaded.",
        "fix": "Inspect upstream latency, retries, circuit breakers, DNS, network routes, and recent traffic spikes.",
    },
    "memory": {
        "keywords": ("memory", "oom", "out of memory", "heap", "rss"),
        "cause": "The service is under memory pressure or has a possible memory leak.",
        "fix": "Review memory limits, recent load, heap profiles, container OOM events, and scaling rules.",
    },
    "disk": {
        "keywords": ("disk", "no space", "volume", "filesystem", "storage"),
        "cause": "Disk or persistent volume usage is approaching a dangerous threshold.",
        "fix": "Clean old logs/artifacts, rotate files, expand the volume, and check retention policies.",
    },
    "restart": {
        "keywords": ("restart", "crashloop", "crashed", "exit code", "terminated"),
        "cause": "The service restarted, crashed, or was replaced by orchestration.",
        "fix": "Check deployment events, container exit codes, liveness probes, and application startup logs.",
    },
}

SEVERITY_MARKERS = {
    "high": ("fatal", "panic", "critical", "emergency", "error", "failed", "exception", "crash", "oom"),
    "medium": ("warn", "warning", "timeout", "retry", "degraded", "slow", "high memory", "high disk"),
    "low": ("info", "debug", "notice", "started", "restarted", "success"),
}


async def analyze_logs(raw_logs: str) -> AnalysisResult:
    if _openai_configured():
        ai_result = await _analyze_with_openai(raw_logs)
        if ai_result is not None:
            return ai_result

    return _analyze_with_mock_llm(raw_logs)


def _openai_configured() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


async def _analyze_with_openai(raw_logs: str) -> AnalysisResult | None:
    try:
        from openai import AsyncOpenAI
    except ImportError:
        return None

    client = AsyncOpenAI()
    prompt = (
        "You are a senior DevOps engineer. Analyze the logs and return only valid JSON "
        "matching this schema: summary string, errors_found array of objects with error, "
        "frequency integer, severity low|medium|high, possible_cause, suggested_fix, "
        "root_cause_analysis string, overall_health good|warning|critical. "
        "Group repeated errors and explain clearly.\n\n"
        f"Logs:\n{raw_logs[:60000]}"
    )

    try:
        response = await client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        return AnalysisResult.model_validate(json.loads(content))
    except Exception:
        return None


def _analyze_with_mock_llm(raw_logs: str) -> AnalysisResult:
    lines = [line.strip() for line in raw_logs.splitlines() if line.strip()]
    notable_lines = [line for line in lines if _is_notable(line)]
    grouped = _group_notable_lines(notable_lines)
    findings = [_finding_from_group(error, count) for error, count in grouped.items()]
    findings.sort(key=lambda item: (_severity_rank(item.severity), item.frequency), reverse=True)

    high_count = sum(1 for finding in findings if finding.severity == "high")
    medium_count = sum(1 for finding in findings if finding.severity == "medium")
    overall_health = _overall_health(high_count, medium_count, len(lines))

    if findings:
        top = findings[0]
        summary = (
            f"Analyzed {len(lines)} log lines and found {len(findings)} notable pattern"
            f"{'' if len(findings) == 1 else 's'}. The most urgent issue is "
            f"'{top.error}', seen {top.frequency} time{'' if top.frequency == 1 else 's'}."
        )
        root_cause = _root_cause(findings)
    else:
        summary = f"Analyzed {len(lines)} log lines. No error or warning patterns were detected."
        root_cause = "The logs do not show a clear failure pattern. Continue monitoring for repeated warnings, errors, or latency spikes."

    return AnalysisResult(
        summary=summary,
        errors_found=findings,
        root_cause_analysis=root_cause,
        overall_health=overall_health,
    )


def _is_notable(line: str) -> bool:
    lowered = line.lower()
    markers = ("error", "warn", "fatal", "critical", "exception", "failed", "timeout", "oom", "denied", "high ")
    return any(marker in lowered for marker in markers)


def _group_notable_lines(lines: list[str]) -> Counter[str]:
    normalized = [_normalize_log_line(line) for line in lines]
    return Counter(normalized)


def _normalize_log_line(line: str) -> str:
    line = re.sub(r"\[[^\]]+\]", "", line)
    line = re.sub(r"\b\d{1,2}:\d{2}(:\d{2})?\b", "", line)
    line = re.sub(r"\b\d+\b", "<num>", line)
    line = re.sub(r"\s+", " ", line)
    return line.strip(" -:") or "Unknown log event"


def _finding_from_group(error: str, count: int) -> ErrorFinding:
    category = _category_for(error)
    severity = _severity_for(error, count)
    details = ERROR_PATTERNS.get(
        category,
        {
            "cause": "The log message indicates a failure condition that needs investigation.",
            "fix": "Correlate this event with metrics, deployment history, dependency status, and surrounding logs.",
        },
    )

    return ErrorFinding(
        error=error,
        frequency=count,
        severity=severity,
        possible_cause=details["cause"],
        suggested_fix=details["fix"],
    )


def _category_for(text: str) -> str:
    lowered = text.lower()
    for category, data in ERROR_PATTERNS.items():
        if any(keyword in lowered for keyword in data["keywords"]):
            return category
    return "generic"


def _severity_for(text: str, count: int) -> str:
    lowered = text.lower()
    if any(marker in lowered for marker in SEVERITY_MARKERS["high"]):
        return "high"
    if any(marker in lowered for marker in SEVERITY_MARKERS["medium"]) or count >= 3:
        return "medium"
    return "low"


def _severity_rank(severity: str) -> int:
    return {"low": 1, "medium": 2, "high": 3}[severity]


def _overall_health(high_count: int, medium_count: int, total_lines: int) -> str:
    if high_count >= 2 or (high_count >= 1 and total_lines <= 20):
        return "critical"
    if high_count or medium_count:
        return "warning"
    return "good"


def _root_cause(findings: list[ErrorFinding]) -> str:
    top = findings[0]
    repeated = [finding for finding in findings if finding.frequency > 1]
    repeat_note = (
        f" Repetition is present in {len(repeated)} pattern{'' if len(repeated) == 1 else 's'}, "
        "which usually means this is a persistent condition rather than a one-off event."
        if repeated
        else " The issue appears isolated in this sample, so correlation with recent deployments and metrics is important."
    )
    return (
        f"The strongest root-cause signal is {top.error.lower()}. "
        f"{top.possible_cause} Start by validating the dependency or resource named in that event, "
        "then check whether warnings nearby are symptoms of the same failure."
        f"{repeat_note}"
    )


def analysis_to_dict(result: AnalysisResult) -> dict[str, Any]:
    return result.model_dump()
