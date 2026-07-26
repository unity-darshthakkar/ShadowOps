"""
GraniteAnalyser — builds the prompt and calls IBM Granite via watsonx.ai SDK.
Falls back to CachedDemoProvider on missing credentials or any call failure.
"""
from __future__ import annotations
import json
import logging
import re

from backend.config import Settings
from backend.models.schemas import AnalysisMetrics, GraniteOutput, HiddenWorkSummary
from backend.services import cached_provider

logger = logging.getLogger(__name__)


def build_prompt(metrics: AnalysisMetrics, hidden: HiddenWorkSummary) -> str:
    official_steps = "ticket created → assigned → first response → resolution → closed"
    actual_steps = ", ".join(hidden.hidden_event_types) or "none detected"

    return f"""You are a workflow design expert. Analyse the following workflow data and respond ONLY
with valid JSON matching the schema below. Do not include any text outside the JSON object.

WORKFLOW DATA:
- Official steps: {official_steps}
- Hidden-work types detected: {actual_steps}
- Hidden work ratio: {metrics.hidden_work_ratio:.0%}
- Net time saved with AI: {metrics.net_time_saved:.0f} minutes
- Automation readiness: {metrics.automation_readiness_label}
- Skill-loss risk: {metrics.skill_loss_risk}

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
) -> GraniteOutput:
    """Entry point: use live Granite if credentials are present, else cached demo."""
    if not settings.has_watsonx_credentials:
        logger.info("No watsonx credentials configured; using cached demo provider.")
        return cached_provider.get()
    prompt = build_prompt(metrics, hidden)
    return call_granite(prompt, settings)
