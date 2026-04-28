from __future__ import annotations

from copy import deepcopy
from typing import Any, cast

from financial_reports.models.inputs import HistoricalFinancials, MarketInputs


def build_base_assumptions(
    historical: HistoricalFinancials, market: MarketInputs, config: dict[str, Any]
) -> dict[str, float | list[float]]:
    years = int(config["valuation"]["forecast_years"])
    last_revenue = historical.revenue[-1]
    growth = (historical.revenue[-1] / historical.revenue[0]) ** (
        1 / (len(historical.revenue) - 1)
    ) - 1
    last_margin = historical.ebit[-1] / max(last_revenue, 1e-9)
    target_margin = min(last_margin + 0.01, 0.5)
    margin_path = [
        last_margin + (target_margin - last_margin) * (i + 1) / years for i in range(years)
    ]
    wacc = market.risk_free_rate + market.beta * market.equity_risk_premium
    terminal_growth = min(
        config["valuation"]["terminal_growth"]["default"], market.risk_free_rate - 0.005
    )
    return {
        "revenue_growth_path": [growth for _ in range(years)],
        "ebit_margin_path": margin_path,
        "reinvestment_rate": 0.25,
        "wacc": max(
            config["valuation"]["wacc"]["floor"], min(wacc, config["valuation"]["wacc"]["cap"])
        ),
        "terminal_growth": terminal_growth,
    }


def apply_overrides(
    assumptions: dict[str, float | list[float]], overrides: dict[str, float] | None
) -> dict[str, float | list[float]]:
    if overrides is None:
        return assumptions
    merged = deepcopy(assumptions)
    for key, value in overrides.items():
        merged[key] = value
    return merged


def build_scenario_assumptions(
    base_assumptions: dict[str, float | list[float]],
    scenario: str,
    config: dict[str, Any] | None = None,
) -> dict[str, float | list[float]]:
    out = deepcopy(base_assumptions)
    if config is None:
        return out
    delta = config.get("scenarios", {}).get(scenario, {})
    revenue_delta = float(delta.get("revenue_cagr_delta", 0.0))
    margin_delta = float(delta.get("margin_delta", 0.0))
    revenue_growth_path = cast(list[float], out["revenue_growth_path"])
    ebit_margin_path = cast(list[float], out["ebit_margin_path"])
    out["revenue_growth_path"] = [x + revenue_delta for x in revenue_growth_path]
    out["ebit_margin_path"] = [x + margin_delta for x in ebit_margin_path]
    return out
