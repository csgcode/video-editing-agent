from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)


@dataclass
class CreativeBriefInput:
    prompt: str
    template_id: str


@dataclass
class CreativeBrief:
    angle: str
    tone: str


@dataclass
class CopySet:
    headline: str
    benefit: str
    cta: str


class CopyProvider(Protocol):
    def generate_creative_brief(self, data: CreativeBriefInput) -> CreativeBrief: ...

    def generate_copy(self, brief: CreativeBrief) -> CopySet: ...


class LocalFallbackProvider:
    def generate_creative_brief(self, data: CreativeBriefInput) -> CreativeBrief:
        angle = data.prompt.strip() or "Level up your gameplay"
        return CreativeBrief(angle=angle, tone="direct")

    def generate_copy(self, brief: CreativeBrief) -> CopySet:
        return CopySet(
            headline=brief.angle[:80],
            benefit="Win faster with smarter controls",
            cta="Play Free",
        )


class GeminiProvider:
    def __init__(self, api_key: str, model: str, timeout_seconds: int = 20):
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds

    def generate_creative_brief(self, data: CreativeBriefInput) -> CreativeBrief:
        angle = data.prompt.strip() or "Promote this gameplay"
        return CreativeBrief(angle=angle, tone="high-converting")

    def generate_copy(self, brief: CreativeBrief) -> CopySet:
        prompt = (
            "Generate short mobile ad copy as strict JSON with keys: "
            "headline, benefit, cta. "
            "Rules: headline <= 80 chars, benefit <= 70 chars, cta <= 20 chars. "
            "No markdown, no extra text. "
            f"Context: {brief.angle}. Tone: {brief.tone}."
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.4,
                "maxOutputTokens": 180,
                "responseMimeType": "application/json",
            },
        }
        body = json.dumps(payload).encode("utf-8")
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
            f"?key={self.api_key}"
        )
        request = Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except (HTTPError, URLError, TimeoutError) as exc:
            raise RuntimeError(f"Gemini API request failed: {exc}") from exc

        data = json.loads(raw)
        text = _extract_candidate_text(data)
        if not text:
            raise RuntimeError("Gemini returned no candidate text")

        parsed = json.loads(text)
        return CopySet(
            headline=str(parsed.get("headline", ""))[:80] or "Level up your gameplay",
            benefit=str(parsed.get("benefit", ""))[:70] or "Win faster with smarter controls",
            cta=str(parsed.get("cta", ""))[:20] or "Play Free",
        )


def _extract_candidate_text(payload: dict[str, Any]) -> str:
    candidates = payload.get("candidates", [])
    if not candidates:
        return ""
    parts = candidates[0].get("content", {}).get("parts", [])
    for part in parts:
        text = part.get("text")
        if isinstance(text, str) and text.strip():
            return text.strip()
    return ""


def get_provider() -> CopyProvider:
    provider_name = os.getenv("AI_PROVIDER", "local").strip().lower()
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    timeout_seconds = int(os.getenv("GEMINI_TIMEOUT_SECONDS", "20"))

    if provider_name == "gemini":
        if not gemini_key:
            logger.warning("AI_PROVIDER=gemini but GEMINI_API_KEY is empty; using local fallback provider")
            return LocalFallbackProvider()
        return GeminiProvider(api_key=gemini_key, model=gemini_model, timeout_seconds=timeout_seconds)

    return LocalFallbackProvider()
