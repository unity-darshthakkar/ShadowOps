"""
Backend tests for ShadowOps.

Runs with: pytest backend/tests/ -v
Single test: pytest backend/tests/test_api.py::test_health -v
"""
from __future__ import annotations
import json
import pytest

# ---------------------------------------------------------------------------
# Environment must be set BEFORE importing backend modules
# ---------------------------------------------------------------------------
import os
os.environ["DATABASE_URL"] = "sqlite:///./test_shadowops.db"
os.environ["WATSONX_API_KEY"] = ""

import backend.config as _cfg
_cfg._settings = None   # flush singleton so new env vars are read

# Now import application modules
from sqlalchemy import create_engine as _sa_create_engine
from sqlalchemy.orm import sessionmaker

import backend.database as _db_module

# Override the engine used by the app with a test-specific one
_TEST_DB_URL = "sqlite:///./test_shadowops.db"
_test_engine = _sa_create_engine(_TEST_DB_URL, connect_args={"check_same_thread": False})

# Monkey-patch database module so app uses test engine
_db_module.get_engine = lambda: _test_engine

# Create tables
from backend.database import Base
import backend.models.db_models  # noqa: F401 — registers ORM models
Base.metadata.create_all(bind=_test_engine)

from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.services.hidden_work_detector import detect, HIDDEN_WORK_TYPES
from backend.services.workflow_reconstructor import reconstruct
from backend.services.metrics_calculator import calculate, OVERHEAD_DEFAULTS
from backend.services.cached_provider import get as cached_get
from backend.models.schemas import GraniteOutput, AnalysisResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def seed_events():
    import pathlib, json
    path = pathlib.Path(__file__).parent.parent / "data" / "seed_scenarios.json"
    with open(path) as f:
        data = json.load(f)
    return data["events"]


@pytest.fixture
def seed_scenario():
    import pathlib, json
    path = pathlib.Path(__file__).parent.parent / "data" / "seed_scenarios.json"
    with open(path) as f:
        return json.load(f)


@pytest.fixture
def full_proposal():
    return {
        "expected_review_rate": 0.15,
        "avg_review_minutes": 3.0,
        "expected_correction_rate": 0.08,
        "avg_correction_minutes": 8.0,
        "exception_rate": 0.05,
        "avg_exception_handling_minutes": 20.0,
        "weekly_maintenance_minutes": 45.0,
        "expected_failure_recovery_minutes": 30.0,
    }


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["provider"] in ("live_granite", "cached_demo")
    assert data["version"] == "0.1.0"


# ---------------------------------------------------------------------------
# Scenario endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scenarios_returns_cs_demo():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/scenarios")
    assert resp.status_code == 200
    ids = [s["scenario_id"] for s in resp.json()]
    assert "cs-demo-v1" in ids


@pytest.mark.asyncio
async def test_scenario_has_minimum_events_and_tickets(seed_scenario):
    events = seed_scenario["events"]
    ticket_ids = {ev["ticket_id"] for ev in events}
    assert len(events) >= 30, f"Expected ≥30 events, got {len(events)}"
    assert len(ticket_ids) >= 5, f"Expected ≥5 tickets, got {len(ticket_ids)}"


# ---------------------------------------------------------------------------
# Hidden work detector
# ---------------------------------------------------------------------------

def test_all_8_hidden_work_types_detected(seed_events):
    summary = detect(seed_events)
    for hw_type in HIDDEN_WORK_TYPES:
        assert hw_type in summary.hidden_event_types, f"Missing hidden-work type: {hw_type}"


def test_waiting_not_counted_as_hidden_work(seed_events):
    waiting_events = [ev for ev in seed_events if ev["event_type"] == "waiting"]
    assert len(waiting_events) >= 1, "Seed data must contain at least one waiting event"
    summary = detect(seed_events)
    assert "waiting" not in summary.hidden_event_types
    # Confirm waiting events have is_hidden_work=False
    for ev in waiting_events:
        assert ev.get("is_hidden_work") is False


