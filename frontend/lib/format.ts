import { clsx, type ClassValue } from "clsx";

export function cn(...inputs: ClassValue[]): string {
  return clsx(inputs);
}

export function shortAddress(addr: string | null | undefined, size = 6): string {
  if (!addr) return "—";
  if (addr.length <= size * 2 + 2) return addr;
  return `${addr.slice(0, size + 2)}…${addr.slice(-size)}`;
}

export function formatBps(bps: number | null | undefined): string {
  if (bps === null || bps === undefined) return "inconclusive";
  return `${(bps / 100).toFixed(2)}%`;
}

export function formatWei(wei: number | null | undefined, decimals = 4): string {
  if (wei === null || wei === undefined) return "—";
  return (wei / 1e18).toFixed(decimals);
}

export function formatBig(value: number | string | null | undefined): string {
  if (value === null || value === undefined) return "—";
  const n = typeof value === "string" ? Number(value) : value;
  if (!Number.isFinite(n)) return String(value);
  if (n >= 1e15) return `${(n / 1e15).toFixed(2)}Q`;
  if (n >= 1e12) return `${(n / 1e12).toFixed(2)}T`;
  if (n >= 1e9) return `${(n / 1e9).toFixed(2)}B`;
  if (n >= 1e6) return `${(n / 1e6).toFixed(2)}M`;
  return n.toLocaleString();
}

export function formatDuration(ms: number | null | undefined): string {
  if (ms === null || ms === undefined) return "—";
  if (ms < 1000) return `${Math.round(ms)} ms`;
  return `${(ms / 1000).toFixed(2)} s`;
}

export function timeAgo(iso: string): string {
  const then = new Date(iso).getTime();
  const diff = Date.now() - then;
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}
