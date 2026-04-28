from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class GradeComponent(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    name: str
    score: float = Field(ge=0, le=100)
    weight: float = Field(ge=0, le=1)
    weighted_score: float = Field(ge=0, le=100)
    reason_codes: list[str]


class GradeResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    total_score_0_100: float = Field(ge=0, le=100)
    letter_grade: Literal["A", "B", "C", "D", "F"]
    components: list[GradeComponent]
    explanation: str
