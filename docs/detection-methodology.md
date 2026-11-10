# Detection methodology

## Evidence sources

Findings record *where* the evidence came from, weakest to strongest:

| Source | Meaning |
| --- | --- |
| `heuristic` | Naming / pattern matching only |
| `bytecode` | Function selectors present in bytecode |
| `abi` | Contract ABI |
| `source_code` | Verified Solidity source |
| `explorer` | Explorer metadata (verification, proxy flag) |
| `onchain` | Direct chain state / `eth_call` |
| `simulation` | Reproduced behaviour on a fork |

Confidence is orthogonal to severity:

- **confirmed** — reproduced behaviour or authoritative source.
- **suspicious** — strong indicator, not proven.
- **inconclusive** — could not be established either way.

## Honeypot detection

The primary signal is behavioural: a real buy followed by a real sell on a fork.

- Buy succeeds, all sells revert → **confirmed honeypot** (critical).
- All buys revert → token may be paused/trading-gated.
- Buy and sell succeed → informational (still not a safety guarantee).
- Simulation unavailable → static signals only, reported as inconclusive.

Revert reasons are captured and included as evidence.

## Owner privileges

A catalogue of administrative capabilities (mint, pause, blacklist, tax control,
trading gates, upgrade authority, asset withdrawal). Each is reported with the
selector, evidence, abuse scenario and mitigation. The existence of a privilege
is **not** treated as proof of malice; severity reflects the damage it enables.

## Transfer restrictions

Bytecode selectors plus verified source reveal blacklists, whitelists, trading
switches, max-tx / max-wallet limits and cooldown logic. Ordinary anti-bot
controls are scored lower than owner-adjustable restrictions that can block
selling.

## Taxes

Effective tax = 1 − (actual received / AMM quoted), computed from balance deltas,
excluding gas. The swap runs with no minimum-output guard in measurement mode so
that the true deduction is observable; a non-zero slippage tolerance can be set
for realistic-mode runs. Where a round trip does not complete, tax is
**inconclusive**.

## Static analysis

Custom detectors flag mint logic, block/time restrictions, transfer overrides,
blacklists, whitelists, `delegatecall`, low-level calls and apparently
unrestricted admin functions. Slither (optional) adds its standard detectors,
mapped into the same finding model.

## What the tool explicitly does not claim

- It does not decompile arbitrary bytecode and assert source-level meaning.
- It does not trust token metadata or function names.
- It does not present a low score as proof of safety, nor a single heuristic as
  proof of malice.
