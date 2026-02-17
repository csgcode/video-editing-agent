from __future__ import annotations

from pipeline.context import build_video_context, save_video_context
from projects.models import Asset, Project, VideoContext


def test_build_video_context_has_expected_shape(db):
    project = Project.objects.create(name="ctx", template_id="hook_benefit_cta_v1")
    metadata = {
        "duration_sec": 24.0,
        "width": 1080,
        "height": 1920,
        "fps": "30/1",
        "codec_name": "h264",
        "format_name": "mov,mp4,m4a,3gp,3g2,mj2",
    }
    context = build_video_context(project, metadata)
    assert context["project_id"] == str(project.id)
    assert len(context["scenes"]) >= 1
    assert context["recommended_windows"]["hook"]["start_sec"] == 0.0


def test_save_video_context_upserts(db):
    project = Project.objects.create(name="ctx-save")
    asset = Asset.objects.create(project=project, asset_type=Asset.AssetType.SOURCE_VIDEO, file="assets/source.mp4")
    metadata_a = {"duration_sec": 10.0, "width": 100, "height": 200, "fps": "30/1", "codec_name": "h264", "format_name": "mp4"}
    metadata_b = {"duration_sec": 20.0, "width": 100, "height": 200, "fps": "30/1", "codec_name": "h264", "format_name": "mp4"}

    row1 = save_video_context(project, asset, metadata_a)
    row2 = save_video_context(project, asset, metadata_b)

    assert row1.id == row2.id
    assert VideoContext.objects.count() == 1
    assert float(row2.context_json["video"]["duration_sec"]) == 20.0
