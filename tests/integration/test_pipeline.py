from datetime import date

from financial_reports.models.inputs import ReportRequest
from financial_reports.pipeline.run_report import run_report_pipeline
from financial_reports.settings import load_settings


def test_pipeline_end_to_end() -> None:
    settings = load_settings("config/report_config.yaml")
    request = ReportRequest(ticker="MSFT", as_of_date=date(2026, 4, 28))
    output = run_report_pipeline(request, settings)
    assert output.request.ticker == "MSFT"
    assert output.grade.letter_grade in {"A", "B", "C", "D", "F"}
