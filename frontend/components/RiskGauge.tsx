import { riskColor } from "@/lib/constants";

export function RiskGauge({ score, classification }: { score: number; classification: string }) {
  const size = 180;
  const stroke = 14;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = Math.max(0, Math.min(100, score)) / 100;
  const color = riskColor(score);

  return (
    <div className="flex items-center gap-6">
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} stroke="#1f2937" strokeWidth={stroke} fill="none" />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={color}
          strokeWidth={stroke}
          fill="none"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - progress)}
          style={{ transition: "stroke-dashoffset 700ms ease" }}
        />
      </svg>
      <div className="-ml-[130px]" style={{ minWidth: 110 }}>
        <p className="text-5xl font-bold" style={{ color }}>
          {score}
          <span className="text-lg text-muted">/100</span>
        </p>
      </div>
      <div>
        <p className="text-xs uppercase tracking-wide text-muted">Verdict</p>
        <p className="text-xl font-semibold" style={{ color }}>
          {classification}
        </p>
      </div>
    </div>
  );
}
