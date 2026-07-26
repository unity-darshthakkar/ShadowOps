# Project Architecture Rules (Non-Obvious Only)

- Deterministic Python metric layer (AI Tax, burden shift, skill-loss, automation readiness) MUST stay decoupled from the IBM Granite/watsonx.ai inference layer — they serve different trust levels.
- The 4 workflow types are the top-level domain model: official → actual → AI-automated → hybrid. Architecture should reflect this pipeline.
- SQLite is the intended database (inferred from `.gitignore`) — do not plan for a separate DB server unless requirements change.
- `generated-reports/` and `uploads/` are runtime-only directories (gitignored) — plan for them to exist at runtime but never be committed.
- IBM Bob is the primary tool constraint; plan features in a way that assumes Bob-native implementation first.
