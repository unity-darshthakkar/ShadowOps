# ShadowOps

**AI Deployment Preflight Platform**  
IBM July Wildcard Hackathon — *Build Intelligent Systems for the Future of Work*

ShadowOps answers a question that is often skipped before organizations deploy AI:

> **What will this automation actually save, what hidden work will remain, and what safeguards are required before deployment?**

ShadowOps reconstructs how work is actually performed from structured activity logs, compares it with the documented workflow, estimates the true cost of AI automation, and generates a safer human-AI redesign using IBM Granite.

---

## The Problem

Organizations often automate the workflow shown in policy documents, process diagrams, or operating procedures.

However, the documented workflow rarely includes all the work employees actually perform:

- manual status checks
- follow-up messages
- context reconstruction
- duplicate data entry
- rework
- exception handling
- escalations
- reconciliation across systems

When these activities are ignored, an AI deployment can appear more valuable than it really is.

Automation may also introduce new work:

- reviewing AI output
- correcting mistakes
- handling exceptions
- maintaining prompts and integrations
- recovering from failures
- preserving employee expertise

ShadowOps exposes these costs before deployment.

---

## The Solution

ShadowOps provides a four-stage AI deployment preflight.

### 1. Setup

Select a synthetic workflow scenario and run the preflight analysis.

### 2. Workflow Reality

Compare the official workflow with the workflow reconstructed from activity logs.

ShadowOps identifies hidden work and links every finding to supporting event evidence.

### 3. AI Impact

Estimate the expected impact of the proposed automation, including:

- gross time saved
- review overhead
- correction overhead
- exception-handling overhead
- maintenance overhead
- failure-recovery overhead
- AI Tax
- net time saved
- automation readiness
- skill-loss risk
- burden concentration by role

### 4. Safer Redesign

IBM Granite generates a grounded human-AI workflow containing:

- AI, human, and hybrid execution labels
- confidence thresholds
- approval requirements
- exception routing
- manual fallback procedures
- skill-preservation controls
- audit-trail requirements
- evidence-based redesign recommendations

The complete preflight can be exported as JSON.

---

## Why ShadowOps Is Different

Most AI automation tools focus on what the model can automate.

ShadowOps focuses on what the deployment team may have missed.

It separates:

- **deterministic analysis**, used for metrics and evidence
- **generative AI reasoning**, used for narratives, guardrails, and redesign recommendations

IBM Granite does not invent the numerical results. It receives grounded workflow evidence and deterministic metrics, then explains the risks and proposes a safer redesign.

---

## Demo Flow

The included customer-support scenario contains:

- 5 official workflow steps
- 46 synthetic events across 5 tickets
- 14 actual workflow step types
- 19 hidden-work events
- 8 hidden-work categories

The preflight identifies approximately:

- 20.1% hidden-work ratio
- 61% burden concentration
- 20.5% AI Tax
- 640.5 minutes of net estimated time savings

These values are deterministic and based on the supplied scenario.

---

## Architecture

![ShadowOps architecture](docs/architecture/shadowops-architecture.png)

```text
┌───────────────────────────────┐
│ React + TypeScript Frontend   │
│                               │
│ Setup                         │
│ Workflow Reality              │
│ AI Impact                     │
│ Safer Redesign                │
└───────────────┬───────────────┘
                │ REST API
                ▼
┌───────────────────────────────┐
│ FastAPI Backend               │
│                               │
│ Scenario Loader               │
│ Workflow Reconstruction       │
│ Hidden-Work Detection         │
│ Deterministic Metrics Engine  │
│ PII Redaction                 │
│ Report Export                 │
└───────────────┬───────────────┘
                │ grounded prompt
                ▼
┌───────────────────────────────┐
│ IBM watsonx.ai                │
│ IBM Granite 4 H Small         │
│                               │
│ Workflow narratives           │
│ Redesign recommendations      │
│ Guardrails                    │
│ Safer workflow generation     │
└───────────────────────────────┘
```

