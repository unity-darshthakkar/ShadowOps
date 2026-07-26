# ShadowOps

ShadowOps is an AI Deployment Preflight platform for the IBM July Wildcard Challenge.

It compares:
1. The official workflow.
2. The actual workflow reconstructed from activity logs.
3. A proposed AI-automated workflow.
4. A safer hybrid workflow recommended by the system.

Core capabilities:
- Detect hidden work such as follow-ups, status checks, context repair, duplicate entry, rework, escalations, and exception handling.
- Use IBM Granite through watsonx.ai for workflow analysis and redesign recommendations.
- Calculate AI Tax and other metrics deterministically in Python.
- Show human burden shifts, skill-loss risks, missing fallback procedures, and automation readiness.
- Recommend a safer future workflow with human checkpoints and manual fallback.

IBM Bob must be the primary development tool.
Claude Code with Nemotron will only be used later for secondary review, testing, debugging, and polish.
