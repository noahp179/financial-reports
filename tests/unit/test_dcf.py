from financial_reports.models.inputs import HistoricalFinancials, MarketInputs
from financial_reports.valuation.dcf import run_dcf


def test_run_dcf_returns_positive_intrinsic() -> None:
    hist = HistoricalFinancials(
        revenue=[100, 110, 120],
        ebit=[20, 22, 24],
        tax_rate=[0.2, 0.2, 0.2],
        da=[4, 4, 4],
        capex=[5, 5, 5],
        nwc_change=[1, 1, 1],
        shares_outstanding=[10, 10, 10],
        net_debt=[15, 14, 13],
    )
    market = MarketInputs(
        price=20,
        risk_free_rate=0.04,
        equity_risk_premium=0.05,
        beta=1.0,
        cost_of_debt=0.05,
        marginal_tax_rate=0.2,
    )
    assumptions = {
        "revenue_growth_path": [0.05] * 5,
        "ebit_margin_path": [0.2] * 5,
        "wacc": 0.1,
        "terminal_growth": 0.03,
    }
    result = run_dcf(hist, market, assumptions, 5)
    assert result.intrinsic_value_per_share > 0
