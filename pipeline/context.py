from __future__ import annotations

from typing import Any

from projects.models import Asset, Project, VideoContext


def _scene_segments(duration_sec: float, segments: int = 4) -> list[dict[str, Any]]:
    if duration_sec <= 0:
        return []
    count = max(1, min(segments, int(duration_sec // 3) + 1))
    chunk = duration_sec / count
    out = []
    for i in range(count):
        start = round(i * chunk, 2)
        end = round(duration_sec if i == count - 1 else (i + 1) * chunk, 2)
        out.append(
            {
                "scene_id": f"scene_{i+1}",
                "start_sec": start,
                "end_sec": end,
                "summary": "High motion gameplay segment",
                "ad_score": round(0.7 + (0.2 * (i % 2)), 2),
            }
        )
    return out


def build_video_context(project: Project, metadata: dict[str, Any]) -> dict[str, Any]:
    duration = float(metadata.get("duration_sec", 0.0))
    scenes = _scene_segments(duration)
    hook_window_end = round(min(max(2.0, duration * 0.2), duration), 2) if duration else 2.0
    return {
        "project_id": str(project.id),
        "template_id": project.template_id,
        "summary": "Gameplay-focused source suitable for ad overlays",
        "video": {
            "duration_sec": duration,
            "width": int(metadata.get("width", 0)),
            "height": int(metadata.get("height", 0)),
            "fps": metadata.get("fps", "0/1"),
            "codec_name": metadata.get("codec_name", "unknown"),
            "format_name": metadata.get("format_name", "unknown"),
        },
        "recommended_windows": {
            "hook": {"start_sec": 0.0, "end_sec": hook_window_end},
            "cta": {"start_sec": round(duration * 0.74, 2), "end_sec": round(duration, 2)},
        },
        "scenes": scenes,
    }


def save_video_context(project: Project, source_asset: Asset, metadata: dict[str, Any]) -> VideoContext:
    context = build_video_context(project, metadata)
    row, _ = VideoContext.objects.update_or_create(
        project=project,
        defaults={
            "source_asset": source_asset,
            "status": VideoContext.Status.READY,
            "context_json": context,
            "error": "",
        },
    )
    return row
