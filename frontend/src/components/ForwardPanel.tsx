"use client";

import { useEffect, useState } from "react";
import {
  ForwardSummary,
  ForwardCandidate,
  getForwardSummary,
} from "@/lib/forwardApi";

const BOOK_LABELS: Record<string, string> = {
  FSENT_SIG_MULTI: "sig multi",
  FSENT_CHAMP_LONG: "champ long",
  MCLOFF_HTF15: "107 - mcloff+htf15",
  HTF15_TSKIP6: "110 - tskip6 (110 candidate)",
  HTFFS: "106 - htffs",
  TSKIP4: "tskip4",
  HTF15_HTFFS: "htf15+htffs",
  HTFESMCL4: "108 - htfsmcl4",
};

function fmtVerdict(v: string | object | undefined): { text: string; cls: string } {
  if (typeof v === "string") {
    if (v.includes("NOT PRE-REGISTERED"))
      return { text: "info", cls: "text-[#6e7681]" };
    if (v.includes("NO VERDICT"))
      return { text: "provisional", cls: "text-[#d29922]" };
    if (v.includes("verdict"))
      return { text: "verdict", cls: "text-[#3fb950]" };
    return { text: "-", cls: "text-[#6e7681]" };
  }
  return { text: "provisional", cls: "text-[#6e7681]" };
}

interface BookRow {
  key: string;
  config: string;
  forward: ForwardCandidate["forward"];
  verdict: ForwardCandidate["verdict"];
  forward_trade_log: ForwardCandidate["forward_trade_log"];
}

