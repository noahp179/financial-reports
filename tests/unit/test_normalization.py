from financial_reports.models.inputs import HistoricalFinancials
from financial_reports.normalization.financials import normalize_historical


def test_normalization_passthrough() -> None:
    hist = HistoricalFinancials(
        revenue=[1, 2],
        ebit=[1, 2],
        tax_rate=[0.2, 0.2],
        da=[1, 1],
        capex=[1, 1],
        nwc_change=[1, 1],
        shares_outstanding=[1, 1],
        net_debt=[1, 1],
    )
    assert normalize_historical(hist) == hist
