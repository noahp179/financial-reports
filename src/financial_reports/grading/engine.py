from __future__ import annotations

from typing import Any, Literal, cast

from financial_reports.models.grading import GradeComponent, GradeResult
from financial_reports.models.outputs import DCFResult


def _letter(score: float, bands: dict[str, list[float]]) -> Literal["A", "B", "C", "D", "F"]:
    for letter, (low, high) in bands.items():
        if low <= score <= high:
            return cast(Literal["A", "B", "C", "D", "F"], letter)
    return "F"


def grade_report(
    dcf: DCFResult,
    quality_issues: list[str],
    risk_flags: list[str],
    config: dict[str, Any],
    market_price: float,
) -> GradeResult:
    weights = config["grading"]["weights"]
    upside = (dcf.intrinsic_value_per_share - market_price) / market_price
    valuation_score = max(0.0, min(100.0, 50 + upside * 100))
    reasons = ["VAL_UPSIDE_HIGH"] if upside > 0.2 else ["VAL_UPSIDE_LOW"]
    balance_score = 75.0
    cash_flow_score = 70.0
    forecast_score = max(30.0, 90 - 20 * len(quality_issues))
    risk_penalty_base = max(0.0, 100 - 15 * len(risk_flags))

    raw = [
        ("valuation", valuation_score, weights["valuation"], reasons),
        ("balance_sheet", balance_score, weights["balance_sheet"], []),
        ("cash_flow", cash_flow_score, weights["cash_flow"], []),
        ("forecast_quality", forecast_score, weights["forecast_quality"], quality_issues),
        (
            "risk_penalty",
            risk_penalty_base,
            weights["risk_penalty"],
            ["RISK_FLAGS"] if risk_flags else [],
        ),
    ]
    components = [
        GradeComponent(name=n, score=s, weight=w, weighted_score=s * w, reason_codes=r)
        for n, s, w, r in raw
    ]
    total = sum(c.weighted_score for c in components)
    letter_grade = _letter(total, config["grading"]["letter_bands"])
    return GradeResult(
        total_score_0_100=total,
        letter_grade=letter_grade,
        components=components,
        explanation=(
            "Computed from weighted rubric with "
            f"{len(quality_issues)} quality issues and {len(risk_flags)} risks."
        ),
    )
