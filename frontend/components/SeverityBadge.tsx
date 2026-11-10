import type { Severity } from "@/types";
import { SEVERITY_STYLES } from "@/lib/constants";
import { cn } from "@/lib/format";

export function SeverityBadge({ severity }: { severity: Severity }) {
  const s = SEVERITY_STYLES[severity] ?? SEVERITY_STYLES.informational;
  return <span className={cn("pill", s.bg, s.text)}>{severity}</span>;
}

export function ConfidenceTag({ confidence }: { confidence: string }) {
  const tone =
    confidence === "confirmed"
      ? "text-emerald-400"
      : confidence === "suspicious"
        ? "text-yellow-400"
        : "text-slate-400";
  return <span className={cn("text-xs", tone)}>{confidence}</span>;
}
