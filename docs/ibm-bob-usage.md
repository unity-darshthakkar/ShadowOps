# ShadowOps — IBM Bob Usage Log

This document tracks how IBM Bob was used as the primary development tool throughout the ShadowOps build.

---

## Role of IBM Bob

IBM Bob served as the **primary development tool** for ShadowOps, as specified in `SHADOWOPS_BRIEF.md`.  
All code architecture, planning documents, implementation, test writing, and debugging were performed through Bob.

---

## Planning Phase (Bob Plan Mode)

Bob was used in Plan mode to produce all five planning documents before a single line of code was written:

| Document | Purpose |
|---|---|
| `PROJECT_SPEC.md` | Product overview, stack, API endpoints, demo data |
| `docs/architecture.md` | System flow, directory structure, layer responsibilities |
| `docs/bob-implementation-plan.md` | Phased build plan with per-phase file lists and todo items |
| `docs/data-contracts.md` | Pydantic schemas, seed JSON schema, formulas, Granite prompt |
| `docs/acceptance-criteria.md` | 40+ testable criteria across 6 phases |

The planning documents were revised in a second planning session to incorporate six specification corrections (hidden-work taxonomy, model ID from env var, live Granite required, 4 stages vs 8 pages, raw event IDs, explicit overhead formula).

---

## Implementation Phase (Bob Agent Mode)

Bob was used in Agent mode to implement the complete vertical slice:

### Backend
- `backend/config.py` — pydantic-settings with watsonx env vars
- `backend/database.py` — SQLAlchemy engine and session factory
- `backend/models/schemas.py` — all Pydantic v2 schemas
- `backend/models/db_models.py` — SQLAlchemy ORM model
- `backend/services/hidden_work_detector.py` — `HIDDEN_WORK_TYPES` frozenset, evidence with raw event IDs
- `backend/services/workflow_reconstructor.py` — timeline reconstruction
- `backend/services/metrics_calculator.py` — all deterministic formulas including 5-component overhead
- `backend/services/granite_analyser.py` — IBM Granite SDK integration with fallback
- `backend/services/cached_provider.py` — hard-coded `GraniteOutput` for offline/failure use
- `backend/routers/health.py`, `scenarios.py`, `analysis.py` — FastAPI routes
- `backend/main.py` — app factory with CORS and static file serving
- `backend/data/seed_scenarios.json` — 46 events, 5 tickets, 8 hidden-work types

### Frontend
- `frontend/src/types/api.ts` — TypeScript mirrors of all Pydantic schemas
- `frontend/src/api/client.ts` — typed `apiFetch<T>` wrapper
- `frontend/src/context/AnalysisContext.tsx` — React context for analysis state
- `frontend/src/App.tsx` — React Router v6, layout wrapper, ProviderBanner
- 4 stage pages and 6 components (ProviderBanner, WorkflowDiff, HiddenWorkTable, MetricsCard, OverheadBreakdown, ReportExport)

### Tests
- 25 backend tests covering all acceptance criteria — 25/25 pass
- TypeScript check: 0 errors
- Production build: success

---

## Screenshots

> **[PLACEHOLDER]** Insert screenshot of Stage 1 — Setup here.

> **[PLACEHOLDER]** Insert screenshot of Stage 2 — Workflow Reality with hidden-work evidence table.

> **[PLACEHOLDER]** Insert screenshot of Stage 3 — AI Impact with overhead breakdown and ⚠ Assumption labels.

> **[PLACEHOLDER]** Insert screenshot of Stage 4 — Safer Redesign with guardrails and export button.

> **[PLACEHOLDER]** Insert screenshot of 🟢 Live IBM Granite banner (requires credentials).

---

## Commit IDs

> **[PLACEHOLDER]** Insert git commit SHA after final commit.

---

## Key Decisions Made During Build

1. **Granite called after deterministic metrics** — metrics are computed first, then Granite receives them as numbered inputs so it generates narrative only, never scores.
2. **CachedDemoProvider returns real Pydantic objects** — not mocked JSON strings, so it always passes schema validation.
3. **Test DB isolation** — engine monkey-patching at test module load time ensures SQLite tables exist before the first request test.
4. **`waiting` event type excluded from `HIDDEN_WORK_TYPES`** — it records workflow delay but is not itself a labour activity.
5. **AnalysisMetrics exposes all 5 overhead fields** — frontend `OverheadBreakdown` reads them directly rather than recomputing.
