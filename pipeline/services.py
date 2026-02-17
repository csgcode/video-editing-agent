from __future__ import annotations

import json
import subprocess
import uuid
from datetime import UTC, datetime
from pathlib import Path

from django.conf import settings

from pipeline.ai import CreativeBriefInput, get_provider
from projects.models import Asset, Draft, DraftVersion, Overlay, Project


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


def _logo_asset(project: Project) -> Asset | None:
    return project.assets.filter(asset_type=Asset.AssetType.LOGO).order_by("-created_at").first()


def _template_hook_benefit_cta(project: Project, duration_sec: float, copy: dict) -> list[dict]:
    section_a = round(duration_sec * 0.22, 2)
    section_b = round(duration_sec * 0.74, 2)
    overlays = [
        {
            "id": f"ovl_{uuid.uuid4().hex[:8]}",
            "type": "headline",
            "start_sec": 0.0,
            "end_sec": max(2.0, section_a),
            "text": copy["headline"].upper(),
            "position": {"x": 0.5, "y": 0.16, "anchor": "center"},
            "style": {"font_size": 96, "color": "white", "box": "black@0.55", "box_border": 22},
        },
        {
            "id": f"ovl_{uuid.uuid4().hex[:8]}",
            "type": "callout",
            "start_sec": section_a,
            "end_sec": max(section_a + 1.5, section_b),
            "text": copy["benefit"],
            "position": {"x": 0.5, "y": 0.78, "anchor": "center"},
            "style": {"font_size": 64, "color": "white", "box": "black@0.45", "box_border": 18},
        },
        {
            "id": f"ovl_{uuid.uuid4().hex[:8]}",
            "type": "cta",
            "start_sec": section_b,
            "end_sec": duration_sec,
            "text": copy["cta"],
            "position": {"x": 0.5, "y": 0.9, "anchor": "center"},
            "style": {"font_size": 82, "color": "white", "bg": project.primary_color},
        },
    ]
    return overlays


def _template_problem_solution_cta(project: Project, duration_sec: float, copy: dict) -> list[dict]:
    section_a = round(duration_sec * 0.30, 2)
    section_b = round(duration_sec * 0.76, 2)
    overlays = [
        {
            "id": f"ovl_{uuid.uuid4().hex[:8]}",
            "type": "headline",
            "start_sec": 0.0,
            "end_sec": max(2.2, section_a),
            "text": f"STUCK? {copy['headline'][:48].upper()}",
            "position": {"x": 0.5, "y": 0.14, "anchor": "center"},
            "style": {"font_size": 88, "color": "white", "box": "black@0.6", "box_border": 24},
        },
        {
            "id": f"ovl_{uuid.uuid4().hex[:8]}",
            "type": "callout",
            "start_sec": section_a,
            "end_sec": max(section_a + 1.2, section_b),
            "text": f"SOLUTION: {copy['benefit']}",
            "position": {"x": 0.5, "y": 0.74, "anchor": "center"},
            "style": {"font_size": 62, "color": "white", "box": "black@0.45", "box_border": 16},
        },
        {
            "id": f"ovl_{uuid.uuid4().hex[:8]}",
            "type": "cta",
            "start_sec": section_b,
            "end_sec": duration_sec,
            "text": copy["cta"],
            "position": {"x": 0.5, "y": 0.9, "anchor": "center"},
            "style": {"font_size": 78, "color": "white", "bg": project.primary_color},
        },
    ]
    return overlays


def build_timeline(project: Project, duration_sec: float, copy: dict) -> dict:
    if project.template_id == "problem_solution_cta_v1":
        overlays = _template_problem_solution_cta(project, duration_sec, copy)
    else:
        overlays = _template_hook_benefit_cta(project, duration_sec, copy)

    logo = _logo_asset(project)
    if logo:
        overlays.append(
            {
                "id": f"ovl_{uuid.uuid4().hex[:8]}",
                "type": "logo",
                "start_sec": 0.0,
                "end_sec": duration_sec,
                "text": "",
                "position": {"x": 0.04, "y": 0.04, "anchor": "left"},
                "style": {"scale_width": 220},
                "asset_ref": str(logo.id),
            }
        )

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
            "model_provider": "phase1_provider",
            "created_at": datetime.now(tz=UTC).isoformat(),
        },
    }


def _escape_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def _hex_to_ffmpeg_color(value: str, default: str = "0x00A86B") -> str:
    raw = (value or "").strip()
    if raw.startswith("#") and len(raw) == 7:
        return f"0x{raw[1:]}"
    return default


def _text_x_expr(position: dict) -> str:
    anchor = position.get("anchor", "center")
    x = float(position.get("x", 0.5))
    if anchor == "left":
        return f"w*{x}"
    if anchor == "right":
        return f"w*{x}-text_w"
    return f"(w-text_w)*{x}"


def _overlay_key(item: dict, idx: int) -> str:
    key = str(item.get("id", "")).strip()
    if key:
        return key
    return f"idx_{idx}"


def compute_overlay_diff(previous: list[dict], current: list[dict]) -> dict:
    prev_map = {_overlay_key(item, i): item for i, item in enumerate(previous)}
    curr_map = {_overlay_key(item, i): item for i, item in enumerate(current)}

    added = []
    removed = []
    updated = []

    for key, item in curr_map.items():
        if key not in prev_map:
            added.append({"id": key, "overlay": item})
        elif prev_map[key] != item:
            updated.append({"id": key, "before": prev_map[key], "after": item})

    for key, item in prev_map.items():
        if key not in curr_map:
            removed.append({"id": key, "overlay": item})

    return {"added": added, "removed": removed, "updated": updated}


