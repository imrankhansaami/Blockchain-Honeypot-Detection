"""Generate a real, reproducible example security report from the fixtures.

Deploys HoneypotERC20 onto a local Anvil with the mock DEX, runs the actual
buy/sell simulation, then runs the honeypot/tax/owner/risk analyzers and writes
JSON/HTML/PDF example reports to ``docs/examples/``.

Usage:  python scripts/generate_example_report.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import os

_foundry_bin = Path(os.environ.get("USERPROFILE", "")) / ".foundry" / "bin"
if _foundry_bin.exists():
    os.environ["PATH"] = str(_foundry_bin) + os.pathsep + os.environ.get("PATH", "")

from app.analyzers.abi_utils import detect_selectors  # noqa: E402
from app.analyzers.honeypot_detector import HoneypotDetectionEngine  # noqa: E402
from app.analyzers.owner_analyzer import OwnerPrivilegeAnalyzer  # noqa: E402
from app.analyzers.risk_engine import RiskEngine  # noqa: E402
from app.analyzers.tax_analyzer import TaxAnalyzer  # noqa: E402
from app.core.chains import ChainConfig, DexConfig  # noqa: E402
from app.reports.models import SecurityReport  # noqa: E402
from app.reports.writer import write_reports  # noqa: E402
from app.schemas.analysis import AnalysisResult, AnalysisStatus  # noqa: E402
from app.schemas.token import TokenInfo, TokenMetadata  # noqa: E402
from app.simulations.fork_manager import AnvilNode  # noqa: E402
from app.simulations.simulation_runner import discover_route, run_scenarios  # noqa: E402

sys.path.insert(0, str(ROOT / "backend"))
from tests.local_chain import add_liquidity_eth, deploy, deploy_dex, transact  # noqa: E402


def main() -> None:
    out = ROOT / "docs" / "examples"
    out.mkdir(parents=True, exist_ok=True)

    node = AnvilNode.start()
    try:
        dex = deploy_dex(node)
        chain = ChainConfig(
            chain_id=31337,
            name="Local Anvil (mock DEX)",
            short_name="anvil",
            native_symbol="ETH",
            native_decimals=18,
            wrapped_native=dex["weth"].address,
            wrapped_native_symbol="WETH",
            dexes=(
                DexConfig(
                    name="Mock Uniswap V2",
                    factory=dex["factory"].address,
                    router=dex["router"].address,
                ),
            ),
        )

        token = deploy(node, "HoneypotERC20", "HoneypotERC20")
        transact(node, token.functions.enableTrading())
        pair = add_liquidity_eth(node, dex, token, 100_000 * 10**18, 100 * 10**18)
        transact(node, token.functions.setPair(pair))

        route = discover_route(node.w3, chain, token.address)
        assert route is not None
        block = node.current_block()
        simulation = run_scenarios(
            node=node,
            chain=chain,
            token_address=token.address,
            route=route,
            fork_block=block,
            scenarios=[("medium", "0x000000000000000000000000000000000000bEEF", 10**17)],
        )
        simulation.limitations.append(
            "Example generated against a local mock DEX with the Foundry fixtures."
        )

        code = node.w3.eth.get_code(token.address).to_0x_hex()
        detected = detect_selectors(code)
        source = (
            "contract HoneypotERC20 { mapping(address=>bool) isWhitelisted; bool tradingEnabled; "
            "function enableTrading() external onlyOwner {} function setPair(address) external onlyOwner {} "
            "function setWhitelisted(address,bool) external onlyOwner {} }"
        )

        findings = []
        findings += OwnerPrivilegeAnalyzer(source).analyze(detected).findings
        findings += HoneypotDetectionEngine(source).analyze(simulation=simulation, detected_functions=detected).findings
        tax = TaxAnalyzer().analyze(simulation)
        findings += tax.findings
        risk = RiskEngine().score(findings, uncertainties=["Example: bytecode selectors are heuristic."])

        token_info = TokenInfo(
            address=token.address,
            chain_id=chain.chain_id,
            chain_name=chain.name,
            is_contract=True,
            bytecode_size=(len(code) - 2) // 2,
            metadata=TokenMetadata(
                name="Honeypot Token",
                symbol="HNY",
                decimals=18,
                total_supply=1_000_000 * 10**18,
                metadata_complete=True,
            ),
            owner=node.w3.eth.accounts[0],
            contract_type="ownable_erc20",
            erc20_compliant=True,
            detected_functions=detected,
        )

        result = AnalysisResult(
            analysis_id="example-honeypot",
            chain_id=chain.chain_id,
            token_address=token.address,
            status=AnalysisStatus.COMPLETED,
            analysis_depth="standard",
            block_number=block,
            duration_ms=1234.5,
            token=token_info,
            findings=findings,
            risk=risk,
            simulation=simulation,
            tax=tax.data,
        )
        report = SecurityReport(report_id="example-honeypot", result=result)
        paths = write_reports(report, out_dir=str(out))
        print("Wrote example reports:")
        for kind, path in paths.items():
            print(f"  {kind}: {path}")
        print(f"  risk score: {risk.score} ({risk.classification})")
    finally:
        node.destroy()


if __name__ == "__main__":
    main()
