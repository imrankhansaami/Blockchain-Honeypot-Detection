"""HTML report generator using a Jinja2 template."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.reports.models import SecurityReport

_TEMPLATE_DIR = Path(__file__).parent / "templates"


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )


def render(report: SecurityReport) -> str:
    env = _env()
    template = env.get_template("report.html.j2")
    return template.render(report=report, result=report.result)
