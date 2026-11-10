"use client";

import type { SimulationReport } from "@/types";
import { Card } from "@/components/Card";
import { formatBps, formatWei, shortAddress } from "@/lib/format";

export function SimulationPanel({ simulation }: { simulation: SimulationReport }) {
  if (!simulation.performed) {
    return (
      <Card>
        <h3 className="text-lg font-semibold">Buy / Sell Simulation</h3>
        <p className="mt-2 text-sm text-yellow-400">Not performed</p>
        <p className="text-sm text-muted">{simulation.reason}</p>
        {simulation.limitations.length > 0 && (
          <ul className="mt-3 list-disc pl-5 text-xs text-muted">
            {simulation.limitations.map((l) => (
              <li key={l}>{l}</li>
            ))}
          </ul>
        )}
      </Card>
    );
  }

  return (
    <Card>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-lg font-semibold">Buy / Sell Simulation</h3>
        <span className="text-xs text-muted">
          fork block {simulation.fork_block} · {(simulation.pair?.dex as string) ?? "pair"}{" "}
          {simulation.pair?.address ? shortAddress(simulation.pair.address as string) : ""}
        </span>
      </div>

      <div className="mb-4 grid gap-3 sm:grid-cols-2">
        <div className="rounded-lg border border-border bg-black/20 p-3">
          <p className="text-xs uppercase text-muted">Effective buy tax</p>
          <p className="text-2xl font-semibold">{formatBps(simulation.buy_tax_bps)}</p>
        </div>
        <div className="rounded-lg border border-border bg-black/20 p-3">
          <p className="text-xs uppercase text-muted">Effective sell tax</p>
          <p className="text-2xl font-semibold">{formatBps(simulation.sell_tax_bps)}</p>
        </div>
      </div>

      {simulation.can_buy_cannot_sell && (
        <p className="mb-4 rounded-lg border border-rose-500/40 bg-rose-500/10 p-3 text-sm text-rose-300">
          This token could be bought but could not be sold in simulation — honeypot behaviour.
        </p>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase text-muted">
              <th className="py-2">Scenario</th>
              <th className="py-2">Wallet</th>
              <th className="py-2">Buy</th>
              <th className="py-2">Tokens received</th>
              <th className="py-2">Sell</th>
              <th className="py-2">Native received</th>
              <th className="py-2">Gas</th>
            </tr>
          </thead>
          <tbody>
            {simulation.scenarios.map((s) => (
              <tr key={s.name} className="border-t border-border/60">
                <td className="py-2">{s.name}</td>
                <td className="py-2 font-mono text-xs">{shortAddress(s.wallet, 4)}</td>
                <td className="py-2">
                  {s.buy_result.success ? (
                    <span className="text-emerald-400">ok</span>
                  ) : (
                    <span className="text-rose-400" title={s.buy_result.revert_reason ?? ""}>
                      fail
                    </span>
                  )}
                </td>
                <td className="py-2">{s.tokens_received ?? "—"}</td>
                <td className="py-2">
                  {s.sell_result?.success ? (
                    <span className="text-emerald-400">ok</span>
                  ) : (
                    <span className="text-rose-400" title={s.sell_result?.revert_reason ?? ""}>
                      {s.sell_result?.revert_reason ? "revert" : "—"}
                    </span>
                  )}
                </td>
                <td className="py-2">{formatWei(s.native_received_wei)}</td>
                <td className="py-2 text-xs text-muted">{s.buy_result.gas_used ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {simulation.scenarios.some((s) => s.sell_result?.revert_reason) && (
        <div className="mt-4">
          <p className="text-xs uppercase text-muted">Revert evidence</p>
          {simulation.scenarios
            .filter((s) => s.sell_result?.revert_reason)
            .map((s) => (
              <pre
                key={s.name}
                className="mt-1 overflow-auto rounded-lg border border-border bg-black/40 p-3 text-xs text-rose-300"
              >
                {s.sell_result?.revert_reason}
              </pre>
            ))}
        </div>
      )}

      {simulation.limitations.length > 0 && (
        <ul className="mt-4 list-disc pl-5 text-xs text-muted">
          {simulation.limitations.map((l) => (
            <li key={l}>{l}</li>
          ))}
        </ul>
      )}
    </Card>
  );
}
