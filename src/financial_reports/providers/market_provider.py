from __future__ import annotations

from datetime import date

from financial_reports.models.inputs import HistoricalFinancials, MarketInputs
from financial_reports.providers.sec_provider import MockSecProvider


class MockMarketProvider(MockSecProvider):
    def get_historical_financials(self, ticker: str, as_of: date) -> HistoricalFinancials:
        return super().get_historical_financials(ticker, as_of)

    def get_market_inputs(self, ticker: str, as_of: date) -> MarketInputs:
        return super().get_market_inputs(ticker, as_of)
