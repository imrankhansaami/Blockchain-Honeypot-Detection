"use client";

import { useState } from "react";
import type { Finding } from "@/types";
import { SeverityBadge, ConfidenceTag } from "@/components/SeverityBadge";
import { Card } from "@/components/Card";

export function FindingCard({ finding }: { finding: Finding }) {
  const [open, setOpen] = useState(false);
  return (
    <Card className="!p-4">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-start justify-between gap-3 text-left"
      >
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <SeverityBadge severity={finding.severity} />
            <span className="font-medium text-slate-100">{finding.title}</span>
          </div>
          <p className="mt-2 text-sm text-slate-400">{finding.description}</p>
          <p className="mt-1 text-xs text-muted">
            category: {finding.category} · <ConfidenceTag confidence={finding.confidence} /> · source:{" "}
            {finding.source}
          </p>
        </div>
        <span className="mt-1 shrink-0 text-muted">{open ? "−" : "+"}</span>
      </button>

      {open && (
        <div className="mt-4 space-y-3 border-t border-border pt-4">
          {finding.impact && (
            <div>
              <p className="text-xs uppercase tracking-wide text-muted">Impact</p>
              <p className="text-sm text-slate-300">{finding.impact}</p>
            </div>
          )}
          {finding.recommendation && (
            <div>
              <p className="text-xs uppercase tracking-wide text-muted">Recommended mitigation</p>
              <p className="text-sm text-slate-300">{finding.recommendation}</p>
            </div>
          )}
          {finding.references.length > 0 && (
            <div>
              <p className="text-xs uppercase tracking-wide text-muted">References</p>
              <div className="mt-1 flex flex-wrap gap-2">
                {finding.references.map((r) => (
                  <code key={r} className="rounded bg-black/40 px-2 py-0.5 text-xs text-slate-300">
                    {r}
                  </code>
                ))}
              </div>
            </div>
          )}
          <div>
            <p className="text-xs uppercase tracking-wide text-muted">Technical evidence</p>
            <pre className="mt-1 max-h-72 overflow-auto rounded-lg border border-border bg-black/40 p-3 text-xs text-slate-300">
              {JSON.stringify(finding.evidence, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </Card>
  );
}
