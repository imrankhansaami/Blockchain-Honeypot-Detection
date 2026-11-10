"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import type { AnalysisResult, Severity } from "@/types";
import { Card } from "@/components/Card";
import { RiskGauge } from "@/components/RiskGauge";
import { TokenInfoCard } from "@/components/TokenInfoCard";
import { SimulationPanel } from "@/components/SimulationPanel";
import { FindingCard } from "@/components/FindingCard";
import { formatDuration, shortAddress } from "@/lib/format";
import { SEVERITY_ORDER, SEVERITY_STYLES } from "@/lib/constants";
import { cn } from "@/lib/format";

type Tab = "results" | "simulation" | "findings";

function AnalysisView() {
  const searchParams = useSearchParams();
  const id = searchParams.get("id") ?? "";
  const [data, setData] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("results");
  const [filter, setFilter] = useState<Severity | "all">("all");

  const load = useCallback(async () => {
    if (!id) {
      setError("No analysis id provided.");
      return "failed";
    }
    try {
      const result = await api.analysis(id);
      setData(result);
      return result.status;
    } catch (err) {
      setError(String(err));
      return "failed";
    }
  }, [id]);

  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      const status = await load();
      if (!active) return;
      if (status === "queued" || status === "running") {
        timer = setTimeout(poll, 2500);
      }
    }
    poll();
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [load]);

  if (error) {
    return (
      <Card className="border-rose-500/40">
        <p className="text-sm text-rose-300">{error}</p>
        <Link href="/analyze" className="btn-ghost mt-3">
          Back to analyzer
        </Link>
      </Card>
    );
  }

  if (!data) {
    return <p className="text-sm text-muted">Loading analysis…</p>;
  }

  const pending = data.status === "queued" || data.status === "running";
  const findings = data.findings ?? [];
  const filtered = filter === "all" ? findings : findings.filter((f) => f.severity === filter);

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">
            Security Results{" "}
            <span className="font-mono text-base text-muted">{shortAddress(data.token_address, 8)}</span>
          </h1>
          <p className="text-sm text-muted">
            chain {data.chain_id} · block {data.block_number ?? "—"} · {data.analysis_depth} ·{" "}
            {formatDuration(data.duration_ms)}
          </p>
        </div>
        {!pending && (
          <div className="flex gap-2">
            <a className="btn-ghost" href={api.reportUrl(id, "json")} target="_blank" rel="noreferrer">
              JSON
            </a>
            <a className="btn-ghost" href={api.reportUrl(id, "pdf")} target="_blank" rel="noreferrer">
              PDF
            </a>
            <a className="btn-ghost" href={api.reportUrl(id, "html")} target="_blank" rel="noreferrer">
              HTML
            </a>
          </div>
        )}
      </header>

      {pending && (
        <Card>
          <p className="text-sm text-sky-300">Analysis {data.status}… this can take a few seconds.</p>
          <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-white/10">
            <div className="h-full w-1/2 animate-pulse rounded-full bg-sky-500" />
          </div>
        </Card>
      )}

      {data.status === "failed" && (
        <Card className="border-rose-500/40">
          <p className="text-sm text-rose-300">Analysis failed: {data.error}</p>
        </Card>
      )}

      {!pending && data.risk && (
        <Card>
          <RiskGauge score={data.risk.score} classification={data.risk.classification} />
          <div className="mt-5 grid gap-4 md:grid-cols-2">
            <div>
              <p className="mb-1 text-xs uppercase tracking-wide text-muted">Scoring explanation</p>
              <ul className="space-y-1 text-sm text-slate-300">
                {data.risk.explanation.map((line) => (
                  <li key={line}>• {line}</li>
                ))}
              </ul>
            </div>
            {data.risk.uncertainties.length > 0 && (
              <div>
                <p className="mb-1 text-xs uppercase tracking-wide text-muted">Uncertainties</p>
                <ul className="space-y-1 text-sm text-slate-400">
                  {data.risk.uncertainties.map((u) => (
                    <li key={u}>• {u}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
          <p className="mt-4 border-t border-border pt-3 text-xs text-muted">{data.risk.disclaimer}</p>
        </Card>
      )}

      <div className="flex gap-2 border-b border-border">
        {(["results", "simulation", "findings"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={cn(
              "-mb-px border-b-2 px-4 py-2 text-sm capitalize transition-colors",
              tab === t ? "border-sky-500 text-white" : "border-transparent text-muted hover:text-slate-200",
            )}
          >
            {t} {t === "findings" ? `(${findings.length})` : ""}
          </button>
        ))}
      </div>

      {tab === "results" && (
        <div className="space-y-6">
          {data.token && <TokenInfoCard token={data.token} />}
          {data.owner_analysis && Array.isArray((data.owner_analysis as { privileges?: unknown[] }).privileges) && (
            <Card>
              <h3 className="mb-3 text-lg font-semibold">Owner privileges</h3>
              <div className="space-y-2">
                {((data.owner_analysis as { privileges: { title: string; selector: string; severity: Severity }[] }).privileges).map(
                  (p) => (
                    <div key={p.selector} className="flex items-center justify-between border-b border-border/60 py-2 text-sm last:border-0">
                      <span>{p.title}</span>
                      <code className="text-xs text-muted">{p.selector}</code>
                    </div>
                  ),
                )}
              </div>
            </Card>
          )}
        </div>
      )}

      {tab === "simulation" && data.simulation && <SimulationPanel simulation={data.simulation} />}

      {tab === "findings" && (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setFilter("all")}
              className={cn("pill border", filter === "all" ? "border-sky-500 text-sky-300" : "border-border text-muted")}
            >
              all ({findings.length})
            </button>
            {SEVERITY_ORDER.map((s) => {
              const count = findings.filter((f) => f.severity === s).length;
              return (
                <button
                  key={s}
                  onClick={() => setFilter(s)}
                  className={cn(
                    "pill border",
                    filter === s ? `${SEVERITY_STYLES[s].border} ${SEVERITY_STYLES[s].text}` : "border-border text-muted",
                  )}
                >
                  {s} ({count})
                </button>
              );
            })}
          </div>
          {filtered.length === 0 ? (
            <p className="text-sm text-muted">No findings at this severity.</p>
          ) : (
            filtered.map((f) => <FindingCard key={f.id} finding={f} />)
          )}
        </div>
      )}
    </div>
  );
}

export default function AnalysisPage() {
  return (
    <Suspense fallback={<p className="text-sm text-muted">Loading…</p>}>
      <AnalysisView />
    </Suspense>
  );
}
