from __future__ import annotations

import uuid

from financial_reports.analysis.quality_checks import (
    check_data_completeness,
    check_model_stability,
    check_outlier_assumptions,
)
from financial_reports.analysis.risk import build_risk_flags
from financial_reports.errors import InternalPipelineError
from financial_reports.grading.engine import grade_report
from financial_reports.models.inputs import ReportRequest
from financial_reports.models.outputs import ReportOutput
from financial_reports.normalization.financials import normalize_historical
from financial_reports.providers.sec_provider import MockSecProvider
from financial_reports.reporting.compose import compose_report
from financial_reports.settings import Settings
from financial_reports.valuation.assumptions import (
    apply_overrides,
    build_base_assumptions,
    build_scenario_assumptions,
)
from financial_reports.valuation.dcf import run_dcf

SCENARIOS = ("bear", "base", "bull")


def run_report_pipeline(request: ReportRequest, settings: Settings) -> ReportOutput:
    provider = MockSecProvider()
    trace_id = str(uuid.uuid4())
    try:
        historical = normalize_historical(
            provider.get_historical_financials(request.ticker, request.as_of_date)
        )
        market = provider.get_market_inputs(request.ticker, request.as_of_date)
        profile = provider.get_company_profile(request.ticker)

        base_assumptions = build_base_assumptions(historical, market, settings.raw)
        base_assumptions = apply_overrides(base_assumptions, request.overrides)

        dcf_results = {}
        quality_issues = check_data_completeness(historical)
        quality_issues.extend(check_outlier_assumptions(base_assumptions))

        for scenario in SCENARIOS:
            scenario_assumptions = build_scenario_assumptions(
                base_assumptions, scenario, settings.raw
            )
            dcf = run_dcf(historical, market, scenario_assumptions, request.forecast_years)
            dcf_results[scenario] = dcf
            quality_issues.extend(check_model_stability(dcf))

        weighted_intrinsic = sum(
            request.scenario_weights[s] * dcf_results[s].intrinsic_value_per_share
            for s in SCENARIOS
        )
        risks = build_risk_flags(historical, base_assumptions)
        grade = grade_report(dcf_results["base"], quality_issues, risks, settings.raw, market.price)
        return compose_report(
            request,
            profile,
            dcf_results,
            weighted_intrinsic,
            grade,
            quality_issues,
            risks,
        )
    except Exception as exc:  # noqa: BLE001
        raise InternalPipelineError(f"INTERNAL_PIPELINE_ERROR trace_id={trace_id}") from exc
