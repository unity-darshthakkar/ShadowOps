# docs/bob-implementation-plan.md — ShadowOps Build Plan

## Timeline Overview

| Phase | Name | Day |
|---|---|---|
| 0 | Repo scaffold & tooling | Day 1 AM |
| 1 | Data layer & seed events | Day 1 AM |
| 2 | Deterministic analysis engine | Day 1 AM–PM |
| 3 | AI layer & cached provider | Day 1 PM |
| 4 | FastAPI routes & integration | Day 1 PM |
| 5 | React frontend (all pages) | Day 2 AM–PM |
| 6 | Docker, polish, export | Day 2 PM |

---

## Phase 0 — Repo Scaffold & Tooling

**Intent:** Create the project skeleton so every later phase has a stable home.

**Expected Outcomes:**
- Repository structure matches `docs/architecture.md`
- Backend starts with `uvicorn backend.main:app --reload`
- Frontend dev server starts with `npm run dev`
- Both hot-reload independently

**Files Created:**
```
.env.example
.gitignore  (already exists — no change)
backend/
  main.py
  config.py
  database.py
  models/__init__.py
  models/db_models.py
  models/schemas.py
  routers/__init__.py
  services/__init__.py
  data/
  tests/__init__.py
frontend/
  package.json
  vite.config.ts
  tsconfig.json
  tailwind.config.ts
  index.html
  src/main.tsx
  src/App.tsx
  src/types/api.ts
  src/api/client.ts
Dockerfile
docker-compose.yml
requirements.txt
```

**Todo List:**
1. Create `backend/main.py` — FastAPI app with CORS middleware, static file mount placeholder, include routers
2. Create `backend/config.py` — `pydantic-settings` class reading `.env`; `watsonx_api_key`, `watsonx_url`, `watsonx_project_id`, `watsonx_model_id` (default `ibm/granite-4-h-small`), `database_url`, `cors_origins`
3. Create `backend/database.py` — SQLAlchemy `create_engine`, `SessionLocal`, `Base`, `get_db` dependency
4. Create `backend/models/db_models.py` — `AnalysisRun` ORM model (id, scenario_id, status, created_at, completed_at, result_json)
5. Create `backend/models/schemas.py` — all Pydantic v2 schemas from `docs/data-contracts.md` section 2
6. Create `frontend/package.json` with React 18, TypeScript, Vite, Tailwind, React Router v6
7. Create `frontend/src/types/api.ts` — TypeScript interfaces mirroring all Pydantic schemas
8. Create `frontend/src/api/client.ts` — typed `apiFetch<T>` wrapper around `fetch`
9. Create `requirements.txt` with pinned versions: fastapi, uvicorn, pydantic, pydantic-settings, sqlalchemy, ibm-watsonx-ai, pytest, pytest-asyncio, httpx

**Relevant Context:**
- Schemas defined in full in `docs/data-contracts.md` §2
- Env vars defined in `docs/data-contracts.md` §6
- No auth middleware needed

---

## Phase 1 — Data Layer & Seed Events

**Intent:** Provide the synthetic customer-support dataset that all analysis runs against.

**Expected Outcomes:**
- `GET /api/scenarios` returns the demo scenario with metadata
- Seed JSON loads without errors
- `GET /api/health` returns `200 OK`

**Files Created:**
```
backend/data/seed_scenarios.json
backend/routers/health.py
backend/routers/scenarios.py
backend/tests/test_api.py  (health + scenarios tests)
```

**Todo List:**
1. Create `backend/data/seed_scenarios.json` with `cs-demo-v1` scenario
   - Minimum 25 events across 5 tickets
   - Include the `automation_proposal` block with all 8 explicit overhead fields (see `docs/data-contracts.md` §1)
   - At least one event of every canonical hidden-work type:
     `follow_up`, `manual_status_check`, `context_repair`, `duplicate_entry`,
     `rework`, `exception_handling`, `escalation`, `manual_reconciliation`
   - Include at least one `waiting` event to verify it is NOT tagged `is_hidden_work: true`
   - Ground-truth `is_hidden_work` labels set correctly on all hidden-work events
   - Realistic timestamps spanning 10 simulated days
   - Mix of `duration_minutes`: quick (1–3) and slow (10–30)
2. Create `backend/routers/health.py` — `GET /api/health` → `HealthResponse`
   - `provider` determined by whether `settings.watsonx_api_key` is truthy