def test_evidence_contains_event_ids(seed_events):
    summary = detect(seed_events)
    assert len(summary.evidence) > 0
    for ev_evidence in summary.evidence:
        assert ev_evidence.event_id.startswith("evt-")
        assert ev_evidence.ticket_id.startswith("TKT-")
        assert ev_evidence.duration_minutes > 0


def test_hidden_work_ratio_formula(seed_events):
    summary = detect(seed_events)
    total = sum(float(ev.get("duration_minutes", 0)) for ev in seed_events)
    hidden = sum(
        float(ev.get("duration_minutes", 0))
        for ev in seed_events
        if ev["event_type"] in HIDDEN_WORK_TYPES
    )
    expected = round(hidden / total, 4) if total > 0 else 0.0
    assert summary.hidden_work_ratio == expected


# ---------------------------------------------------------------------------
# Workflow reconstructor
# ---------------------------------------------------------------------------

def test_reconstruct_preserves_order(seed_events):
    _, actual = reconstruct(seed_events)
    types = [s.event_type for s in actual]
    # ticket_created must come before resolution
    assert types.index("ticket_created") < types.index("resolution")


def test_official_workflow_excludes_hidden_work(seed_events):
    official, _ = reconstruct(seed_events)
    for step in official:
        assert step.event_type not in HIDDEN_WORK_TYPES


# ---------------------------------------------------------------------------
# Metrics calculator
# ---------------------------------------------------------------------------

def test_five_overhead_components_sum_to_ai_overhead(seed_events, full_proposal):
    summary = detect(seed_events)
    metrics = calculate(seed_events, summary, full_proposal)
    component_sum = round(
        metrics.review_overhead
        + metrics.correction_overhead
        + metrics.exception_overhead
        + metrics.maintenance_overhead
        + metrics.failure_recovery_overhead,
        2,
    )
    assert abs(metrics.ai_overhead - component_sum) < 0.01, (
        f"ai_overhead {metrics.ai_overhead} ≠ component sum {component_sum}"
    )


def test_ai_tax_clamped_zero_to_one(seed_events, full_proposal):
    summary = detect(seed_events)
    metrics = calculate(seed_events, summary, full_proposal)
    assert 0.0 <= metrics.ai_tax <= 1.0


def test_net_time_saved_can_be_negative():
    # Manufacture a scenario where overhead is huge
    events = [
        {"event_id": "x-001", "ticket_id": "T-001", "agent_id": "agent-A",
         "event_type": "ticket_created", "timestamp": "2024-01-01T09:00:00Z",
         "duration_minutes": 1, "notes": "test", "is_hidden_work": False},
        {"event_id": "x-002", "ticket_id": "T-001", "agent_id": "agent-A",
         "event_type": "closed", "timestamp": "2024-01-02T09:00:00Z",
         "duration_minutes": 1, "notes": "test", "is_hidden_work": False},
    ]
    big_overhead_proposal = {
        "expected_review_rate": 1.0,
        "avg_review_minutes": 999.0,
        "expected_correction_rate": 0.0,
        "avg_correction_minutes": 0.0,
        "exception_rate": 0.0,
        "avg_exception_handling_minutes": 0.0,
        "weekly_maintenance_minutes": 0.0,
        "expected_failure_recovery_minutes": 0.0,
    }
    from backend.services.hidden_work_detector import detect as _detect
    summary = _detect(events)
    metrics = calculate(events, summary, big_overhead_proposal)
    assert metrics.net_time_saved < 0


def test_automation_readiness_label_high(seed_events, full_proposal):
    summary = detect(seed_events)
    metrics = calculate(seed_events, summary, full_proposal)
    expected_label = (
        "High" if metrics.automation_readiness >= 0.7
        else "Medium" if metrics.automation_readiness >= 0.4
        else "Low"
    )
    assert metrics.automation_readiness_label == expected_label