### Processing Pipeline

```text
Synthetic event logs
        │
        ▼
Actual workflow reconstruction
        │
        ▼
Hidden-work classification and evidence
        │
        ▼
Deterministic metric calculation
        │
        ▼
PII redaction and grounded prompt construction
        │
        ▼
IBM Granite structured JSON response
        │
        ▼
Schema and completeness validation
        │
        ├── valid → Live Granite result
        │
        └── invalid/unavailable → Cached demo fallback
```

---

## IBM Granite Integration

ShadowOps uses IBM Granite through `watsonx.ai` to generate grounded workflow analysis and safer redesigns.

The model receives:

- the official workflow
- the reconstructed actual workflow
- detected hidden-work categories
- supporting event evidence
- deterministic metrics
- AI-overhead assumptions
- the proposed automation workflow
- a strict JSON output schema

Live output must pass structural and completeness validation before it is displayed.

ShadowOps requires:

- 5–8 redesign recommendations
- 5–8 guardrails
- all six required guardrail categories
- 6–10 safer workflow steps
- fallbacks for every AI or hybrid step
- approval requirements for hybrid steps
- valid confidence thresholds
- complete beginning-to-end workflow coverage

If authentication, generation, parsing, or validation fails, ShadowOps automatically uses cached demonstration output.

The UI displays:

- `🟢 Live IBM Granite`
- `🟡 Cached Demo Data`

### Environment Configuration

Create `.env` from `.env.example`:

```env
WATSONX_API_KEY=<your-api-key>
WATSONX_URL=https://us-south.ml.cloud.ibm.com
WATSONX_PROJECT_ID=<your-project-id>
WATSONX_MODEL_ID=ibm/granite-4-h-small
```

Never commit `.env` or expose watsonx credentials in screenshots, logs, or documentation.

---

## IBM Bob Usage

IBM Bob was the primary development tool used to build ShadowOps.

Bob was used to:

- plan the application architecture
- scaffold the FastAPI backend
- scaffold the React and TypeScript frontend
- define API routes and Pydantic schemas
- implement workflow reconstruction
- implement deterministic metric calculations
- build the four-stage interface
- integrate IBM Granite through watsonx.ai
- migrate from the deprecated text-generation endpoint to the chat endpoint
- enforce structured Granite responses
- add completeness validation and fallback behavior
- create and expand the backend test suite
- improve Windows setup documentation

The project evolved through iterative Bob tasks rather than a single generated code dump. Each major feature was tested before being committed.

A secondary coding assistant was used only for targeted review and polish, including waiting-event semantics, privacy checks, role-based burden concentration, and Granite prompt grounding.

---

## Technical Challenges

### Reconstructing the real workflow

The official process contained only five steps, while the event logs contained fourteen distinct step types.

ShadowOps needed to preserve normal delay events such as `waiting` without incorrectly classifying them as employee effort or automatable hidden work.

### Measuring the AI Tax

Gross time savings alone overstate automation value.

ShadowOps calculates five separate overhead categories and subtracts them from gross savings to estimate net impact.

### Preventing hallucinated metrics

IBM Granite is not used to calculate numerical values.

All metrics are generated deterministically before the model is called. Granite receives those results as grounded context.

### Reliable structured generation

The original Granite integration used the deprecated text-generation endpoint and sometimes returned non-JSON output.

The integration was migrated to the watsonx chat endpoint with JSON response mode, Pydantic validation, completeness validation, and a cached fallback.

### Protecting privacy

Synthetic inputs are used throughout the demo. A redaction layer also removes likely personal names before sending workflow evidence to the model while preserving role names and workflow terminology.

---

## Metrics

All numerical metrics are deterministic.

| Metric | Formula |
|---|---|
| Hidden Work Ratio | hidden minutes ÷ total actual minutes |
| Gross Time Saved | actual total − AI-automated total |
| AI Tax | total AI overhead ÷ gross time saved |
| Net Time Saved | gross time saved − total AI overhead |
| Burden Concentration | highest hidden minutes for one role ÷ total hidden minutes |
| Automation Readiness | weighted workflow-structure heuristic |
| Skill-Loss Risk | heuristic based on concentration and automation readiness |

