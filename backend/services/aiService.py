import json
import os
import re
from collections import Counter
from typing import Any

from backend.models.schemas import (
    AnalysisResult,
    ErrorFinding,
    IncidentEvent,
    MlSignal,
    RunbookStep,
    ServiceImpact,
    SloImpact,
)


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
    local_result = _enrich_result(_analyze_with_mock_llm(raw_logs), raw_logs)

    if _openai_configured():
        ai_result = await _enhance_with_openai(raw_logs, local_result)
        if ai_result is not None:
            return _enrich_result(ai_result, raw_logs)
        local_result.ai_provider_status = "OpenAI was configured, but the request failed; local fallback used"
        local_result.detection_notes.append(
            "OpenAI enhancement was attempted but failed, so the deterministic local analysis was returned."
        )

    return local_result


def _openai_configured() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


async def _enhance_with_openai(raw_logs: str, local_result: AnalysisResult) -> AnalysisResult | None:
    try:
        from openai import AsyncOpenAI
    except ImportError:
        return None

    client = AsyncOpenAI()
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    baseline = local_result.model_dump(mode="json")
    prompt = _openai_prompt(raw_logs=raw_logs, baseline=baseline, model=model)

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert SRE and DevOps incident commander. "
                        "Return only valid JSON. Do not include markdown."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        result = AnalysisResult.model_validate(json.loads(content))
        result.ai_engine = "openai"
        result.ai_model = model
        result.ai_provider_status = "LLM-enhanced reasoning applied"
        result.detection_notes.append(f"OpenAI model {model} refined the local baseline analysis.")
        return result
    except Exception:
        return None


def _openai_prompt(raw_logs: str, baseline: dict[str, Any], model: str) -> str:
    return (
        "Analyze these DevOps logs as a production incident report. Use the local baseline as evidence, "
        "but improve root-cause reasoning, service impact, SLO impact, runbook quality, and next actions. "
        "Do not invent services, timestamps, commands, or causes that are not supported by the logs. "
        "Return a single JSON object matching exactly this shape:\n"
        "{"
        '"summary": string, '
        '"errors_found": [{"error": string, "frequency": integer, "severity": "low|medium|high", '
        '"possible_cause": string, "suggested_fix": string}], '
        '"root_cause_analysis": string, '
        '"overall_health": "good|warning|critical", '
        '"ai_engine": "openai", '
        f'"ai_model": "{model}", '
        '"ai_provider_status": "LLM-enhanced reasoning applied", '
        '"incident_score": integer 0-100, '
        '"ml_signals": [{"name": string, "score": number 0-100, "confidence": number 0-1, '
        '"trend": "stable|rising|falling|spiky", "explanation": string}], '
        '"incident_timeline": [{"time": string, "phase": "detected|correlated|mitigating|resolved", '
        '"title": string, "detail": string}], '
        '"impacted_services": [{"service": string, "impact_score": integer 0-100, "evidence": string}], '
        '"runbook": [{"title": string, "command": string|null, "rationale": string}], '
        '"slo_impact": {"availability_risk": integer 0-100, "latency_risk": integer 0-100, '
        '"error_budget_burn": string, "customer_impact": string}, '
        '"next_best_actions": [string], '
        '"detection_notes": [string]'
        "}\n\n"
        f"Local baseline JSON:\n{json.dumps(baseline, ensure_ascii=True)}\n\n"
        f"Raw logs:\n{raw_logs[:60000]}"
    )


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
        ai_engine="local-ml",
        ai_model=None,
        ai_provider_status="local deterministic analysis",
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


