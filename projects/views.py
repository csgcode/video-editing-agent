from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from pipeline.context import save_video_context
from pipeline.services import ffprobe_metadata, rerender_draft
from pipeline.tasks import export_final_task, generate_draft_task
from projects.models import Asset, Draft, ExportArtifact, Job, Overlay, Project
from projects.schemas import DraftTimeline
from projects.serializers import (
    AssetUploadSerializer,
    DraftSerializer,
    DraftUpdateSerializer,
    ExportSerializer,
    JobSerializer,
    ProjectCreateSerializer,
)


class ProjectCreateView(APIView):
    def post(self, request):
        serializer = ProjectCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = serializer.save()
        return Response(ProjectCreateSerializer(project).data, status=status.HTTP_201_CREATED)


class ProjectAssetUploadView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, project_id):
        project = get_object_or_404(Project, id=project_id)
        serializer = AssetUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        asset = serializer.save(project=project)

        if asset.asset_type == Asset.AssetType.SOURCE_VIDEO:
            metadata = ffprobe_metadata(Path(asset.file.path))
            if metadata["duration_sec"] > settings.VIDEO_MAX_DURATION_SECONDS:
                asset.delete()
                return Response(
                    {"detail": f"Video duration exceeds {settings.VIDEO_MAX_DURATION_SECONDS}s"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            asset.metadata = metadata
            asset.save(update_fields=["metadata", "updated_at"])
            save_video_context(project, asset, metadata)

        return Response(AssetUploadSerializer(asset).data, status=status.HTTP_201_CREATED)


class DraftGenerateView(APIView):
    def post(self, request, project_id):
        project = get_object_or_404(Project, id=project_id)
        job = Job.objects.create(project=project, job_type=Job.JobType.GENERATE_DRAFT, payload_json=request.data)
        task = generate_draft_task.delay(str(job.id))
        if not job.task_id:
            job.task_id = getattr(task, "id", "") or ""
            job.save(update_fields=["task_id", "updated_at"])
        return Response(JobSerializer(job).data, status=status.HTTP_202_ACCEPTED)


class JobDetailView(APIView):
    def get(self, request, job_id):
        job = get_object_or_404(Job, id=job_id)
        return Response(JobSerializer(job).data)


class DraftDetailView(APIView):
    def get(self, request, project_id):
        project = get_object_or_404(Project, id=project_id)
        draft = get_object_or_404(Draft, project=project)
        return Response(DraftSerializer(draft).data)

    def put(self, request, project_id):
        project = get_object_or_404(Project, id=project_id)
        draft = get_object_or_404(Draft, project=project)
        serializer = DraftUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        if "approved" in payload:
            draft.approved = payload["approved"]

        overlays_in = payload.get("overlays")
        if overlays_in is not None:
            for item in overlays_in:
                if item["end_sec"] <= item["start_sec"]:
                    return Response({"detail": "Invalid overlay timing."}, status=status.HTTP_400_BAD_REQUEST)

            draft.overlays.all().delete()
            overlay_rows = []
            timeline_items = []
            for item in overlays_in:
                overlay_rows.append(
                    Overlay(
                        draft=draft,
                        overlay_type=item["overlay_type"],
                        start_sec=item["start_sec"],
                        end_sec=item["end_sec"],
                        text=item.get("text", ""),
                        position=item.get("position", {}),
                        style=item.get("style", {}),
                    )
                )
                timeline_items.append(
                    {
                        "id": str(item.get("id", "")),
                        "type": item["overlay_type"],
                        "start_sec": item["start_sec"],
                        "end_sec": item["end_sec"],
                        "text": item.get("text", ""),
                        "position": item.get("position", {}),
                        "style": item.get("style", {}),
                    }
                )
            Overlay.objects.bulk_create(overlay_rows)
            timeline = draft.timeline_json or {}
            timeline["overlays"] = timeline_items
            DraftTimeline.model_validate({
                "template_id": timeline.get("template_id", project.template_id),
                "overlays": timeline_items,
                "copy_variants": timeline.get("copy_variants", {}),
            })
            draft.timeline_json = timeline
            rerender_draft(project, draft, timeline, source="api_overlay_edit")

        draft.save()
        return Response(DraftSerializer(draft).data)


class ExportCreateView(APIView):
    def post(self, request, project_id):
        project = get_object_or_404(Project, id=project_id)
        if not hasattr(project, "draft"):
            return Response({"detail": "No draft available."}, status=status.HTTP_400_BAD_REQUEST)

        job = Job.objects.create(project=project, job_type=Job.JobType.EXPORT_FINAL, payload_json=request.data)
        task = export_final_task.delay(str(job.id))
        if not job.task_id:
            job.task_id = getattr(task, "id", "") or ""
            job.save(update_fields=["task_id", "updated_at"])
        return Response(JobSerializer(job).data, status=status.HTTP_202_ACCEPTED)


class ProjectArtifactsView(APIView):
    def get(self, request, project_id):
        project = get_object_or_404(Project, id=project_id)
        artifacts = ExportArtifact.objects.filter(project=project).order_by("-created_at")
        return Response(ExportSerializer(artifacts, many=True).data)
