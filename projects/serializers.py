from __future__ import annotations

from rest_framework import serializers

from .models import Asset, Draft, ExportArtifact, Job, Overlay, Project


class ProjectCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ["id", "name", "prompt", "template_id", "primary_color", "status", "created_at"]
        read_only_fields = ["id", "status", "created_at"]


class AssetUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = ["id", "asset_type", "file", "metadata", "created_at"]
        read_only_fields = ["id", "metadata", "created_at"]


class OverlaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Overlay
        fields = [
            "id",
            "overlay_type",
            "start_sec",
            "end_sec",
            "text",
            "position",
            "style",
        ]


class DraftSerializer(serializers.ModelSerializer):
    overlays = OverlaySerializer(many=True, read_only=True)

    class Meta:
        model = Draft
        fields = ["id", "status", "approved", "draft_video", "timeline_json", "error", "overlays", "updated_at"]


class DraftUpdateSerializer(serializers.Serializer):
    approved = serializers.BooleanField(required=False)
    overlays = OverlaySerializer(many=True, required=False)


class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = [
            "id",
            "job_type",
            "status",
            "task_id",
            "payload_json",
            "result_json",
            "error",
            "started_at",
            "finished_at",
            "created_at",
        ]


class ExportSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExportArtifact
        fields = ["id", "file", "metadata_json", "created_at"]
