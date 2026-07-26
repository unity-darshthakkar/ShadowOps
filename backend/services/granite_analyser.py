"""
GraniteAnalyser — builds structured chat messages and calls IBM Granite via watsonx.ai SDK.
Falls back to CachedDemoProvider on missing credentials, any call failure, or when the live
response fails completeness validation.

Uses ModelInference.chat() (not the deprecated generate_text path).
"""
from __future__ import annotations
import json
import logging

from backend.config import Settings
from backend.models.schemas import (
    AnalysisMetrics,
    GraniteOutput,
    HiddenWorkSummary,
    REQUIRED_GUARDRAIL_TYPES,
    REQUIRED_WORKFLOW_CONCEPTS,
    WorkflowStep,
)
from backend.services import cached_provider

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

_SYSTEM_MESSAGE = (
    "You are a workflow-risk analyst specialising in AI deployment safety for customer-support operations. "
    "Your task is to analyse the structured workflow data provided by the user "
    "and produce a JSON response that exactly matches the schema they request. "
    "Return ONLY valid JSON. Do not include any explanation, commentary, "
    "markdown fences, or text outside the JSON object. "
    "\n\n"
    "CRITICAL OUTPUT RULES — you MUST follow all of these without exception:\n"
    "1. redesign_recommendations: produce EXACTLY 5 to 8 string items. "
    "Each item must be a concrete, actionable recommendation grounded in the workflow data supplied. "
    "Do not invent metrics or fabricate evidence. "
    "Do not include generic advice unrelated to the customer-support scenario.\n"
    "2. guardrails: produce EXACTLY 5 to 8 items. "
    "You MUST include at least one item of EACH of these six types: "
    "human_approval, confidence_threshold, exception_routing, manual_fallback, "
    "skill_preservation, audit_trail. "
    "Every item must have: id (slug), label (short), type (one of the six), description (1 sentence).\n"
    "3. safer_workflow_steps: produce EXACTLY 6 to 10 steps in logical beginning-to-end order. "
    "You MUST include steps that cover ALL of the following concepts — use these exact concepts "
    "as guidance for your step labels and sequencing:\n"
    "   a) Ticket intake or creation (e.g. 'Ticket Created', 'Ticket Intake')\n"
    "   b) Assignment or routing (e.g. 'Assigned', 'Auto-Routed')\n"
    "   c) First response to customer (e.g. 'First Response', 'Initial Response Sent')\n"
    "   d) Exception handling or exception check (e.g. 'Exception Check', 'Escalation Triage')\n"
    "   e) Resolution (e.g. 'Resolution', 'Issue Resolved')\n"
    "   f) Reconciliation or record synchronisation (e.g. 'Automated Reconciliation', 'Record Sync')\n"
    "   g) Closure (e.g. 'Closed', 'Ticket Closed')\n"
    "4. Every step MUST include ALL six fields: "
    "step_id (slug), label (human-readable), executor (ai|hybrid|human), "
    "requires_approval (true/false), fallback_procedure (string or null), confidence_threshold (0.0-1.0 or null).\n"
    "5. VALIDATION CONSTRAINTS:\n"
    "   - Every ai or hybrid step MUST have a non-empty fallback_procedure string (not null).\n"
    "   - Every hybrid step MUST have requires_approval set to true.\n"
    "   - confidence_threshold, when present (not null), must be a number between 0.0 and 1.0.\n"
    "   - The final step (closure) should have executor set to human or hybrid.\n"
    "   - Do NOT invent new metrics. Use only the numbers provided in the user message.\n"
    "   - Do NOT include workflow steps from domains other than the customer-support scenario supplied."
)


