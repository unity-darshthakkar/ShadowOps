"""
GraniteAnalyser — builds structured chat messages and calls IBM Granite via watsonx.ai SDK.
Falls back to CachedDemoProvider on missing credentials or any call failure.

Uses ModelInference.chat() (not the deprecated generate_text path).
"""
from __future__ import annotations
import json
import logging

from backend.config import Settings
from backend.models.schemas import AnalysisMetrics, GraniteOutput, HiddenWorkSummary, WorkflowStep
from backend.services import cached_provider

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

_SYSTEM_MESSAGE = (
    "You are a workflow-risk analyst specialising in AI deployment safety. "
    "Your task is to analyse the structured workflow data provided by the user "
    "and produce a JSON response that exactly matches the schema they request. "
    "Return ONLY valid JSON. Do not include any explanation, commentary, "
    "markdown fences, or text outside the JSON object."
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

    return f"""Analyse the following workflow data and respond with ONLY the JSON object described at the end.

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
  "workflow_gap_narrative": "<2-3 sentence description of workflow gaps>",
  "hidden_work_narrative": "<2-3 sentence description of hidden work patterns>",
  "redesign_recommendations": ["<recommendation 1>", "<recommendation 2>", "<recommendation 3>"],
  "guardrails": [
    {{
      "id": "<slug>",
      "label": "<short label>",
      "type": "<human_approval|confidence_threshold|exception_routing|manual_fallback|skill_preservation|audit_trail>",
      "description": "<1 sentence>"
    }}
  ],
  "safer_workflow_steps": [
    {{
      "step_id": "<slug>",
      "label": "<step name>",
      "executor": "<human|ai|hybrid>",
      "requires_approval": true,
      "fallback_procedure": "<1 sentence or null>",
      "confidence_threshold": 0.85
    }}
  ],
  "provider": "live_granite"
}}"""


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
# Live Granite call
# ---------------------------------------------------------------------------

def call_granite(prompt: str, settings: Settings) -> GraniteOutput:
    """
    Attempt a live chat call to IBM Granite via ModelInference.chat().
    Falls back to CachedDemoProvider on any failure.

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
                "max_tokens": 2500,
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
        logger.info("Live Granite chat succeeded and passed schema validation.")
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
