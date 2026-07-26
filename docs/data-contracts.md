# docs/data-contracts.md — ShadowOps Data Contracts

## 1. Seed Event Schema (JSON input)

File: `backend/data/seed_scenarios.json`

```json
{
  "scenario_id": "cs-demo-v1",
  "name": "Customer Support Ticket Lifecycle",
  "description": "Synthetic 30-day sample of support ticket activity.",
  "official_workflow": [
    "ticket_created", "assigned", "first_response", "resolution", "closed"
  ],
  "automation_proposal": {
    "expected_review_rate": 0.15,
    "avg_review_minutes": 3.0,
    "expected_correction_rate": 0.08,
    "avg_correction_minutes": 8.0,
    "exception_rate": 0.05,
    "avg_exception_handling_minutes": 20.0,
    "weekly_maintenance_minutes": 45.0,
    "expected_failure_recovery_minutes": 30.0
  },
  "events": [
    {
      "event_id": "evt-001",
      "ticket_id": "TKT-1001",
      "agent_id": "agent-A",
      "event_type": "ticket_created",
      "timestamp": "2024-06-01T09:00:00Z",
      "duration_minutes": 2,
      "notes": "Customer reports login failure.",
      "is_hidden_work": false
    },
    {
      "event_id": "evt-002",
      "ticket_id": "TKT-1001",
      "agent_id": "agent-A",
      "event_type": "manual_status_check",
      "timestamp": "2024-06-01T11:30:00Z",
      "duration_minutes": 3,
      "notes": "Agent manually checked CRM for ticket status.",
      "is_hidden_work": true
    }
  ]
}
```

**Hidden-work event types — exactly 8, canonical names** (always tagged `is_hidden_work: true` in seed data):
`follow_up`, `manual_status_check`, `context_repair`, `duplicate_entry`,
`rework`, `exception_handling`, `escalation`, `manual_reconciliation`

> `waiting` events are permitted in seed data to record workflow delay gaps but
> **must not** appear in `HIDDEN_WORK_TYPES` and are never counted toward hidden-work metrics.

### AutomationProposal fields

| Field | Meaning |
|---|---|
| `expected_review_rate` | Fraction of AI outputs a human reviews (0.0–1.0) |
| `avg_review_minutes` | Average time per human review in minutes |
| `expected_correction_rate` | Fraction of AI outputs requiring human correction |
| `avg_correction_minutes` | Average time per correction in minutes |
| `exception_rate` | Fraction of tickets triggering manual exception handling |
| `avg_exception_handling_minutes` | Average time per exception in minutes |
| `weekly_maintenance_minutes` | AI system maintenance time per week |
| `expected_failure_recovery_minutes` | Time to recover from one AI failure event |

If any field is absent from the scenario's `automation_proposal`, the calculator
falls back to a documented default (see §3). All assumptions must be surfaced in
the `AnalysisMetrics.overhead_assumptions` list and labelled in the UI.

---

## 2. Pydantic Schemas (backend/models/schemas.py)

### AnalysisRequest
```python
class AnalysisRequest(BaseModel):
    scenario_id: str
```

### WorkflowStep
```python
class WorkflowStep(BaseModel):
    step_id: str
    event_type: str
    label: str
    avg_duration_minutes: float
    occurrence_count: int
    is_hidden_work: bool
    is_in_official: bool
```

### HiddenWorkEvidence
```python
class HiddenWorkEvidence(BaseModel):
    event_id: str                     # raw event ID from seed data
    ticket_id: str
    event_type: str
    duration_minutes: float
    notes: str
    description: str                  # human-readable sentence
```

### HiddenWorkSummary
```python
class HiddenWorkSummary(BaseModel):
    total_hidden_events: int
    total_hidden_minutes: float
    hidden_work_ratio: float          # 0.0–1.0
    hidden_event_types: list[str]
    evidence: list[HiddenWorkEvidence]   # one entry per hidden-work event; includes raw event_id
```

### OverheadAssumption
```python
class OverheadAssumption(BaseModel):
    field: str       # e.g. "expected_review_rate"
    value: float
    source: Literal["proposal", "default"]   # "default" triggers UI assumption label
    default_value: float | None              # populated only when source == "default"
```

