from __future__ import annotations

from typing import Any

from financial_reports.models.inputs import HistoricalFinancials, MarketInputs
from financial_reports.models.outputs import DCFProjectionYear, DCFResult


def run_dcf(
    historical: HistoricalFinancials,
    market: MarketInputs,
    assumptions: dict[str, Any],
    forecast_years: int,
) -> DCFResult:
    wacc = float(assumptions["wacc"])
    g = float(assumptions["terminal_growth"])
    if wacc <= g:
        raise ValueError("WACC must be greater than terminal growth")
    shares = historical.shares_outstanding[-1]
    if shares <= 0:
        raise ValueError("Shares outstanding must be positive")

    revenue = historical.revenue[-1]
    projection: list[DCFProjectionYear] = []
    total_pv = 0.0
    warnings: list[str] = []
    da = historical.da[-1]
    capex = historical.capex[-1]
    nwc = historical.nwc_change[-1]
    tax = market.marginal_tax_rate

    for i in range(forecast_years):
        year = i + 1
        revenue *= 1 + assumptions["revenue_growth_path"][i]
        margin = assumptions["ebit_margin_path"][i]
        ebit = revenue * margin
        nopat = ebit * (1 - tax)
        fcff = nopat + da - capex - nwc
        discount_factor = (1 + wacc) ** year
        pv_fcff = fcff / discount_factor
        total_pv += pv_fcff
        projection.append(
            DCFProjectionYear(
                year=year,
                revenue=revenue,
                ebit_margin=margin,
                ebit=ebit,
                nopat=nopat,
                fcff=fcff,
                discount_factor=discount_factor,
                pv_fcff=pv_fcff,
            )
        )

    terminal_fcff = projection[-1].fcff * (1 + g)
    terminal_value = terminal_fcff / (wacc - g)
    pv_terminal = terminal_value / ((1 + wacc) ** forecast_years)
    ev = total_pv + pv_terminal
    equity = ev - historical.net_debt[-1]
    intrinsic = equity / shares

    if wacc - g < 0.01:
        warnings.append("WACC_G_TIGHT_SPREAD")
    if intrinsic < 0:
        warnings.append("NEGATIVE_EQUITY_VALUE")

    return DCFResult(
        enterprise_value=ev,
        equity_value=equity,
        intrinsic_value_per_share=intrinsic,
        wacc=wacc,
        terminal_growth=g,
        terminal_value=terminal_value,
        pv_terminal_value=pv_terminal,
        projection=projection,
        warnings=warnings,
    )
