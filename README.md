# ShadowOps

**AI Deployment Preflight Platform** — IBM July Wildcard Hackathon
*Build Intelligent Systems for the Future of Work*

ShadowOps answers: **Before you automate a workflow with AI, what will you actually gain, what will you lose, and what safeguards are required?**

It reconstructs the actual workflow from structured activity logs, compares it to the official process, proposes an AI-automated version, and surfaces a safer hybrid design with quantified metrics.

---

## Quick Start

### Without Docker

**Backend (Python 3.11+):**
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # configure watsonx credentials if available
python -m uvicorn backend.main:app --reload --port 8000
```

**Frontend (Node 18+, separate terminal):**
```bash
cd frontend
npm install
npm run dev                      # runs on http://localhost:5173
```

### With Docker (requires Docker Desktop)
```bash
docker build -t shadowops .
docker run -p 8000:8000 --env-file .env shadowops
# Open http://localhost:8000
```

---

## IBM Granite Integration

By default, the app runs with `CachedDemoProvider` (no network calls, no credentials required).

To enable live IBM Granite calls, set in `.env`:
```
WATSONX_API_KEY=<your-key>
WATSONX_URL=https://us-south.ml.cloud.ibm.com
WATSONX_PROJECT_ID=<your-project-id>
WATSONX_MODEL_ID=ibm/granite-4-h-small
```

The UI displays a green `🟢 Live IBM Granite` banner when live, amber `🟡 Cached Demo Data` when not.

---

## Running Tests

```bash
# All backend tests
pytest backend/tests/ -v

# Single test
pytest backend/tests/test_api.py::test_five_overhead_components_sum_to_ai_overhead -v

# Frontend TypeScript check
cd frontend && npx tsc --noEmit

# Frontend production build
cd frontend && npm run build
```

---

## Metrics Computed

All metrics are deterministic — no LLM involvement in number generation.

| Metric | Formula |
|---|---|
| Hidden Work Ratio | hidden minutes / total actual minutes |
| Gross Time Saved | actual total − AI-automated total |
| AI Tax | total AI overhead / gross time saved (clamped 0–1) |
| Net Time Saved | gross time saved − AI overhead |
| Burden Concentration | max hidden minutes by role / total hidden minutes |
| Automation Readiness | weighted composite (structured ratio + low exception rate + low hidden ratio) |
| Skill-Loss Risk | derived from burden concentration + automation readiness |

**AI Overhead** = review + correction + exception + maintenance + failure-recovery overhead.  
Each component uses values from the scenario's `automation_proposal` block, or documented defaults.

---

## Ethical Constraints

- No individual employee rankings or scores are exposed
- No demographic data in any schema
- All data is synthetic — no real personal information
- Automation Readiness and Skill-Loss Risk are labelled as scenario-based heuristics, not validated assessments
- Disclaimer on every report export

---

## Project Structure

```
backend/          FastAPI app, services, tests
frontend/         React/TypeScript/Vite app
docs/             Architecture and planning documents
backend/data/     Synthetic seed scenarios
```
