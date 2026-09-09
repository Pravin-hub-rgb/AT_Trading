"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { API_BASE } from "@/lib/api";

interface TfStatus {
  last_ts: string;
}

interface FetchStatus {
  "1m": TfStatus;
  "5m": TfStatus;
  "15m": TfStatus;
  "1h": TfStatus;
  "4h": TfStatus;
}

interface FetchResult {
  tf: string;
  ok: boolean;
  appended: number;
  fetched: number;
  last_ts: string;
  note?: string;
}

const ALL_TFS = ["1m", "5m", "15m", "1h", "4h"] as const;
type TfKey = (typeof ALL_TFS)[number];

const tfLabels: Record<TfKey, string> = {
  "1m": "1-Min",
  "5m": "5-Min",
  "15m": "15-Min",
  "1h": "1-Hour",
  "4h": "4-Hour",
};

export default function BtcFetchPanel() {
  const [status, setStatus] = useState<FetchStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState<Set<TfKey>>(new Set(["15m", "1h"]));
  const [result, setResult] = useState<FetchResult[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/btc/fetch/status`);
      if (res.ok) setStatus(await res.json());
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 30000);
    return () => clearInterval(id);
  }, [refresh]);

  const toggle = (tf: TfKey) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(tf)) next.delete(tf);
      else next.add(tf);
      return next;
    });
  };

  const handleFetch = async () => {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch(`${API_BASE}/api/btc/fetch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tfs: Array.from(selected) }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setResult(data.results);
      refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const handleFetchAll = async () => {
    setSelected(new Set(ALL_TFS));
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch(`${API_BASE}/api/btc/fetch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tfs: Array.from(ALL_TFS) }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setResult(data.results);
      refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const totalAppended = result?.reduce((s, r) => s + r.appended, 0) ?? 0;

  return (
    <div className="rounded-lg border border-[#21262d] bg-[#161b22] p-4">
      <div className="mb-3 flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-[#e6edf3]">BTC / USDT</h2>
          <p className="text-xs text-[#8b949e]">
            Binance spot OHLCV · appends only new candles · idempotent
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href="/btc"
            className="rounded-md border border-[#6366f1] bg-[#6366f1]/10 px-3 py-1.5 text-xs font-medium text-[#6366f1] hover:bg-[#6366f1]/20"
          >
            Go to BTC Chart →
          </Link>
          <button
            onClick={handleFetchAll}
            disabled={busy}
            className="rounded-md border border-[#f59e0b] bg-[#f59e0b]/10 px-3 py-1.5 text-xs font-medium text-[#f59e0b] hover:bg-[#f59e0b]/20 disabled:opacity-50"
          >
            {busy ? "Fetching..." : "Fetch All"}
          </button>
          <button
            onClick={handleFetch}
            disabled={busy || selected.size === 0}
            className="rounded-md bg-[#6366f1] px-4 py-1.5 text-xs font-medium text-white hover:bg-[#7c7ff7] disabled:opacity-50"
          >
            {busy ? "Fetching..." : `Fetch Selected (${selected.size})`}
          </button>
        </div>
      </div>

      {/* TF selector */}
      <div className="mb-3 flex flex-wrap gap-2">
        {ALL_TFS.map((tf) => (
          <button
            key={tf}
            onClick={() => toggle(tf)}
            className={`rounded-md border px-3 py-1 text-xs font-medium transition-colors ${
              selected.has(tf)
                ? "border-[#6366f1] bg-[#6366f1]/20 text-[#6366f1]"
                : "border-[#30363d] bg-[#0d1117] text-[#8b949e] hover:border-[#6366f1]/50"
            }`}
          >
            {tfLabels[tf]}
          </button>
        ))}
      </div>

      {/* Status grid */}
      {status && (
        <div className="mb-3 grid grid-cols-5 gap-2">
          {ALL_TFS.map((tf) => (
            <div
              key={tf}
              className="rounded-md border border-[#21262d] bg-[#0d1117] px-2 py-1.5 text-center"
            >
              <div className="text-[10px] text-[#8b949e]">{tfLabels[tf]}</div>
              <div className="truncate font-mono text-xs text-[#e6edf3]">
                {status[tf]?.last_ts?.slice(5, 16) ?? "—"}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Result */}
      {result && (
        <div
          className={`rounded-md border px-3 py-2 text-xs ${
            totalAppended > 0
              ? "border-[#10b981]/50 bg-[#10b981]/10 text-[#10b981]"
              : "border-[#30363d] bg-[#0d1117] text-[#8b949e]"
          }`}
        >
          {totalAppended > 0
            ? `✓ Appended ${totalAppended} new rows across ${result.length} TF(s)`
            : "All TFs are current — nothing to append"}
        </div>
      )}

      {error && (
        <div className="mt-2 rounded-md border border-[#ef4444]/50 bg-[#ef4444]/10 px-3 py-2 text-xs text-[#ef4444]">
          {error}
        </div>
      )}
    </div>
  );
}
