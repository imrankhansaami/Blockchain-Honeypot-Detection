"""Persist reports to disk in JSON, HTML and PDF."""

from __future__ import annotations

import os
from pathlib import Path

from app.core.config import get_settings
from app.reports import html_report, json_report, pdf_report
from app.reports.models import SecurityReport


def write_reports(report: SecurityReport, out_dir: str | None = None) -> dict[str, str | None]:
    """Write JSON/HTML/PDF reports and return their paths (None on failure)."""
    base = Path(out_dir or get_settings().report_output_dir)
    base.mkdir(parents=True, exist_ok=True)
    stem = report.report_id

    paths: dict[str, str | None] = {"json": None, "html": None, "pdf": None}

    json_path = base / f"{stem}.json"
    json_path.write_text(json_report.generate(report), encoding="utf-8")
    paths["json"] = str(json_path)

    html_path = base / f"{stem}.html"
    html_path.write_text(html_report.render(report), encoding="utf-8")
    paths["html"] = str(html_path)

    try:
        pdf_path = base / f"{stem}.pdf"
        pdf_path.write_bytes(pdf_report.build(report))
        paths["pdf"] = str(pdf_path)
    except Exception:  # noqa: BLE001 - PDF must not break the analysis
        paths["pdf"] = None

    return paths
