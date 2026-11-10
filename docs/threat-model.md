# Threat model

This document describes the assets, trust boundaries and abuse cases the tool is
designed around. It is a threat model for the *tool itself*, not for arbitrary
tokens.

## Assets

- The host running the backend and its filesystem/network.
- Configured RPC endpoints and explorer API keys.
- The integrity of produced reports (a report must not silently claim false
  safety or false guilt).

## Trust boundaries

1. **User input (untrusted).** Chain ID and token address are validated. Addresses
   are checksummed; unknown chain IDs are rejected.
2. **Token metadata / ABI (untrusted).** Function names and metadata are never
   trusted. Behaviour must be evidenced by simulation or on-chain state.
3. **RPC responses (untrusted).** A malicious or compromised RPC could return
   misleading data. Every report records the exact chain and block used.
4. **Token-provided code (untrusted).** Token bytecode is only ever executed
   inside a disposable Anvil fork, never on the host. Solidity source is never
   compiled or executed on the host except by Slither, which runs as a sandboxed
   subprocess with a timeout.

## Key risks and mitigations

| Risk | Mitigation |
| --- | --- |
| SSRF via user-supplied RPC URL | RPC URLs come only from server configuration; `validate_rpc_url` enforces http(s), rejects private/loopback/link-local hosts, and supports an allow-list |
| Secret leakage | No secrets in code; API keys from env only; no private keys/seed phrases ever requested or stored |
| Real-fund loss | Simulations run on local forks only; wallets are impersonated; no broadcasts to real networks |
| Resource exhaustion | Anvil process per analysis, port range, timeouts, bounded retries, rate limiting |
| Host code execution | Untrusted token code runs only in Anvil; Slither and Anvil run as subprocesses with timeouts |
| Report over-claiming | Findings carry confidence + evidence source; disclaimers on every report; uncertain conclusions marked inconclusive |
| Non-determinism | Exact block recorded; findings derived from deterministic analysis wherever possible |

## Non-goals

- The tool does not attempt to prove a token is safe.
- The tool does not execute arbitrary bytecode on the host.
- The tool does not decompile bytecode and claim full source understanding.