def _build_user_message(
    metrics: AnalysisMetrics,
    hidden: HiddenWorkSummary,
    official_workflow: list[WorkflowStep],
    actual_workflow: list[WorkflowStep],
    proposal: dict,
) -> str:
    """Build the grounded user message containing all quantitative context."""
    official_steps = " → ".join(s.label for s in official_workflow)
    actual_steps = " → ".join(s.label for s in actual_workflow)
    hidden_types = ", ".join(hidden.hidden_event_types) or "none detected"

    # Overhead component breakdown
    overhead_lines = "\n".join([
        f"  - Review overhead: {metrics.review_overhead:.1f} min",
        f"  - Correction overhead: {metrics.correction_overhead:.1f} min",
        f"  - Exception-handling overhead: {metrics.exception_overhead:.1f} min",
        f"  - Maintenance overhead: {metrics.maintenance_overhead:.1f} min",
        f"  - Failure-recovery overhead: {metrics.failure_recovery_overhead:.1f} min",
        f"  - Total AI overhead: {metrics.ai_overhead:.1f} min",
    ])

    # Overhead input provenance
    assumption_lines = "\n".join(
        f"  - {a.field}: {a.value} "
        f"({'from proposal' if a.source == 'proposal' else f'DEFAULT ({a.default_value})'})"
        for a in metrics.overhead_assumptions
    ) or "  (none)"

    # Sample hidden-work evidence (capped at 5 for token budget)
    evidence_lines = "\n".join(
        f"  - {ev.event_id}: {ev.description}"
        for ev in hidden.evidence[:5]
    )
    if len(hidden.evidence) > 5:
        evidence_lines += f"\n  - ... and {len(hidden.evidence) - 5} more"
    evidence_text = evidence_lines or "  (none)"

    fallback_text = (
        f"{metrics.missing_fallback_count} automated step(s) lack fallback procedures"
        if metrics.missing_fallback_count > 0
        else "All automated steps have fallback procedures"
    )

    return f"""Analyse the following customer-support workflow data and respond with ONLY the JSON object described at the end.

OFFICIAL WORKFLOW ({len(official_workflow)} steps):
  {official_steps}

ACTUAL WORKFLOW ({len(actual_workflow)} step types, including hidden work):
  {actual_steps}

HIDDEN-WORK TYPES DETECTED:
  {hidden_types}

HIDDEN WORK EVIDENCE (sample):
{evidence_text}

KEY METRICS:
  - Hidden work ratio: {metrics.hidden_work_ratio:.0%} of actual time
  - Burden concentration: {metrics.burden_concentration:.0%} (max hidden work on single role)
  - AI Tax: {metrics.ai_tax:.0%} (overhead / gross time saved)
  - Net time saved with AI: {metrics.net_time_saved:.0f} minutes
  - Automation readiness: {metrics.automation_readiness_label} ({metrics.automation_readiness:.0%})
  - Skill-loss risk: {metrics.skill_loss_risk}
  - Fallback gaps: {fallback_text}

AI OVERHEAD BREAKDOWN:
{overhead_lines}

OVERHEAD INPUT ASSUMPTIONS (source):
{assumption_lines}

RESPOND WITH THIS EXACT JSON STRUCTURE (no other text):
{{
  "workflow_gap_narrative": "<2-3 sentence description of workflow gaps, grounded in the data above>",
  "hidden_work_narrative": "<2-3 sentence description of hidden work patterns, grounded in the data above>",
  "redesign_recommendations": [
    "<recommendation 1 — concrete, actionable, grounded in the supplied workflow>",
    "<recommendation 2>",
    "<recommendation 3>",
    "<recommendation 4>",
    "<recommendation 5>"
  ],
  "guardrails": [
    {{
      "id": "human-approval-<slug>",
      "label": "<short label>",
      "type": "human_approval",
      "description": "<1 sentence>"
    }},
    {{
      "id": "confidence-threshold-<slug>",
      "label": "<short label>",
      "type": "confidence_threshold",
      "description": "<1 sentence>"
    }},
    {{
      "id": "exception-routing-<slug>",
      "label": "<short label>",
      "type": "exception_routing",
      "description": "<1 sentence>"
    }},
    {{
      "id": "manual-fallback-<slug>",
      "label": "<short label>",
      "type": "manual_fallback",
      "description": "<1 sentence>"
    }},
    {{
      "id": "skill-preservation-<slug>",
      "label": "<short label>",
      "type": "skill_preservation",
      "description": "<1 sentence>"
    }},
    {{
      "id": "audit-trail-<slug>",
      "label": "<short label>",
      "type": "audit_trail",
      "description": "<1 sentence>"
    }}
  ],
  "safer_workflow_steps": [
    {{
      "step_id": "ticket-created",
      "label": "Ticket Created",
      "executor": "ai",
      "requires_approval": false,
      "fallback_procedure": "<1 sentence describing manual fallback>",
      "confidence_threshold": null
    }},
    {{
      "step_id": "assigned",
      "label": "Assigned",
      "executor": "ai",
      "requires_approval": false,
      "fallback_procedure": "<1 sentence describing manual fallback>",
      "confidence_threshold": 0.85
    }},
    {{
      "step_id": "first-response",
      "label": "First Response",
      "executor": "hybrid",
      "requires_approval": true,
      "fallback_procedure": "<1 sentence describing manual fallback>",
      "confidence_threshold": 0.80
    }},
    {{
      "step_id": "exception-check",
      "label": "Exception Check",
      "executor": "hybrid",
      "requires_approval": true,
      "fallback_procedure": "<1 sentence describing manual fallback>",
      "confidence_threshold": 0.75
    }},
    {{
      "step_id": "resolution",
      "label": "Resolution",
      "executor": "hybrid",
      "requires_approval": true,
      "fallback_procedure": "<1 sentence describing manual fallback>",
      "confidence_threshold": 0.80
    }},
    {{
      "step_id": "auto-reconciliation",
      "label": "Automated Reconciliation",
      "executor": "ai",
      "requires_approval": false,
      "fallback_procedure": "<1 sentence describing manual fallback>",
      "confidence_threshold": null
    }},
    {{
      "step_id": "closed",
      "label": "Closed",
      "executor": "human",
      "requires_approval": false,
      "fallback_procedure": null,
      "confidence_threshold": null
    }}
  ],
  "provider": "live_granite"
}}

REMINDER: redesign_recommendations must have 5-8 items. guardrails must have 5-8 items and include ALL SIX types. safer_workflow_steps must have 6-10 items covering all 7 required concepts. Every ai/hybrid step must have a non-empty fallback_procedure. Every hybrid step must have requires_approval=true."""