### AnalysisMetrics
```python
class AnalysisMetrics(BaseModel):
    # All durations in minutes
    official_total_minutes: float
    actual_total_minutes: float
    ai_automated_total_minutes: float
    hybrid_total_minutes: float

    hidden_work_ratio: float          # hidden_minutes / actual_total_minutes
    gross_time_saved: float           # actual - ai_automated
    ai_overhead: float                # computed from explicit proposal fields (see §3)
    ai_tax: float                     # ai_overhead / gross_time_saved  (0.0–1.0)
    net_time_saved: float             # gross_time_saved - ai_overhead

    burden_concentration: float       # fraction of hidden work on single role  (0.0–1.0)
    automation_readiness: float       # 0.0–1.0 composite score
    automation_readiness_label: str   # "Low" | "Medium" | "High"

    skill_loss_risk: str              # "Low" | "Medium" | "High"
    missing_fallback_count: int       # number of steps with no fallback
    overhead_assumptions: list[OverheadAssumption]  # documents each input; flags defaults
```

### GraniteOutput
```python
class GraniteOutput(BaseModel):
    workflow_gap_narrative: str
    hidden_work_narrative: str
    redesign_recommendations: list[str]   # 3–7 bullet points
    guardrails: list[GuardrailItem]
    safer_workflow_steps: list[SaferStep]
    provider: Literal["live_granite", "cached_demo"]
```

### GuardrailItem
```python
class GuardrailItem(BaseModel):
    id: str
    label: str
    type: Literal["human_approval", "confidence_threshold",
                  "exception_routing", "manual_fallback",
                  "skill_preservation", "audit_trail"]
    description: str
```

### SaferStep
```python
class SaferStep(BaseModel):
    step_id: str
    label: str
    executor: Literal["human", "ai", "hybrid"]
    requires_approval: bool
    fallback_procedure: str | None
    confidence_threshold: float | None   # 0.0–1.0, None if human-only
```

### AnalysisResult (top-level response)
```python
class AnalysisResult(BaseModel):
    analysis_id: str
    scenario_id: str
    status: Literal["pending", "running", "complete", "error"]
    created_at: datetime
    completed_at: datetime | None

    official_workflow: list[WorkflowStep]
    actual_workflow: list[WorkflowStep]
    hidden_work: HiddenWorkSummary
    metrics: AnalysisMetrics
    granite_output: GraniteOutput | None

    provider_status: Literal["live_granite", "cached_demo"]
    disclaimer: str    # always present, legal/ethical notice
```

### HealthResponse
```python
class HealthResponse(BaseModel):
    status: str           # "ok"
    provider: Literal["live_granite", "cached_demo"]
    version: str
```

---

## 3. Deterministic Scoring Formulas

All implemented in `backend/services/metrics_calculator.py`.
All inputs come from event data and the `automation_proposal` block, never from LLM output.

### AI Overhead — explicit formula

```
routine_events          = events NOT in HIDDEN_WORK_TYPES
routine_count           = len(routine_events)

review_overhead         = routine_count × expected_review_rate × avg_review_minutes
correction_overhead     = routine_count × expected_correction_rate × avg_correction_minutes
exception_overhead      = routine_count × exception_rate × avg_exception_handling_minutes

# weekly_maintenance_minutes and failure_recovery are period costs;
# normalise to the scenario window (days in dataset / 7 weeks):
scenario_weeks          = (max_timestamp - min_timestamp).days / 7
maintenance_overhead    = weekly_maintenance_minutes × scenario_weeks
failure_overhead        = expected_failure_recovery_minutes × scenario_weeks × exception_rate

ai_overhead             = review_overhead + correction_overhead + exception_overhead
                        + maintenance_overhead + failure_overhead
```

**Fallback defaults** (used when `automation_proposal` field is absent; each triggers a
`source: "default"` entry in `overhead_assumptions`):

| Field | Default |
|---|---|
| `expected_review_rate` | 0.15 |
| `avg_review_minutes` | 3.0 |
| `expected_correction_rate` | 0.08 |
| `avg_correction_minutes` | 8.0 |
| `exception_rate` | 0.05 |
| `avg_exception_handling_minutes` | 20.0 |
| `weekly_maintenance_minutes` | 45.0 |
| `expected_failure_recovery_minutes` | 30.0 |

### Remaining formulas

