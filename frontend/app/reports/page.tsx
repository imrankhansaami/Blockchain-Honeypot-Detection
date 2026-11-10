"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { AnalysisSummary } from "@/types";
import { Card } from "@/components/Card";
import { shortAddress, timeAgo } from "@/lib/format";
import { riskColor } from "@/lib/constants";

export default function ReportsPage() {
  const [rows, setRows] = useState<AnalysisSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .analyses(50)
      .then(setRows)
      .catch((e) => setError(String(e)));
  }, []);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold">Report Center</h1>
        <p className="text-sm text-muted">View and download previous security analyses.</p>
      </header>

      {error && (
        <Card className="border-rose-500/40">
          <p className="text-sm text-rose-300">Could not reach the API: {error}</p>
        </Card>
      )}

      <Card>
        {rows.length === 0 ? (
          <p className="text-sm text-muted">No reports yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase text-muted">
                  <th className="py-2">Token</th>
                  <th className="py-2">Chain</th>
                  <th className="py-2">Risk</th>
                  <th className="py-2">Created</th>
                  <th className="py-2">Downloads</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.analysis_id} className="border-t border-border/60">
                    <td className="py-2">
                      <Link href={`/analysis/${r.analysis_id}`} className="font-mono text-xs text-sky-400 hover:underline">
                        {shortAddress(r.token_address, 8)}
                      </Link>
                    </td>
                    <td className="py-2">{r.chain_id}</td>
                    <td className="py-2">
                      {r.risk_score === null ? (
                        <span className="text-muted">—</span>
                      ) : (
                        <span className="font-semibold" style={{ color: riskColor(r.risk_score) }}>
                          {r.risk_score} · {r.risk_classification}
                        </span>
                      )}
                    </td>
                    <td className="py-2 text-muted">{timeAgo(r.created_at)}</td>
                    <td className="py-2">
                      {r.status === "completed" ? (
                        <div className="flex gap-3 text-xs">
                          <a className="text-sky-400 hover:underline" href={api.reportUrl(r.analysis_id, "json")}>
                            JSON
                          </a>
                          <a className="text-sky-400 hover:underline" href={api.reportUrl(r.analysis_id, "pdf")}>
                            PDF
                          </a>
                          <a className="text-sky-400 hover:underline" href={api.reportUrl(r.analysis_id, "html")}>
                            HTML
                          </a>
                        </div>
                      ) : (
                        <span className="text-muted">{r.status}</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
