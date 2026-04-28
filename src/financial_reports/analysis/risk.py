from __future__ import annotations

from typing import Any

from financial_reports.models.inputs import HistoricalFinancials


def build_risk_flags(historical: HistoricalFinancials, assumptions: dict[str, Any]) -> list[str]:
    risks: list[str] = []
    if historical.net_debt[-1] > historical.ebit[-1] * 2:
        risks.append("Leverage risk elevated due to high net debt relative to EBIT.")
    if min(assumptions["ebit_margin_path"]) < historical.ebit[-1] / historical.revenue[-1]:
        risks.append("Margin compression risk in downside assumptions.")
    risks.append("Macro sensitivity: valuation is sensitive to rates via WACC and terminal spread.")
    return risks
