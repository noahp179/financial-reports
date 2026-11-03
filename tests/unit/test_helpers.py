from datetime import date
from pathlib import Path

from financial_reports.analysis.risk import build_risk_flags
from financial_reports.logging_setup import configure_logging
from financial_reports.models.inputs import ReportRequest
from financial_reports.pipeline.run_report import run_report_pipeline
from financial_reports.providers.cache import DiskCache
from financial_reports.providers.market_provider import MockMarketProvider
from financial_reports.reporting.export import write_json, write_markdown
from financial_reports.reporting.html import render_html
from financial_reports.settings import load_settings
from financial_reports.utils.dates import parse_iso_date
from financial_reports.utils.maths import clamp


def _report():
    settings = load_settings("config/report_config.yaml")
    return run_report_pipeline(ReportRequest(ticker="MSFT", as_of_date=date(2026, 4, 28)), settings)


def test_parse_iso_date() -> None:
    assert parse_iso_date("2026-04-28") == date(2026, 4, 28)


def test_clamp() -> None:
    assert clamp(5, 0, 1) == 1
    assert clamp(-5, 0, 1) == 0
    assert clamp(0.5, 0, 1) == 0.5


def test_configure_logging() -> None:
    configure_logging("config/logging.yaml")


def test_disk_cache_round_trip_and_expiry(tmp_path: Path) -> None:
    cache = DiskCache(tmp_path / "cache", ttl_seconds=60)
    assert cache.get("ns", "k") is None
    cache.set("ns", "k", {"a": 1})
    assert cache.get("ns", "k") == {"a": 1}

    expired = DiskCache(tmp_path / "expired", ttl_seconds=-1)
    expired.set("ns", "k", {"a": 1})
    assert expired.get("ns", "k") is None


def test_disk_cache_ignores_malformed_entries(tmp_path: Path) -> None:
    cache = DiskCache(tmp_path)
    cache._path("ns", "list").write_text("[1, 2]")
    assert cache.get("ns", "list") is None
    cache._path("ns", "bad").write_text('{"expires_at": "2999-01-01T00:00:00+00:00", "payload": 3}')
    assert cache.get("ns", "bad") is None


def test_exports_and_html(tmp_path: Path) -> None:
    report = _report()
    json_path = write_json(report, tmp_path)
    md_path = write_markdown("# hi", tmp_path, "MSFT", "2026-04-28")
    assert json_path.exists() and md_path.read_text() == "# hi"
    assert "MSFT" in render_html(report, "templates/report.html.j2")


def test_market_provider_and_risk_flags() -> None:
    provider = MockMarketProvider()
    as_of = date(2026, 4, 28)
    historical = provider.get_historical_financials("MSFT", as_of)
    assert provider.get_market_inputs("MSFT", as_of) is not None
    flags = build_risk_flags(historical, {"ebit_margin_path": [0.0]})
    assert any("Margin compression" in f for f in flags)
