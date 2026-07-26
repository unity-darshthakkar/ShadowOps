from __future__ import annotations
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------

class AnalysisRequest(BaseModel):
    scenario_id: str


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------

class WorkflowStep(BaseModel):
    step_id: str
    event_type: str
    label: str
    avg_duration_minutes: float
    occurrence_count: int
    is_hidden_work: bool
    is_in_official: bool


# ---------------------------------------------------------------------------
# Hidden work
# ---------------------------------------------------------------------------

class HiddenWorkEvidence(BaseModel):
    event_id: str
    ticket_id: str
    event_type: str
    duration_minutes: float
    notes: str
    description: str


class HiddenWorkSummary(BaseModel):
    total_hidden_events: int
    total_hidden_minutes: float
    hidden_work_ratio: float
    hidden_event_types: list[str]
    evidence: list[HiddenWorkEvidence]


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

class OverheadAssumption(BaseModel):
    field: str
    value: float
    source: Literal["proposal", "default"]
    default_value: float | None = None


class AnalysisMetrics(BaseModel):
    # durations in minutes
    official_total_minutes: float
    actual_total_minutes: float
    ai_automated_total_minutes: float
    hybrid_total_minutes: float

    hidden_work_ratio: float
    gross_time_saved: float

    # five explicit overhead components
    review_overhead: float
    correction_overhead: float
    exception_overhead: float
    maintenance_overhead: float
    failure_recovery_overhead: float

    ai_overhead: float          # must equal sum of five components
    ai_tax: float               # ai_overhead / gross_time_saved, clamped [0,1]
    net_time_saved: float       # may be negative

    burden_concentration: float
    automation_readiness: float
    automation_readiness_label: Literal["Low", "Medium", "High"]

    skill_loss_risk: Literal["Low", "Medium", "High"]
    missing_fallback_count: int
    overhead_assumptions: list[OverheadAssumption]


# ---------------------------------------------------------------------------
# Granite / AI layer
# ---------------------------------------------------------------------------

class GuardrailItem(BaseModel):
    id: str
    label: str
    type: Literal[
        "human_approval",
        "confidence_threshold",
        "exception_routing",
        "manual_fallback",
        "skill_preservation",
        "audit_trail",
    ]
    description: str


class SaferStep(BaseModel):
    step_id: str
    label: str
    executor: Literal["human", "ai", "hybrid"]
    requires_approval: bool
    fallback_procedure: str | None = None
    confidence_threshold: float | None = None


class GraniteOutput(BaseModel):
    workflow_gap_narrative: str
    hidden_work_narrative: str
    redesign_recommendations: list[str] = Field(min_length=3)
    guardrails: list[GuardrailItem]
    safer_workflow_steps: list[SaferStep]
    provider: Literal["live_granite", "cached_demo"]


# ---------------------------------------------------------------------------
# Top-level result
# ---------------------------------------------------------------------------

DISCLAIMER = (
    "Results are based on synthetic demonstration data and are intended for "
    "exploratory purposes only. They do not represent individual employee "
    "performance, demographic characteristics, or production-grade recommendations. "
    "Skill-Loss Risk and Automation Readiness are scenario-based heuristics, "
    "not validated assessments. "
    "Always engage human judgment before automating any business workflow."
)


class AnalysisResult(BaseModel):
    analysis_id: str
    scenario_id: str
    status: Literal["pending", "running", "complete", "error"]
    created_at: datetime
    completed_at: datetime | None = None

    official_workflow: list[WorkflowStep]
    actual_workflow: list[WorkflowStep]
    hidden_work: HiddenWorkSummary
    metrics: AnalysisMetrics
    granite_output: GraniteOutput | None = None

    provider_status: Literal["live_granite", "cached_demo"]
    disclaimer: str = DISCLAIMER


# ---------------------------------------------------------------------------
# Health / misc
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str
    provider: Literal["live_granite", "cached_demo"]
    version: str


class ProviderStatusResponse(BaseModel):
    provider: Literal["live_granite", "cached_demo"]


class ScenarioMeta(BaseModel):
    scenario_id: str
    name: str
    description: str
    event_count: int
    ticket_count: int
