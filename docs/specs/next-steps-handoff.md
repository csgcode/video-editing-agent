# Next Steps Handoff (Resume Plan)

## Current Status
Completed and committed:
- `5a4facb` Prompt-based overlay editing + render regression tests.
- `d9ad7b1` Draft version artifacts with overlay diffs.
- `3b6d2f7` Upload-time `video_context` artifact generation.

Interrupted WIP (not committed yet):
- Modified: `projects/admin.py`
- Modified: `projects/models.py`
- Modified: `projects/schemas.py`
- New file: `pipeline/planner.py`

WIP intent: add `EditPlan` artifact + schema validation and quality gate before render.

## Immediate Resume Checklist
1. Finish `EditPlan` artifact model and migration.
2. Finish planner service (`pipeline/planner.py`) integration.
3. Add quality gate module to block critical render issues.
4. Wire planning + quality gate into:
- draft generation task
- prompt/json overlay re-render path
5. Add tests for:
- `EditPlan` schema validation
- quality gate pass/fail conditions
- persistence/versioning for edit plans
6. Run validation:
- `uv run ruff check .`
- `uv run pytest`
7. Commit step once green.

## Detailed Plan for Next Implementation Step

### Step A: Planning Artifact (`edit_plan`) + Persistence
- Add model: `EditPlanArtifact`
- Fields:
  - `project` FK
  - `draft` FK (nullable)
  - `version` (monotonic per project)
  - `source` (`initial_generate`, `prompt_patch`, `manual_json_edit`, etc.)
  - `status` (`ready|failed`)
  - `plan_json`
  - `quality_report_json`
  - `error`
- Add admin registration.
- Add migration.

Acceptance:
- Can create/retrieve plan artifacts in DB.
- Version increments per project.

### Step B: Edit Plan Schema
- Extend `projects/schemas.py` with `EditPlan` schema.
- Required structure:
  - `plan_id`, `objective`, `template_id`, `source`
  - `video_context`
  - `overlays` (reuse validated overlay schema)
  - `constraints`
  - `reasoning_summary`

Acceptance:
- Invalid overlay timing/shape in plan fails fast at schema validation.

### Step C: Quality Gate (Pre-render)
- New module: `pipeline/quality.py`
- Input: timeline/plan + known video duration.
- Output report:
  - `critical`: blocking issues
  - `warnings`: non-blocking issues
- Critical checks:
  - overlay timings valid (`end > start`, in bounds)
  - normalized position ranges
  - at least one CTA overlay
  - at least one headline/callout overlay
- Warnings:
  - small font sizes (below threshold)
  - poor safe-zone positions

Acceptance:
- Critical failure prevents render.
- Report saved in `EditPlanArtifact`.

### Step D: Wire into Runtime Paths
- `generate_draft_task` flow:
  1. Build timeline
  2. Build and validate edit plan
  3. Run quality gate
  4. Persist `EditPlanArtifact`
  5. If no critical, render
- Re-render paths (`prompt_patch`, `manual_json_edit`, API edit): same sequence.

Acceptance:
- Every render attempt has a persisted plan artifact with quality report.

## Recommended Commit Strategy (per-step commits)
1. `feat: add edit plan artifact model and schema`
2. `feat: add quality gate and pre-render validation`
3. `feat: persist edit plan reports in draft and rerender paths`
4. `test: add plan and quality gate regression tests`

## Runbook to Continue Later
```bash
# install/sync
make setup

# migrations
uv run python manage.py makemigrations
uv run python manage.py migrate

# tests/lint
make lint
make test
```

## Notes
- Keep fallback behavior configurable later:
  - `AUTO_FALLBACK_TEMPLATE_ON_RENDER_FAIL=1|0`
- Keep provider layer pluggable; Gemini can remain default while preserving local fallback.
