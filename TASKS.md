# TASKS

Implementation plan and status. Phases follow the project brief.

## Phase 1 — Repository inspection and planning ✅

- [x] Inspect the (empty) repository and available tooling
- [x] Install Foundry (forge/anvil/cast) and OpenZeppelin
- [x] Establish monorepo architecture
- [x] Create this TASKS.md and the docs set
- [x] Pin backend dependencies and create `.env.example`

## Phase 2 — Smart-contract testing environment ✅

- [x] Configure Foundry (`foundry.toml`, remappings, `via_ir`)
- [x] Uniswap-V2-compatible mock DEX (WETH, factory, pair, router with
      fee-on-transfer entry points)
- [x] 13 token fixtures (standard, honeypot, adjustable tax, excessive sell tax,
      blacklist, whitelist-only, max-tx, trading switch, mintable, upgradeable
      UUPS V1/V2, fee-on-transfer, non-standard, no-liquidity)
- [x] Forge tests: unit, fuzz, invariant, adversarial (20 passing)

## Phase 3 — Blockchain integration ✅

- [x] Chain registry (Ethereum, Sepolia, BSC, BSC testnet) with configurable
      RPC/explorer/DEX; no hardcoded keys
- [x] Web3 RPC client with timeouts, retries, SSRF validation
- [x] Bytecode, metadata, owner and EIP-1967 proxy detection
- [x] Explorer integration (Etherscan-family)
- [x] DEX pair discovery

## Phase 4 — Static analysis ✅

- [x] Custom detectors: arbitrary mint, block/time restrictions, custom transfer,
      blacklist, whitelist, delegatecall, low-level call, unrestricted admin
- [x] OwnerPrivilegeAnalyzer with abuse scenarios
- [x] Optional Slither subprocess integration
- [x] Structured findings with severity/confidence/evidence

## Phase 5 — Dynamic simulation ✅

- [x] Anvil fork manager (isolated process per analysis, always destroyed)
- [x] Buy and sell simulators using fee-on-transfer-supporting router entry points
- [x] Multi-scenario runner (small/medium/large, second wallet)
- [x] Effective tax from balance deltas
- [x] Revert-reason capture as evidence
- [x] Hermetic Anvil integration test with the Foundry fixtures

## Phase 6 — Risk engine ✅

- [x] 0–100 explainable score
- [x] Severity × evidence-weight × confidence, category de-duplication
- [x] Classification bands and uncertainty reporting
- [x] Unit tests incl. false-positive / correlated-finding cases

## Phase 7 — Backend API and database ✅

- [x] FastAPI endpoints (analyze, token, simulate, reports, health, chains)
- [x] Pydantic schemas and request validation
- [x] SQLAlchemy models (chains, tokens, analyses, simulation_runs,
      security_findings, token_privileges, tax_results, security_reports)
- [x] Background task queue (thread pool + optional Celery)
- [x] Structured exceptions, logging, rate limiting

## Phase 8 — Frontend ✅

- [x] Dark security dashboard (Overview, Token Analyzer, Security Results with
      Results/Simulation/Findings tabs, Report Center)
- [x] Severity/confidence styling, expandable evidence, risk gauge
- [x] Strict TypeScript

## Phase 9 — Reports and documentation ✅

- [x] JSON, HTML and PDF report generators
- [x] README, architecture, threat model, methodology, scoring, limitations

## Phase 10 — Quality assurance ✅ (ongoing)

- [x] Forge tests pass
- [x] Pytest suite passes (53 tests)
- [x] Frontend typecheck/build
- [x] GitHub Actions CI workflow

## Follow-ups / nice-to-haves

- [ ] Uniswap V3 route support
- [ ] Multi-block adversarial matrices
- [ ] Alembic migrations (currently SQLAlchemy `create_all` for dev)
- [ ] Screenshot set and demo video
