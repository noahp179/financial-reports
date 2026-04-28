from datetime import date

from financial_reports.models.inputs import ReportRequest
from financial_reports.pipeline.run_report import run_report_pipeline
from financial_reports.reporting.markdown import render_markdown
from financial_reports.settings import load_settings


def test_markdown_snapshot_shape() -> None:
    settings = load_settings("config/report_config.yaml")
    request = ReportRequest(ticker="MSFT", as_of_date=date(2026, 4, 28))
    report = run_report_pipeline(request, settings)
    md = render_markdown(report, "templates/report.md.j2")
    assert md.startswith("# MSFT Valuation Report")
    assert "## Grade" in md