# Keep build_prompt for backward-compatibility with existing tests
def build_prompt(
    metrics: AnalysisMetrics,
    hidden: HiddenWorkSummary,
    official_workflow: list[WorkflowStep],
    actual_workflow: list[WorkflowStep],
    proposal: dict,
) -> str:
    """Return the user message content (used by tests to inspect prompt structure)."""
    return _build_user_message(metrics, hidden, official_workflow, actual_workflow, proposal)


# ---------------------------------------------------------------------------
# Completeness validation
# ---------------------------------------------------------------------------

def _validate_completeness(result: GraniteOutput) -> str | None:
    """
    Check that the live Granite output meets completeness requirements beyond
    what the Pydantic schema enforces (list lengths are enforced by the schema).

    Returns a concise failure reason string, or None if everything is valid.
    Does NOT check list lengths — those raise ValidationError before this is called.
    """
    # 1. All six required guardrail types must be present
    present_types = {g.type for g in result.guardrails}
    missing_types = REQUIRED_GUARDRAIL_TYPES - present_types
    if missing_types:
        return f"missing required guardrail type(s): {', '.join(sorted(missing_types))}"

    for step in result.safer_workflow_steps:
        # 2. Every ai or hybrid step must have a non-empty fallback_procedure
        if step.executor in ("ai", "hybrid"):
            if not step.fallback_procedure or not step.fallback_procedure.strip():
                return (
                    f"step '{step.step_id}' is executor={step.executor} "
                    "but has no fallback_procedure"
                )
        # 3. Every hybrid step must require approval
        if step.executor == "hybrid" and not step.requires_approval:
            return (
                f"hybrid step '{step.step_id}' must have requires_approval=true"
            )
        # 4. Confidence thresholds must be in [0, 1] when present
        if step.confidence_threshold is not None:
            if not (0.0 <= step.confidence_threshold <= 1.0):
                return (
                    f"step '{step.step_id}' confidence_threshold "
                    f"{step.confidence_threshold} is outside [0, 1]"
                )

    # 5. Required workflow concepts must be present in the step labels
    all_labels = " ".join(s.label.lower() for s in result.safer_workflow_steps)
    for concept, keywords in REQUIRED_WORKFLOW_CONCEPTS.items():
        if not any(kw in all_labels for kw in keywords):
            return f"safer_workflow_steps missing required concept '{concept}'"

    return None


