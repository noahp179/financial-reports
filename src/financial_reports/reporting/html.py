from __future__ import annotations

from pathlib import Path

from jinja2 import Template

from financial_reports.models.outputs import ReportOutput


def render_html(report: ReportOutput, template_path: str) -> str:
    template = Template(Path(template_path).read_text())
    return template.render(report=report.model_dump())
