# PROJECT_SPEC.md — ShadowOps

## Overview

ShadowOps is an AI Deployment Preflight platform built for the IBM July Wildcard Challenge:
**"Build Intelligent Systems for the Future of Work."**

It answers: *Before you automate a business workflow with AI, what will you actually gain, what will you
lose, and what safeguards are required?*

The platform reconstructs what actually happens in a workflow from structured activity logs, compares it
to the official process, proposes an AI-automated version, and surfaces a safer hybrid design with
quantified metrics and exportable preflight reports.

---

## Assumptions (MVP)

1. Input data is a pre-loaded set of synthetic customer-support events (JSON). No file-upload UI required.
2. A single scenario (customer-support ticket lifecycle) is used for the demo. The schema supports others.
3. Metrics are computed deterministically from event data; IBM Granite is called only for narrative
   analysis and redesign recommendations.
4. If `WATSONX_API_KEY` is absent, the backend automatically falls back to a cached demo provider.
5. All results display a banner: **"Live IBM Granite"** or **"Cached Demo Data"**.
6. Persistence is SQLite; schema is created on first run via SQLAlchemy.
7. The frontend is built by Vite and served as static files through FastAPI. One Docker container only.
8. No authentication, no real external integrations (Slack, Gmail), no payments.

---

## Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| Backend | Python 3.11, FastAPI, Uvicorn |
| Validation | Pydantic v2 |
| Database | SQLite via SQLAlchemy 2.x |
| AI | ibm-watsonx-ai SDK, IBM Granite (model read from `WATSONX_MODEL_ID` env var; default `ibm/granite-4-h-small`) |
| Testing | Pytest, pytest-asyncio, Vitest |
| Container | Docker (multi-stage: Node build → Python serve) |

---

## Frontend Stages (React Router)

Four stages replace the previous eight separate pages. Metrics, hidden-work evidence,
guardrails, and report export are **sections within stages**, not separate routes.

| Route | Stage | Sections within stage |
|---|---|---|
| `/` | Stage 1 — Setup | Scenario selection, run trigger, provider banner |
| `/reality` | Stage 2 — Workflow Reality | Official vs actual diff, hidden-work evidence table (with raw event IDs), metrics grid |
| `/ai-impact` | Stage 3 — AI Impact | Workflow time comparison, AI Tax & net-benefit metrics, overhead breakdown, assumption labels |
| `/redesign` | Stage 4 — Safer Redesign | Safer workflow steps, guardrails, redesign recommendations, report export |

---

## Backend Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Liveness check + provider banner |
| GET | `/api/scenarios` | List available scenarios |
| POST | `/api/analysis/run` | Trigger full analysis for a scenario |
| GET | `/api/analysis/{id}` | Retrieve cached analysis result |
| GET | `/api/analysis/{id}/report` | Download PDF/JSON preflight report |
| GET | `/api/demo/provider-status` | Returns `live` or `cached` |

---

## Out of Scope

- Authentication / user accounts
- Real Slack, Gmail, or CRM integrations
- Drag-and-drop workflow editor
- Autonomous business-action execution
- Demographic inference or individual productivity ranking
- Employee surveillance

---

## Demo Data

Synthetic customer-support ticket lifecycle. Official steps:
`ticket_created`, `assigned`, `first_response`, `resolution`, `closed`

Hidden-work event types (exactly 8, canonical names):
`follow_up`, `manual_status_check`, `context_repair`, `duplicate_entry`,
`rework`, `exception_handling`, `escalation`, `manual_reconciliation`

> `waiting` events may appear in seed data to measure workflow delay but are **not** counted
> as hidden work and must not appear in `HIDDEN_WORK_TYPES`.

Events carry: `event_id`, `ticket_id`, `agent_id`, `event_type`, `timestamp`, `duration_minutes`,
`notes`, `is_hidden_work` (ground-truth label for demo purposes).

The scenario object also carries an `automation_proposal` block with explicit AI overhead
parameters (see `docs/data-contracts.md` §1).
