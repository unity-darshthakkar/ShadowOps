"""
Reconstructs official and actual workflows from raw event lists.
Pure function — no side effects.
"""
from __future__ import annotations
from backend.models.schemas import WorkflowStep

OFFICIAL_STEP_TYPES = frozenset(
    {"ticket_created", "assigned", "first_response", "resolution", "closed"}
)


def reconstruct(
    events: list[dict],
    official_step_types: frozenset[str] | None = None,
) -> tuple[list[WorkflowStep], list[WorkflowStep]]:
    """
    Returns (official_workflow, actual_workflow).

    official_workflow — deduplicated steps present in OFFICIAL_STEP_TYPES.
    actual_workflow   — all deduplicated steps (including hidden work).

    Duration averages are computed across all occurrences of each event_type.
    """
    if official_step_types is None:
        official_step_types = OFFICIAL_STEP_TYPES

    # Aggregate by event_type
    agg: dict[str, dict] = {}
    for ev in events:
        et = ev["event_type"]
        if et not in agg:
            agg[et] = {
                "event_type": et,
                "total_duration": 0.0,
                "count": 0,
                "is_hidden_work": ev.get("is_hidden_work", False),
            }
        agg[et]["total_duration"] += float(ev.get("duration_minutes", 0))
        agg[et]["count"] += 1

    def _make_step(et: str, data: dict, in_official: bool) -> WorkflowStep:
        avg = data["total_duration"] / data["count"] if data["count"] else 0.0
        return WorkflowStep(
            step_id=et,
            event_type=et,
            label=et.replace("_", " ").title(),
            avg_duration_minutes=round(avg, 2),
            occurrence_count=data["count"],
            is_hidden_work=data["is_hidden_work"],
            is_in_official=in_official,
        )

    # Preserve order of first occurrence for actual workflow
    seen_order: list[str] = []
    for ev in events:
        et = ev["event_type"]
        if et not in seen_order:
            seen_order.append(et)

    actual_workflow = [
        _make_step(et, agg[et], et in official_step_types)
        for et in seen_order
    ]

    # Official workflow: same ordering, restricted to official types
    official_workflow = [s for s in actual_workflow if s.is_in_official]

    return official_workflow, actual_workflow