3. Create `backend/routers/scenarios.py` — `GET /api/scenarios` reads seed JSON, returns list
4. Register both routers in `backend/main.py` with prefix `/api`
5. Write `backend/tests/test_api.py` — test health endpoint returns 200, scenarios returns list with `cs-demo-v1`

**Relevant Context:**
- `HealthResponse` schema in `docs/data-contracts.md` §2
- Seed event schema in `docs/data-contracts.md` §1
- `is_hidden_work` field is demo ground-truth; detector will also compute this algorithmically

---

## Phase 2 — Deterministic Analysis Engine

**Intent:** Build the pure-Python calculation layer. No LLM calls. All formulas from `docs/data-contracts.md` §3.

**Expected Outcomes:**
- All 7 metrics computed correctly from seed data
- Exactly 8 canonical hidden-work types detected; `waiting` excluded
- AI overhead computed from explicit `automation_proposal` fields; fallbacks documented in `overhead_assumptions`
- Tests pass deterministically (same input → same output always)

**Files Created:**
```
backend/services/workflow_reconstructor.py
backend/services/hidden_work_detector.py
backend/services/metrics_calculator.py
backend/tests/test_metrics.py
backend/tests/test_hidden_work.py
backend/tests/test_reconstructor.py
```

**Todo List:**
1. Create `backend/services/workflow_reconstructor.py`
   - Input: raw event list from seed JSON
   - Group events by `ticket_id`, sort each group by `timestamp`
   - Produce `list[WorkflowStep]` for both `official_workflow` and `actual_workflow`
   - `actual_workflow` includes hidden-work steps; `official_workflow` filters to only `is_in_official` types
   - Deduplicate step types; aggregate `avg_duration_minutes` and `occurrence_count`
2. Create `backend/services/hidden_work_detector.py`
   - `HIDDEN_WORK_TYPES = frozenset({"follow_up", "manual_status_check", "context_repair",
     "duplicate_entry", "rework", "exception_handling", "escalation", "manual_reconciliation"})`
   - `waiting` must NOT be in this set
   - `detect(events) -> HiddenWorkSummary`
   - Build `evidence: list[HiddenWorkEvidence]` — one entry per hidden-work event; each entry
     carries the raw `event_id`, `ticket_id`, `event_type`, `duration_minutes`, `notes`,
     and a generated `description` sentence
3. Create `backend/services/metrics_calculator.py`
   - `calculate(events, hidden_summary, proposal: dict) -> AnalysisMetrics`
   - Implement every formula exactly as written in `docs/data-contracts.md` §3
   - For each of the 8 `automation_proposal` fields: read from `proposal` dict if present
     (source `"proposal"`), else use the documented default (source `"default"`)
   - Build `overhead_assumptions: list[OverheadAssumption]` — one entry per field
   - For `ai_automated_total_minutes`: sum durations of routine events × 0.70
   - For `hybrid_total_minutes`: `ai_automated_total_minutes` × 1.15
   - For `ai_overhead`: use the explicit 5-component formula from `docs/data-contracts.md` §3
   - For `structured_ratio`: count events with non-empty `notes` / total
   - For `low_exception_rate`: 1 - (count of `exception_handling` events / total events)
4. Write `backend/tests/test_metrics.py`:
   - Test `hidden_work_ratio` formula with known fixture
   - Test `ai_tax` clamping at both extremes
   - Test `net_time_saved` can be negative
   - Test all three `automation_readiness_label` branches
   - Test all three `skill_loss_risk` branches
   - Test `ai_overhead` with full `automation_proposal` matches manual calculation
   - Test `ai_overhead` with missing fields uses documented defaults and flags `source: "default"`
5. Write `backend/tests/test_hidden_work.py`:
   - Fixture with one event of each of the 8 canonical types
   - Assert all 8 types appear in `hidden_event_types`
   - Assert `waiting` events are present in fixture but absent from `hidden_event_types`
   - Assert each evidence entry carries `event_id`, `ticket_id`, `event_type`, `duration_minutes`
6. Write `backend/tests/test_reconstructor.py`:
   - Assert events sorted by timestamp within each ticket
   - Assert official workflow excludes hidden-work types

**Relevant Context:**
- Formulas in `docs/data-contracts.md` §3
- `WorkflowStep`, `HiddenWorkSummary`, `AnalysisMetrics` schemas in §2

