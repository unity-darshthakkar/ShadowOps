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

    result = analyse(metrics, summary, settings)
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