export default function ForwardPanel() {
  const [data, setData] = useState<ForwardSummary | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(true);
  const [selected, setSelected] = useState<string | null>(null);

  const load = (refresh = false) => {
    setBusy(true);
    getForwardSummary(refresh)
      .then((d) => {
        setData(d);
        setErr(null);
      })
      .catch((e: Error) => setErr(e.message))
      .finally(() => setBusy(false));
  };

  useEffect(() => {
    let cancelled = false;
    getForwardSummary()
      .then((d) => {
        if (cancelled) return;
        setData(d);
        setErr(null);
      })
      .catch((e: Error) => {
        if (cancelled) return;
        setErr(e.message);
      })
      .finally(() => {
        if (!cancelled) setBusy(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const rows: BookRow[] = Object.entries(data?.candidates ?? {}).map(
    ([k, v]) => ({ key: k, config: v.config, forward: v.forward, verdict: v.verdict, forward_trade_log: v.forward_trade_log }),
  );

  if (err) {
    return (
      <div className="rounded-lg border border-[#3a1a1c] bg-[#161b22] p-4 text-sm text-[#f85149]">
        <p className="font-semibold">Could not load forward data.</p>
        <p className="mt-1 text-[#8b949e]">{err}</p>
        <p className="mt-2 text-[#8b949e]">
          Regenerate the artifact with:{" "}
          <code className="text-[#6366f1]">cd backtest && python tests/exp_forward_eval.py</code>
        </p>
      </div>
    );
  }

  if (!data) {
    return <p className="text-sm text-[#8b949e]">{busy ? "Loading..." : ""}</p>;
  }

  const sel = rows.find((r) => r.key === selected);

  return (
    <div className="space-y-5">
      {/* header */}
      <div>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-xl font-semibold text-[#e6edf3]">
            Forward Testing Dashboard
          </h1>
          <button
            onClick={() => load(true)}
            className="rounded-md border border-[#30363d] px-3 py-1.5 text-sm text-[#e6edf3] hover:bg-[#21262d]"
          >
            {busy ? "Refreshing..." : "Refresh artifact"}
          </button>
        </div>
        <p className="mt-1 max-w-4xl text-sm text-[#8b949e]">
          Cutoff: <strong className="text-[#e6edf3]">{data.cutoff_ist}</strong> IST
          ({data.cutoff_ts}). Combined:{" "}
          {data.combined_15m_bars.toLocaleString()} 15m bars,{" "}
          {data.combined_1h_bars.toLocaleString()} 1h bars,{" "}
          {data.fine_1m_bars.toLocaleString()} 1m bars. The forward window is never
          searched or tuned - see{" "}
          <code className="text-[#6366f1]">
            backtest/docs/learn/01_rules/FORWARD_BOUNDARY.md
          </code>
          .
        </p>
      </div>

      {/* provisional banner */}
      <div className="rounded-md border border-[#2d2a1c] bg-[#1c1e16] p-4">
        <div className="flex items-start gap-3">
          <div className="mt-0.5 shrink-0 rounded bg-[#d29922] px-2 py-0.5 text-xs font-bold text-white">
            PROVISIONAL
          </div>
          <p className="text-sm text-[#c9a5a5]">
            Below 50 trades for every candidate. Per the pre-registered contract,
            results are informational only - no verdict until the stop rule (50
            trades or 6 months) is met.
          </p>
        </div>
      </div>

      {/* candidate table */}
      <div className="overflow-x-auto rounded-lg border border-[#21262d]">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-[#161b22]">
              <th className="px-3 py-2 text-left text-xs font-semibold text-[#8b949e]">
                candidate
              </th>
              <th className="px-3 py-2 text-left text-xs font-semibold text-[#8b949e]">
                config
              </th>
              <th className="px-3 py-2 text-right text-xs font-semibold text-[#8b949e]">
                fwd trades
              </th>
              <th className="px-3 py-2 text-right text-xs font-semibold text-[#8b949e]">
                net R
              </th>
              <th className="px-3 py-2 text-right text-xs font-semibold text-[#8b949e]">
                avg R
              </th>
              <th className="px-3 py-2 text-right text-xs font-semibold text-[#8b949e]">
                WR
              </th>
              <th className="px-3 py-2 text-right text-xs font-semibold text-[#8b949e]">
                PF
              </th>
              <th className="px-3 py-2 text-right text-xs font-semibold text-[#8b949e]">
                max DD
              </th>
              <th className="px-3 py-2 text-right text-xs font-semibold text-[#8b949e]">
                verdict
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((b) => {
              const g = b.forward.gross;
              const n = b.forward.net;
              const v = fmtVerdict(b.verdict);
              return (
                <tr
                  key={b.key}
                  className={`border-t border-[#21262d] cursor-pointer transition-colors ${
                    selected === b.key ? "bg-[#1b2330]" : "hover:bg-[#161b22]"
                  }`}
                  onClick={() =>
                    setSelected(selected === b.key ? null : b.key)
                  }
                >
                  <td className="px-3 py-1.5 text-[#e6edf3]">
                    {BOOK_LABELS[b.key] ?? b.key}
                  </td>
                  <td className="px-3 py-1.5 font-mono text-xs text-[#8b949e]">
                    {b.config}
                  </td>
                  <td className="px-3 py-1.5 text-right tabular-nums">
                    {g.n}
                  </td>
                  <td className="px-3 py-1.5 text-right tabular-nums">
                    <span className={n.sum_r >= 0 ? "text-[#3fb950]" : "text-[#f85149]"}>
                      {n.sum_r >= 0 ? "+" : ""}{n.sum_r.toFixed(2)}
                    </span>
                  </td>
                  <td className="px-3 py-1.5 text-right tabular-nums">
                    {n.avg_r.toFixed(3)}
                  </td>
                  <td className="px-3 py-1.5 text-right tabular-nums">
                    {g.wr_pct.toFixed(1)}%
                  </td>
                  <td className="px-3 py-1.5 text-right tabular-nums">
                    {g.pf.toFixed(2)}
                  </td>
                  <td className="px-3 py-1.5 text-right tabular-nums">
                    {n.max_dd.toFixed(1)}R
                  </td>
                  <td className="px-3 py-1.5 text-right">
                    <span className={v.cls}>{v.text}</span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* monthly breakdown for selected */}
      {sel && <MonthlyBreakdown candidate={sel} bookKey={selected!} />}

      {/* equity curve for selected */}
      {sel && <EquityCurve candidate={sel} bookKey={selected!} />}

      {/* trade log for selected */}
      {sel && <TradeLog candidate={sel} bookKey={selected!} cutoff={data.cutoff_ist} />}
    </div>
  );
}

function EquityCurve({
  candidate,
  bookKey,
}: {
  candidate: BookRow;
  bookKey: string;
}) {
  const trades = candidate.forward_trade_log ?? [];
  if (trades.length === 0) return null;

  const cum = [];
  let running = 0;
  for (const t of trades) {
    running += t.net;
    cum.push(running);
  }
  const vMax = Math.max(...cum, 0);
  const vMin = Math.min(...cum, 0);
  const W = 580, H = 200, PL = 50, PR = 16, PT = 12, PB = 28;

  const x = (i: number) => PL + (i / Math.max(1, cum.length - 1)) * (W - PL - PR);
  const y = (v: number) => PT + H - PT - PB - ((v - vMin) / (vMax - vMin || 1)) * (H - PT - PB - 14);

  const palette = "#3fb950";
  const path = cum
    .map((v, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(v).toFixed(1)}`)
    .join(" ");

  return (
    <div className="rounded-lg border border-[#21262d] bg-[#161b22] p-4">
      <h2 className="text-sm font-semibold text-[#e6edf3]">
        Forward equity curve - {BOOK_LABELS[bookKey] ?? bookKey}
      </h2>
      <p className="mb-3 text-xs text-[#8b949e]">
        Cumulative net R per forward trade ({trades.length} trades)
      </p>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} className="block">
        <line x1={PL} y1={y(0)} x2={W - PR} y2={y(0)} stroke="#30363d" strokeWidth={1} />
        {[0, 0.25, 0.5, 0.75, 1].map((f) => {
          const v = vMin + f * (vMax - vMin);
          return (
            <text key={f} x={PL - 6} y={y(v) + 4} textAnchor="end" fontSize={10} fill="#8b949e">
              {v.toFixed(0)}R
            </text>
          );
        })}
        <path d={path} fill="none" stroke={palette} strokeWidth={1.8} />
        <text x={PL} y={H - 6} fontSize={10} fill="#8b949e">
          trade 1
        </text>
        <text x={W - PR} y={H - 6} fontSize={10} fill="#8b949e" textAnchor="end">
          {trades.length} trades
        </text>
        <line
          x1={x(trades.length - 1)}
          y1={PT}
          x2={x(trades.length - 1)}
          y2={y(cum[cum.length - 1])}
          stroke={palette}
          strokeWidth={1}
          strokeDasharray="3,2"
        />
      </svg>
    </div>
  );
}

function MonthlyBreakdown({
  candidate,
  bookKey,
}: {
  candidate: BookRow;
  bookKey: string;
}) {
  const monthly = candidate.forward.monthly_net ?? {};
  const entries = Object.entries(monthly).sort(([a], [b]) =>
    a < b ? -1 : 1,
  );
  const posCount = entries.filter(([, v]) => v > 0).length;

  return (
    <div className="rounded-lg border border-[#21262d] bg-[#161b22] p-4">
      <h2 className="text-sm font-semibold text-[#e6edf3]">
        Monthly net - {BOOK_LABELS[bookKey] ?? bookKey}
      </h2>
      <p className="mb-3 text-xs text-[#8b949e]">
        {posCount}/{entries.length} months positive
      </p>
      <div className="space-y-1.5">
        {entries.map(([month, val]) => (
          <div key={month} className="flex items-center gap-3">
            <span className="w-16 text-xs text-[#8b949e]">{month}</span>
            <div className="relative h-4 w-full">
              <div
                className={`h-full rounded ${val >= 0 ? "bg-[#3fb950]" : "bg-[#f85149]"}`}
                style={{
                  width: `${Math.min(Math.abs(val) * 10, 100)}%`,
                }}
              />
            </div>
            <span
              className={`w-16 text-right text-xs tabular-nums ${val >= 0 ? "text-[#3fb950]" : "text-[#f85149]"}`}
            >
              {val >= 0 ? "+" : ""}{val.toFixed(2)}R
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function TradeLog({
  candidate,
  bookKey,
  cutoff,
}: {
  candidate: BookRow;
  bookKey: string;
  cutoff: string;
}) {
  const log = candidate.forward_trade_log ?? [];
  return (
    <div className="rounded-lg border border-[#21262d] bg-[#161b22] p-4">
      <h2 className="text-sm font-semibold text-[#e6edf3]">
        Forward trade log - {BOOK_LABELS[bookKey] ?? bookKey}
      </h2>
      <p className="mb-3 text-xs text-[#8b949e]">
        {log.length} forward trades (entered after {cutoff})
      </p>
      {log.length === 0 ? (
        <p className="text-xs text-[#8b949e]">No forward trades.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-[#0d1117]">
                <th className="px-2 py-1 text-left text-[#8b949e]">entry</th>
                <th className="px-2 py-1 text-left text-[#8b949e]">dir</th>
                <th className="px-2 py-1 text-right text-[#8b949e]">gross R</th>
                <th className="px-2 py-1 text-right text-[#8b949e]">net R</th>
                <th className="px-2 py-1 text-right text-[#8b949e]">bars</th>
                <th className="px-2 py-1 text-left text-[#8b949e]">outcome</th>
              </tr>
            </thead>
            <tbody>
              {log.map((t, i) => (
                <tr key={i} className="border-t border-[#21262d]">
                  <td className="px-2 py-1 text-[#e6edf3]">{t.entry_date}</td>
                  <td className="px-2 py-1">{t.dir}</td>
                  <td className="px-2 py-1 text-right tabular-nums">
                    {t.r >= 0 ? "+" : ""}{t.r.toFixed(2)}
                  </td>
                  <td className="px-2 py-1 text-right tabular-nums">
                    <span
                      className={t.net >= 0 ? "text-[#3fb950]" : "text-[#f85149]"}
                    >
                      {t.net >= 0 ? "+" : ""}{t.net.toFixed(2)}
                    </span>
                  </td>
                  <td className="px-2 py-1 text-right tabular-nums">
                    {t.bars_held}
                  </td>
                  <td className="px-2 py-1 text-[#8b949e]">{t.outcome}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
