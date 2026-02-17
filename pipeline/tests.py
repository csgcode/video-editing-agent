from __future__ import annotations

from pipeline.ai import GeminiProvider, LocalFallbackProvider, edit_overlays_with_prompt, get_provider
from pipeline.services import build_timeline, compute_overlay_diff, persist_draft_version
from projects.models import Draft, Project


def test_build_timeline_has_three_overlays(db):
    project = Project.objects.create(name="x", prompt="Awesome game")
    timeline = build_timeline(project, duration_sec=30.0, copy={"headline": "H", "benefit": "B", "cta": "C"})
    assert len(timeline["overlays"]) == 3
    assert timeline["overlays"][0]["type"] == "headline"


def test_provider_defaults_to_local(monkeypatch):
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    provider = get_provider()
    assert isinstance(provider, LocalFallbackProvider)


def test_provider_uses_gemini_when_configured(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.0-flash")
    provider = get_provider()
    assert isinstance(provider, GeminiProvider)


def test_provider_falls_back_if_gemini_missing_key(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    provider = get_provider()
    assert isinstance(provider, LocalFallbackProvider)


def test_overlay_prompt_local_makes_text_bigger(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "local")
    overlays = [
        {
            "type": "headline",
            "start_sec": 0.0,
            "end_sec": 2.0,
            "text": "hello",
            "position": {"x": 0.5, "y": 0.2, "anchor": "center"},
            "style": {"font_size": 50},
        }
    ]
    updated = edit_overlays_with_prompt(overlays, "Make it bigger and uppercase")
    assert updated[0]["style"]["font_size"] > 50
    assert updated[0]["text"] == "HELLO"


def test_overlay_prompt_local_updates_cta_text(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "local")
    overlays = [
        {
            "type": "cta",
            "start_sec": 3.0,
            "end_sec": 5.0,
            "text": "Play Free",
            "position": {"x": 0.5, "y": 0.9, "anchor": "center"},
            "style": {"font_size": 64},
        }
    ]
    updated = edit_overlays_with_prompt(overlays, 'Change CTA to "Install Now"')
    assert updated[0]["text"] == "Install Now"


def test_compute_overlay_diff_detects_add_remove_update():
    previous = [
        {"id": "a", "type": "headline", "text": "A", "start_sec": 0, "end_sec": 2, "position": {}, "style": {}},
        {"id": "b", "type": "cta", "text": "Play", "start_sec": 2, "end_sec": 4, "position": {}, "style": {}},
    ]
    current = [
        {"id": "a", "type": "headline", "text": "A+", "start_sec": 0, "end_sec": 2, "position": {}, "style": {}},
        {"id": "c", "type": "callout", "text": "New", "start_sec": 1, "end_sec": 3, "position": {}, "style": {}},
    ]
    diff = compute_overlay_diff(previous, current)
    assert len(diff["updated"]) == 1
    assert diff["updated"][0]["id"] == "a"
    assert len(diff["removed"]) == 1
    assert diff["removed"][0]["id"] == "b"
    assert len(diff["added"]) == 1
    assert diff["added"][0]["id"] == "c"


def test_persist_draft_version_increments(db):
    project = Project.objects.create(name="v")
    draft = Draft.objects.create(project=project)
    timeline_v1 = {"overlays": [{"id": "a", "type": "headline", "start_sec": 0, "end_sec": 2, "position": {}, "style": {}}]}
    timeline_v2 = {"overlays": [{"id": "a", "type": "headline", "text": "X", "start_sec": 0, "end_sec": 2, "position": {}, "style": {}}]}

    v1 = persist_draft_version(draft, timeline_v1, source="initial_generate")
    v2 = persist_draft_version(draft, timeline_v2, source="prompt_patch")

    assert v1.version == 1
    assert v2.version == 2
    assert len(v2.overlay_diff_json["updated"]) == 1
