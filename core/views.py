from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlencode

from django.conf import settings
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from rest_framework.response import Response
from rest_framework.views import APIView

from pipeline.ai import edit_overlays_with_prompt
from pipeline.services import PipelineError, ffprobe_metadata, rerender_draft
from pipeline.tasks import export_final_task, generate_draft_task
from projects.models import Asset, Draft, ExportArtifact, Job, Project
from projects.schemas import DraftTimeline


class HomeView(View):
    def get(self, request):
        projects = Project.objects.order_by("-created_at")[:20]
        return render(request, "home.html", {"projects": projects})

    def post(self, request):
        name = (request.POST.get("name") or "Untitled Project").strip()
        prompt = (request.POST.get("prompt") or "").strip()
        template_id = (request.POST.get("template_id") or "hook_benefit_cta_v1").strip()
        color = (request.POST.get("primary_color") or "#00A86B").strip()
        project = Project.objects.create(name=name, prompt=prompt, template_id=template_id, primary_color=color)
        return redirect(reverse("workspace", kwargs={"project_id": project.id}))


class WorkspaceView(View):
    def get(self, request, project_id):
        project = get_object_or_404(Project, id=project_id)
        draft = Draft.objects.filter(project=project).first()
        jobs = Job.objects.filter(project=project).order_by("-created_at")[:10]
        exports = ExportArtifact.objects.filter(project=project).order_by("-created_at")[:10]
        overlay_json = "[]"
        if draft and draft.timeline_json:
            overlay_json = json.dumps(draft.timeline_json.get("overlays", []), indent=2)
        return render(
            request,
            "workspace.html",
            {
                "project": project,
                "draft": draft,
                "jobs": jobs,
                "exports": exports,
                "assets": project.assets.order_by("-created_at"),
                "max_duration": settings.VIDEO_MAX_DURATION_SECONDS,
                "overlay_json": overlay_json,
                "error_message": request.GET.get("error", ""),
            },
        )

    def post(self, request, project_id):
        project = get_object_or_404(Project, id=project_id)
        action = request.POST.get("action", "")

        if action == "upload_source":
            upload = request.FILES.get("source_video")
            if upload:
                asset = Asset.objects.create(project=project, asset_type=Asset.AssetType.SOURCE_VIDEO, file=upload)
                metadata = ffprobe_metadata(Path(asset.file.path))
                if metadata["duration_sec"] > settings.VIDEO_MAX_DURATION_SECONDS:
                    asset.delete()
                else:
                    asset.metadata = metadata
                    asset.save(update_fields=["metadata", "updated_at"])

        elif action == "upload_logo":
            upload = request.FILES.get("logo")
            if upload:
                Asset.objects.create(project=project, asset_type=Asset.AssetType.LOGO, file=upload)

        elif action == "generate_draft":
            job = Job.objects.create(project=project, job_type=Job.JobType.GENERATE_DRAFT)
            task = generate_draft_task.delay(str(job.id))
            if not job.task_id:
                job.task_id = getattr(task, "id", "") or ""
                job.save(update_fields=["task_id", "updated_at"])

        elif action == "approve_draft":
            draft = Draft.objects.filter(project=project).first()
            if draft:
                draft.approved = request.POST.get("approved") == "1"
                draft.save(update_fields=["approved", "updated_at"])

        elif action == "export_final":
            job = Job.objects.create(project=project, job_type=Job.JobType.EXPORT_FINAL)
            task = export_final_task.delay(str(job.id))
            if not job.task_id:
                job.task_id = getattr(task, "id", "") or ""
                job.save(update_fields=["task_id", "updated_at"])

        elif action == "update_overlays":
            draft = Draft.objects.filter(project=project).first()
            if not draft:
                error_qs = urlencode({"error": "No draft available. Generate one first."})
                return HttpResponseRedirect(f"{reverse('workspace', kwargs={'project_id': project.id})}?{error_qs}")

            raw = (request.POST.get("overlays_json") or "").strip()
            try:
                overlays = json.loads(raw)
                if not isinstance(overlays, list):
                    raise ValueError("Overlay payload must be a JSON array.")
                timeline = draft.timeline_json or {}
                timeline["overlays"] = overlays
                DraftTimeline.model_validate(
                    {
                        "template_id": timeline.get("template_id", project.template_id),
                        "overlays": overlays,
                        "copy_variants": timeline.get("copy_variants", {}),
                    }
                )
                rerender_draft(project, draft, timeline)
            except (ValueError, json.JSONDecodeError, PipelineError) as exc:
                error_qs = urlencode({"error": str(exc)})
                return HttpResponseRedirect(f"{reverse('workspace', kwargs={'project_id': project.id})}?{error_qs}")

        elif action == "prompt_edit_overlays":
            draft = Draft.objects.filter(project=project).first()
            if not draft:
                error_qs = urlencode({"error": "No draft available. Generate one first."})
                return HttpResponseRedirect(f"{reverse('workspace', kwargs={'project_id': project.id})}?{error_qs}")
            instruction = (request.POST.get("overlay_prompt") or "").strip()
            if not instruction:
                error_qs = urlencode({"error": "Overlay prompt cannot be empty."})
                return HttpResponseRedirect(f"{reverse('workspace', kwargs={'project_id': project.id})}?{error_qs}")
            try:
                timeline = draft.timeline_json or {}
                current_overlays = timeline.get("overlays", [])
                updated_overlays = edit_overlays_with_prompt(current_overlays, instruction)
                timeline["overlays"] = updated_overlays
                DraftTimeline.model_validate(
                    {
                        "template_id": timeline.get("template_id", project.template_id),
                        "overlays": updated_overlays,
                        "copy_variants": timeline.get("copy_variants", {}),
                    }
                )
                rerender_draft(project, draft, timeline)
            except (ValueError, json.JSONDecodeError, PipelineError, RuntimeError) as exc:
                error_qs = urlencode({"error": str(exc)})
                return HttpResponseRedirect(f"{reverse('workspace', kwargs={'project_id': project.id})}?{error_qs}")

        return HttpResponseRedirect(reverse("workspace", kwargs={"project_id": project.id}))


class HealthView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response({"status": "ok"})
