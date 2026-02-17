from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


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

    @model_validator(mode="after")
    def validate_timing(self):
        if self.end_sec <= self.start_sec:
            raise ValueError("overlay end_sec must be greater than start_sec")
        return self


class DraftTimeline(BaseModel):
    template_id: str
    overlays: list[OverlayItem]
    copy_variants: dict = Field(default_factory=dict)


class EditPlan(BaseModel):
    plan_id: str
    objective: str
    template_id: str
    source: str = "auto"
    video_context: dict = Field(default_factory=dict)
    overlays: list[OverlayItem]
    constraints: dict = Field(default_factory=dict)
    reasoning_summary: str = ""
