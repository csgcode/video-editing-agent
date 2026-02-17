from __future__ import annotations

import json
import subprocess
import uuid
from datetime import UTC, datetime
from pathlib import Path

from django.conf import settings

from pipeline.ai import CreativeBriefInput, get_provider
from projects.models import Asset, Draft, Overlay, Project


class PipelineError(Exception):
    pass


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise PipelineError(proc.stderr.strip() or "subprocess command failed")


def ffprobe_metadata(path: Path) -> dict:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_streams",
        "-show_format",
        "-print_format",
        "json",
        str(path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise PipelineError(proc.stderr.strip() or "ffprobe failed")
    data = json.loads(proc.stdout)
    video_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
    if not video_stream:
        raise PipelineError("No video stream found")
    duration = float(data.get("format", {}).get("duration", 0.0))
    return {
        "duration_sec": duration,
        "width": int(video_stream.get("width", 0)),
        "height": int(video_stream.get("height", 0)),
        "fps": video_stream.get("r_frame_rate", "0/1"),
        "codec_name": video_stream.get("codec_name"),
        "format_name": data.get("format", {}).get("format_name"),
    }


def normalize_video(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    vf = (
        f"scale={settings.TARGET_WIDTH}:{settings.TARGET_HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={settings.TARGET_WIDTH}:{settings.TARGET_HEIGHT}:(ow-iw)/2:(oh-ih)/2,format=yuv420p"
    )
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(src),
        "-vf",
        vf,
        "-r",
        str(settings.TARGET_FPS),
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-c:a",
        "aac",
        str(dst),
    ]
    _run(cmd)


def generate_copy(prompt: str, template_id: str) -> dict:
    provider = get_provider()
    brief = provider.generate_creative_brief(CreativeBriefInput(prompt=prompt, template_id=template_id))
    copy = provider.generate_copy(brief)
    return {"headline": copy.headline, "benefit": copy.benefit, "cta": copy.cta}


def build_timeline(project: Project, duration_sec: float, copy: dict) -> dict:
    section_a = round(duration_sec * 0.2, 2)
    section_b = round(duration_sec * 0.75, 2)
    overlays = [
        {
            "id": f"ovl_{uuid.uuid4().hex[:8]}",
            "type": "headline",
            "start_sec": 0.0,
            "end_sec": max(1.5, section_a),
            "text": copy["headline"],
            "position": {"x": 0.5, "y": 0.1, "anchor": "center"},
            "style": {"font_size": 56, "color": "white"},
        },
        {
            "id": f"ovl_{uuid.uuid4().hex[:8]}",
            "type": "callout",
            "start_sec": section_a,
            "end_sec": max(section_a + 1.0, section_b),
            "text": copy["benefit"],
            "position": {"x": 0.5, "y": 0.82, "anchor": "center"},
            "style": {"font_size": 44, "color": "white"},
        },
        {
            "id": f"ovl_{uuid.uuid4().hex[:8]}",
            "type": "cta",
            "start_sec": section_b,
            "end_sec": duration_sec,
            "text": copy["cta"],
            "position": {"x": 0.5, "y": 0.9, "anchor": "center"},
            "style": {"font_size": 48, "color": "white", "bg": project.primary_color},
        },
    ]
    return {
        "project_id": str(project.id),
        "template_id": project.template_id,
        "video": {
            "duration_sec": duration_sec,
            "width": settings.TARGET_WIDTH,
            "height": settings.TARGET_HEIGHT,
            "fps": settings.TARGET_FPS,
        },
        "copy_variants": {
            "headline": [copy["headline"]],
            "cta": [copy["cta"]],
        },
        "overlays": overlays,
        "generation": {
            "model_provider": "fallback_local",
            "created_at": datetime.now(tz=UTC).isoformat(),
        },
    }


def _escape_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def render_with_overlays(src: Path, dst: Path, timeline: dict) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    filters: list[str] = []
    filters.append("[0:v]format=yuv420p[base]")

    for i, overlay in enumerate(timeline.get("overlays", [])):
        in_tag = "base" if i == 0 else f"v{i}"
        out_tag = f"v{i+1}"
        text = _escape_text(overlay.get("text", ""))
        start = float(overlay.get("start_sec", 0))
        end = float(overlay.get("end_sec", 1))
        font_size = int(overlay.get("style", {}).get("font_size", 42))

        draw = (
            f"[{in_tag}]drawtext=text='{text}':x=(w-text_w)/2:y=h*{overlay['position']['y']}-text_h/2:"
            f"fontsize={font_size}:fontcolor=white:box=1:boxcolor=black@0.4:boxborderw=16:"
            f"enable='between(t,{start},{end})'[{out_tag}]"
        )
        filters.append(draw)

    filter_complex = ";".join(filters)
    last = f"v{len(timeline.get('overlays', []))}" if timeline.get("overlays") else "base"
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(src),
        "-filter_complex",
        filter_complex,
        "-map",
        f"[{last}]",
        "-map",
        "0:a?",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-c:a",
        "aac",
        str(dst),
    ]
    _run(cmd)


def source_video_asset(project: Project) -> Asset:
    asset = project.assets.filter(asset_type=Asset.AssetType.SOURCE_VIDEO).order_by("-created_at").first()
    if not asset:
        raise PipelineError("Project has no source video uploaded")
    return asset


def rebuild_overlays(draft: Draft, timeline_json: dict) -> None:
    draft.overlays.all().delete()
    rows = []
    for overlay in timeline_json.get("overlays", []):
        rows.append(
            Overlay(
                draft=draft,
                overlay_type=overlay.get("type", "callout"),
                start_sec=float(overlay.get("start_sec", 0.0)),
                end_sec=float(overlay.get("end_sec", 1.0)),
                text=overlay.get("text", ""),
                position=overlay.get("position", {}),
                style=overlay.get("style", {}),
            )
        )
    Overlay.objects.bulk_create(rows)
