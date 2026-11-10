"""Analysis orchestration.

Runs the full pipeline for one token and assembles a single AnalysisResult:

    token metadata -> ownership/privileges -> static detectors -> simulation
        -> honeypot detection -> tax -> risk scoring
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from app.analyzers.base import Finding
from app.analyzers.honeypot_detector import HoneypotDetectionEngine
from app.analyzers.owner_analyzer import OwnerPrivilegeAnalyzer
from app.analyzers.risk_engine import RiskEngine
from app.analyzers.static.detectors import run_detectors
from app.analyzers.static.slither_runner import SlitherRunner
from app.analyzers.tax_analyzer import TaxAnalyzer
from app.analyzers.token_analyzer import TokenAnalyzer
from app.core.chains import get_chain, resolve_explorer_key, resolve_rpc_url
from app.core.config import AnalysisDepth, get_settings
from app.core.exceptions import RpcUnavailableError
from app.core.logging import get_logger
from app.schemas.analysis import AnalysisResult, AnalysisStatus
from app.schemas.simulation import SimulationReport
from app.services.explorer import ExplorerClient
from app.services.rpc import RpcClient
from app.simulations.simulation_runner import SimulationRunner

logger = get_logger(__name__)


@dataclass
class AnalysisRequest:
    chain_id: int
    token_address: str
    analysis_depth: AnalysisDepth = "standard"
    block_number: int | None = None


@dataclass
class OrchestrationOutcome:
    result: AnalysisResult
    source_code: str | None = None
    inconclusive: list[str] = field(default_factory=list)


class AnalysisOrchestrator:
    def __init__(self, request: AnalysisRequest) -> None:
        self.request = request
        self.settings = get_settings()
        self.chain = get_chain(request.chain_id)

    def _build_rpc(self) -> RpcClient:
        url = resolve_rpc_url(self.request.chain_id)
        if not url:
            raise RpcUnavailableError(
                f"No RPC endpoint is configured for {self.chain.name}. "
                "Set the corresponding *_RPC_URL environment variable."
            )
        return RpcClient(url)

    def _build_explorer(self) -> ExplorerClient | None:
        key = resolve_explorer_key(self.request.chain_id)
        if not key or not self.chain.supports_explorer_api:
            return None
        try:
            return ExplorerClient(self.chain, key)
        except ValueError:
            return None

    def run(self) -> OrchestrationOutcome:
        started = time.time()
        analysis_id = uuid.uuid4().hex
        findings: list[Finding] = []
        warnings: list[str] = []
        inconclusive: list[str] = []
        simulation: SimulationReport | None = None
        tax_data: dict | None = None
        owner_data: dict | None = None

        rpc = self._build_rpc()
        explorer = self._build_explorer()

        try:
            block_number = self.request.block_number or rpc.block_number()
        except RpcUnavailableError:
            block_number = None
            warnings.append("Could not read the current block number from the RPC endpoint.")

        # --- 1. token metadata + classification ---
        token_analyzer = TokenAnalyzer(rpc, self.chain, explorer)
        token_result = token_analyzer.analyze(self.request.token_address, block_number)
        findings.extend(token_result.findings)
        warnings.extend(token_result.warnings)
        inconclusive.extend(token_result.inconclusive)
        token_info = token_result.data

        # --- 2. verified source (for source-level analysis) ---
        source_code: str | None = None
        if explorer is not None:
            try:
                src = explorer.get_source_code(self.request.token_address)
                if src and src.get("verified"):
                    source_code = src.get("source")
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"Explorer source retrieval failed: {exc}")

        detected_functions: dict[str, bool] = token_info.get("detected_functions", {})

        # --- 3. owner privileges ---
        owner_analyzer = OwnerPrivilegeAnalyzer(source_code)
        owner_result = owner_analyzer.analyze(detected_functions)
        findings.extend(owner_result.findings)
        warnings.extend(owner_result.warnings)
        owner_data = owner_result.data

        # --- 4. static detectors ---
        findings.extend(run_detectors(source_code, detected_functions))
        if source_code is None:
            inconclusive.append(
                "Source code is not verified/available; source-level detectors were skipped."
            )

        # --- 5. Slither (full depth only) ---
        if self.request.analysis_depth == "full" and self.settings.slither_enabled:
            slither_findings, slither_warnings = SlitherRunner().run(
                self.request.token_address, source_code or ""
            )
            findings.extend(slither_findings)
            warnings.extend(slither_warnings)

        # --- 6. simulation ---
        if self.request.analysis_depth == "quick":
            simulation = SimulationReport(
                performed=False,
                reason="Analysis depth 'quick' skips dynamic simulation.",
                chain_id=self.request.chain_id,
                token_address=self.request.token_address,
            )
        else:
            rpc_url = resolve_rpc_url(self.request.chain_id)
            runner = SimulationRunner(
                chain_id=self.request.chain_id,
                token_address=self.request.token_address,
                rpc_url=rpc_url,
                block_number=block_number,
            )
            try:
                simulation = runner.run()
            except Exception as exc:  # noqa: BLE001
                logger.exception("Simulation failed")
                warnings.append(f"Simulation error: {exc}")
                simulation = SimulationReport(
                    performed=False,
                    reason=f"Simulation error: {exc}",
                    chain_id=self.request.chain_id,
                    token_address=self.request.token_address,
                )

        # --- 7. honeypot detection ---
        honeypot_result = HoneypotDetectionEngine(source_code).analyze(
            simulation=simulation, detected_functions=detected_functions
        )
        findings.extend(honeypot_result.findings)
        inconclusive.extend(honeypot_result.inconclusive)

        # --- 8. tax ---
        tax_result = TaxAnalyzer().analyze(simulation)
        findings.extend(tax_result.findings)
        inconclusive.extend(tax_result.inconclusive)
        tax_data = tax_result.data

        # --- 9. risk scoring ---
        risk = RiskEngine().score(findings, uncertainties=inconclusive)

        duration_ms = (time.time() - started) * 1000
        result = AnalysisResult(
            analysis_id=analysis_id,
            chain_id=self.request.chain_id,
            token_address=self.request.token_address,
            status=AnalysisStatus.COMPLETED,
            analysis_depth=self.request.analysis_depth,
            block_number=block_number,
            started_at=None,
            finished_at=None,
            duration_ms=round(duration_ms, 2),
            token=token_info,
            findings=findings,
            risk=risk,
            simulation=simulation,
            tax=tax_data,
            owner_analysis=owner_data,
            warnings=warnings,
        )
        return OrchestrationOutcome(result=result, source_code=source_code, inconclusive=inconclusive)
