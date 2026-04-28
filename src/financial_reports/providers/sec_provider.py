from __future__ import annotations

from datetime import date

from financial_reports.models.inputs import HistoricalFinancials, MarketInputs
from financial_reports.providers.base import FinancialDataProvider


class MockSecProvider(FinancialDataProvider):
    """Fixture-backed provider for deterministic integration testing."""

    def get_historical_financials(self, ticker: str, as_of: date) -> HistoricalFinancials:
        return HistoricalFinancials(
            revenue=[100, 108, 117, 125],
            ebit=[20, 23, 25, 28],
            tax_rate=[0.2, 0.2, 0.2, 0.2],
            da=[4, 4.2, 4.5, 4.7],
            capex=[5, 5.4, 5.8, 6.2],
            nwc_change=[1.0, 1.2, 1.4, 1.5],
            shares_outstanding=[10, 10, 10, 10],
            net_debt=[20, 19, 18, 17],
        )

    def get_market_inputs(self, ticker: str, as_of: date) -> MarketInputs:
        return MarketInputs(
            price=28,
            risk_free_rate=0.04,
            equity_risk_premium=0.05,
            beta=1.1,
            cost_of_debt=0.055,
            marginal_tax_rate=0.21,
        )

    def get_company_profile(self, ticker: str) -> dict[str, str]:
        return {"ticker": ticker.upper(), "name": f"{ticker.upper()} Corp", "sector": "Technology"}
