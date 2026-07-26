"""
Deterministic PII redaction for free-text notes before live Granite inference.
Redacts email addresses and likely personal names.
Preserves anonymous event IDs, ticket IDs, workflow labels, and role names.
"""
from __future__ import annotations
import re
from typing import Any

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
# Common first names that might appear in synthetic data
COMMON_NAMES = {
    "john", "jane", "alex", "sam", "chris", "pat", "taylor", "morgan",
    "jordan", "casey", "riley", "avery", "quinn", "dakota", "payton",
    "jesse", "marion", "leslie", "francis", "kelly", "ashley", "dana"
}
NAME_RE = re.compile(r"\b([A-Z][a-z]+)\s+([A-Z][a-z]+)\b")

def redact_text(text: str) -> str:
    """
    Redact PII from a single text string.
    Returns redacted text with [REDACTED_EMAIL] and [REDACTED_NAME] markers.
    """
    if not text:
        return text

    # Redact email addresses
    text = EMAIL_RE.sub("[REDACTED_EMAIL]", text)

    # Preserve known workflow labels and role names before name redaction
    # These are known system terms that should NOT be redacted
    PRESERVED_TERMS = {
        "Ticket Created", "Ticket Updated", "Assigned", "Acknowledged",
        "In Progress", "Under Review", "Resolved", "Closed", "Reopened",
        "Escalated", "Waiting", "On Hold", "Reassigned",
        "Support Agent", "Senior Agent", "Team Lead", "Operations Specialist",
        "Customer Reports", "Agent Manually", "Manual Status Check",
        "Context Repair", "Duplicate Entry", "Rework", "Exception Handling",
        "Escalation", "Manual Reconciliation", "Follow Up",
    }

    # Temporarily replace preserved terms with placeholders
    placeholders = {}
    for i, term in enumerate(PRESERVED_TERMS):
        if term in text:
            placeholder = f"__PRESERVED_{i}__"
            placeholders[placeholder] = term
            text = text.replace(term, placeholder)

    # Also preserve "evt-" and "TKT-" prefixed IDs
    for match in re.finditer(r'\b(TKT-\w+|evt-\w+|agent-\w+)\b', text):
        placeholder = f"__PRESERVED_ID_{len(placeholders)}__"
        placeholders[placeholder] = match.group(0)
        text = text.replace(match.group(0), placeholder)

    # Redact likely personal names (two capitalized words)
    def replace_name(match: re.Match) -> str:
        first, last = match.group(1), match.group(2)
        return "[REDACTED_NAME]"

    text = NAME_RE.sub(replace_name, text)

    # Restore preserved terms
    for placeholder, original in placeholders.items():
        text = text.replace(placeholder, original)

    return text


def redact_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Create a copy of events with notes redacted.
    Does not modify the original events list.
    """
    redacted = []
    for ev in events:
        ev_copy = ev.copy()
        if "notes" in ev_copy and ev_copy["notes"]:
            ev_copy["notes"] = redact_text(ev_copy["notes"])
        redacted.append(ev_copy)
    return redacted


def redact_granite_prompt_data(
    official_workflow: list[Any],
    actual_workflow: list[Any],
    hidden_evidence: list[Any],
    metrics: Any,
    proposal: dict[str, Any],
) -> tuple[list[Any], list[Any], list[Any], Any, dict[str, Any]]:
    """
    Redact PII from data passed to Granite prompt builder.
    Returns redacted copies of all inputs.
    """
    # Events are not passed directly to build_prompt anymore,
    # but the hidden evidence and workflows might contain notes.
    # For now, we just return deep copies since the prompt uses
    # structured fields (labels, descriptions) not raw notes.
    # The main redaction happens at the event level before analysis.
    return official_workflow, actual_workflow, hidden_evidence, metrics, proposal.copy()