```
hidden_work_ratio       = sum(duration of hidden events) / sum(duration of all actual events)

gross_time_saved        = actual_total_minutes - ai_automated_total_minutes
                          # ai_automated = sum of routine event durations × 0.70 (AI 30% faster)

ai_tax                  = ai_overhead / gross_time_saved          # clamp to [0, 1]

net_time_saved          = gross_time_saved - ai_overhead          # may be negative

burden_concentration    = max_hidden_minutes_by_role / total_hidden_minutes
                          # 1.0 means one role carries all hidden work

automation_readiness    = weighted average of:
                            structured_ratio   * 0.40   # % of steps with non-empty notes
                            low_exception_rate * 0.30   # 1 - (exception_handling events / total)
                            low_hidden_ratio   * 0.30   # 1 - hidden_work_ratio
                          # result clamped to [0, 1]

automation_readiness_label:
    >= 0.7  → "High"
    >= 0.4  → "Medium"
    else    → "Low"

skill_loss_risk:
    burden_concentration >= 0.7 AND automation_readiness >= 0.7  → "High"
    burden_concentration >= 0.5 OR  automation_readiness >= 0.5  → "Medium"
    else                                                          → "Low"

missing_fallback_count  = count of safer_workflow_steps where
                          executor != "human" AND fallback_procedure is None
```

---

## 4. IBM Granite Prompt Contract

Prompt template (built in `backend/services/granite_analyser.py`):

```
You are a workflow design expert. Analyse the following workflow data and respond ONLY
with valid JSON matching the schema below. Do not include explanations outside the JSON.

WORKFLOW DATA:
- Official steps: {official_step_labels}
- Actual steps (including hidden work): {actual_step_labels}
- Hidden work ratio: {hidden_work_ratio:.0%}
- Net time saved with AI: {net_time_saved:.0f} minutes
- Automation readiness: {automation_readiness_label}
- Skill-loss risk: {skill_loss_risk}

RESPOND WITH JSON:
{
  "workflow_gap_narrative": "<2–3 sentence description of gaps>",
  "hidden_work_narrative": "<2–3 sentence description of hidden work patterns>",
  "redesign_recommendations": ["<recommendation 1>", ...],  // 3–7 items
  "guardrails": [
    {
      "id": "<slug>",
      "label": "<short label>",
      "type": "<one of: human_approval | confidence_threshold | exception_routing |
                          manual_fallback | skill_preservation | audit_trail>",
      "description": "<1 sentence>"
    }
  ],
  "safer_workflow_steps": [
    {
      "step_id": "<slug>",
      "label": "<step name>",
      "executor": "<human | ai | hybrid>",
      "requires_approval": true,
      "fallback_procedure": "<1 sentence or null>",
      "confidence_threshold": 0.85
    }
  ]
}
```

Model: read from `WATSONX_MODEL_ID` env var (default `ibm/granite-4-h-small`)
Parameters: `max_new_tokens=1200`, `temperature=0.2`, `top_p=0.9`

---

## 5. Frontend TypeScript Types (frontend/src/types/api.ts)

TypeScript interfaces mirror the Pydantic schemas 1:1.
All enums use string literal unions, not TypeScript `enum` keyword.

```typescript
export type ProviderStatus = "live_granite" | "cached_demo";
export type StepExecutor = "human" | "ai" | "hybrid";
export type GuardrailType =
  | "human_approval" | "confidence_threshold" | "exception_routing"
  | "manual_fallback" | "skill_preservation" | "audit_trail";
export type AnalysisStatus = "pending" | "running" | "complete" | "error";
export type ReadinessLabel = "Low" | "Medium" | "High";
export type RiskLabel = "Low" | "Medium" | "High";

export interface AnalysisMetrics { ... }   // mirror of Pydantic schema above
export interface AnalysisResult { ... }    // mirror of Pydantic schema above
```

---

## 6. Environment Variables (.env.example)

```
# IBM watsonx.ai credentials
# Leave WATSONX_API_KEY blank to use cached demo provider
WATSONX_API_KEY=
WATSONX_URL=https://us-south.ml.cloud.ibm.com
WATSONX_PROJECT_ID=
WATSONX_MODEL_ID=ibm/granite-4-h-small

# App
SHADOWOPS_ENV=development
DATABASE_URL=sqlite:///./shadowops.db
CORS_ORIGINS=http://localhost:5173
```

`WATSONX_MODEL_ID` can be changed to any Granite model available on your watsonx account
without touching code. The backend reads it via `pydantic-settings` at startup.