def _enrich_result(result: AnalysisResult, raw_logs: str) -> AnalysisResult:
    lines = [line.strip() for line in raw_logs.splitlines() if line.strip()]
    notable_lines = [line for line in lines if _is_notable(line)]
    high_count = sum(1 for item in result.errors_found if item.severity == "high")
    medium_count = sum(1 for item in result.errors_found if item.severity == "medium")
    repeated_count = sum(1 for item in result.errors_found if item.frequency > 1)
    error_density = len(notable_lines) / max(len(lines), 1)

    incident_score = result.incident_score or _incident_score(
        high_count=high_count,
        medium_count=medium_count,
        repeated_count=repeated_count,
        error_density=error_density,
    )

    if not result.ml_signals:
        result.ml_signals = _ml_signals(result, lines, notable_lines, incident_score)
    if not result.impacted_services:
        result.impacted_services = _impacted_services(raw_logs, result.errors_found)
    if not result.incident_timeline:
        result.incident_timeline = _incident_timeline(lines, result)
    if not result.runbook:
        result.runbook = _runbook(result)
    if result.slo_impact is None:
        result.slo_impact = _slo_impact(incident_score, high_count, medium_count)
    if not result.next_best_actions:
        result.next_best_actions = _next_best_actions(result)
    if not result.detection_notes:
        result.detection_notes = _detection_notes(lines, notable_lines, result)

    result.incident_score = incident_score
    return result


def _incident_score(high_count: int, medium_count: int, repeated_count: int, error_density: float) -> int:
    score = high_count * 28 + medium_count * 14 + repeated_count * 9 + int(error_density * 45)
    return max(0, min(100, score))


def _ml_signals(
    result: AnalysisResult,
    lines: list[str],
    notable_lines: list[str],
    incident_score: int,
) -> list[MlSignal]:
    frequency_counts = [item.frequency for item in result.errors_found] or [0]
    max_frequency = max(frequency_counts)
    density = len(notable_lines) / max(len(lines), 1)
    trend = "spiky" if max_frequency >= 3 and density < 0.6 else "rising" if incident_score >= 55 else "stable"

    return [
        MlSignal(
            name="Anomaly intensity",
            score=incident_score,
            confidence=min(0.96, 0.45 + density + (0.08 * len(result.errors_found))),
            trend=trend,
            explanation="Heuristic ML layer scores severity, repeated patterns, and error density to estimate incident pressure.",
        ),
        MlSignal(
            name="Pattern recurrence",
            score=min(100, max_frequency * 22),
            confidence=0.78 if max_frequency > 1 else 0.52,
            trend="rising" if max_frequency > 2 else "stable",
            explanation="Repeated normalized log lines are treated as a stronger production signal than isolated events.",
        ),
        MlSignal(
            name="Noise-to-signal ratio",
            score=round(density * 100, 1),
            confidence=0.7 if lines else 0.3,
            trend="stable" if density < 0.35 else "spiky",
            explanation="Compares actionable warning/error lines against total log volume.",
        ),
    ]


def _impacted_services(raw_logs: str, findings: list[ErrorFinding]) -> list[ServiceImpact]:
    lowered = raw_logs.lower()
    service_keywords = {
        "database": ("database", "postgres", "mysql", "mongo", "db"),
        "auth-service": ("auth", "oauth", "jwt", "401", "403"),
        "api-gateway": ("gateway", "nginx", "proxy", "504", "502"),
        "worker": ("queue", "job", "worker", "consumer"),
        "storage": ("disk", "volume", "filesystem", "s3", "bucket"),
        "application": ("exception", "traceback", "panic", "fatal"),
    }
    impacts: list[ServiceImpact] = []
    for service, keywords in service_keywords.items():
        hits = sum(lowered.count(keyword) for keyword in keywords)
        if hits:
            impacts.append(
                ServiceImpact(
                    service=service,
                    impact_score=min(100, 30 + hits * 12),
                    evidence=f"{hits} related signal{'' if hits == 1 else 's'} found in logs.",
                )
            )

    if not impacts and findings:
        impacts.append(
            ServiceImpact(
                service="unknown-service",
                impact_score=45,
                evidence="Failures are present, but the log sample does not name a clear service boundary.",
            )
        )
    impacts.sort(key=lambda item: item.impact_score, reverse=True)
    return impacts[:5]


