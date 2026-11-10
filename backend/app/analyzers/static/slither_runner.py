"""Optional Slither integration.

Slither is invoked as an isolated subprocess with a timeout. Its JSON output is
mapped onto our Finding schema. Slither is optional: when the binary is absent
or disabled, the analyzer reports that static tooling was unavailable rather
than failing.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from app.analyzers.base import (
    Confidence,
    EvidenceSource,
    Finding,
    FindingCategory,
    Severity,
    make_finding,
)
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_SLITHER_IMPACT = {
    "High": Severity.HIGH,
    "Medium": Severity.MEDIUM,
    "Low": Severity.LOW,
    "Informational": Severity.INFO,
    "Optimization": Severity.INFO,
}

# Detector -> our category mapping for the most relevant checkers.
_CATEGORY_MAP = {
    "reentrancy-eth": FindingCategory.FUNCTIONALITY,
    "arbitrary-send-eth": FindingCategory.OWNERSHIP,
    "suicidal": FindingCategory.ACCESS_CONTROL,
    "controlled-delegatecall": FindingCategory.UPGRADEABILITY,
    "delegatecall-loop": FindingCategory.UPGRADEABILITY,
    "unprotected-upgrade": FindingCategory.UPGRADEABILITY,
    "missing-zero-check": FindingCategory.FUNCTIONALITY,
    "tx-origin": FindingCategory.ACCESS_CONTROL,
}


class SlitherRunner:
    def __init__(self) -> None:
        self.settings = get_settings()

    def available(self) -> bool:
        import shutil

        return shutil.which(self.settings.slither_binary) is not None

    def run(self, contract_address: str, source_code: str) -> tuple[list[Finding], list[str]]:
        warnings: list[str] = []
        if not self.settings.slither_enabled:
            return [], ["Slither integration is disabled."]
        if not self.available():
            return [], ["Slither binary not found on PATH."]
        if not source_code.strip():
            return [], ["No verified source available for Slither."]

        with tempfile.TemporaryDirectory(prefix="slither_") as tmp:
            sol = Path(tmp) / "Target.sol"
            sol.write_text(source_code, encoding="utf-8")
            try:
                proc = subprocess.run(
                    [self.settings.slither_binary, str(sol), "--json", "-"],
                    capture_output=True,
                    text=True,
                    timeout=self.settings.slither_timeout_seconds,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                return [], ["Slither timed out."]
            except Exception as exc:  # noqa: BLE001
                return [], [f"Slither invocation failed: {exc}"]

            payload = proc.stdout.strip()
            if not payload:
                return [], ["Slither produced no output (compilation may have failed)."]
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                return [], ["Slither output was not valid JSON."]

        findings: list[Finding] = []
        for result in data.get("results", {}).get("detectors", []):
            check = result.get("check", "unknown")
            impact = result.get("impact", "Informational")
            finding = make_finding(
                f"slither.{check}",
                f"Slither: {check}",
                _CATEGORY_MAP.get(check, FindingCategory.FUNCTIONALITY),
                _SLITHER_IMPACT.get(impact, Severity.LOW),
                Confidence.SUSPICIOUS,
                EvidenceSource.SOURCE_CODE,
                result.get("description", "")[:1000],
                evidence={
                    "check": check,
                    "impact": impact,
                    "confidence": result.get("confidence"),
                    "elements": [
                        el.get("name")
                        for el in result.get("elements", [])
                        if el.get("name")
                    ][:10],
                },
                references=[contract_address],
            )
            findings.append(finding)
        return findings, warnings