---

## Phase 3 — AI Layer & Cached Provider

**Intent:** Integrate IBM Granite via watsonx.ai with a real call path; build a drop-in cached fallback.

**Expected Outcomes:**
- With no credentials: `CachedDemoProvider` returns valid `GraniteOutput`
- With credentials: live call attempted using model from `WATSONX_MODEL_ID`
- Prompt contains all required fields from `docs/data-contracts.md` §4
- Any failure (JSON error, validation error, SDK exception) falls back to cached provider with warning log

**Files Created:**
```
backend/services/granite_analyser.py
backend/services/cached_provider.py
backend/tests/test_granite.py  (prompt + fallback tests)
```

**Todo List:**
1. Create `backend/services/cached_provider.py`
   - Hard-coded `GraniteOutput` that is realistic for the `cs-demo-v1` scenario
   - At least 5 `redesign_recommendations`, 6 `guardrails` (at least one of each `GuardrailType`), 6 `safer_workflow_steps`
   - `provider` field = `"cached_demo"`
2. Create `backend/services/granite_analyser.py`
   - `build_prompt(metrics: AnalysisMetrics, hidden: HiddenWorkSummary) -> str`
     - Use template from `docs/data-contracts.md` §4
     - Format `hidden_work_ratio` as percentage, `net_time_saved` as integer minutes
   - `call_granite(prompt: str, settings: Settings) -> GraniteOutput`
     - Instantiate `ibm_watsonx_ai.foundation_models.ModelInference` with:
       - `model_id = settings.watsonx_model_id`
       - `credentials = {"url": settings.watsonx_url, "apikey": settings.watsonx_api_key}`
       - `project_id = settings.watsonx_project_id`
     - Call `.generate_text(prompt=prompt, params={"max_new_tokens": 1200, "temperature": 0.2, "top_p": 0.9})`
     - Extract JSON from response (strip markdown fences if present)
     - Validate with `GraniteOutput.model_validate(json.loads(raw_json))`
     - On `JSONDecodeError`: log warning `"Granite response was not valid JSON; using cached demo"`, return `CachedDemoProvider().get()`
     - On `ValidationError`: log warning `"Granite response failed schema validation; using cached demo"`, return `CachedDemoProvider().get()`
     - On any `Exception` from the SDK: log warning `"Granite SDK error; using cached demo"`, return `CachedDemoProvider().get()`
   - `analyse(metrics, hidden, settings) -> GraniteOutput`
     - If any of `watsonx_api_key`, `watsonx_url`, `watsonx_project_id` is falsy → return `CachedDemoProvider().get()`
     - Else call `call_granite(...)`
3. Write `backend/tests/test_granite.py`:
   - Test `build_prompt` output contains `hidden_work_ratio`, `net_time_saved`, `automation_readiness_label`
   - Test `analyse` returns `cached_demo` when any credential is absent
   - Test `CachedDemoProvider` output passes `GraniteOutput` Pydantic validation
   - Test `call_granite` falls back to cached on `JSONDecodeError` (mock SDK to raise it)
   - Test `call_granite` falls back to cached on `ValidationError` (mock SDK to return invalid JSON)
   - Test `call_granite` falls back to cached on generic SDK `Exception`
   - Test that `call_granite` passes `settings.watsonx_model_id` to `ModelInference` (mock SDK, inspect call args)

**Relevant Context:**
- Model ID: read from `settings.watsonx_model_id` — default `ibm/granite-4-h-small`
- Parameters: `max_new_tokens=1200`, `temperature=0.2`, `top_p=0.9`
- Prompt template: `docs/data-contracts.md` §4

---

## Phase 4 — FastAPI Routes & Integration

**Intent:** Wire all services into the API. The backend is fully functional after this phase.

**Expected Outcomes:**
- `POST /api/analysis/run` returns complete `AnalysisResult` for `cs-demo-v1`
- Analysis result is persisted to SQLite and retrievable by ID
- Preflight report endpoint returns valid JSON

**Files Created:**
```
backend/routers/analysis.py
backend/tests/test_api.py  (extended with analysis tests)
```

