# docs/architecture.md — ShadowOps System Architecture

## High-Level Flow

```
Browser (React/TS/Vite)
        │
        │ HTTP/JSON
        ▼
FastAPI Application (Python 3.11)
  ├── /api/scenarios        ← static seed data loader
  ├── /api/analysis/run     ← orchestration entry point
  │       │
  │       ├── WorkflowReconstructor   (deterministic)
  │       ├── HiddenWorkDetector      (deterministic)
  │       ├── MetricsCalculator       (deterministic)
  │       └── GraniteAnalyser         (AI layer)
  │               │
  │               └──► watsonx.ai  OR  CachedDemoProvider
  │
  └── Static files (React build served here)
        │
        SQLite (SQLAlchemy 2.x)
```

---

## Directory Structure

```
shadowops/
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── PROJECT_SPEC.md
├── docs/
│   ├── architecture.md
│   ├── bob-implementation-plan.md
│   ├── data-contracts.md
│   └── acceptance-criteria.md
│
├── backend/
│   ├── main.py                        # FastAPI app factory
│   ├── config.py                      # Settings via pydantic-settings
│   ├── database.py                    # SQLAlchemy engine + session factory
│   ├── models/
│   │   ├── db_models.py               # SQLAlchemy ORM models
│   │   └── schemas.py                 # Pydantic request/response schemas
│   ├── routers/
│   │   ├── health.py
│   │   ├── scenarios.py
│   │   └── analysis.py
│   ├── services/
│   │   ├── workflow_reconstructor.py  # Builds actual workflow from events
│   │   ├── hidden_work_detector.py    # Tags hidden-work event types
│   │   ├── metrics_calculator.py      # All deterministic formulas
│   │   ├── granite_analyser.py        # Prompt builder + IBM Granite caller
│   │   └── cached_provider.py        # Fallback demo responses
│   ├── data/
│   │   └── seed_scenarios.json        # Synthetic customer-support events
│   └── tests/
│       ├── test_metrics.py
│       ├── test_hidden_work.py
│       ├── test_reconstructor.py
│       └── test_api.py
│
└── frontend/
    ├── index.html
    ├── vite.config.ts
    ├── tsconfig.json
    ├── package.json
    ├── tailwind.config.ts
    ├── src/
    │   ├── main.tsx
    │   ├── App.tsx
    │   ├── api/
    │   │   └── client.ts              # Typed fetch wrapper
    │   ├── pages/
    │   │   ├── StageSetup.tsx           # Stage 1
    │   │   ├── StageReality.tsx         # Stage 2 — diff + hidden work + metrics
    │   │   ├── StageAIImpact.tsx        # Stage 3 — time comparison + AI Tax + overhead
    │   │   └── StageRedesign.tsx        # Stage 4 — safer steps + guardrails + export
    │   ├── components/
    │   │   ├── ProviderBanner.tsx      # Live vs Cached badge (rendered in layout on all stages)
    │   │   ├── WorkflowDiff.tsx        # Official vs actual side-by-side
    │   │   ├── HiddenWorkTable.tsx     # Evidence rows with raw event_ids
    │   │   ├── MetricsCard.tsx
    │   │   ├── OverheadBreakdown.tsx   # Shows explicit overhead params + assumption labels
    │   │   └── ReportExport.tsx
    │   └── types/
    │       └── api.ts                 # TypeScript mirrors of Pydantic schemas
    └── tests/
        └── MetricsCard.test.tsx
```

---

## Layer Responsibilities

### Deterministic Layer (Python)
`WorkflowReconstructor`, `HiddenWorkDetector`, `MetricsCalculator` — no LLM calls.
These produce the numbers. They are pure functions: same input → same output, always.

### AI Layer (Python)
`GraniteAnalyser` builds a structured prompt from the deterministic outputs and calls
IBM Granite for:
- Narrative descriptions of workflow gaps
- Redesign recommendations
- Risk labels (not scores — scores come from MetricsCalculator)

`GraniteAnalyser` always attempts a live call when `WATSONX_API_KEY`, `WATSONX_URL`,
and `WATSONX_PROJECT_ID` are all non-empty. The model ID is read from `WATSONX_MODEL_ID`
(default `ibm/granite-4-h-small`). `CachedDemoProvider` is used when credentials are
absent **or** when the live call fails (JSON parse error, validation error, SDK exception).

### Presentation Layer (React)
Reads from the analysis result JSON. All numbers displayed come from the backend.
The `ProviderBanner` component reads `provider_status` from `/api/demo/provider-status`
and shows "🟢 Live IBM Granite" or "🟡 Cached Demo Data" on every page.

---

## Data Flow for a Full Analysis

```
1. User selects scenario on /
2. POST /api/analysis/run { scenario_id: "cs-demo-v1" }
3. Backend loads seed events from seed_scenarios.json
4. WorkflowReconstructor builds timeline of actual steps
5. HiddenWorkDetector tags hidden-work events
6. MetricsCalculator produces AnalysisMetrics
7. GraniteAnalyser (or CachedDemoProvider) produces GraniteOutput
8. AnalysisResult assembled and written to SQLite
9. Frontend polls GET /api/analysis/{id} until status == "complete"
10. React Router navigates user through 4 stages
11. Stage 4 /redesign section renders full summary + triggers JSON export
```

---

## Docker Build

Multi-stage Dockerfile:
1. **Stage 1 (node:20-slim):** `cd frontend && npm ci && npm run build` → `/app/frontend/dist`
2. **Stage 2 (python:3.11-slim):** Copy built frontend + Python source, install deps,
   run `uvicorn backend.main:app`. FastAPI mounts `/app/frontend/dist` as static files at `/`.
