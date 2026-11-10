export function StatCard({
  label,
  value,
  hint,
  tone = "neutral",
}: {
  label: string;
  value: string | number;
  hint?: string;
  tone?: "neutral" | "danger" | "warn" | "ok";
}) {
  const color =
    tone === "danger"
      ? "text-rose-400"
      : tone === "warn"
        ? "text-orange-400"
        : tone === "ok"
          ? "text-emerald-400"
          : "text-slate-100";
  return (
    <div className="card">
      <p className="text-xs font-medium uppercase tracking-wide text-muted">{label}</p>
      <p className={`mt-2 text-3xl font-semibold ${color}`}>{value}</p>
      {hint ? <p className="mt-1 text-xs text-muted">{hint}</p> : null}
    </div>
  );
}
