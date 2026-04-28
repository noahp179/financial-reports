from __future__ import annotations

import json
from pathlib import Path

from financial_reports.models.outputs import ReportOutput


def write_json(report: ReportOutput, out_dir: str | Path) -> Path:
    p = Path(out_dir)
    p.mkdir(parents=True, exist_ok=True)
    out = p / f"{report.request.ticker}_{report.request.as_of_date}_report.json"
    out.write_text(json.dumps(report.model_dump(mode="json"), indent=2))
    return out


def write_markdown(md: str, out_dir: str | Path, ticker: str, as_of: str) -> Path:
    p = Path(out_dir)
    p.mkdir(parents=True, exist_ok=True)
    out = p / f"{ticker}_{as_of}_report.md"
    out.write_text(md)
    return out
