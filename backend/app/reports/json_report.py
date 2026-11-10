"""JSON report generator."""

from __future__ import annotations

import json

from app.reports.models import SecurityReport


def to_dict(report: SecurityReport) -> dict:
    return report.model_dump(mode="json")


def generate(report: SecurityReport, *, indent: int | None = 2) -> str:
    return json.dumps(to_dict(report), indent=indent, default=str)
