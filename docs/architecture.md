# Architecture

## Overview

The system is a monorepo with three deployable units and a shared contract
testing project.

- **backend/** — FastAPI service. Owns all analysis, simulation orchestration,
  persistence and reporting. Stateless per request apart from the database and
  the ephemeral Anvil processes it spawns.
- **contracts/** — Foundry project. Contains the Uniswap-V2-compatible mock DEX
  and 13 token fixtures used to verify the detection engine.
- **frontend/** — Next.js dashboard. Pure presentation; talks only to the REST API.

## Backend layers

```
app/
  api/         HTTP layer: routers, schemas, dependencies, rate limiting
  core/        config, chains, logging, exceptions, security (SSRF), constants
  services/    rpc client, explorer client, analysis orchestrator, task queue
  analyzers/   token, owner, honeypot, tax, risk + static detectors
  simulations/ anvil fork manager, buy/sell simulators, scenario runner
  reports/     JSON / HTML / PDF generators and the report writer
  models/      SQLAlchemy ORM
  db/          engine, session, repositories
```

### Orchestration

`services/analysis_service.AnalysisOrchestrator` runs the pipeline:

1. `TokenAnalyzer` — metadata, bytecode, owner, proxy, DEX pairs, classification.
2. Source retrieval (explorer) — for source-level analysis.
3. `OwnerPrivilegeAnalyzer` — administrative capabilities.
4. Static detectors (and Slither when enabled and the depth is `full`).
5. `SimulationRunner` — a disposable Anvil fork runs the scenario matrix.
6. `HoneypotDetectionEngine` — combines behavioural and static signals.
7. `TaxAnalyzer` — effective taxes from simulation deltas.
8. `RiskEngine` — explainable score.

Every stage returns an `AnalyzerResult` containing `findings`, `data`, `warnings`
and `inconclusive` notes. The orchestrator aggregates these into an
`AnalysisResult`, which is persisted and rendered into reports.

## Simulation model

Each analysis (or explicit simulate call) starts its own Anvil instance on a free
localhost port. Two modes exist:

- **fork** — Anvil forks the configured chain at a fixed block (production path).
- **local** — a bare Anvil onto which the Foundry fixtures are deployed (used by
  the hermetic tests).

Wallets are funded with `anvil_setBalance` and impersonated with
`anvil_impersonateAccount`; transactions are sent with `eth_sendTransaction`. The
simulator never requires a private key and never broadcasts to a real network.
Instances are terminated in a `finally` block.

Buys and sells use the `swapExact*SupportingFeeOnTransferTokens` router entry
points, which measure the amount actually received by each pair. This is the
correct, real-world way to route taxed / fee-on-transfer tokens. Effective taxes
are derived from token and native balance deltas, excluding gas.

## Data flow

```
POST /analyze → task queue → orchestrator → { TokenInfo, Findings, SimulationReport, TaxResult, RiskAssessment }
                                             → database (result_json + normalised child tables)
                                             → reports/{id}.{json,html,pdf}
```

## Extensibility

- **New chains** — add a `ChainConfig` to `core/chains.py`.
- **New detectors** — implement `BaseDetector` and register it in
  `analyzers/static/detectors.py`.
- **New privileges** — add a `PrivilegeSpec` in `analyzers/owner_analyzer.py`.
- **New DEX flavours** — extend `DexConfig.kind` and the route discovery logic.
