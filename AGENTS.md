# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Project: ShadowOps

AI Deployment Preflight platform for the IBM July Wildcard Hackathon. See [`SHADOWOPS_BRIEF.md`](SHADOWOPS_BRIEF.md) for the full spec.

**IBM Bob is the PRIMARY development tool.** Claude Code + Nemotron is reserved for secondary review, testing, debugging, and polish only.

## Intended Stack (inferred from `.gitignore` — no code written yet)

- **Backend:** Python (pytest, venv, `.venv/`)
- **Frontend:** Node.js / JS / TS (`node_modules/`, `dist/`, `build/`)
- **Database:** SQLite (`*.db`, `*.sqlite`, `*.sqlite3` excluded)
- **AI:** IBM Granite via watsonx.ai
- **Testing:** pytest

## Key Domain Concepts

- **AI Tax:** Deterministic metric calculated in Python — represents hidden overhead cost of AI automation
- **Hidden Work:** follow-ups, status checks, context repair, duplicate entry, rework, escalations, exception handling
- **4 Workflow Types:** official, actual (from logs), AI-automated (proposed), hybrid (system-recommended)
- Outputs must include: human burden shifts, skill-loss risks, missing fallback procedures, automation readiness score

## File Conventions (from `.gitignore`)

- Secrets in `.env` (excluded); provide `.env.example` for documentation
- Generated reports go in `generated-reports/` (gitignored)
- User uploads go in `uploads/` (gitignored)

## Build/Test Commands

> No commands exist yet. When established, document them here.
> Expected: `pytest` for Python tests, `npm run ...` for frontend.
> Single test: `pytest tests/path/to/test_file.py::test_name -v`
