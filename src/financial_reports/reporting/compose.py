from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from financial_reports.models.grading import GradeResult
from financial_reports.models.inputs import ReportRequest
from financial_reports.models.outputs import DCFResult, ReportOutput


def compose_report(
    request: ReportRequest,
    company_profile: dict[str, Any],
    dcf_by_scenario: dict[str, DCFResult],
    weighted_intrinsic: float,
    grade: GradeResult,
    quality_issues: list[str],
    risks: list[str],
) -> ReportOutput:
    valuation = {
        "scenarios": {k: v.model_dump() for k, v in dcf_by_scenario.items()},
        "weighted_intrinsic_value_per_share": weighted_intrinsic,
        "confidence_flags": quality_issues,
    }
    narrative = {
        "executive_summary": f"Estimated intrinsic value is {weighted_intrinsic:.2f} per share.",
        "methodology": "Discounted cash flow with bear/base/bull scenario weighting.",
        "grade_summary": grade.explanation,
    }
    return ReportOutput(
        request=request,
        company_summary=company_profile,
        financial_health={"quality_issues": quality_issues},
        valuation=valuation,
        grade=grade,
        risks=risks,
        narrative_sections=narrative,
        generated_at_utc=datetime.now(UTC),
    )
