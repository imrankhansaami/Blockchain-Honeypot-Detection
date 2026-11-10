import type { Severity } from "@/types";

export const SEVERITY_ORDER: Severity[] = [
  "critical",
  "high",
  "medium",
  "low",
  "informational",
];

export const SEVERITY_STYLES: Record<Severity, { text: string; bg: string; border: string; dot: string }> = {
  critical: { text: "text-rose-400", bg: "bg-rose-500/10", border: "border-rose-500/40", dot: "bg-rose-500" },
  high: { text: "text-orange-400", bg: "bg-orange-500/10", border: "border-orange-500/40", dot: "bg-orange-500" },
  medium: { text: "text-yellow-400", bg: "bg-yellow-500/10", border: "border-yellow-500/40", dot: "bg-yellow-500" },
  low: { text: "text-sky-400", bg: "bg-sky-500/10", border: "border-sky-500/40", dot: "bg-sky-500" },
  informational: { text: "text-slate-400", bg: "bg-slate-500/10", border: "border-slate-500/40", dot: "bg-slate-500" },
};

export function riskColor(score: number): string {
  if (score >= 80) return "#f43f5e";
  if (score >= 60) return "#fb923c";
  if (score >= 40) return "#facc15";
  if (score >= 20) return "#38bdf8";
  return "#34d399";
}
