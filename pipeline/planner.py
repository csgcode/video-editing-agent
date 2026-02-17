from __future__ import annotations

import uuid

from projects.models import Draft, EditPlanArtifact, Project
from projects.schemas import EditPlan


def build_edit_plan(project: Project, video_context: dict, copy: dict, timeline: dict, source: str = "auto") -> dict:
    plan = EditPlan.model_validate(
        {
            "plan_id": f"plan_{uuid.uuid4().hex[:10]}",
            "objective": f"Generate high-converting playable-style ad for {project.name}",
            "template_id": project.template_id,
            "source": source,
            "video_context": video_context,
            "overlays": timeline.get("overlays", []),
            "constraints": {
                "max_duration_seconds": 60,
                "platform": "tiktok_reels_vertical",
                "safe_zone": "top-bottom padding retained",
            },
            "reasoning_summary": (
                "Auto-selected highest confidence template layout using context windows for hook and CTA."
            ),
        }
    )
    return plan.model_dump()


def persist_edit_plan(
    project: Project,
    draft: Draft | None,
    plan_json: dict,
    quality_report_json: dict,
    source: str,
    status: str = EditPlanArtifact.Status.READY,
    error: str = "",
) -> EditPlanArtifact:
    latest = project.edit_plans.first()
    next_version = (latest.version + 1) if latest else 1
    return EditPlanArtifact.objects.create(
        project=project,
        draft=draft,
        version=next_version,
        source=source,
        status=status,
        plan_json=plan_json,
        quality_report_json=quality_report_json,
        error=error,
    )