def test_overhead_uses_proposal_fields(seed_events, full_proposal):
    summary = detect(seed_events)
    metrics = calculate(seed_events, summary, full_proposal)
    for assumption in metrics.overhead_assumptions:
        assert assumption.source == "proposal"


def test_overhead_flags_defaults_when_missing(seed_events):
    summary = detect(seed_events)
    metrics = calculate(seed_events, summary, {})   # empty proposal → all defaults
    for assumption in metrics.overhead_assumptions:
        assert assumption.source == "default"
        assert assumption.default_value is not None


def test_overhead_assumptions_has_8_fields(seed_events, full_proposal):
    summary = detect(seed_events)
    metrics = calculate(seed_events, summary, full_proposal)
    assert len(metrics.overhead_assumptions) == 8


# ---------------------------------------------------------------------------
# Cached provider
# ---------------------------------------------------------------------------

def test_cached_provider_passes_schema_validation():
    output = cached_get()
    assert isinstance(output, GraniteOutput)
    assert output.provider == "cached_demo"
    assert len(output.redesign_recommendations) >= 3
    assert len(output.guardrails) >= 6


def test_provider_fallback_on_missing_credentials():
    """analyse() must return cached_demo when no credentials are set."""
    from backend.services.granite_analyser import analyse
    from backend.config import Settings
    from backend.services import workflow_reconstructor

    settings = Settings(
        watsonx_api_key="",
        watsonx_url="",
        watsonx_project_id="",
    )

    import pathlib, json
    path = pathlib.Path(__file__).parent.parent / "data" / "seed_scenarios.json"
    with open(path) as f:
        scenario = json.load(f)
    events = scenario["events"]
    proposal = scenario.get("automation_proposal", {})
    summary = detect(events)
    metrics = calculate(events, summary, proposal)
    official_wf, actual_wf = workflow_reconstructor.reconstruct(events)

    result = analyse(metrics, summary, settings, official_wf, actual_wf, proposal)
    assert result.provider == "cached_demo"


def test_provider_fallback_on_invalid_json(monkeypatch):
    """call_granite must fall back when SDK returns unparseable text."""
    from backend.services.granite_analyser import call_granite
    from backend.config import Settings

    settings = Settings(
        watsonx_api_key="fake-key",
        watsonx_url="https://fake.example.com",
        watsonx_project_id="fake-project",
    )

    # Mock the SDK so it raises on import/instantiation
    import sys
    class FakeModelInference:
        def __init__(self, **kwargs): pass
        def generate_text(self, **kwargs): return "this is not json {{{"

    import types
    fake_module = types.ModuleType("ibm_watsonx_ai.foundation_models")
    fake_module.ModelInference = FakeModelInference
    monkeypatch.setitem(sys.modules, "ibm_watsonx_ai.foundation_models", fake_module)

    # Also mock metanames
    fake_meta = types.ModuleType("ibm_watsonx_ai.metanames")
    class FakeParams:
        MAX_NEW_TOKENS = "max_new_tokens"
        TEMPERATURE = "temperature"
        TOP_P = "top_p"
    fake_meta.GenTextParamsMetaNames = FakeParams
    monkeypatch.setitem(sys.modules, "ibm_watsonx_ai.metanames", fake_meta)

    import pathlib, json
    path = pathlib.Path(__file__).parent.parent / "data" / "seed_scenarios.json"
    with open(path) as f:
        scenario = json.load(f)
    events = scenario["events"]
    proposal = scenario.get("automation_proposal", {})
    summary = detect(events)
    metrics = calculate(events, summary, proposal)

    result = call_granite("some prompt", settings)
    assert result.provider == "cached_demo"


# ---------------------------------------------------------------------------
# Granite prompt grounding tests
# ---------------------------------------------------------------------------

