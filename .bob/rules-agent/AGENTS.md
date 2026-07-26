# Project Coding Rules (Non-Obvious Only)

- IBM Bob is the **primary** dev tool — do not lead with Claude Code patterns or suggest Claude-first workflows.
- AI Tax and all metrics MUST be calculated deterministically in Python — do NOT delegate metric calculation to LLM inference.
- Secrets are loaded via `.env`; always provide `.env.example` with placeholder values when adding new env vars.
- Generated report files go in `generated-reports/` (gitignored) — never commit them.
- User-uploaded files go in `uploads/` (gitignored) — never commit them.
- When adding new watsonx.ai/IBM Granite calls, keep them isolated from deterministic Python metric code — the two layers must stay separable.
