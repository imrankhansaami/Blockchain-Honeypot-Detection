# Limitations

Automated analysis has hard limits. These are surfaced in every report rather
than hidden.

## Simulation

- **Uniswap-V2-compatible routers only.** V3 and non-standard routers are not yet
  supported; such tokens report "Simulation unavailable: no supported DEX route
  found."
- **Liquidity required.** Without a V2 pair with the wrapped native token, the
  tool returns "Insufficient liquidity to perform a meaningful buy/sell
  simulation."
- **Block sensitivity.** Behaviour can change between blocks and after owner
  actions. Every report records the fork block; results are a snapshot.
- **Wallet sensitivity.** Simulations use fresh on-fork wallets. A token that
  treats certain wallets specially may behave differently elsewhere.
- **Historical state.** Forking an old block requires an archive-capable RPC.
- **Single-block scenarios.** Multi-block adversarial sequences (e.g. cooldowns,
  time locks) are not yet executed.

## Static analysis

- **Source availability.** For unverified contracts only ABI/bytecode-level
  conclusions are possible, and these are labelled as such.
- **No decompilation claims.** Bytecode heuristics (selector presence) prove a
  code path *may* exist, not that it is reachable or what it does.
- **Detector heuristics.** Custom detectors are pattern-based and can both miss
  novel patterns and flag legitimate code. Slither is optional and adds its own
  false positives.

## Scoring

- The score is a heuristic aggregation, not a probability of loss.
- A low score does **not** mean a token is safe.
- Absence of findings may reflect analysis limits (no verification, no
  simulation) rather than absence of risk.

## Infrastructure

- RPC quality and availability bound the analysis; failures are reported as
  warnings or inconclusive results, never silently ignored.
- Rate limits and timeouts bound throughput.

## Scope

This is a security-research tool, **not** a formal audit, and provides no legal,
financial or investment advice.
