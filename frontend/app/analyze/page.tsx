"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { ChainInfo } from "@/types";
import { Card } from "@/components/Card";

const DEPTHS = [
  { value: "quick", label: "Quick — static analysis only" },
  { value: "standard", label: "Standard — static + simulation" },
  { value: "full", label: "Full — static + simulation + Slither" },
];

export default function AnalyzePage() {
  const router = useRouter();
  const [chains, setChains] = useState<ChainInfo[]>([]);
  const [chainId, setChainId] = useState(1);
  const [address, setAddress] = useState("");
  const [depth, setDepth] = useState("standard");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .health()
      .then((h) => setChains(h.chains))
      .catch(() => setChains([]));
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!/^0x[a-fA-F0-9]{40}$/.test(address.trim())) {
      setError("Enter a valid 0x-prefixed 42-character contract address.");
      return;
    }
    setBusy(true);
    try {
      const created = await api.analyze(chainId, address.trim(), depth);
      router.push(`/analysis/${created.analysis_id}`);
    } catch (err) {
      setError(String(err));
      setBusy(false);
    }
  }

  const selected = chains.find((c) => c.chain_id === chainId);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold">Token Analyzer</h1>
        <p className="text-sm text-muted">
          Analyze an ERC-20 contract for honeypot behaviour, owner privileges and taxes.
        </p>
      </header>

      <Card>
        <form onSubmit={submit} className="space-y-5">
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="label" htmlFor="chain">
                Blockchain
              </label>
              <select
                id="chain"
                className="input"
                value={chainId}
                onChange={(e) => setChainId(Number(e.target.value))}
              >
                {chains.length === 0 && <option value={1}>Ethereum Mainnet</option>}
                {chains.map((c) => (
                  <option key={c.chain_id} value={c.chain_id}>
                    {c.name} {c.rpc_configured ? "" : "(no RPC configured)"}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="label" htmlFor="depth">
                Analysis depth
              </label>
              <select id="depth" className="input" value={depth} onChange={(e) => setDepth(e.target.value)}>
                {DEPTHS.map((d) => (
                  <option key={d.value} value={d.value}>
                    {d.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="label" htmlFor="address">
              Token contract address
            </label>
            <input
              id="address"
              className="input font-mono"
              placeholder="0x…"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              spellCheck={false}
              autoComplete="off"
            />
          </div>

          {selected && !selected.rpc_configured && (
            <p className="rounded-lg border border-yellow-500/40 bg-yellow-500/10 p-3 text-sm text-yellow-300">
              No RPC endpoint is configured for {selected.name}. Set its *_RPC_URL environment variable
              on the backend to analyze real on-chain data.
            </p>
          )}

          {error && (
            <p className="rounded-lg border border-rose-500/40 bg-rose-500/10 p-3 text-sm text-rose-300">
              {error}
            </p>
          )}

          <button type="submit" className="btn-primary" disabled={busy}>
            {busy ? "Starting analysis…" : "Analyze token"}
          </button>
        </form>
      </Card>

      <Card>
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted">
          What this analysis does
        </h2>
        <ul className="list-disc space-y-1 pl-5 text-sm text-slate-300">
          <li>Reads live contract bytecode, metadata, owner and proxy storage slots.</li>
          <li>Detects privileged functions, blacklist/whitelist and transfer restrictions.</li>
          <li>
            Executes real buy and sell swaps on a disposable local fork (Anvil) and measures the
            effective taxes from balance deltas.
          </li>
          <li>Produces an explainable 0–100 risk score with evidence and confidence.</li>
        </ul>
      </Card>
    </div>
  );
}
