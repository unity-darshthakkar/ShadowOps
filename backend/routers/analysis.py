import uuid
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from backend.config import get_settings, Settings
from backend.database import get_db
from backend.models.db_models import AnalysisRun
from backend.models.schemas import (
    AnalysisRequest,
    AnalysisResult,
    ProviderStatusResponse,
    DISCLAIMER,
)
from backend.routers.scenarios import get_scenario_by_id
from backend.services import workflow_reconstructor, hidden_work_detector, metrics_calculator, granite_analyser, redaction

router = APIRouter()


def _run_analysis(scenario: dict, settings: Settings) -> AnalysisResult:
    events = scenario.get("events", [])

    # Redact PII from event notes before any processing
    events = redaction.redact_events(events)

    proposal = scenario.get("automation_proposal", {})

    official_wf, actual_wf = workflow_reconstructor.reconstruct(events)
    hidden = hidden_work_detector.detect(events)

    # Compute metrics first (deterministic); then call Granite with real numbers.
    # Use cached provider's safer_steps for missing_fallback_count on first pass.
    cached_steps = None
    from backend.services import cached_provider as _cp
    cached_steps = _cp.get().safer_workflow_steps

    metrics = metrics_calculator.calculate(
        events=events,
        hidden_summary=hidden,
        proposal=proposal,
        safer_steps=cached_steps,
    )
    granite_out = granite_analyser.analyse(
        metrics=metrics,
        hidden=hidden,
        settings=settings,
        official_workflow=official_wf,
        actual_workflow=actual_wf,
        proposal=proposal,
    )

    # Recompute missing_fallback_count with final safer steps
    metrics = metrics_calculator.calculate(
        events=events,
        hidden_summary=hidden,
        proposal=proposal,
        safer_steps=granite_out.safer_workflow_steps,
    )

    analysis_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    provider_status = granite_out.provider

    return AnalysisResult(
        analysis_id=analysis_id,
        scenario_id=scenario["scenario_id"],
        status="complete",
        created_at=now,
        completed_at=now,
        official_workflow=official_wf,
        actual_workflow=actual_wf,
        hidden_work=hidden,
        metrics=metrics,
        granite_output=granite_out,
        provider_status=provider_status,
        disclaimer=DISCLAIMER,
    )


@router.post("/analysis/run", response_model=AnalysisResult)
def run_analysis(
    request: AnalysisRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AnalysisResult:
    scenario = get_scenario_by_id(request.scenario_id)
    result = _run_analysis(scenario, settings)

    run = AnalysisRun(
        id=result.analysis_id,
        scenario_id=result.scenario_id,
        status="complete",
        completed_at=result.completed_at,
        result_json=result.model_dump_json(),
    )
    db.add(run)
    db.commit()
    return result


@router.get("/analysis/{analysis_id}", response_model=AnalysisResult)
def get_analysis(analysis_id: str, db: Session = Depends(get_db)) -> AnalysisResult:
    run = db.query(AnalysisRun).filter(AnalysisRun.id == analysis_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    return AnalysisResult.model_validate_json(run.result_json)


@router.get("/analysis/{analysis_id}/report")
def get_report(analysis_id: str, db: Session = Depends(get_db)):
    run = db.query(AnalysisRun).filter(AnalysisRun.id == analysis_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    parsed = json.loads(run.result_json)
    return JSONResponse(
        content=parsed,
        headers={
            "Content-Disposition": f'attachment; filename="shadowops-preflight-{analysis_id}.json"'
        },
    )


@router.get("/demo/provider-status", response_model=ProviderStatusResponse)
def provider_status(settings: Settings = Depends(get_settings)) -> ProviderStatusResponse:
    """
    Return the provider that would actually be used for Granite calls.
    Returns 'cached_demo' if credentials are missing OR if the SDK is unavailable.
    """
    # First check if credentials exist
    if not settings.has_watsonx_credentials:
        return ProviderStatusResponse(provider="cached_demo")

    # Then check if the SDK is importable
    try:
        from ibm_watsonx_ai.foundation_models import ModelInference  # noqa: F401
        # Credentials and SDK available - would attempt live call
        return ProviderStatusResponse(provider="live_granite")
    except Exception:
        # SDK not installed or import failed
        return ProviderStatusResponse(provider="cached_demo")
