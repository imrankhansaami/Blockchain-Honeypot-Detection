import type {
  AnalysisCreated,
  AnalysisResult,
  AnalysisSummary,
  ChainInfo,
  Stats,
  TokenInfo,
} from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}/api/v1${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? body);
    } catch {
      /* ignore */
    }
    throw new Error(`API ${res.status}: ${detail}`);
  }
  return (await res.json()) as T;
}

export const api = {
  health: () => request<{ status: string; chains: ChainInfo[] }>("/health"),
  chains: () => request<ChainInfo[]>("/chains"),
  stats: () => request<Stats>("/stats"),
  analyses: (limit = 20) => request<AnalysisSummary[]>(`/analyses?limit=${limit}`),
  analyze: (chain_id: number, token_address: string, analysis_depth: string) =>
    request<AnalysisCreated>("/analyze", {
      method: "POST",
      body: JSON.stringify({ chain_id, token_address, analysis_depth }),
    }),
  analysis: (id: string) => request<AnalysisResult>(`/analyze/${id}`),
  token: (chainId: number, address: string) =>
    request<TokenInfo>(`/token/${chainId}/${address}`),
  simulation: (id: string) => request<unknown>(`/reports/${id}`),
  reportUrl: (id: string, format: "json" | "html" | "pdf") =>
    `${API_BASE}/api/v1/reports/${id}/download?format=${format}`,
};

export { API_BASE };
