from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from financial_reports.models.inputs import HistoricalFinancials, MarketInputs


class FinancialDataProvider(ABC):
    @abstractmethod
    def get_historical_financials(self, ticker: str, as_of: date) -> HistoricalFinancials: ...

    @abstractmethod
    def get_market_inputs(self, ticker: str, as_of: date) -> MarketInputs: ...

    @abstractmethod
    def get_company_profile(self, ticker: str) -> dict[str, str]: ...
