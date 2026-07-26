"""
GraniteAnalyser — builds the prompt and calls IBM Granite via watsonx.ai SDK.
Falls back to CachedDemoProvider on missing credentials or any call failure.
"""
from __future__ import annotations
import json
import logging
import re

from backend.config import Settings
from backend.models.schemas import AnalysisMetrics, GraniteOutput, HiddenWorkSummary, WorkflowStep
from backend.services import cached_provider

logger = logging.getLogger(__name__)


def build_prompt(
    metrics: AnalysisMetrics,
    hidden: HiddenWorkSummary,
    official_workflow: list[WorkflowStep],
    actual_workflow: list[WorkflowStep],
    proposal: dict,
) -> str:
    official_steps = " → ".join(s.label for s in official_workflow)
    actual_steps = " → ".join(s.label for s in actual_workflow)
    hidden_types = ", ".join(hidden.hidden_event_types) or "none detected"

    # Format overhead components
    overhead_lines = [
        f"  - Review overhead: {metrics.review_overhead:.1f} min",
        f"  - Correction overhead: {metrics.correction_overhead:.1f} min",
        f"  - Exception-handling overhead: {metrics.exception_overhead:.1f} min",
        f"  - Maintenance overhead: {metrics.maintenance_overhead:.1f} min",
        f"  - Failure-recovery overhead: {metrics.failure_recovery_overhead:.1f} min",
    ]
    overhead_text = "\n".join(overhead_lines)

    # Format assumption flags
    assumption_lines = []
    for a in metrics.overhead_assumptions:
        src = "from proposal" if a.source == "proposal" else f"DEFAULT ({a.default_value})"
        assumption_lines.append(f"  - {a.field}: {a.value} ({src})")
    assumption_text = "\n".join(assumption_lines) if assumption_lines else "  (none)"

    # Hidden work evidence summary
    evidence_lines = []
    for ev in hidden.evidence[:5]:  # top 5 for brevity
        evidence_lines.append(f"  - {ev.event_id}: {ev.description}")
    if len(hidden.evidence) > 5:
        evidence_lines.append(f"  - ... and {len(hidden.evidence) - 5} more")
    evidence_text = "\n".join(evidence_lines) if evidence_lines else "  (none)"

    # Fallback gaps
    fallback_gaps = metrics.missing_fallback_count
    fallback_text = f"{fallback_gaps} automated step(s) lack fallback procedures" if fallback_gaps > 0 else "All automated steps have fallback procedures"

    return f"""You are a workflow design expert. Analyse the following workflow data and respond ONLY
with valid JSON matching the schema below. Do not include any text outside the JSON object.

WORKFLOW DATA:
- Official workflow steps ({len(official_workflow)}): {official_steps}
- Actual workflow steps ({len(actual_workflow)}): {actual_steps}
- Hidden-work types detected: {hidden_types}
- Hidden work ratio: {metrics.hidden_work_ratio:.0%}
- Total hidden work: {metrics.hidden_work_ratio * 100:.0f}% of actual time
- Burden concentration: {metrics.burden_concentration:.0%} (max hidden work on single role)

AI OVERHEAD BREAKDOWN:
{overhead_text}

OVERHEAD ASSUMPTIONS (source):
{assumption_text}

HIDDEN WORK EVIDENCE (sample):
{evidence_text}

KEY METRICS:
- AI Tax: {metrics.ai_tax:.0%} (overhead / gross time saved)
- Net time saved with AI: {metrics.net_time_saved:.0f} minutes
- Automation readiness: {metrics.automation_readiness_label} ({metrics.automation_readiness:.0%})
- Skill-loss risk: {metrics.skill_loss_risk}
- Fallback gaps: {fallback_text}

RESPOND WITH THIS EXACT JSON STRUCTURE:
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


def _extract_json(raw: str) -> str:
    """Strip markdown code fences if present, then return the JSON string."""
    raw = raw.strip()
    # Remove ```json ... ``` or ``` ... ```
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if match:
        return match.group(1).strip()
    return raw


def call_granite(prompt: str, settings: Settings) -> GraniteOutput:
    """
    Attempt a live call to IBM Granite.
    Falls back to cached provider on any failure.
    """
    try:
        from ibm_watsonx_ai.foundation_models import ModelInference
        from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as Params

        model = ModelInference(
            model_id=settings.watsonx_model_id,
            credentials={
                "url": settings.watsonx_url,
                "apikey": settings.watsonx_api_key,
            },
            project_id=settings.watsonx_project_id,
        )
        response = model.generate_text(
            prompt=prompt,
            params={
                Params.MAX_NEW_TOKENS: 1200,
                Params.TEMPERATURE: 0.2,
                Params.TOP_P: 0.9,
            },
        )
        raw_json = _extract_json(response)
        parsed = json.loads(raw_json)
        parsed["provider"] = "live_granite"
        return GraniteOutput.model_validate(parsed)

    except json.JSONDecodeError as exc:
        logger.warning("Granite response was not valid JSON; using cached demo. Detail: %s", exc)
        return cached_provider.get()
    except Exception as exc:  # ValidationError, SDK errors, network errors
        logger.warning("Granite call failed (%s: %s); using cached demo.", type(exc).__name__, exc)
        return cached_provider.get()


def analyse(
    metrics: AnalysisMetrics,
    hidden: HiddenWorkSummary,
    settings: Settings,
    official_workflow: list[WorkflowStep],
    actual_workflow: list[WorkflowStep],
    proposal: dict,
) -> GraniteOutput:
    """Entry point: use live Granite if credentials are present, else cached demo."""
    if not settings.has_watsonx_credentials:
        logger.info("No watsonx credentials configured; using cached demo provider.")
        return cached_provider.get()
    prompt = build_prompt(metrics, hidden, official_workflow, actual_workflow, proposal)
    return call_granite(prompt, settings)
