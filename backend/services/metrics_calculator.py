"""
Deterministic metrics calculator.
All numbers come from event data and the automation_proposal block — never from LLM output.
"""
from __future__ import annotations
from datetime import datetime, timezone
from backend.models.schemas import AnalysisMetrics, OverheadAssumption
from backend.services.hidden_work_detector import HIDDEN_WORK_TYPES

# ---------------------------------------------------------------------------
# Fallback defaults (used when automation_proposal field is absent)
# ---------------------------------------------------------------------------
OVERHEAD_DEFAULTS: dict[str, float] = {
    "expected_review_rate": 0.15,
    "avg_review_minutes": 3.0,
    "expected_correction_rate": 0.08,
    "avg_correction_minutes": 8.0,
    "exception_rate": 0.05,
    "avg_exception_handling_minutes": 20.0,
    "weekly_maintenance_minutes": 45.0,
    "expected_failure_recovery_minutes": 30.0,
}


def _resolve(
    proposal: dict,
    field: str,
    assumptions: list[OverheadAssumption],
) -> float:
    """Return value from proposal if present, else documented default. Records provenance."""
    if field in proposal and proposal[field] is not None:
        val = float(proposal[field])
        assumptions.append(
            OverheadAssumption(field=field, value=val, source="proposal", default_value=None)
        )
    else:
        val = OVERHEAD_DEFAULTS[field]
        assumptions.append(
            OverheadAssumption(
                field=field,
                value=val,
                source="default",
                default_value=val,
            )
        )
    return val


