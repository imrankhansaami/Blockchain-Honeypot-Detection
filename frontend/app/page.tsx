"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { AnalysisSummary, Stats } from "@/types";
import { StatCard } from "@/components/StatCard";
import { Card } from "@/components/Card";
import { SeverityBadge } from "@/components/SeverityBadge";
import { formatDuration, shortAddress, timeAgo } from "@/lib/format";
import { riskColor } from "@/lib/constants";

export default function OverviewPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [recent, setRecent] = useState<AnalysisSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.stats(), api.analyses(8)])
      .then(([s, r]) => {
        setStats(s);
        setRecent(r);
      })
      .catch((e) => setError(String(e)));
  }, []);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold">Security Operations Overview</h1>
        <p className="text-sm text-muted">
          Automated ERC-20 honeypot detection, owner-privilege analysis and on-fork simulation.
        </p>
      </header>

      {error && (
        <Card className="border-rose-500/40">
          <p className="text-sm text-rose-300">Could not reach the API: {error}</p>
          <p className="mt-1 text-xs text-muted">
            Start the backend with <code>uvicorn app.main:app</code> and set NEXT_PUBLIC_API_BASE.
          </p>
        </Card>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Tokens analyzed" value={stats?.total_analyses ?? "—"} />
        <StatCard label="High risk" value={stats?.high_risk ?? "—"} tone="warn" hint="score ≥ 60" />
        <StatCard label="Critical risk" value={stats?.critical_risk ?? "—"} tone="danger" hint="score ≥ 80" />
        <StatCard label="Avg. analysis time" value={formatDuration(stats?.average_duration_ms ?? null)} />
      </div>

      <Card>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Recent scans</h2>
          <Link href="/analyze" className="btn-primary">
            New analysis
          </Link>
        </div>
        {recent.length === 0 ? (
          <p className="text-sm text-muted">No analyses yet. Run one from the Token Analyzer.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase text-muted">
                  <th className="py-2">Token</th>
                  <th className="py-2">Chain</th>
                  <th className="py-2">Status</th>
                  <th className="py-2">Risk</th>
                  <th className="py-2">When</th>
                  <th className="py-2" />
                </tr>
              </thead>
              <tbody>
                {recent.map((a) => (
                  <tr key={a.analysis_id} className="border-t border-border/60">
                    <td className="py-2 font-mono text-xs">{shortAddress(a.token_address, 6)}</td>
                    <td className="py-2">{a.chain_id}</td>
                    <td className="py-2 text-muted">{a.status}</td>
                    <td className="py-2">
                      {a.risk_score === null ? (
                        <span className="text-muted">—</span>
                      ) : (
                        <span className="font-semibold" style={{ color: riskColor(a.risk_score) }}>
                          {a.risk_score} · {a.risk_classification}
                        </span>
                      )}
                    </td>
                    <td className="py-2 text-muted">{timeAgo(a.created_at)}</td>
                    <td className="py-2 text-right">
                      <Link href={`/analysis/${a.analysis_id}`} className="text-sky-400 hover:underline">
                        View
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card>
        <h2 className="mb-2 text-lg font-semibold">Severity scale</h2>
        <div className="flex flex-wrap gap-2">
          {(["critical", "high", "medium", "low", "informational"] as const).map((s) => (
            <SeverityBadge key={s} severity={s} />
          ))}
        </div>
      </Card>
    </div>
  );
}
