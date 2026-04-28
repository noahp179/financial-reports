from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Literal

import typer
from pydantic import ValidationError as PydanticValidationError

from financial_reports.models.inputs import ReportRequest
from financial_reports.pipeline.run_report import run_report_pipeline
from financial_reports.reporting.export import write_json, write_markdown
from financial_reports.reporting.html import render_html
from financial_reports.reporting.markdown import render_markdown
from financial_reports.settings import load_settings

app = typer.Typer(help="Financial reports CLI")


@app.command("generate")
def generate(
    ticker: str = typer.Option(...),
    as_of: str = typer.Option(..., "--as-of"),
    config: str = typer.Option("config/report_config.yaml"),
    out_dir: str = typer.Option("out", "--out-dir"),
    fmt: Literal["json", "md", "html", "all"] = typer.Option("all", "--format"),
) -> None:
    try:
        settings = load_settings(config)
        request = ReportRequest(ticker=ticker, as_of_date=date.fromisoformat(as_of))
        report = run_report_pipeline(request, settings)
        if fmt in {"json", "all"}:
            write_json(report, out_dir)
        if fmt in {"md", "all"}:
            md = render_markdown(report, "templates/report.md.j2")
            write_markdown(md, out_dir, ticker.upper(), as_of)
        if fmt in {"html", "all"}:
            html = render_html(report, "templates/report.html.j2")
            out = Path(out_dir)
            out.mkdir(parents=True, exist_ok=True)
            (out / f"{ticker.upper()}_{as_of}_report.html").write_text(html)
        raise typer.Exit(0)
    except PydanticValidationError as exc:
        typer.echo(str(exc))
        raise typer.Exit(2) from exc


@app.command("grade-only")
def grade_only(path: str = typer.Argument(...)) -> None:
    data = json.loads(Path(path).read_text())
    typer.echo(
        "Existing grade: "
        f"{data['grade']['letter_grade']} "
        f"({data['grade']['total_score_0_100']:.2f})"
    )


@app.command("validate-config")
def validate_config(config: str = typer.Option("config/report_config.yaml")) -> None:
    load_settings(config)
    typer.echo("Config valid")
