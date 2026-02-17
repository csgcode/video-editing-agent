from __future__ import annotations

from pipeline.ai import GeminiProvider, LocalFallbackProvider, get_provider
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
