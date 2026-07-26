"""
PII redaction utilities for ShadowOps.

Applies lightweight pattern-based redaction to free-text fields (event notes)
before they are passed to IBM Granite or stored in responses.

Preserves:
  - Ticket IDs: TKT-\d+, TKT-\w+
  - Event IDs: evt-\w+
  - Agent IDs: agent-\w+
  - Role names: Support Agent, Senior Support Agent, Operations Specialist, Team Lead
  - Workflow labels: Ticket Created, First Response, etc. (title-cased workflow terms)

Redacts:
  - Email addresses → [REDACTED_EMAIL]
  - Likely personal names (Title Case two-word sequences not in the allow-list) → [REDACTED_NAME]

Strategy: protect multi-word terms first by temporarily substituting them, then
redact remaining bare title-case pairs, then restore the substitutions.
"""
from __future__ import annotations
import re
import copy

# ---------------------------------------------------------------------------
# Compiled patterns
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")

# Title-case two-word sequences that are candidates for name-redaction
_TITLE_CASE_PAIR_RE = re.compile(r"\b([A-Z][a-z]+)\s+([A-Z][a-z]+)\b")

# Protected phrases — sorted longest-first so longer phrases are matched preferentially
_PROTECTED_TERMS: list[str] = sorted(
    [
        "Senior Support Agent",
        "Support Agent",
        "Operations Specialist",
        "Team Lead",
        "Ticket Created",
        "First Response",
        "Manual Status Check",
        "Context Repair",
        "Duplicate Entry",
        "Exception Handling",
        "Manual Reconciliation",
        "Follow Up",
        "Ticket Resolution",
    ],
    key=len,
    reverse=True,
)

# Prefixes that indicate IDs rather than personal names
_ID_PREFIX_RE = re.compile(r"^(agent|evt|tkt|tkid)-", re.IGNORECASE)


def redact_text(text: str) -> str:
    """
    Redact PII patterns from a single text string.
    Preserves ticket IDs, event IDs, agent IDs, role names, and workflow labels.
    """
    # 1. Redact emails first (unambiguous)
    text = _EMAIL_RE.sub("[REDACTED_EMAIL]", text)

    # 2. Temporarily replace protected multi-word phrases with numbered tokens
    #    so they survive the name-redaction pass.
    saved: list[str] = []
    for phrase in _PROTECTED_TERMS:
        if phrase in text:
            token = f"\x00PROTECTED{len(saved)}\x00"
            text = text.replace(phrase, token)
            saved.append(phrase)

    # 3. Redact remaining bare title-case pairs that are not IDs
    def _maybe_redact_name(m: re.Match) -> str:
        # Skip if it looks like an ID token (starts with \x00)
        if m.group(0).startswith("\x00"):
            return m.group(0)
        # Skip if either word looks like an ID-prefixed token
        if _ID_PREFIX_RE.match(m.group(1)) or _ID_PREFIX_RE.match(m.group(2)):
            return m.group(0)
        return "[REDACTED_NAME]"

    text = _TITLE_CASE_PAIR_RE.sub(_maybe_redact_name, text)

    # 4. Restore protected phrases
    for i, phrase in enumerate(saved):
        text = text.replace(f"\x00PROTECTED{i}\x00", phrase)

    return text


def redact_events(events: list[dict]) -> list[dict]:
    """
    Return a deep copy of the event list with PII redacted from the 'notes' field.
    Does not modify the original list or any other field.
    """
    redacted: list[dict] = []
    for ev in events:
        ev_copy = copy.copy(ev)
        notes = ev_copy.get("notes", "")
        if notes:
            ev_copy["notes"] = redact_text(notes)
        redacted.append(ev_copy)
    return redacted
