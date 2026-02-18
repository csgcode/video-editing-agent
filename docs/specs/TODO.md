# Phase 1 TODO Tracker

This is the canonical project task list for agent handoff and execution continuity.

## Update Protocol
- Keep tasks detailed and implementation-ready.
- When a task is completed and committed, mark it complete (`[x]`) and add:
  - commit hash
  - summary of what changed
  - handoff notes (any caveats, follow-ups, or operational notes)
- Do not remove completed tasks; preserve history for new agents.
- If a task is superseded, mark it as `superseded` in notes and link replacement task.

## Status Legend
- `[x]` Completed and committed
- `[ ]` Pending
- `[~]` In progress / partial

## Completed Tasks

### [x] Bootstrap Django/DRF/Celery + media pipeline foundation
- Commit(s): `e4fe24e`, `db3f0cf`, `c942118`
- Summary:
  - Initialized Python project with `uv` and Django stack.
  - Added project/data models, API scaffolding, FFmpeg-based draft generation/export flow.
  - Added minimal web UI and initial interaction loop.
- Handoff notes:
  - Foundation is stable; later tasks should build on existing services (`pipeline/services.py`, `pipeline/tasks.py`).

### [x] Prompt-based overlay editing + render regression tests
- Commit: `5a4facb`
- Summary:
  - Added overlay prompt editing path (Gemini/local fallback) and improved ad-style rendering.
  - Added FFmpeg regression tests to catch drawbox/logo render failures.
- Handoff notes:
  - Restart server/worker when testing filter changes to avoid stale process confusion.

### [x] Draft artifact versioning with overlay diffs
- Commit: `d9ad7b1`
- Summary:
  - Added `DraftVersion` artifact persistence and overlay diff computation.
  - Stored version history for every render/re-render path.
- Handoff notes:
  - Use `draft.versions` for auditability and UI debugging surfaces.

### [x] Upload-time video context artifact generation
- Commit: `3b6d2f7`
- Summary:
  - Added `VideoContext` model and context generation on source upload.
  - Context is persisted and exposed in workspace UI.
- Handoff notes:
  - Current context is heuristic; future task upgrades to richer analysis (shots/OCR/highlights).

### [x] Edit plan artifacts + schema validation
- Commit: `d038325`
- Summary:
  - Added `EditPlanArtifact` model, planner module, and `EditPlan` schema.
  - Added tests for plan creation and artifact versioning.
- Handoff notes:
  - Planner output should remain strictly schema-validated before render.

### [x] Pre-render quality gate + persisted quality reports
- Commit: `f522e66`
- Summary:
  - Added `pipeline/quality.py` with critical/warning checks.
  - Wired quality gate into generation/re-render and persisted reports in `EditPlanArtifact`.
- Handoff notes:
  - Critical failures currently block unless fallback setting routes to safe template.

### [x] Configurable safe-template fallback on render failures
- Commit: `85ae004`
- Summary:
  - Added `AUTO_FALLBACK_TEMPLATE_ON_RENDER_FAIL` setting.
  - Implemented fallback timeline flow for failed quality/render paths.
- Handoff notes:
  - Keep this behavior configurable per environment; future task adds per-project control.

### [x] Agent decisions panel in workspace
- Commit: `4f761d9`
- Summary:
  - Added debugging panel showing latest plan status, quality report, and draft version diff counts.
- Handoff notes:
  - Next enhancement is plan history navigation (not only latest summary).

## Pending Tasks

### [ ] Add edit-plan history API and UI drill-down
- Context:
  - Workspace currently surfaces latest plan summary only.
  - Debugging and integration require querying historical plans and versions.
- Scope:
  - API endpoints:
    - `GET /api/v1/projects/{project_id}/plans`
    - `GET /api/v1/projects/{project_id}/plans/{version}`
  - UI:
    - list of plan versions with source/status/timestamps
    - expandable plan JSON and quality report per version
- Implementation notes:
  - Reuse existing `EditPlanArtifact` ordering and version field.
  - Include pagination or capped list for performance.
- Acceptance criteria:
  - Can fetch complete plan history for a project.
  - Can inspect plan + quality report for any version in UI/API.
- Handoff comments:
  - Ensure backward-compatible serializer fields for existing UI use.

### [ ] Upgrade `video_context` analyzer from heuristic to richer, timecoded analysis
- Context:
  - Current context generation is static and simplistic.
  - Planning quality improves with better context fidelity.
- Scope:
  - Add richer context fields:
    - shot/scene boundaries
    - OCR text snippets with timestamps (where feasible)
    - highlight candidates for hook/cta windows
  - Preserve stable schema contract for planner.
- Implementation notes:
  - Keep processing time bounded for Phase 1 (<5 min overall target).
  - If advanced analyzers fail, gracefully fall back to heuristic context and set warning metadata.
- Acceptance criteria:
  - `video_context.context_json` includes enriched timecoded sections.
  - Planner consumes enriched fields without breaking old projects.
- Handoff comments:
  - Prefer deterministic extraction first; avoid introducing fragile heavy dependencies without fallback.

### [ ] Structured overlay editor UI (replace JSON-only editing)
- Context:
  - JSON editing works but is high-friction for marketers and easy to break.
- Scope:
  - Add row-based overlay editor:
    - text
    - start/end
    - x/y/anchor
    - style (font size, box/color)
  - Keep JSON editor as advanced/debug mode.
- Implementation notes:
  - Validate client-side and server-side before rerender.
  - Keep prompt editor flow intact.
- Acceptance criteria:
  - User can modify overlays without touching raw JSON.
  - Invalid edits are blocked with field-level errors.
- Handoff comments:
  - Reuse existing schema validation to avoid duplicating business rules.

### [ ] Add project-level runtime setting for fallback behavior
- Context:
  - Fallback is currently environment-level only.
- Scope:
  - Add per-project setting (e.g., `project.auto_fallback_enabled`) with UI toggle.
  - Runtime resolves project setting first, env fallback second.
- Implementation notes:
  - Keep default behavior aligned with current env value.
- Acceptance criteria:
  - Two projects can run with different fallback behavior in the same environment.
- Handoff comments:
  - Make migration default explicit to avoid null/implicit behavior.

### [ ] Expand task-level integration tests for planning + quality + fallback lifecycle
- Context:
  - Unit coverage is solid; end-to-end task-path assertions need to be stronger.
- Scope:
  - Add tests for:
    - initial generation persists successful `EditPlanArtifact`
    - quality failure persists failed plan artifact
    - fallback path persists `*_fallback` source and succeeds when valid
- Implementation notes:
  - Mock expensive FFmpeg branches where possible; keep one real render regression path.
- Acceptance criteria:
  - Failure/success/fallback execution paths are covered and deterministic.
- Handoff comments:
  - Ensure assertions include persisted artifact content, not only HTTP status.

### [ ] Phase 1 benchmark run and report
- Context:
  - Reliability and latency targets need measured confirmation.
- Scope:
  - Run benchmark on representative video set.
  - Capture:
    - success rate
    - median draft generation time
    - categorized failures + top remediation actions
- Acceptance criteria:
  - Report stored under `docs/specs/` with reproducible run commands.
- Handoff comments:
  - This is the release-go/no-go artifact for Phase 1 validation.

## Operational Runbook
```bash
make setup
uv run python manage.py migrate
make lint
make test
make run
```

## Related Docs
- `docs/specs/phase1-video-to-ad-poc.md`
- `docs/specs/next-steps-handoff.md`
