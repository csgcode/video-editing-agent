from __future__ import annotations

import uuid
from pathlib import Path

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from pipeline.services import (
    PipelineError,
    build_timeline,
    ffprobe_metadata,
    generate_copy,
    normalize_video,
    rebuild_overlays,
    render_with_overlays,
    source_video_asset,
)
from projects.models import Draft, ExportArtifact, Job, Project


@shared_task(bind=True, autoretry_for=(PipelineError,), retry_backoff=True, max_retries=1)
def generate_draft_task(self, job_id: str) -> dict:
    job = Job.objects.get(id=job_id)
    job.status = Job.Status.RUNNING
    job.started_at = timezone.now()
    job.task_id = self.request.id
    job.save(update_fields=["status", "started_at", "task_id"])

    try:
        project = job.project
        source_asset = source_video_asset(project)
        src_path = Path(source_asset.file.path)
        normalized = Path(settings.MEDIA_ROOT) / "normalized" / f"{project.id}.mp4"
        normalize_video(src_path, normalized)
        metadata = ffprobe_metadata(normalized)
        if metadata["duration_sec"] > settings.VIDEO_MAX_DURATION_SECONDS:
            raise PipelineError(f"Input too long: {metadata['duration_sec']:.2f}s")

        copy = generate_copy(project.prompt, project.template_id)
        timeline = build_timeline(project, metadata["duration_sec"], copy)

        draft, _ = Draft.objects.get_or_create(project=project)
        draft.timeline_json = timeline
        draft.status = Draft.Status.PENDING
        draft.error = ""
        draft.save(update_fields=["timeline_json", "status", "error", "updated_at"])

        draft_path = Path(settings.MEDIA_ROOT) / "drafts" / f"{project.id}-{uuid.uuid4().hex[:6]}.mp4"
        render_with_overlays(normalized, draft_path, timeline, project)

        rel = draft_path.relative_to(Path(settings.MEDIA_ROOT))
        draft.draft_video.name = str(rel)
        draft.status = Draft.Status.READY
        draft.save(update_fields=["draft_video", "status", "updated_at"])
        rebuild_overlays(draft, timeline)

        project.status = Project.Status.DRAFT_READY
        project.save(update_fields=["status", "updated_at"])

        job.status = Job.Status.SUCCESS
        job.finished_at = timezone.now()
        job.result_json = {"draft_id": str(draft.id), "draft_video": draft.draft_video.url}
        job.save(update_fields=["status", "finished_at", "result_json", "updated_at"])
        return job.result_json
    except Exception as exc:
        msg = str(exc)
        Draft.objects.update_or_create(project=job.project, defaults={"status": Draft.Status.FAILED, "error": msg})
        job.status = Job.Status.FAILED
        job.error = msg
        job.finished_at = timezone.now()
        job.save(update_fields=["status", "error", "finished_at", "updated_at"])
        job.project.status = Project.Status.FAILED
        job.project.save(update_fields=["status", "updated_at"])
        raise


@shared_task(bind=True)
def export_final_task(self, job_id: str) -> dict:
    job = Job.objects.get(id=job_id)
    job.status = Job.Status.RUNNING
    job.started_at = timezone.now()
    job.task_id = self.request.id
    job.save(update_fields=["status", "started_at", "task_id"])

    try:
        project = job.project
        draft = project.draft
        if not draft.approved:
            raise PipelineError("Draft must be approved before export")
        if not draft.draft_video:
            raise PipelineError("Draft video missing")

        src = Path(draft.draft_video.path)
        dst = Path(settings.MEDIA_ROOT) / "exports" / f"{project.id}-{uuid.uuid4().hex[:6]}.mp4"
        dst.parent.mkdir(parents=True, exist_ok=True)

        # Export currently mirrors draft; hook for future final rendering differences.
        dst.write_bytes(src.read_bytes())

        rel = dst.relative_to(Path(settings.MEDIA_ROOT))
        artifact = ExportArtifact.objects.create(
            project=project,
            draft=draft,
            file=str(rel),
            metadata_json={"timeline": draft.timeline_json},
        )

        project.status = Project.Status.EXPORTED
        project.save(update_fields=["status", "updated_at"])

        job.status = Job.Status.SUCCESS
        job.finished_at = timezone.now()
        job.result_json = {"export_id": str(artifact.id), "file": artifact.file.url}
        job.save(update_fields=["status", "finished_at", "result_json", "updated_at"])
        return job.result_json
    except Exception as exc:
        job.status = Job.Status.FAILED
        job.error = str(exc)
        job.finished_at = timezone.now()
        job.save(update_fields=["status", "error", "finished_at", "updated_at"])
        raise
