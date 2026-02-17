from __future__ import annotations

from typing import Any


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def validate_plan_quality(overlays: list[dict[str, Any]], duration_sec: float) -> dict[str, list[str]]:
    critical: list[str] = []
    warnings: list[str] = []

    has_cta = False
    has_hook_text = False

    for idx, overlay in enumerate(overlays):
        kind = str(overlay.get("type", "")).strip().lower()
        if kind == "cta":
            has_cta = True
        if kind in {"headline", "callout"}:
            has_hook_text = True

        start = _as_float(overlay.get("start_sec"), -1)
        end = _as_float(overlay.get("end_sec"), -1)
        if start < 0 or end <= start:
            critical.append(f"overlay[{idx}] has invalid timing")
        if duration_sec > 0 and end > duration_sec + 0.01:
            critical.append(f"overlay[{idx}] end exceeds video duration")

        pos = overlay.get("position", {}) if isinstance(overlay.get("position"), dict) else {}
        x = _as_float(pos.get("x"), -1)
        y = _as_float(pos.get("y"), -1)
        if x < 0 or x > 1 or y < 0 or y > 1:
            critical.append(f"overlay[{idx}] has out-of-bounds position")

        style = overlay.get("style", {}) if isinstance(overlay.get("style"), dict) else {}
        font_size = _as_float(style.get("font_size"), 0)
        if kind in {"headline", "callout", "cta"} and font_size and font_size < 36:
            warnings.append(f"overlay[{idx}] font_size is low ({int(font_size)})")

    if not has_cta:
        critical.append("missing cta overlay")
    if not has_hook_text:
        critical.append("missing headline/callout overlay")

    return {"critical": critical, "warnings": warnings}