# ---------------------------------------------------------------------------
# Live Granite call
# ---------------------------------------------------------------------------

def call_granite(prompt: str, settings: Settings) -> GraniteOutput:
    """
    Attempt a live chat call to IBM Granite via ModelInference.chat().
    Falls back to CachedDemoProvider on any failure OR when completeness
    validation fails.

    'prompt' is the user-message content; the system message is added internally.
    Credentials are never logged.
    """
    logger.info(
        "Attempting live Granite chat call (model=%s, project=%s)",
        settings.watsonx_model_id,
        settings.watsonx_project_id,
    )
    try:
        from ibm_watsonx_ai import Credentials
        from ibm_watsonx_ai.foundation_models import ModelInference

        credentials = Credentials(
            api_key=settings.watsonx_api_key,
            url=settings.watsonx_url,
        )
        model = ModelInference(
            model_id=settings.watsonx_model_id,
            credentials=credentials,
            project_id=settings.watsonx_project_id,
        )

        messages = [
            {"role": "system", "content": _SYSTEM_MESSAGE},
            {"role": "user",   "content": prompt},
        ]

        response = model.chat(
            messages=messages,
            params={
                "max_tokens": 3500,
                "temperature": 0,
                "response_format": {"type": "json_object"},
            },
        )

        raw_content: str = response["choices"][0]["message"]["content"]

        if not raw_content or not raw_content.strip():
            logger.warning(
                "Granite chat returned empty content (%s); using cached demo.",
                type(response).__name__,
            )
            return cached_provider.get()

        parsed = json.loads(raw_content)
        parsed["provider"] = "live_granite"
        result = GraniteOutput.model_validate(parsed)

        # Post-schema completeness validation
        failure_reason = _validate_completeness(result)
        if failure_reason:
            logger.warning(
                "Live Granite output failed completeness validation (%s); "
                "using cached demo.",
                failure_reason,
            )
            return cached_provider.get()

        logger.info("Live Granite chat succeeded and passed completeness validation.")
        return result

    except json.JSONDecodeError as exc:
        logger.warning(
            "Granite chat response was not valid JSON (%s: %s); using cached demo.",
            type(exc).__name__, exc,
        )
        return cached_provider.get()
    except Exception as exc:
        # Covers ValidationError, SDK errors, network errors, KeyError in response dict
        logger.warning(
            "Granite chat call failed (%s: %s); using cached demo.",
            type(exc).__name__, exc,
        )
        return cached_provider.get()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def analyse(
    metrics: AnalysisMetrics,
    hidden: HiddenWorkSummary,
    settings: Settings,
    official_workflow: list[WorkflowStep],
    actual_workflow: list[WorkflowStep],
    proposal: dict,
) -> GraniteOutput:
    """Use live Granite when all credentials are present; else return cached demo."""
    if not settings.has_watsonx_credentials:
        logger.info("No watsonx credentials configured; using cached demo provider.")
        return cached_provider.get()

    user_msg = _build_user_message(
        metrics, hidden, official_workflow, actual_workflow, proposal
    )
    return call_granite(user_msg, settings)