def persist_draft_version(draft: Draft, timeline: dict, source: str) -> DraftVersion:
    latest = draft.versions.first()
    previous_overlays = latest.timeline_json.get("overlays", []) if latest else []
    current_overlays = timeline.get("overlays", [])
    next_version = (latest.version + 1) if latest else 1
    diff = compute_overlay_diff(previous_overlays, current_overlays)
    return DraftVersion.objects.create(
        draft=draft,
        version=next_version,
        source=source,
        timeline_json=timeline,
        overlay_diff_json=diff,
        draft_video_name=draft.draft_video.name if draft.draft_video else "",
    )


def render_with_overlays(src: Path, dst: Path, timeline: dict, project: Project) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    overlays = timeline.get("overlays", [])

    cmd = ["ffmpeg", "-y", "-i", str(src)]
    logo_inputs: dict[str, int] = {}

    for overlay in overlays:
        if overlay.get("type") != "logo":
            continue
        asset_ref = str(overlay.get("asset_ref", "")).strip()
        if not asset_ref or asset_ref in logo_inputs:
            continue
        asset = project.assets.filter(id=asset_ref, asset_type=Asset.AssetType.LOGO).first()
        if asset and asset.file:
            logo_inputs[asset_ref] = len(cmd)  # placeholder not used directly
            cmd.extend(["-i", asset.file.path])

    filters: list[str] = ["[0:v]format=yuv420p[v0]"]
    current = "v0"
    tag_idx = 1

    for overlay in overlays:
        otype = overlay.get("type", "callout")
        start = float(overlay.get("start_sec", 0))
        end = float(overlay.get("end_sec", 1))
        pos = overlay.get("position", {})
        style = overlay.get("style", {})

        if otype == "logo":
            asset_ref = str(overlay.get("asset_ref", "")).strip()
            if not asset_ref:
                continue
            input_order = list(logo_inputs.keys())
            if asset_ref not in input_order:
                continue
            stream_index = input_order.index(asset_ref) + 1
            logo_tag = f"lg{tag_idx}"
            out_tag = f"v{tag_idx}"
            tag_idx += 1
            scale_width = int(style.get("scale_width", 220))
            filters.append(f"[{stream_index}:v]scale={scale_width}:-1[{logo_tag}]")
            filters.append(
                f"[{current}][{logo_tag}]overlay=x=(W-w)*{float(pos.get('x', 0.04))}:"
                f"y=(H-h)*{float(pos.get('y', 0.04))}:enable='between(t,{start},{end})'[{out_tag}]"
            )
            current = out_tag
            continue

        text = _escape_text(overlay.get("text", ""))
        font_size = int(style.get("font_size", 64))
        color = style.get("color", "white")
        x_expr = _text_x_expr(pos)
        y_expr = f"h*{float(pos.get('y', 0.5))}-text_h/2"

        if otype == "cta":
            cta_bg = _hex_to_ffmpeg_color(str(style.get("bg", project.primary_color)))
            box_tag = f"v{tag_idx}"
            tag_idx += 1
            filters.append(
                f"[{current}]drawbox=x=iw*0.16:y=ih*{float(pos.get('y', 0.9))}-ih*0.055:"
                f"w=iw*0.68:h=ih*0.11:color={cta_bg}@0.92:t=fill:enable='between(t,{start},{end})'[{box_tag}]"
            )
            current = box_tag

        out_tag = f"v{tag_idx}"
        tag_idx += 1
        box = style.get("box", "black@0.4")
        box_border = int(style.get("box_border", 18))
        draw = (
            f"[{current}]drawtext=text='{text}':x={x_expr}:y={y_expr}:"
            f"fontsize={font_size}:fontcolor={color}:box=1:boxcolor={box}:boxborderw={box_border}:"
            f"enable='between(t,{start},{end})'[{out_tag}]"
        )
        filters.append(draw)
        current = out_tag

    filter_complex = ";".join(filters)
    cmd.extend(
        [
            "-filter_complex",
            filter_complex,
            "-map",
            f"[{current}]",
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
    )
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
        asset_ref = str(overlay.get("asset_ref", "")).strip()
        asset = None
        if asset_ref:
            asset = draft.project.assets.filter(id=asset_ref).first()
        rows.append(
            Overlay(
                draft=draft,
                overlay_type=overlay.get("type", "callout"),
                start_sec=float(overlay.get("start_sec", 0.0)),
                end_sec=float(overlay.get("end_sec", 1.0)),
                text=overlay.get("text", ""),
                position=overlay.get("position", {}),
                style=overlay.get("style", {}),
                asset=asset,
            )
        )
    Overlay.objects.bulk_create(rows)


def rerender_draft(project: Project, draft: Draft, timeline: dict, source: str = "manual_patch") -> None:
    source_asset = source_video_asset(project)
    src_path = Path(source_asset.file.path)
    normalized = Path(settings.MEDIA_ROOT) / "normalized" / f"{project.id}.mp4"
    if not normalized.exists():
        normalize_video(src_path, normalized)

    draft_path = Path(settings.MEDIA_ROOT) / "drafts" / f"{project.id}-{uuid.uuid4().hex[:6]}.mp4"
    render_with_overlays(normalized, draft_path, timeline, project)
    rel = draft_path.relative_to(Path(settings.MEDIA_ROOT))

    draft.timeline_json = timeline
    draft.draft_video.name = str(rel)
    draft.status = Draft.Status.READY
    draft.error = ""
    draft.save(update_fields=["timeline_json", "draft_video", "status", "error", "updated_at"])
    rebuild_overlays(draft, timeline)
    persist_draft_version(draft, timeline, source=source)
