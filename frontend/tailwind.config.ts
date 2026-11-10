import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0b0f17",
        panel: "#121826",
        border: "#1f2937",
        muted: "#8b97ab",
        crit: "#f43f5e",
        high: "#fb923c",
        med: "#facc15",
        low: "#38bdf8",
        info: "#64748b",
        ok: "#34d399",
      },
      fontFamily: {
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
