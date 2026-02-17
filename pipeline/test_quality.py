from __future__ import annotations

from pipeline.quality import validate_plan_quality


def test_quality_gate_passes_valid_overlays():
    overlays = [
        {
            "id": "h1",
            "type": "headline",
            "start_sec": 0.0,
            "end_sec": 2.0,
            "position": {"x": 0.5, "y": 0.2},
            "style": {"font_size": 64},
        },
        {
            "id": "c1",
            "type": "cta",
            "start_sec": 2.0,
            "end_sec": 4.0,
            "position": {"x": 0.5, "y": 0.9},
            "style": {"font_size": 64},
        },
    ]
    report = validate_plan_quality(overlays, duration_sec=4.0)
    assert report["critical"] == []


def test_quality_gate_blocks_missing_cta_and_bad_timing():
    overlays = [
        {
            "id": "h1",
            "type": "headline",
            "start_sec": 2.0,
            "end_sec": 1.0,
            "position": {"x": 0.5, "y": 0.2},
            "style": {"font_size": 64},
        }
    ]
    report = validate_plan_quality(overlays, duration_sec=4.0)
    assert any("invalid timing" in msg for msg in report["critical"])
    assert any("missing cta" in msg for msg in report["critical"])


def test_quality_gate_warns_small_font_size():
    overlays = [
        {
            "id": "h1",
            "type": "headline",
            "start_sec": 0.0,
            "end_sec": 1.0,
            "position": {"x": 0.5, "y": 0.2},
            "style": {"font_size": 20},
        },
        {
            "id": "c1",
            "type": "cta",
            "start_sec": 1.0,
            "end_sec": 2.0,
            "position": {"x": 0.5, "y": 0.9},
            "style": {"font_size": 44},
        },
    ]
    report = validate_plan_quality(overlays, duration_sec=2.0)
    assert report["critical"] == []
    assert any("font_size is low" in msg for msg in report["warnings"])
