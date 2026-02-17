from __future__ import annotations

import pytest

from pipeline.planner import build_edit_plan, persist_edit_plan
from projects.models import Draft, EditPlanArtifact, Project
from projects.schemas import EditPlan


@pytest.mark.django_db
def test_build_edit_plan_validates_schema():
    project = Project.objects.create(name="plan", template_id="hook_benefit_cta_v1")
    video_context = {"video": {"duration_sec": 20.0}, "recommended_windows": {"hook": {"start_sec": 0.0}}}
    timeline = {
        "overlays": [
            {
                "id": "ovl1",
                "type": "headline",
                "start_sec": 0.0,
                "end_sec": 2.0,
                "text": "HELLO",
                "position": {"x": 0.5, "y": 0.2, "anchor": "center"},
                "style": {"font_size": 64},
            }
        ]
    }

    plan = build_edit_plan(project, video_context, copy={}, timeline=timeline, source="initial_generate")
    validated = EditPlan.model_validate(plan)

    assert validated.template_id == "hook_benefit_cta_v1"
    assert len(validated.overlays) == 1


@pytest.mark.django_db
def test_persist_edit_plan_versions_increment():
    project = Project.objects.create(name="persist-plan")
    draft = Draft.objects.create(project=project)

    plan = {
        "plan_id": "plan_1",
        "objective": "obj",
        "template_id": "hook_benefit_cta_v1",
        "source": "initial_generate",
        "video_context": {},
        "overlays": [
            {
                "id": "ovl1",
                "type": "headline",
                "start_sec": 0.0,
                "end_sec": 1.0,
                "text": "X",
                "position": {"x": 0.5, "y": 0.2, "anchor": "center"},
                "style": {},
            }
        ],
        "constraints": {},
        "reasoning_summary": "x",
    }

    p1 = persist_edit_plan(project, draft, plan, {"critical": [], "warnings": []}, source="initial_generate")
    p2 = persist_edit_plan(project, draft, plan, {"critical": [], "warnings": []}, source="prompt_patch")

    assert p1.version == 1
    assert p2.version == 2
    assert EditPlanArtifact.objects.count() == 2