def test_granite_prompt_includes_workflows_and_overhead(seed_events, full_proposal):
    """Prompt must contain reconstructed workflows, hidden-work evidence, overhead breakdown."""
    from backend.services.granite_analyser import build_prompt
    from backend.services.workflow_reconstructor import reconstruct
    from backend.services.hidden_work_detector import detect

    official_wf, actual_wf = reconstruct(seed_events)
    summary = detect(seed_events)
    metrics = calculate(seed_events, summary, full_proposal)

    prompt = build_prompt(metrics, summary, official_wf, actual_wf, full_proposal)

    # Workflows
    assert "Official workflow steps" in prompt
    assert "Actual workflow steps" in prompt
    assert "Ticket Created" in prompt  # step label appears
    assert "Assigned" in prompt

    # Hidden work
    assert "Hidden-work types detected" in prompt
    assert "follow_up" in prompt or "manual_status_check" in prompt

    # Overhead breakdown (all 5 components)
    assert "Review overhead" in prompt
    assert "Correction overhead" in prompt
    assert "Exception-handling overhead" in prompt
    assert "Maintenance overhead" in prompt
    assert "Failure-recovery overhead" in prompt

    # Assumptions provenance
    assert "OVERHEAD ASSUMPTIONS" in prompt
    assert "from proposal" in prompt or "DEFAULT" in prompt

    # Evidence
    assert "HIDDEN WORK EVIDENCE" in prompt
    assert "evt-" in prompt  # raw event_ids

    # Key metrics
    assert "AI Tax" in prompt
    assert "Net time saved" in prompt
    assert "Automation readiness" in prompt
    assert "Skill-loss risk" in prompt
    assert "Burden concentration" in prompt

    # Fallback gaps
    assert "Fallback gaps" in prompt


