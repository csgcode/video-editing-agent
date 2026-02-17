from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from django.core.files import File

from pipeline.services import render_with_overlays
from projects.models import Asset, Project


def _ffmpeg_available() -> bool:
    return subprocess.run(["ffmpeg", "-version"], capture_output=True).returncode == 0


def _make_test_video(path: Path) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "color=c=black:s=360x640:d=2",
        "-c:v",
        "libx264",
        str(path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def _make_test_logo(path: Path) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "color=c=yellow:s=120x60:d=0.1",
        "-frames:v",
        "1",
        str(path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)


pytestmark = pytest.mark.skipif(not _ffmpeg_available(), reason="ffmpeg not available")


@pytest.mark.django_db
def test_render_with_cta_drawbox_succeeds(tmp_path: Path):
    project = Project.objects.create(name="render-test", primary_color="#00A86B")
    src = tmp_path / "source.mp4"
    dst = tmp_path / "out.mp4"
    _make_test_video(src)

    timeline = {
        "overlays": [
            {
                "type": "headline",
                "start_sec": 0.0,
                "end_sec": 1.0,
                "text": "BIG HEADLINE",
                "position": {"x": 0.5, "y": 0.2, "anchor": "center"},
                "style": {"font_size": 48, "color": "white", "box": "black@0.5", "box_border": 10},
            },
            {
                "type": "cta",
                "start_sec": 1.0,
                "end_sec": 2.0,
                "text": "PLAY NOW",
                "position": {"x": 0.5, "y": 0.9, "anchor": "center"},
                "style": {"font_size": 54, "color": "white", "bg": "#00A86B"},
            },
        ]
    }

    render_with_overlays(src, dst, timeline, project)

    assert dst.exists()
    assert dst.stat().st_size > 0


@pytest.mark.django_db
def test_render_with_logo_overlay_succeeds(tmp_path: Path):
    project = Project.objects.create(name="logo-test", primary_color="#00A86B")
    src = tmp_path / "source.mp4"
    dst = tmp_path / "out_logo.mp4"
    logo = tmp_path / "logo.png"
    _make_test_video(src)
    _make_test_logo(logo)

    with logo.open("rb") as fh:
        logo_asset = Asset.objects.create(project=project, asset_type=Asset.AssetType.LOGO)
        logo_asset.file.save("logo.png", File(fh), save=True)

    timeline = {
        "overlays": [
            {
                "type": "logo",
                "start_sec": 0.0,
                "end_sec": 2.0,
                "text": "",
                "position": {"x": 0.04, "y": 0.04, "anchor": "left"},
                "style": {"scale_width": 90},
                "asset_ref": str(logo_asset.id),
            },
            {
                "type": "cta",
                "start_sec": 1.2,
                "end_sec": 2.0,
                "text": "INSTALL",
                "position": {"x": 0.5, "y": 0.9, "anchor": "center"},
                "style": {"font_size": 44, "color": "white", "bg": "#00A86B"},
            },
        ]
    }

    render_with_overlays(src, dst, timeline, project)

    assert dst.exists()
    assert dst.stat().st_size > 0
