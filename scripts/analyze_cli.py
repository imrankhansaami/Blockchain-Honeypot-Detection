"""Command-line analysis runner.

Usage:
    python -m scripts.analyze_cli 1 0xTOKENADDRESS [--depth standard]

Requires the backend to be importable (run from the repo root) and the relevant
*_RPC_URL environment variable to be set.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.analysis_service import AnalysisOrchestrator, AnalysisRequest  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a token security analysis")
    parser.add_argument("chain_id", type=int)
    parser.add_argument("token_address")
    parser.add_argument("--depth", default="standard", choices=["quick", "standard", "full"])
    args = parser.parse_args()

    outcome = AnalysisOrchestrator(
        AnalysisRequest(chain_id=args.chain_id, token_address=args.token_address, analysis_depth=args.depth)
    ).run()
    result = outcome.result
    print(json.dumps(result.model_dump(mode="json"), indent=2, default=str))
    if result.risk:
        print(f"\nRisk: {result.risk.score}/100 - {result.risk.classification}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
