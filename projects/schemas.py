from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class OverlayPosition(BaseModel):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    anchor: Literal["left", "center", "right"] = "center"


class OverlayItem(BaseModel):
    id: str
    type: str
    start_sec: float = Field(ge=0)
    end_sec: float = Field(gt=0)
    text: str = ""
    position: OverlayPosition
    style: dict = Field(default_factory=dict)


class DraftTimeline(BaseModel):
    template_id: str
    overlays: list[OverlayItem]
    copy_variants: dict = Field(default_factory=dict)