def calculate(
    events: list[dict],
    hidden_summary,
    proposal: dict,
    safer_steps: list | None = None,
) -> AnalysisMetrics:
    """
    Compute all deterministic metrics.
    safer_steps: list of SaferStep objects (optional, for missing_fallback_count).
    """
    assumptions: list[OverheadAssumption] = []

    # ------------------------------------------------------------------
    # Resolve proposal fields
    # ------------------------------------------------------------------
    review_rate = _resolve(proposal, "expected_review_rate", assumptions)
    review_min = _resolve(proposal, "avg_review_minutes", assumptions)
    correction_rate = _resolve(proposal, "expected_correction_rate", assumptions)
    correction_min = _resolve(proposal, "avg_correction_minutes", assumptions)
    exception_rate = _resolve(proposal, "exception_rate", assumptions)
    exception_min = _resolve(proposal, "avg_exception_handling_minutes", assumptions)
    weekly_maint = _resolve(proposal, "weekly_maintenance_minutes", assumptions)
    failure_rec = _resolve(proposal, "expected_failure_recovery_minutes", assumptions)

    # ------------------------------------------------------------------
    # Time totals
    # ------------------------------------------------------------------
    all_minutes = [float(ev.get("duration_minutes", 0)) for ev in events]
    actual_total = sum(all_minutes)

    # Official = non-hidden, non-waiting events only
    from backend.services.workflow_reconstructor import OFFICIAL_STEP_TYPES
    official_minutes = sum(
        float(ev.get("duration_minutes", 0))
        for ev in events
        if ev["event_type"] in OFFICIAL_STEP_TYPES
    )

    # Routine events = everything except hidden work (includes waiting)
    routine_events = [ev for ev in events if ev["event_type"] not in HIDDEN_WORK_TYPES]
    routine_count = len(routine_events)
    routine_total = sum(float(ev.get("duration_minutes", 0)) for ev in routine_events)

    ai_automated_total = round(routine_total * 0.70, 2)   # AI 30 % faster on routine steps
    hybrid_total = round(ai_automated_total * 1.15, 2)    # hybrid adds 15 % for checkpoints

    # ------------------------------------------------------------------
    # Scenario window in weeks
    # ------------------------------------------------------------------
    timestamps = []
    for ev in events:
        ts = ev.get("timestamp")
        if ts:
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                timestamps.append(dt)
            except ValueError:
                pass
    if len(timestamps) >= 2:
        scenario_days = (max(timestamps) - min(timestamps)).days
    else:
        scenario_days = 7   # default to one week if data is sparse
    scenario_weeks = max(scenario_days / 7, 1 / 7)  # at least one day

    # ------------------------------------------------------------------
    # Five overhead components
    # ------------------------------------------------------------------
    review_overhead = round(routine_count * review_rate * review_min, 2)
    correction_overhead = round(routine_count * correction_rate * correction_min, 2)
    exception_overhead = round(routine_count * exception_rate * exception_min, 2)
    maintenance_overhead = round(weekly_maint * scenario_weeks, 2)
    failure_recovery_overhead = round(failure_rec * scenario_weeks * exception_rate, 2)

    ai_overhead = round(
        review_overhead + correction_overhead + exception_overhead
        + maintenance_overhead + failure_recovery_overhead,
        2,
    )

    # ------------------------------------------------------------------
    # Core metrics
    # ------------------------------------------------------------------
    gross_time_saved = round(actual_total - ai_automated_total, 2)
    ai_tax = round(
        min(1.0, ai_overhead / gross_time_saved) if gross_time_saved > 0 else 1.0,
        4,
    )
    net_time_saved = round(gross_time_saved - ai_overhead, 2)

    # Burden concentration: which role carries the most hidden work?
    hidden_by_role: dict[str, float] = {}
    for ev in events:
        if ev["event_type"] in HIDDEN_WORK_TYPES:
            role = ev.get("agent_id", "unknown")
            hidden_by_role[role] = hidden_by_role.get(role, 0.0) + float(
                ev.get("duration_minutes", 0)
            )
    total_hidden = hidden_summary.total_hidden_minutes
    burden_concentration = round(
        max(hidden_by_role.values()) / total_hidden if total_hidden > 0 else 0.0,
        4,
    )

    # Automation readiness composite
    total_events = len(events)
    structured_ratio = (
        sum(1 for ev in events if ev.get("notes", "").strip()) / total_events
        if total_events > 0
        else 0.0
    )
    exception_events = sum(1 for ev in events if ev["event_type"] == "exception_handling")
    low_exception_rate = 1.0 - (exception_events / total_events if total_events > 0 else 0.0)
    low_hidden_ratio = 1.0 - hidden_summary.hidden_work_ratio

    automation_readiness = round(
        min(1.0, max(0.0,
            structured_ratio * 0.40
            + low_exception_rate * 0.30
            + low_hidden_ratio * 0.30
        )),
        4,
    )

    if automation_readiness >= 0.7:
        readiness_label = "High"
    elif automation_readiness >= 0.4:
        readiness_label = "Medium"
    else:
        readiness_label = "Low"

    # Skill-loss risk
    if burden_concentration >= 0.7 and automation_readiness >= 0.7:
        skill_loss_risk = "High"
    elif burden_concentration >= 0.5 or automation_readiness >= 0.5:
        skill_loss_risk = "Medium"
    else:
        skill_loss_risk = "Low"

    # Missing fallback count
    missing_fallback_count = 0
    if safer_steps:
        for step in safer_steps:
            if step.executor != "human" and step.fallback_procedure is None:
                missing_fallback_count += 1

    return AnalysisMetrics(
        official_total_minutes=round(official_minutes, 2),
        actual_total_minutes=round(actual_total, 2),
        ai_automated_total_minutes=ai_automated_total,
        hybrid_total_minutes=hybrid_total,
        hidden_work_ratio=hidden_summary.hidden_work_ratio,
        gross_time_saved=gross_time_saved,
        review_overhead=review_overhead,
        correction_overhead=correction_overhead,
        exception_overhead=exception_overhead,
        maintenance_overhead=maintenance_overhead,
        failure_recovery_overhead=failure_recovery_overhead,
        ai_overhead=ai_overhead,
        ai_tax=ai_tax,
        net_time_saved=net_time_saved,
        burden_concentration=burden_concentration,
        automation_readiness=automation_readiness,
        automation_readiness_label=readiness_label,
        skill_loss_risk=skill_loss_risk,
        missing_fallback_count=missing_fallback_count,
        overhead_assumptions=assumptions,
    )