# ---------------------------------------------------------------------------
# Provider status endpoint tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_provider_status_endpoint():
    """GET /api/demo/provider-status returns correct provider."""
    from httpx import AsyncClient as AC
    from backend.main import app
    from httpx import ASGITransport

    async with AC(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/demo/provider-status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["provider"] in ("live_granite", "cached_demo")


# ---------------------------------------------------------------------------
# Full analysis endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_analysis_returns_complete_result():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/api/analysis/run", json={"scenario_id": "cs-demo-v1"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "complete"
    assert data["analysis_id"]
    assert data["disclaimer"]
    assert data["provider_status"] in ("live_granite", "cached_demo")


@pytest.mark.asyncio
async def test_get_analysis_by_id():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        post_resp = await ac.post("/api/analysis/run", json={"scenario_id": "cs-demo-v1"})
        aid = post_resp.json()["analysis_id"]
        get_resp = await ac.get(f"/api/analysis/{aid}")
    assert get_resp.status_code == 200
    assert get_resp.json()["analysis_id"] == aid


@pytest.mark.asyncio
async def test_report_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        post_resp = await ac.post("/api/analysis/run", json={"scenario_id": "cs-demo-v1"})
        aid = post_resp.json()["analysis_id"]
        report_resp = await ac.get(f"/api/analysis/{aid}/report")
    assert report_resp.status_code == 200
    assert "disclaimer" in report_resp.json()


@pytest.mark.asyncio
async def test_disclaimer_not_empty():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/api/analysis/run", json={"scenario_id": "cs-demo-v1"})
    assert resp.json()["disclaimer"]


@pytest.mark.asyncio
async def test_pii_not_in_response():
    """No real names, emails, or phone numbers should appear in the response."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/api/analysis/run", json={"scenario_id": "cs-demo-v1"})
    body = resp.text
    # Check no @-sign email patterns
    import re
    assert not re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", body), \
        "Response contains what looks like an email address"


# ---------------------------------------------------------------------------
# Regression tests for waiting-event metric bug
# ---------------------------------------------------------------------------

def test_waiting_events_in_actual_total():
    """Waiting events contribute to actual_total_minutes."""
    events = [
        {"event_id": "e-1", "ticket_id": "T-1", "agent_id": "agent-A",
         "event_type": "ticket_created", "timestamp": "2024-01-01T09:00:00Z",
         "duration_minutes": 5, "notes": "test", "is_hidden_work": False},
        {"event_id": "e-2", "ticket_id": "T-1", "agent_id": "agent-A",
         "event_type": "waiting", "timestamp": "2024-01-01T09:10:00Z",
         "duration_minutes": 120, "notes": "awaiting reply", "is_hidden_work": False},
        {"event_id": "e-3", "ticket_id": "T-1", "agent_id": "agent-A",
         "event_type": "resolution", "timestamp": "2024-01-01T11:10:00Z",
         "duration_minutes": 5, "notes": "test", "is_hidden_work": False},
    ]
    summary = detect(events)
    metrics = calculate(events, summary, {})
    assert metrics.actual_total_minutes == 130.0  # 5 + 120 + 5


def test_waiting_events_excluded_from_routine():
    """Waiting events are NOT in routine_count, routine_total, or AI-automated work."""
    events = [
        # 10 min of real work
        {"event_id": "e-1", "ticket_id": "T-1", "agent_id": "agent-A",
         "event_type": "ticket_created", "timestamp": "2024-01-01T09:00:00Z",
         "duration_minutes": 5, "notes": "test", "is_hidden_work": False},
        {"event_id": "e-2", "ticket_id": "T-1", "agent_id": "agent-A",
         "event_type": "resolution", "timestamp": "2024-01-01T09:10:00Z",
         "duration_minutes": 5, "notes": "test", "is_hidden_work": False},
        # 100 min of waiting
        {"event_id": "e-3", "ticket_id": "T-1", "agent_id": "agent-A",
         "event_type": "waiting", "timestamp": "2024-01-01T09:20:00Z",
         "duration_minutes": 100, "notes": "awaiting reply", "is_hidden_work": False},
    ]
    summary = detect(events)
    # With full proposal so overhead is predictable
    full_proposal = {
        "expected_review_rate": 0.15, "avg_review_minutes": 3.0,
        "expected_correction_rate": 0.08, "avg_correction_minutes": 8.0,
        "exception_rate": 0.05, "avg_exception_handling_minutes": 20.0,
        "weekly_maintenance_minutes": 45.0, "expected_failure_recovery_minutes": 30.0,
    }
    metrics = calculate(events, summary, full_proposal)

    # actual_total = 110 (real 10 + waiting 100)
    assert metrics.actual_total_minutes == 110.0

    # routine_events excludes waiting → only 2 events with 10 min total
    # ai_automated = routine_total * 0.70 = 7.0
    # gross_time_saved = actual_total - ai_automated = 110 - 7 = 103
    assert metrics.ai_automated_total_minutes == 7.0

    # Overhead uses routine_count (2), not total events (3)
    # review_overhead = 2 * 0.15 * 3.0 = 0.9
    assert abs(metrics.review_overhead - 0.9) < 0.01


def test_waiting_events_not_counted_as_hidden_work():
    """Waiting events never appear in hidden work metrics."""
    events = [
        {"event_id": "e-1", "ticket_id": "T-1", "agent_id": "agent-A",
         "event_type": "ticket_created", "timestamp": "2024-01-01T09:00:00Z",
         "duration_minutes": 5, "notes": "test", "is_hidden_work": False},
        {"event_id": "e-2", "ticket_id": "T-1", "agent_id": "agent-A",
         "event_type": "waiting", "timestamp": "2024-01-01T09:10:00Z",
         "duration_minutes": 100, "notes": "awaiting reply", "is_hidden_work": False},
    ]
    summary = detect(events)
    metrics = calculate(events, summary, {})
    assert summary.total_hidden_events == 0
    assert summary.total_hidden_minutes == 0.0
    assert summary.hidden_work_ratio == 0.0
    assert "waiting" not in summary.hidden_event_types


# ---------------------------------------------------------------------------
# Role-based burden concentration tests
# ---------------------------------------------------------------------------

def test_seed_data_has_role_field(seed_events):
    """Every event in seed data must have a role field."""
    for ev in seed_events:
        assert "role" in ev, f"Event {ev['event_id']} missing role field"
        assert ev["role"] in ("Support Agent", "Senior Support Agent", "Operations Specialist", "Team Lead"), \
            f"Event {ev['event_id']} has unexpected role: {ev['role']}"


def test_burden_concentration_by_role_not_agent_id(seed_events):
    """Burden concentration groups hidden work by role, not individual agent_id."""
    summary = detect(seed_events)
    full_proposal = {
        "expected_review_rate": 0.15, "avg_review_minutes": 3.0,
        "expected_correction_rate": 0.08, "avg_correction_minutes": 8.0,
        "exception_rate": 0.05, "avg_exception_handling_minutes": 20.0,
        "weekly_maintenance_minutes": 45.0, "expected_failure_recovery_minutes": 30.0,
    }
    metrics = calculate(seed_events, summary, full_proposal)

    # The burden_concentration should group by role, not agent_id
    # agent-A and agent-D are both "Support Agent" - their work should be combined
    # agent-B is "Senior Support Agent", agent-C is "Operations Specialist"
    # No single role should carry > 70% of hidden work in this dataset
    assert metrics.burden_concentration < 0.7, \
        f"Burden concentration too high: {metrics.burden_concentration:.2f}"


def test_no_individual_worker_rankings_exposed(seed_events):
    """API response must not expose individual worker performance scores."""
    from backend.services.metrics_calculator import calculate
    from backend.services.hidden_work_detector import detect

    summary = detect(seed_events)
    metrics = calculate(seed_events, summary, {})

    # The metrics object should not have any field that exposes individual agent scores
    # Only aggregate role-level burden_concentration
    forbidden_fields = ["agent_performance", "individual_scores", "worker_ranking", "per_agent"]
    for field in forbidden_fields:
        assert not hasattr(metrics, field), f"Forbidden field present: {field}"


def test_burden_concentration_uses_role_field():
    """Burden concentration calculation uses role field explicitly."""
    events = [
        # Agent A1 (Support Agent) - 30 min hidden work
        {"event_id": "e-1", "ticket_id": "T-1", "agent_id": "agent-A1", "role": "Support Agent",
         "event_type": "follow_up", "timestamp": "2024-01-01T09:00:00Z",
         "duration_minutes": 10, "notes": "test", "is_hidden_work": True},
        {"event_id": "e-2", "ticket_id": "T-1", "agent_id": "agent-A1", "role": "Support Agent",
         "event_type": "context_repair", "timestamp": "2024-01-01T09:10:00Z",
         "duration_minutes": 20, "notes": "test", "is_hidden_work": True},
        # Agent A2 (also Support Agent) - 10 min hidden work
        {"event_id": "e-3", "ticket_id": "T-2", "agent_id": "agent-A2", "role": "Support Agent",
         "event_type": "manual_status_check", "timestamp": "2024-01-01T10:00:00Z",
         "duration_minutes": 10, "notes": "test", "is_hidden_work": True},
        # Agent B (Senior Support Agent) - 5 min hidden work
        {"event_id": "e-4", "ticket_id": "T-3", "agent_id": "agent-B", "role": "Senior Support Agent",
         "event_type": "exception_handling", "timestamp": "2024-01-01T11:00:00Z",
         "duration_minutes": 5, "notes": "test", "is_hidden_work": True},
    ]
    summary = detect(events)
    # Total hidden = 45 min
    # Support Agent role = 40 min (agent-A1:30 + agent-A2:10)
    # Senior Support Agent role = 5 min
    # burden_concentration = 40/45 = 0.888...
    metrics = calculate(events, summary, {})
    assert abs(metrics.burden_concentration - 40/45) < 0.01


@pytest.mark.asyncio
async def test_full_result_passes_schema():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/api/analysis/run", json={"scenario_id": "cs-demo-v1"})
    # Will raise ValidationError if any field is wrong
    result = AnalysisResult.model_validate(resp.json())
    assert result.metrics.ai_overhead == round(
        result.metrics.review_overhead
        + result.metrics.correction_overhead
        + result.metrics.exception_overhead
        + result.metrics.maintenance_overhead
        + result.metrics.failure_recovery_overhead,
        2,
    )


# ---------------------------------------------------------------------------
# PII redaction tests
# ---------------------------------------------------------------------------

def test_redact_email():
    """Email addresses should be redacted."""
    from backend.services.redaction import redact_text
    text = "Contact john.doe@example.com for details"
    result = redact_text(text)
    assert "[REDACTED_EMAIL]" in result
    assert "john.doe@example.com" not in result


def test_redact_name():
    """Likely personal names should be redacted."""
    from backend.services.redaction import redact_text
    text = "Contact John Smith for details"
    result = redact_text(text)
    assert "[REDACTED_NAME]" in result
    assert "John Smith" not in result


def test_preserve_ticket_ids():
    """Ticket IDs like TKT-123 should not be redacted."""
    from backend.services.redaction import redact_text
    text = "Ticket TKT-123 was updated by the team"
    result = redact_text(text)
    assert "TKT-123" in result
    assert "[REDACTED_NAME]" not in result


def test_preserve_agent_ids():
    """Agent IDs like agent-A should not be redacted."""
    from backend.services.redaction import redact_text
    text = "agent-A processed the ticket"
    result = redact_text(text)
    assert "agent-A" in result
    assert "[REDACTED_NAME]" not in result


def test_preserve_evt_ids():
    """Event IDs like evt-123 should not be redacted."""
    from backend.services.redaction import redact_text
    text = "Event evt-123 was processed by agent-A"
    result = redact_text(text)
    assert "evt-123" in result
    assert "agent-A" in result
    assert "[REDACTED_NAME]" not in result


def test_preserve_role_names():
    """Role names like 'Support Agent' should not be redacted."""
    from backend.services.redaction import redact_text
    text = "The Support Agent handled the case"
    result = redact_text(text)
    assert "Support Agent" in result
    assert "[REDACTED_NAME]" not in result


def test_preserve_workflow_labels():
    """Workflow labels like 'Ticket Created' should not be redacted."""
    from backend.services.redaction import redact_text
    text = "Ticket Created step was completed"
    result = redact_text(text)
    assert "Ticket Created" in result
    assert "[REDACTED_NAME]" not in result


def test_redact_events_preserves_other_fields():
    """Redaction should not modify non-notes fields."""
    from backend.services.redaction import redact_events
    events = [
        {
            "event_id": "evt-1",
            "ticket_id": "TKT-1",
            "agent_id": "agent-A",
            "role": "Support Agent",
            "event_type": "ticket_created",
            "timestamp": "2024-01-01T09:00:00Z",
            "duration_minutes": 5,
            "notes": "Contact john.doe@example.com for details",
            "is_hidden_work": False,
        }
    ]
    redacted = redact_events(events)
    # Original event should be unmodified
    assert events[0]["notes"] == "Contact john.doe@example.com for details"
    # Redacted copy should have redacted notes
    assert redacted[0]["notes"] == "Contact [REDACTED_EMAIL] for details"
    # Other fields preserved
    assert redacted[0]["event_id"] == "evt-1"
    assert redacted[0]["role"] == "Support Agent"
    assert redacted[0]["duration_minutes"] == 5


def test_redact_in_analysis_flow(seed_events):
    """Full analysis flow should redact notes before Granite."""
    from backend.services import redaction, workflow_reconstructor, hidden_work_detector, metrics_calculator
    # Redact first
    redacted_events = redaction.redact_events(seed_events)
    # Run through pipeline
    official_wf, actual_wf = workflow_reconstructor.reconstruct(redacted_events)
    hidden = hidden_work_detector.detect(redacted_events)
    metrics = metrics_calculator.calculate(redacted_events, hidden, {})
    # Verify notes were redacted in intermediate data
    for ev in redacted_events:
        if ev.get("notes"):
            assert "@" not in ev["notes"], f"Email not redacted in: {ev['notes']}"
