from __future__ import annotations

from pipeline.ai import GeminiProvider, LocalFallbackProvider, edit_overlays_with_prompt, get_provider
from pipeline.services import build_timeline
from projects.models import Project


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