def _incident_timeline(lines: list[str], result: AnalysisResult) -> list[IncidentEvent]:
    notable = [line for line in lines if _is_notable(line)]
    first = notable[0] if notable else (lines[0] if lines else "No log lines supplied")
    last = notable[-1] if notable else first
    top = result.errors_found[0].error if result.errors_found else "No dominant error pattern"
    phase = "mitigating" if result.overall_health == "critical" else "correlated" if result.errors_found else "resolved"
    return [
        IncidentEvent(time="T+00m", phase="detected", title="Signal detected", detail=first[:180]),
        IncidentEvent(time="T+02m", phase="correlated", title="Dominant pattern grouped", detail=top[:180]),
        IncidentEvent(time="T+05m", phase=phase, title="Operational posture selected", detail=last[:180]),
    ]


def _runbook(result: AnalysisResult) -> list[RunbookStep]:
    top = result.errors_found[0] if result.errors_found else None
    steps = [
        RunbookStep(
            title="Freeze the evidence window",
            command="kubectl logs deploy/<service> --since=30m > incident-window.log",
            rationale="Preserve the relevant log window before pods rotate or retention removes context.",
        ),
        RunbookStep(
            title="Check recent deploys and config changes",
            command="kubectl rollout history deploy/<service>",
            rationale="Most sudden production regressions correlate with a release, secret, config, or dependency change.",
        ),
    ]
    if top:
        steps.append(
            RunbookStep(
                title=f"Validate {top.severity} pattern",
                command=None,
                rationale=top.suggested_fix,
            )
        )
    steps.append(
        RunbookStep(
            title="Stabilize before deep debugging",
            command="kubectl scale deploy/<service> --replicas=<n>",
            rationale="If customer impact is active, increase healthy capacity or isolate the failing dependency before root-cause work.",
        )
    )
    return steps


def _slo_impact(incident_score: int, high_count: int, medium_count: int) -> SloImpact:
    availability = min(100, incident_score + high_count * 8)
    latency = min(100, incident_score // 2 + medium_count * 12)
    burn = "fast" if incident_score >= 70 else "elevated" if incident_score >= 35 else "normal"
    impact = (
        "Customer-facing degradation is likely; prioritize mitigation and status communication."
        if incident_score >= 70
        else "Potential partial degradation; watch dashboards and dependency health closely."
        if incident_score >= 35
        else "No strong customer-impact signal in this log sample."
    )
    return SloImpact(
        availability_risk=availability,
        latency_risk=latency,
        error_budget_burn=burn,
        customer_impact=impact,
    )


def _next_best_actions(result: AnalysisResult) -> list[str]:
    if not result.errors_found:
        return [
            "Keep collecting logs from the same service for a wider time window.",
            "Compare this sample with metrics for latency, saturation, and restart count.",
            "Create an alert only if this pattern repeats or starts affecting SLOs.",
        ]
    top = result.errors_found[0]
    return [
        f"Triage the top pattern first: {top.error}.",
        top.suggested_fix,
        "Correlate the first occurrence with deployments, autoscaling events, and dependency status.",
        "Attach this report to the incident ticket with the raw log window and affected service list.",
    ]


def _detection_notes(lines: list[str], notable_lines: list[str], result: AnalysisResult) -> list[str]:
    return [
        f"Parsed {len(lines)} log lines and marked {len(notable_lines)} as operationally notable.",
        f"Grouped {len(result.errors_found)} normalized failure pattern{'' if len(result.errors_found) == 1 else 's'}.",
        "Local ML mode uses deterministic heuristics; set OPENAI_API_KEY to add LLM reasoning on top.",
    ]


def analysis_to_dict(result: AnalysisResult) -> dict[str, Any]:
    return result.model_dump()