**Todo List:**
1. Create `backend/routers/analysis.py`
   - `POST /api/analysis/run` — body: `AnalysisRequest`
     1. Load events from seed JSON by `scenario_id`
     2. Run `WorkflowReconstructor.reconstruct(events)`
     3. Run `HiddenWorkDetector.detect(events)`
     4. Run `MetricsCalculator.calculate(events, hidden_summary)`
     5. Run `GraniteAnalyser.analyse(metrics, hidden_summary, settings)`
     6. Assemble `AnalysisResult` with `disclaimer` text (fixed string, see below)
     7. Persist to SQLite `AnalysisRun` row as `result_json = result.model_dump_json()`
     8. Return full `AnalysisResult`
   - `GET /api/analysis/{id}` — load from SQLite, deserialise, return
   - `GET /api/analysis/{id}/report` — return `result_json` as downloadable JSON
   - `GET /api/demo/provider-status` — return `{"provider": "live_granite"|"cached_demo"}`
2. Disclaimer text (hardcoded constant):
   ```
   "Results are based on synthetic demonstration data and are intended for
    exploratory purposes only. They do not represent individual employee
    performance, demographic characteristics, or production-grade recommendations.
    Always engage human judgment before automating any business workflow."
   ```
3. Extend `backend/tests/test_api.py`:
   - Test `POST /api/analysis/run` with `scenario_id="cs-demo-v1"` returns 200 and `analysis_id`
   - Test `GET /api/analysis/{id}` returns `status: "complete"`
   - Test full result passes `AnalysisResult` schema (all required fields present)
   - Test `disclaimer` is non-empty
   - Test `provider_status` is either `"live_granite"` or `"cached_demo"`

**Relevant Context:**
- `AnalysisResult` schema in `docs/data-contracts.md` §2
- Acceptance criteria 4.1–4.5 in `docs/acceptance-criteria.md`

---

## Phase 5 — React Frontend

**Intent:** Build all 4 stages consuming the backend API. Functional and clear; not pixel-perfect.

**Expected Outcomes:**
- All 4 stage routes render without errors
- `ProviderBanner` visible on every stage
- Metrics and overhead breakdown display matches backend values
- Assumption labels visible next to any default-sourced overhead field
- JSON export works

**Files Created:**
```
frontend/src/pages/StageSetup.tsx
frontend/src/pages/StageReality.tsx
frontend/src/pages/StageAIImpact.tsx
frontend/src/pages/StageRedesign.tsx
frontend/src/components/ProviderBanner.tsx
frontend/src/components/WorkflowDiff.tsx
frontend/src/components/HiddenWorkTable.tsx
frontend/src/components/MetricsCard.tsx
frontend/src/components/OverheadBreakdown.tsx
frontend/src/components/ReportExport.tsx
frontend/src/App.tsx  (React Router setup + layout wrapper)
```

**Todo List:**
1. `App.tsx`
   - React Router v6 `<Routes>` with 4 routes: `/`, `/reality`, `/ai-impact`, `/redesign`
   - `AnalysisContext` provides `analysisResult` and `setAnalysisResult` to all stages
   - Layout wrapper renders `ProviderBanner` above every stage
2. `ProviderBanner.tsx`
   - Calls `GET /api/demo/provider-status` on mount
   - Fixed top bar: `🟢 Live IBM Granite` (green) or `🟡 Cached Demo Data` (amber)
3. `StageSetup.tsx` — Stage 1
   - Calls `GET /api/scenarios` on mount; lists available scenarios with description
   - "Run Analysis" button → `POST /api/analysis/run` → stores result in `AnalysisContext` → navigate to `/reality`
   - Shows spinner during analysis; shows error message on failure
4. `StageReality.tsx` — Stage 2
   - Section A: `WorkflowDiff` — two-column official vs actual; hidden-work steps in amber badges, official-only steps in blue
   - Section B: `HiddenWorkTable` — table with columns `event_id`, `ticket_id`, `event_type`, `duration_minutes`, `description`; `hidden_work_ratio` shown as large percentage above table
   - Section C: Metrics grid — `MetricsCard` for Hidden Work Ratio, Burden Concentration, Automation Readiness (label + score), Skill-Loss Risk
5. `StageAIImpact.tsx` — Stage 3
   - Section A: Four-column time comparison table — Official / Actual / AI-Automated / Hybrid total minutes; Gross Time Saved and Net Time Saved highlighted
   - Section B: `OverheadBreakdown` — one row per overhead component (review, correction, exception, maintenance, failure-recovery); value in minutes; source badge: `📋 From Proposal` or `⚠ Assumption (default: X)`
   - Section C: AI Tax `MetricsCard` with colour (green <30%, amber <60%, red ≥60%)
