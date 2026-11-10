"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/format";

const NAV = [
  { href: "/", label: "Overview", icon: "▤" },
  { href: "/analyze", label: "Token Analyzer", icon: "⌕" },
  { href: "/reports", label: "Report Center", icon: "▦" },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="hidden w-60 shrink-0 border-r border-border bg-[#0d1320] px-4 py-6 md:block">
      <div className="mb-8 flex items-center gap-2 px-2">
        <span className="grid h-8 w-8 place-items-center rounded-lg bg-sky-600 text-sm font-bold">H</span>
        <div>
          <p className="text-sm font-semibold leading-tight">Honeypot Detector</p>
          <p className="text-[11px] text-muted">Token Security Analyzer</p>
        </div>
      </div>
      <nav className="space-y-1">
        {NAV.map((item) => {
          const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
                active ? "bg-white/10 text-white" : "text-slate-400 hover:bg-white/5 hover:text-slate-200",
              )}
            >
              <span className="text-muted">{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="mt-10 rounded-lg border border-border bg-panel/60 p-3 text-[11px] text-muted">
        Automated analysis — not a formal audit. No guarantee of token safety.
      </div>
    </aside>
  );
}
