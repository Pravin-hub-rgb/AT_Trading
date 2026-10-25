"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { getTokenStatus, TokenStatus } from "@/lib/api";
import TokenDialog from "./TokenDialog";

const links = [
  { href: "/", label: "Home" },
  { href: "/download", label: "Download Data" },
  { href: "/chart", label: "Chart" },
  { href: "/btc", label: "BTC" },
  { href: "/results", label: "Results" },
  { href: "/forward-testing", label: "Forward Testing" },
];

export default function Navbar() {
  const pathname = usePathname();
  const [token, setToken] = useState<TokenStatus | null>(null);
  const [tokenOpen, setTokenOpen] = useState(false);

  useEffect(() => {
    getTokenStatus()
      .then(setToken)
      .catch(() => setToken(null));
  }, [tokenOpen]);

  const dotColor = !token?.configured
    ? "bg-[#ef4444]"
    : token.valid
      ? "bg-[#10b981]"
      : token.valid === false
        ? "bg-[#ef4444]"
        : "bg-[#f59e0b]";

  return (
    <header className="sticky top-0 z-40 border-b border-[#21262d] bg-[#0d1117]/90 backdrop-blur">
      <nav className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
        <div className="flex items-center gap-6">
          <span className="text-base font-bold text-[#e6edf3]">
            AT<span className="text-[#6366f1]">Trading</span>
          </span>
          <div className="flex items-center gap-1">
            {links.map((l) => {
              const active = pathname === l.href;
              return (
                <Link
                  key={l.href}
                  href={l.href}
                  className={`rounded-md px-3 py-1.5 text-sm transition-colors ${
                    active
                      ? "bg-[#21262d] text-[#e6edf3]"
                      : "text-[#8b949e] hover:text-[#e6edf3]"
                  }`}
                >
                  {l.label}
                </Link>
              );
            })}
          </div>
        </div>
        <button
          onClick={() => setTokenOpen(true)}
          className="rounded-md border border-[#30363d] px-3 py-1.5 text-sm text-[#e6edf3] hover:bg-[#21262d]"
        >
          Token{" "}
          <span className={`ml-1 inline-block h-2 w-2 rounded-full ${dotColor}`} />
        </button>
      </nav>
      <TokenDialog open={tokenOpen} onClose={() => setTokenOpen(false)} />
    </header>
  );
}