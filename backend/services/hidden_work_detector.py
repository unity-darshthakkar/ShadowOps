"""
Detects hidden work in raw event lists.
Pure function — no side effects, no LLM calls.
"""
from __future__ import annotations
from backend.models.schemas import HiddenWorkEvidence, HiddenWorkSummary

HIDDEN_WORK_TYPES: frozenset[str] = frozenset(
    {
        "follow_up",
        "manual_status_check",
        "context_repair",
        "duplicate_entry",
        "rework",
        "exception_handling",
        "escalation",
        "manual_reconciliation",
    }
)

# waiting is intentionally excluded from HIDDEN_WORK_TYPES.
# It records workflow delay but is not itself a hidden-work activity.


def detect(events: list[dict]) -> HiddenWorkSummary:
    total_minutes = sum(float(ev.get("duration_minutes", 0)) for ev in events)
    hidden_events = [ev for ev in events if ev["event_type"] in HIDDEN_WORK_TYPES]

    total_hidden_minutes = sum(float(ev.get("duration_minutes", 0)) for ev in hidden_events)
    hidden_ratio = (
        round(total_hidden_minutes / total_minutes, 4) if total_minutes > 0 else 0.0
    )

    hidden_types_seen = sorted({ev["event_type"] for ev in hidden_events})

    evidence: list[HiddenWorkEvidence] = [
        HiddenWorkEvidence(
            event_id=ev["event_id"],
            ticket_id=ev["ticket_id"],
            event_type=ev["event_type"],
            duration_minutes=float(ev.get("duration_minutes", 0)),
            notes=ev.get("notes", ""),
            description=(
                f"{ev['event_type'].replace('_', ' ').title()} on ticket "
                f"{ev['ticket_id']}: {ev.get('notes', '').rstrip('.')}."
            ),
        )
        for ev in hidden_events
    ]

    return HiddenWorkSummary(
        total_hidden_events=len(hidden_events),
        total_hidden_minutes=round(total_hidden_minutes, 2),
        hidden_work_ratio=hidden_ratio,
        hidden_event_types=hidden_types_seen,
        evidence=evidence,
    )
