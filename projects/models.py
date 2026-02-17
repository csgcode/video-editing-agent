from __future__ import annotations

import uuid

from django.core.exceptions import ValidationError
from django.db import models


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Project(TimestampedModel):
    class Status(models.TextChoices):
        CREATED = "created", "Created"
        DRAFT_READY = "draft_ready", "Draft Ready"
        EXPORTED = "exported", "Exported"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=180)
    prompt = models.TextField(blank=True)
    template_id = models.CharField(max_length=80, default="hook_benefit_cta_v1")
    primary_color = models.CharField(max_length=16, default="#00A86B")
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.CREATED)

    def __str__(self) -> str:
        return self.name


class Asset(TimestampedModel):
    class AssetType(models.TextChoices):
        SOURCE_VIDEO = "source_video", "Source Video"
        LOGO = "logo", "Logo"
        FONT = "font", "Font"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="assets")
    asset_type = models.CharField(max_length=20, choices=AssetType.choices)
    file = models.FileField(upload_to="assets/%Y/%m/%d")
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [models.Index(fields=["project", "asset_type"])]


class VideoContext(TimestampedModel):
    class Status(models.TextChoices):
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name="video_context")
    source_asset = models.ForeignKey(Asset, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.READY)
    context_json = models.JSONField(default=dict, blank=True)
    error = models.TextField(blank=True)


class EditPlanArtifact(TimestampedModel):
    class Status(models.TextChoices):
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="edit_plans")
    draft = models.ForeignKey("Draft", on_delete=models.CASCADE, related_name="edit_plans", null=True, blank=True)
    version = models.PositiveIntegerField()
    source = models.CharField(max_length=32, default="auto")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.READY)
    plan_json = models.JSONField(default=dict, blank=True)
    quality_report_json = models.JSONField(default=dict, blank=True)
    error = models.TextField(blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["project", "version"], name="unique_project_edit_plan_version")]
        ordering = ["-version"]


class Draft(TimestampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name="draft")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    draft_video = models.FileField(upload_to="drafts/%Y/%m/%d", blank=True)
    timeline_json = models.JSONField(default=dict, blank=True)
    approved = models.BooleanField(default=False)
    error = models.TextField(blank=True)


class DraftVersion(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    draft = models.ForeignKey(Draft, on_delete=models.CASCADE, related_name="versions")
    version = models.PositiveIntegerField()
    source = models.CharField(max_length=32, default="unknown")
    timeline_json = models.JSONField(default=dict, blank=True)
    overlay_diff_json = models.JSONField(default=dict, blank=True)
    draft_video_name = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["draft", "version"], name="unique_draft_version")]
        ordering = ["-version"]


class Overlay(TimestampedModel):
    class OverlayType(models.TextChoices):
        HEADLINE = "headline", "Headline"
        CTA = "cta", "CTA"
        LOGO = "logo", "Logo"
        STICKER = "sticker", "Sticker"
        CALLOUT = "callout", "Callout"
        ENDCARD = "endcard", "End Card"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    draft = models.ForeignKey(Draft, on_delete=models.CASCADE, related_name="overlays")
    overlay_type = models.CharField(max_length=16, choices=OverlayType.choices)
    start_sec = models.FloatField()
    end_sec = models.FloatField()
    text = models.CharField(max_length=240, blank=True)
    position = models.JSONField(default=dict, blank=True)
    style = models.JSONField(default=dict, blank=True)
    asset = models.ForeignKey(Asset, on_delete=models.SET_NULL, null=True, blank=True)

    def clean(self):
        if self.start_sec < 0 or self.end_sec <= self.start_sec:
            raise ValidationError("Overlay timing must satisfy 0 <= start < end.")


class ExportArtifact(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="exports")
    draft = models.ForeignKey(Draft, on_delete=models.CASCADE, related_name="exports")
    file = models.FileField(upload_to="exports/%Y/%m/%d")
    metadata_json = models.JSONField(default=dict, blank=True)


class Job(TimestampedModel):
    class JobType(models.TextChoices):
        GENERATE_DRAFT = "generate_draft", "Generate Draft"
        EXPORT_FINAL = "export_final", "Export Final"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="jobs")
    job_type = models.CharField(max_length=32, choices=JobType.choices)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    task_id = models.CharField(max_length=80, blank=True)
    payload_json = models.JSONField(default=dict, blank=True)
    result_json = models.JSONField(default=dict, blank=True)
    error = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