### AI Overhead

```text
AI Overhead =
    review overhead
  + correction overhead
  + exception-handling overhead
  + maintenance overhead
  + failure-recovery overhead
```

Input values come from the scenario’s automation proposal or documented defaults.

---

## Ethical and Safety Constraints

- No individual employee rankings or performance scores
- No demographic attributes in the data schema
- No real customer or employee data
- Synthetic demonstration events only
- PII redaction before model invocation
- Human approval for hybrid workflow steps
- Manual fallback procedures for AI-dependent steps
- Skill-preservation guardrails
- Audit-trail recommendations
- Scenario-based heuristics clearly labeled as non-validated assessments
- Disclaimer included in every exported report

---

## Technology Stack

### Backend

- Python
- FastAPI
- Pydantic
- SQLite
- pytest
- IBM watsonx.ai Python SDK
- IBM Granite 4 H Small

### Frontend

- React
- TypeScript
- Vite
- CSS

### Development

- IBM Bob
- Git and GitHub
- Docker

---

## Quick Start

### Requirements

- Python 3.11+
- Node.js 18+
- npm
- Optional: IBM watsonx.ai credentials
- Optional: Docker Desktop

### Backend

#### Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m uvicorn backend.main:app --reload --port 8000
```

#### macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python -m uvicorn backend.main:app --reload --port 8000
```

### Frontend

Open a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the local URL shown by Vite, normally:

```text
http://localhost:5173
```

If that port is already occupied, Vite may select another port automatically.

---

## Docker

```bash
docker build -t shadowops .
docker run -p 8000:8000 --env-file .env shadowops
```

Open:

```text
http://localhost:8000
```

---

## Running Tests

### Backend

```bash
python -m pytest backend/tests -q
```

Current result:

```text
60 passed
```

### Frontend production build

```bash
cd frontend
npm run build
```

### TypeScript check

```bash
cd frontend
npx tsc --noEmit
```

---

## Windows Notes

If PowerShell blocks virtual-environment activation:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Activate the environment using:

```powershell
.venv\Scripts\Activate.ps1
```

The application has been tested on Python 3.13, though Python 3.11 or 3.12 may provide the broadest package compatibility.

---

## Project Structure

```text
backend/
├── data/                 Synthetic workflow scenarios
├── models/               Pydantic request and response schemas
├── services/             Analysis, metrics, Granite, and redaction logic
├── tests/                Backend test suite
└── main.py               FastAPI application

frontend/
├── src/                  React and TypeScript interface
└── dist/                 Production build output

docs/                     Planning and architecture documentation
CLAUDE_REVIEW.md           Secondary architecture and QA review
Dockerfile                 Container build
requirements.txt           Python dependencies
```

---

## Report Export

ShadowOps exports a JSON report containing:

- analysis metadata
- official workflow
- actual workflow
- hidden-work evidence
- deterministic metrics
- Granite narratives
- redesign recommendations
- guardrails
- safer workflow steps
- provider status
- ethical disclaimer

---

## Future Work

- Upload custom workflow definitions and event logs
- Support CSV and JSON ingestion
- Add interactive workflow diagrams
- Compare multiple automation proposals
- Add scenario sensitivity analysis
- Generate management and technical report formats
- Support additional watsonx models
- Add role-level workload visualizations
- Store analysis history
- Deploy a hosted demonstration

---

## Repository

GitHub: https://github.com/unity-darshthakkar/ShadowOps

---

## Disclaimer

ShadowOps is a hackathon prototype built with synthetic data.

Its recommendations are intended for exploratory workflow analysis only. They are not production-grade deployment decisions, employee assessments, legal guidance, or compliance certifications. Human judgment should always be used before automating a business workflow.
