from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ReportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    ticker: str
    as_of_date: date
    currency: Literal["USD"] = "USD"
    forecast_years: int = Field(default=5, ge=1, le=20)
    scenario_weights: dict[str, float] = Field(
        default_factory=lambda: {"bear": 0.2, "base": 0.6, "bull": 0.2}
    )
    overrides: dict[str, float] | None = None

    @field_validator("ticker")
    @classmethod
    def ticker_upper(cls, value: str) -> str:
        return value.upper().strip()

    @model_validator(mode="after")
    def validate_weights(self) -> ReportRequest:
        required = {"bear", "base", "bull"}
        if set(self.scenario_weights) != required:
            raise ValueError("scenario_weights must include bear/base/bull only")
        if abs(sum(self.scenario_weights.values()) - 1.0) > 1e-6:
            raise ValueError("scenario_weights must sum to 1")
        return self


class HistoricalFinancials(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    revenue: list[float]
    ebit: list[float]
    tax_rate: list[float]
    da: list[float]
    capex: list[float]
    nwc_change: list[float]
    shares_outstanding: list[float]
    net_debt: list[float]

    @model_validator(mode="after")
    def check_lengths(self) -> HistoricalFinancials:
        sizes = {len(getattr(self, field)) for field in self.__class__.model_fields}
        if len(sizes) != 1:
            raise ValueError("all historical arrays must have matching lengths")
        return self


class MarketInputs(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    price: float = Field(gt=0)
    risk_free_rate: float = Field(gt=0)
    equity_risk_premium: float = Field(gt=0)
    beta: float = Field(gt=0)
    cost_of_debt: float = Field(gt=0)
    marginal_tax_rate: float = Field(ge=0, le=1)
