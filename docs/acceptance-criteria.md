# docs/acceptance-criteria.md — ShadowOps Acceptance Criteria

Each criterion maps to a phase in `bob-implementation-plan.md`.
A criterion is met when it passes automated tests OR can be manually verified in the browser.

---

## Phase 1 — Project Scaffold & Data Layer

| # | Criterion | Verified By |
|---|---|---|
| 1.1 | `GET /api/health` returns `{"status":"ok","provider":"cached_demo","version":"0.1.0"}` | pytest `test_api.py` |
| 1.2 | Frontend dev server starts on `localhost:5173` with no console errors | Manual |
| 1.3 | `GET /api/scenarios` returns the `cs-demo-v1` scenario with event count ≥ 20 | pytest |
| 1.4 | SQLite database is created on first run at `DATABASE_URL` path | Manual |
| 1.5 | `.env.example` documents all required variables | Code review |

## Phase 2 — Deterministic Analysis Engine

| # | Criterion | Verified By |
|---|---|---|
| 2.1 | `hidden_work_ratio` equals `hidden_minutes / total_minutes` to 4 decimal places | pytest `test_metrics.py` |
| 2.2 | `ai_tax` is clamped to `[0, 1]` even when `gross_time_saved` is very small | pytest |
| 2.3 | `net_time_saved` is negative when `ai_overhead > gross_time_saved` | pytest |
| 2.4 | `automation_readiness_label` maps correctly: ≥0.7→High, ≥0.4→Medium, else Low | pytest |
| 2.5 | All 8 canonical hidden-work types are detected; `waiting` is NOT counted as hidden work | pytest `test_hidden_work.py` |
| 2.6 | `WorkflowReconstructor` preserves event order and groups by ticket | pytest `test_reconstructor.py` |
| 2.7 | `ai_overhead` uses `automation_proposal` fields when present, not fixed percentages | pytest `test_metrics.py` |
| 2.8 | `overhead_assumptions` contains one `OverheadAssumption` per field; `source` is `"default"` for any missing field | pytest |
| 2.9 | All 8 overhead fields from `automation_proposal` produce correct per-field overhead values | pytest |

## Phase 3 — AI Layer & Cached Provider

| # | Criterion | Verified By |
|---|---|---|
| 3.1 | With no env credentials, `provider_status` returns `"cached_demo"` | pytest |
| 3.2 | Cached provider returns JSON that passes `GraniteOutput` Pydantic validation | pytest |
| 3.3 | With valid `WATSONX_API_KEY`, `WATSONX_URL`, and `WATSONX_PROJECT_ID`, a live call is attempted | pytest (mock SDK) |
| 3.4 | Model ID used in live call equals `settings.watsonx_model_id` (read from `WATSONX_MODEL_ID` env) | pytest (mock SDK) |
| 3.5 | Granite prompt contains `hidden_work_ratio`, `net_time_saved`, `automation_readiness_label` | pytest (prompt inspection) |
| 3.6 | `JSONDecodeError` from live Granite call triggers fallback to cached provider with warning log | pytest |
| 3.7 | `ValidationError` from live Granite call triggers fallback to cached provider with warning log | pytest |
| 3.8 | Any SDK exception from live Granite call triggers fallback to cached provider with warning log | pytest |

## Phase 4 — API Integration

| # | Criterion | Verified By |
|---|---|---|
| 4.1 | `POST /api/analysis/run` returns `analysis_id` within 500ms (cached) or 30s (live) | pytest |
| 4.2 | `GET /api/analysis/{id}` returns `status: "complete"` after run | pytest |
| 4.3 | Full `AnalysisResult` passes Pydantic schema validation with no extra fields | pytest |
| 4.4 | `disclaimer` field is never null or empty | pytest |
| 4.5 | `GET /api/analysis/{id}/report` returns valid JSON preflight report | pytest |

## Phase 5 — Frontend Stages

| # | Criterion | Verified By |
|---|---|---|
| 5.1 | `ProviderBanner` is visible on all four stages | Manual |
| 5.2 | Stage 1 (Setup) lists `cs-demo-v1`, triggers analysis on button click, shows spinner | Manual |
| 5.3 | Stage 2 (Workflow Reality) shows side-by-side official vs actual diff with hidden-work steps highlighted | Manual |
| 5.4 | Stage 2 hidden-work evidence table shows `event_id`, `ticket_id`, `event_type`, `duration_minutes`, and description per row | Manual |
| 5.5 | Stage 2 metrics grid shows Hidden Work Ratio, Burden Concentration, Automation Readiness, Skill-Loss Risk | Manual |
| 5.6 | Stage 3 (AI Impact) shows four-column time comparison (Official / Actual / AI-Automated / Hybrid) | Manual |
| 5.7 | Stage 3 shows AI Tax as a percentage with colour indicator (green <30%, amber <60%, red ≥60%) | Manual |
| 5.8 | Stage 3 `OverheadBreakdown` lists each overhead component; fields sourced from defaults display a visible ⚠ Assumption label | Manual |
| 5.9 | Stage 4 (Safer Redesign) shows safer steps with executor badges, guardrails grouped by type, redesign recommendations | Manual |
| 5.10 | Stage 4 JSON export downloads `shadowops-preflight-{analysis_id}.json` with full `AnalysisResult` | Manual |
| 5.11 | Disclaimer text appears on Stage 4 report section | Manual |

## Phase 6 — Docker & Deployment

| # | Criterion | Verified By |
|---|---|---|
| 6.1 | `docker build .` succeeds with no errors | Manual |
| 6.2 | `docker run -p 8000:8000 shadowops` serves the React app at `localhost:8000` | Manual |
| 6.3 | `GET localhost:8000/api/health` returns `200 OK` from the container | Manual |
| 6.4 | All Phase 2–4 pytest tests pass inside the container | `docker run pytest` |

## Ethical / Out-of-Scope Guard

| # | Criterion | Verified By |
|---|---|---|
| E.1 | No endpoint exposes individual agent performance scores | Code review |
| E.2 | No demographic data fields exist in any schema | Code review |
| E.3 | `disclaimer` text explicitly states results are based on synthetic data | Code review |
| E.4 | No real external API calls (Slack, Gmail) exist in codebase | Code review |
