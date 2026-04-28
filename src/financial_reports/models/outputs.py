from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from financial_reports.models.grading import GradeResult
from financial_reports.models.inputs import ReportRequest


class DCFProjectionYear(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    year: int
    revenue: float
    ebit_margin: float
    ebit: float
    nopat: float
    fcff: float
    discount_factor: float
    pv_fcff: float


class DCFResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    enterprise_value: float
    equity_value: float
    intrinsic_value_per_share: float
    wacc: float
    terminal_growth: float
    terminal_value: float
    pv_terminal_value: float
    projection: list[DCFProjectionYear]
    sensitivity_table: dict[str, float] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class ReportOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    request: ReportRequest
    company_summary: dict[str, Any]
    financial_health: dict[str, Any]
    valuation: dict[str, Any]
    grade: GradeResult
    risks: list[str]
    narrative_sections: dict[str, str]
    generated_at_utc: datetime
