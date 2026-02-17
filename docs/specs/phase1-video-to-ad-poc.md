# Phase 1 Video-to-Ad POC Spec

Implemented POC scope:
- Django/DRF API with async job orchestration.
- Source video upload + ffprobe metadata validation.
- Draft generation pipeline using FFmpeg overlays.
- Draft review/update endpoint for overlay edits and approval.
- Final export endpoint producing MP4 artifact and timeline metadata.

## Endpoints
- `POST /api/v1/projects`
- `POST /api/v1/projects/{project_id}/assets`
- `POST /api/v1/projects/{project_id}/drafts/generate`
- `GET /api/v1/jobs/{job_id}`
- `GET /api/v1/projects/{project_id}/draft`
- `PUT /api/v1/projects/{project_id}/draft`
- `POST /api/v1/projects/{project_id}/export`
- `GET /api/v1/projects/{project_id}/artifacts`

## Notes
- Phase 1 currently defaults to local fallback copy generation.
- Set `CELERY_TASK_ALWAYS_EAGER=0` and run Redis/Celery workers for true async behavior.