6. `StageRedesign.tsx` — Stage 4
   - Section A: Ordered list of `safer_workflow_steps`; each shows label, executor badge (human/ai/hybrid), approval chip, fallback procedure text
   - Section B: Guardrails grouped by `GuardrailType` (6 sections); missing-fallback warning if `missing_fallback_count > 0`
   - Section C: `redesign_recommendations` as bullet list
   - Section D: `ReportExport` button → `JSON.stringify(analysisResult, null, 2)` → Blob → download `shadowops-preflight-{analysis_id}.json`; disclaimer text above and below export button
7. `HiddenWorkTable.tsx` — renders evidence rows from `hidden_work.evidence`; each row contains `event_id`, `ticket_id`, `event_type`, `duration_minutes`, `description`
8. `OverheadBreakdown.tsx` — renders `overhead_assumptions` list; items with `source: "default"` show `⚠ Assumption` label with `default_value`; items with `source: "proposal"` show `📋 From Proposal`

**Relevant Context:**
- Acceptance criteria 5.1–5.11 in `docs/acceptance-criteria.md`
- `ProviderBanner` rendered in layout wrapper, not inside each stage
- Use Tailwind utility classes only; no external component library required

---

## Phase 6 — Docker, Polish & Export

**Intent:** Containerise the full stack and verify the complete acceptance criteria list.

**Expected Outcomes:**
- Single `docker build && docker run` serves the complete app on port 8000
- All acceptance criteria in `docs/acceptance-criteria.md` pass

**Files Created / Modified:**
```
Dockerfile
docker-compose.yml
backend/main.py  (add static file mount for frontend dist)
```

**Todo List:**
1. Write multi-stage `Dockerfile`:
   ```
   FROM node:20-slim AS frontend-build
   WORKDIR /app/frontend
   COPY frontend/package*.json ./
   RUN npm ci
   COPY frontend/ ./
   RUN npm run build

   FROM python:3.11-slim AS backend
   WORKDIR /app
   COPY requirements.txt ./
   RUN pip install --no-cache-dir -r requirements.txt
   COPY backend/ ./backend/
   COPY --from=frontend-build /app/frontend/dist ./frontend/dist
   ENV PYTHONPATH=/app
   EXPOSE 8000
   CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
   ```
2. In `backend/main.py`, after routers are registered, mount:
   ```python
   app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static")
   ```
3. Write `docker-compose.yml` with env_file pointing to `.env`
4. Add `backend/main.py` startup event: `Base.metadata.create_all(bind=engine)`
5. Run full pytest suite: `pytest backend/tests/ -v` — all tests must pass
6. Manual walkthrough: load `localhost:8000`, run demo, visit all 4 stages, export report
7. Check `ProviderBanner` shows `🟡 Cached Demo Data` without credentials
8. Verify E.1–E.4 ethical criteria via code review

---

## Required vs Optional Features

### Required (MVP — must be done Day 1+2)
- All deterministic metrics including explicit AI overhead formula (Phase 2) ✅
- Live IBM Granite integration path + cached demo provider (Phase 3) ✅
- Full backend API (Phase 4) ✅
- All 4 frontend stages (Phase 5) ✅
- ProviderBanner on every stage ✅
- Overhead assumption labels in UI (Phase 5, Stage 3) ✅
- Raw event IDs in hidden-work evidence (Phase 2 + 5) ✅
- JSON export of preflight report ✅
- Docker container (Phase 6) ✅

### Optional (add only if time permits)
- PDF export of preflight report (jsPDF or puppeteer)
- Animated workflow diff visualisation
- Multiple scenarios beyond `cs-demo-v1`
- Dark mode toggle

---

## Running Tests

```bash
# All backend tests
pytest backend/tests/ -v

# Single test file
pytest backend/tests/test_metrics.py -v

# Single test function
pytest backend/tests/test_metrics.py::test_ai_tax_clamped -v

# Frontend tests
cd frontend && npx vitest run
```

## Running Locally (without Docker)

```bash
# Backend
python -m uvicorn backend.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend && npm run dev   # runs on localhost:5173
```
