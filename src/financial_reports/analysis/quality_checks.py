from __future__ import annotations

from typing import Any


def check_data_completeness(historical: Any) -> list[str]:
    issues: list[str] = []
    if len(historical.revenue) < 3:
        issues.append("DATA_GAP_CRITICAL")
    return issues


def check_outlier_assumptions(assumptions: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if max(assumptions["revenue_growth_path"]) > 0.25:
        issues.append("ASSUMPTION_OUTLIER_GROWTH")
    return issues


def check_model_stability(dcf_result: Any) -> list[str]:
    return [w for w in dcf_result.warnings if w in {"WACC_G_TIGHT_SPREAD", "NEGATIVE_EQUITY_VALUE"}]
