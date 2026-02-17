from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from rest_framework.response import Response
from rest_framework.views import APIView

from pipeline.services import ffprobe_metadata
from pipeline.tasks import export_final_task, generate_draft_task
from projects.models import Asset, Draft, ExportArtifact, Job, Project


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

        return HttpResponseRedirect(reverse("workspace", kwargs={"project_id": project.id}))


class HealthView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response({"status": "ok"})
