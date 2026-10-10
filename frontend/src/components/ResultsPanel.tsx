"use client";

import { useEffect, useMemo, useState } from "react";
import {
  BookTag,
  ResultBook,
  ResultsPayload,
  getResults,
} from "@/lib/resultsApi";

/* ------------------------------------------------------------------ config */

type Group = "Significance" | "Return" | "Risk" | "Smoothness" | "Consistency" | "Tail" | "Costs" | "Size";

interface Metric {
  key: keyof ResultBook;
  label: string;
  group: Group;
  lowerBetter?: boolean;
  /** neither end is optimal - never marked as a winner (trade count) */
  neutral?: boolean;
  dp?: number;
  suffix?: string;
  /** short plain-language meaning, shown on hover */
  hint: string;
}

const METRICS: Metric[] = [
  { key: "net", label: "Net R", group: "Return", dp: 0, hint: "Total R across both eras. Big but not the ranking metric." },
  { key: "expectancy", label: "R/trade", group: "Return", dp: 3, hint: "Net R divided by trade count. The per-trade edge." },
  { key: "pf", label: "PF", group: "Return", dp: 2, hint: "Profit factor: gross win / gross loss." },
  { key: "wr", label: "WR %", group: "Return", dp: 1, hint: "Win rate. Do not overvalue it - a right tail is normal here." },
  { key: "tstat", label: "t-stat", group: "Return", dp: 2, hint: "How sure we are the edge is real and not luck. Above 2 is convincing." },

  { key: "max_dd", label: "Max DD", group: "Risk", lowerBetter: true, dp: 2, suffix: "R", hint: "Deepest peak-to-trough fall in R." },
  { key: "net_to_dd", label: "Net/DD", group: "Risk", dp: 1, hint: "How much return per unit of pain." },
  { key: "dd_pct_of_net", label: "DD % of net", group: "Risk", lowerBetter: true, dp: 1, hint: "Drawdown as a share of total return." },
  { key: "max_streak", label: "Loss streak", group: "Risk", lowerBetter: true, dp: 0, hint: "Longest run of consecutive losing trades." },

  { key: "ulcer", label: "Ulcer", group: "Smoothness", lowerBetter: true, dp: 2, hint: "Pain intensity: not just how deep the fall, but how long and how often. The real smoothness number." },
  { key: "sortino", label: "Sortino", group: "Smoothness", dp: 2, hint: "Return per unit of DOWNSIDE volatility. Upside noise is ignored." },
  { key: "calmar", label: "Calmar", group: "Smoothness", dp: 1, hint: "Return divided by max drawdown." },
  { key: "uw_pct", label: "% underwater", group: "Smoothness", lowerBetter: true, dp: 1, suffix: "%", hint: "Share of time spent below the running peak." },
  { key: "longest_underwater", label: "Longest UW", group: "Smoothness", lowerBetter: true, dp: 0, suffix: "t", hint: "Longest stretch below the peak, in trades." },
  { key: "recovery", label: "Recovery", group: "Smoothness", lowerBetter: true, dp: 1, suffix: "t", hint: "Trades needed to climb back from the worst drawdown." },

  { key: "worst_roll50", label: "Worst 50", group: "Consistency", dp: 1, suffix: "R", hint: "Worst net across any 50 consecutive trades. Positive means it has never had a bad 50." },
  { key: "worst_roll100", label: "Worst 100", group: "Consistency", dp: 1, suffix: "R", hint: "Same over any 100 consecutive trades." },
  { key: "retention", label: "OOS retention", group: "Consistency", dp: 0, suffix: "%", hint: "Out-of-sample R/trade as a share of in-sample. Above 100% means it did better OOS." },
  { key: "years_positive", label: "Years +", group: "Consistency", dp: 0, suffix: "%", hint: "Share of calendar years that were profitable." },

  { key: "top1_contrib", label: "Top 1%", group: "Tail", dp: 0, suffix: "%", hint: "Share of profit from the best 1% of trades. High means a few trades carry it." },
  { key: "top5_contrib", label: "Top 5%", group: "Tail", dp: 0, suffix: "%", hint: "40-60% is normal for trend following. 70-90% is a warning zone." },
  { key: "top10_contrib", label: "Top 10%", group: "Tail", dp: 0, suffix: "%", hint: "Share of profit from the best 10% of trades." },
  { key: "cap10_net", label: "10R cap", group: "Tail", dp: 0, suffix: "R", hint: "Net if no trade were allowed to exceed 10R. High means the edge is not one monster trade." },

  { key: "cost_2x", label: "2x costs", group: "Costs", dp: 0, suffix: "R", hint: "Net if fees doubled. Below zero means fees kill it." },
  { key: "cost_3x", label: "3x costs", group: "Costs", dp: 0, suffix: "R", hint: "Net at triple fees." },

  { key: "null_p_is", label: "p IS", group: "Significance", lowerBetter: true, dp: 4, hint: "Paired permutation, in sample. Under the null this arm's trades could have been shuffled against the shipping book's by chance and produced the same gap. Below 0.05 means no." },
  { key: "null_p_oos", label: "p OOS", group: "Significance", lowerBetter: true, dp: 4, hint: "The same test out of sample (2021-22, reused data - not a holdout). The column that matters: an arm can be significant in sample and fail here." },
  { key: "null_dnet_is", label: "gap IS", group: "Significance", dp: 0, suffix: "R", hint: "Net the arm gains over the shipping book, in sample. The size of the effect the p-value is testing." },
  { key: "null_dnet_oos", label: "gap OOS", group: "Significance", dp: 0, suffix: "R", hint: "Same, out of sample." },

  { key: "tuned", label: "Knobs", group: "Size", lowerBetter: true, dp: 0, hint: "Non-default parameters. Each one is another chance to fit noise." },
  { key: "sd", label: "Trade SD", group: "Size", lowerBetter: true, dp: 2, hint: "How much a single trade swings. Large SD means many trades are needed to be sure." },
];

const GROUPS: Group[] = ["Significance", "Return", "Risk", "Smoothness", "Consistency", "Tail", "Costs", "Size"];


const TAG_META: Record<BookTag, { label: string; tone: string; hint: string }> = {
  "zero-negative": { label: "zero-negative", tone: "ok", hint: "No negative half-year in any of the 12 cells." },
  "low-DD": { label: "low-DD", tone: "ok", hint: "Max drawdown under 60% of the 29R budget." },
  "short-underwater": { label: "short-underwater", tone: "ok", hint: "Never below its peak for 30+ trades." },
  "low-tail": { label: "low-tail", tone: "ok", hint: "Best 5% of trades carry under 80% of the profit." },
  "cost-2x-safe": { label: "2x-cost-safe", tone: "ok", hint: "Still profitable at double fees." },
  "2x-cost-death": { label: "2x-cost-DEATH", tone: "bad", hint: "Loses money at double fees." },
  "consistent-eras": { label: "consistent-eras", tone: "ok", hint: "Profitable in BOTH the 2021-22 and 2023-26 eras." },
  "never-negative-50": { label: "never-negative-50", tone: "ok", hint: "Its worst 50 consecutive trades still made money." },
};

const DEFAULT_SELECTED = [
  "fsent_champ_long",
  "fsent_champ_long_mcloff",
  "fsent_champ_long_mcloff_htf15",
  "fsent_sig_multi",
  "fsent_sig_full",
];

const SHIPPING = "fsent_champ_long";

/* ---------------------------------------------------------------- helpers */

function short(name: string) {
  return name.replace(/^fsent_/, "").replace(/_htf15$/, "+htf15");
}

function fmt(m: Metric, v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "boolean") return v ? "yes" : "no";
  if (typeof v === "number") {
    const dp = m.dp ?? 2;
    const s = v.toFixed(dp);
    return m.key === "net" || m.key === "cost_2x" || m.key === "cost_3x" || m.key === "cap10_net"
      ? (v >= 0 ? `+${s}` : s) + (m.suffix ?? "")
      : s + (m.suffix ?? "");
  }
  return String(v);
}

/** Winners are compared at DISPLAY precision, not raw precision. Two books whose
 *  ulcer is 8.701 and 8.704 both print as 8.70; marking one of them the winner
 *  would be picking a tie that only exists in digits nobody can see. */
function isBest(m: Metric, v: number | null, best: number | null): boolean {
  if (v === null || v === undefined || best === null || best === undefined) return false;
  const dp = m.dp ?? 2;
  const scale = Math.pow(10, dp);
  if (Math.round(v * scale) !== Math.round(best * scale)) return false;
  return m.lowerBetter ? v <= best + 1e-9 : v >= best - 1e-9;
}

/* ----------------------------------------------------------------- chart */

function EquityChart({ books }: { books: ResultBook[] }) {
  const W = 1180, H = 340, PL = 62, PR = 16, PT = 14, PB = 30;
  const iw = W - PL - PR, ih = H - PT - PB;
  if (!books.length) return null;

  const nMax = Math.max(...books.map((b) => b.series.length));
  const vMax = Math.max(...books.flatMap((b) => b.series.map((p) => p[1])));
  const vMin = Math.min(0, ...books.flatMap((b) => b.series.map((p) => p[1])));
  const X = (i: number, n: number) => PL + (i / Math.max(1, n - 1)) * iw;
  const Y = (v: number) => PT + ih - ((v - vMin) / (vMax - vMin || 1)) * ih;

  const palette = ["#58a6ff", "#3fb950", "#d29922", "#f85149", "#bc8cff", "#39c5cf", "#ff7b72", "#7ee787"];

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} className="block">
      <line x1={PL} y1={Y(0)} x2={W - PR} y2={Y(0)} stroke="#30363d" strokeWidth={1} />
      {[0, 0.25, 0.5, 0.75, 1].map((f) => {
        const v = vMin + f * (vMax - vMin);
        return (
          <text key={f} x={PL - 6} y={Y(v) + 4} textAnchor="end" fontSize={10} fill="#8b949e">
            {v.toFixed(0)}R
          </text>
        );
      })}
      {books.map((b, bi) => {
        const n = b.series.length;
        const d = b.series
          .map((p, i) => `${i ? "L" : "M"}${X(i, n).toFixed(1)} ${Y(p[1]).toFixed(1)}`)
          .join("");
        return (
          <g key={b.name}>
            <path d={d} fill="none" stroke={palette[bi % palette.length]} strokeWidth={1.8} />
            <text
              x={X(n - 1, n) + 2}
              y={Y(b.series[n - 1][1]) + 3}
              fontSize={10}
              fill={palette[bi % palette.length]}
            >
              {short(b.name)}
            </text>
          </g>
        );
      })}
      <text x={PL} y={H - 8} fontSize={10} fill="#8b949e">
        trade 0
      </text>
      <text x={W - PR} y={H - 8} fontSize={10} fill="#8b949e" textAnchor="end">
        {nMax} trades
      </text>
    </svg>
  );
}

/* --------------------------------------------------------------- component */

export default function ResultsPanel() {
  const [data, setData] = useState<ResultsPayload | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(true);
  const [family, setFamily] = useState<"all" | "multi" | "sig">("all");
  const [selected, setSelected] = useState<string[]>(DEFAULT_SELECTED);
  // "__wins" sorts by the per-view best-in-column tally, which is not a book
  // field, so the sort key is widened here rather than pretending it is one.
  const [sortKey, setSortKey] = useState<keyof ResultBook | "__wins">("net");
  const [sortDir, setSortDir] = useState<1 | -1>(-1);
  const [group, setGroup] = useState<Group>("Significance");

  const load = (refresh = false) => {
    setBusy(true);
    getResults(undefined, refresh)
      .then((d) => {
        setData(d);
        setErr(null);
      })
      .catch((e) => setErr(String(e.message ?? e)))
      .finally(() => setBusy(false));
  };

  // `load` is the refresh-button handler and is allowed to setState synchronously
  // because it runs from a user event. The initial fetch cannot reuse it: calling
  // it from an effect body setStates during the effect, which cascades a second
  // render before anything has been drawn. So the mount fetch is written out, with
  // setState only inside the promise callbacks and a cancel flag so a response
  // that lands after unmount does not touch state.
  useEffect(() => {
    let cancelled = false;
    getResults()
      .then((d) => {
        if (cancelled) return;
        setData(d);
        setErr(null);
      })
      .catch((e) => {
        if (cancelled) return;
        setErr(String(e.message ?? e));
      })
      .finally(() => {
        if (!cancelled) setBusy(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Split in two on purpose. `filtered` is the unsorted set the reader is looking at;
// the winner pass and the win tally are computed from it because "best in column"
// is meaningless against books that are filtered off screen. Only then is the list
// sorted. Doing it the other way round makes books depend on winCounts while
// winCounts depends on books, which is a dependency cycle.
const filtered = useMemo(() => {
  if (!data) return [];
  return family === "all" ? data.books : data.books.filter((b) => b.family === family);
}, [data, family]);

  const shownMetrics = useMemo(() => METRICS.filter((m) => m.group === group), [group]);

  // The best value in each column, across the books currently in view. Recomputed
  // from the filtered set rather than a fixed top-N, so switching the family
  // filter re-decides what "best" means instead of comparing a long book against
  // a short one that is not on screen.
  const bestByKey = useMemo(() => {
    const out: Record<string, number | null> = {};
    for (const m of shownMetrics) {
      let best: number | null = null;
      for (const b of filtered) {
        const v = b[m.key as keyof ResultBook];
        if (typeof v !== "number") continue;
        if (best === null) best = v;
        else if (m.lowerBetter ? v < best : v > best) best = v;
      }
      out[String(m.key)] = best;
    }
    return out;
  }, [filtered, shownMetrics]);

  // How many of the metrics that are open right now each book tops. This is the
  // "which book is optimal at what" answer in one sortable column, and it counts
  // only what the reader is currently looking at rather than a hidden composite.
  const winCounts = useMemo(() => {
    const tally: Record<string, number> = {};
    for (const b of filtered) {
      let c = 0;
      for (const m of shownMetrics) {
        const v = b[m.key as keyof ResultBook];
        if (typeof v === "number" && isBest(m, v, bestByKey[String(m.key)] ?? null)) c += 1;
      }
      tally[b.name] = c;
    }
    return tally;
  }, [filtered, shownMetrics, bestByKey]);

  const topWinCount = useMemo(() => Math.max(0, ...Object.values(winCounts)), [winCounts]);

  const books = useMemo(() => {
    const m = METRICS.find((x) => x.key === sortKey);
    const dir = sortDir;
    return [...filtered].sort((a, b) => {
      // "__wins" is not a book field, it is the per-view best-in-column tally.
      if (sortKey === "__wins")
        return dir * ((winCounts[a.name] ?? 0) - (winCounts[b.name] ?? 0));
      const x = a[sortKey] as never as number | null;
      const y = b[sortKey] as never as number | null;
      if (x === null || x === undefined) return 1;
      if (y === null || y === undefined) return -1;
      const lo = m?.lowerBetter ? dir : -dir;
      return typeof x === "number" && typeof y === "number" ? lo * (x - y) : 0;
    });
  }, [filtered, sortKey, sortDir, winCounts]);
  const chartBooks = useMemo(
    () => books.filter((b) => selected.includes(b.name)),
    [books, selected]
  );

  if (err) {
    return (
      <div className="rounded-lg border border-[#3a1a1c] bg-[#2d1618] p-4 text-sm text-[#f85149]">
        <p className="font-semibold">Could not load results.</p>
        <p className="mt-1 text-[#8b949e]">{err}</p>
        <p className="mt-2 text-[#8b949e]">
          Regenerate the artifact with:{" "}
          <code className="text-[#6366f1]">python backtest/tests/exp_results_export.py</code>
        </p>
      </div>
    );
  }

  if (!data) {
    return <p className="text-sm text-[#8b949e]">{busy ? "Loading…" : ""}</p>;
  }

  const toggle = (name: string) =>
    setSelected((s) => (s.includes(name) ? s.filter((x) => x !== name) : [...s, name].slice(-8)));

  const onSort = (k: keyof ResultBook | "__wins") => {
    if (k === sortKey) setSortDir((d) => (d === 1 ? -1 : 1));
    else {
      setSortKey(k);
      setSortDir(-1);
    }
  };

  return (
    <div className="space-y-5">
      {/* header */}
      <div>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-xl font-semibold text-[#e6edf3]">Results — book comparison</h1>
          <button
            onClick={() => load(true)}
            className="rounded-md border border-[#30363d] px-3 py-1.5 text-sm text-[#e6edf3] hover:bg-[#21262d]"
          >
            {busy ? "Refreshing…" : "Refresh artifact"}
          </button>
        </div>
        <p className="mt-1 max-w-4xl text-sm text-[#8b949e]">
          {data.count} books, both eras on one curve. Metrics come from a committed artifact so
          these numbers are the same ones the research docs quote — regenerate with{" "}
          <code className="text-[#6366f1]">python backtest/tests/exp_results_export.py</code>.
          Built on <code className="text-[#6366f1]">docs/learn/finding optimal book.md</code>: net R
          is shown but is deliberately not the ranking metric.
        </p>
      </div>

      {/* filters */}
      <div className="flex flex-wrap items-center gap-2">
        {(["all", "multi", "sig"] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFamily(f)}
            className={`rounded-md px-3 py-1 text-sm ${
              family === f
                ? "bg-[#21262d] text-[#e6edf3]"
                : "text-[#8b949e] hover:text-[#e6edf3]"
            }`}
          >
            {f === "all" ? `All (${data.count})` : f === "multi" ? "Multi position" : "Sig"}
          </button>
        ))}
        <span className="ml-2 text-xs text-[#6e7681]">
          &ldquo;many at once&rdquo; = several trades can be open together · &ldquo;1 at a
          time&rdquo; = the next one waits for the last to close
        </span>
      </div>

      {/* book picker */}
      <div className="flex flex-wrap gap-1.5">
        {books.map((b) => {
          const on = selected.includes(b.name);
          const isShip = b.name === SHIPPING;
          return (
            <button
              key={b.name}
              onClick={() => toggle(b.name)}
              title={b.desc?.slice(0, 200)}
              className={`rounded-md border px-2 py-1 text-xs transition-colors ${
                on
                  ? "border-[#6366f1] bg-[#1b2330] text-[#e6edf3]"
                  : "border-[#30363d] text-[#8b949e] hover:text-[#e6edf3]"
              }`}
            >
              {short(b.name)}
              {isShip && <span className="ml-1 text-[#6366f1]">●</span>}
              {b.family === "sig" && <span className="ml-1 text-[#6e7681]">sig</span>}
            </button>
          );
        })}
      </div>

      {/* tags legend */}
      <div className="flex flex-wrap items-center gap-1.5 text-xs">
        <span className="text-[#6e7681]">tags:</span>
        {Object.entries(TAG_META).map(([k, m]) => (
          <span
            key={k}
            title={m.hint}
            className={`rounded px-1.5 py-0.5 ${
              m.tone === "bad"
                ? "bg-[#3a1a1c] text-[#f85149]"
                : "bg-[#12351c] text-[#3fb950]"
            } ${m.tone === "bad" ? "" : "opacity-70"}`}
          >
            {m.label}
          </span>
        ))}
      </div>

      {/* tags legend */}
      <div className="flex flex-wrap items-center gap-1.5 text-xs">
        <span
          title="Paired permutation against the shipping book, below p = 0.05 in at least one era."
          className="rounded bg-[#12351c] px-1.5 py-0.5 font-semibold text-[#3fb950]"
        >
          ✓ beats parent
        </span>
        <span
          title="Not significant in either era. The book may still be good - the change to it is what failed the test."
          className="rounded bg-[#21262d] px-1.5 py-0.5 text-[#6e7681]"
        >
          — no difference from parent
        </span>
        <span className="text-[#6e7681]">
          (p is a chance measure, not a quality score — low is meaningful, high is
          not damning)
        </span>
      </div>

      {/* group tabs */}
      <div className="flex flex-wrap gap-1 border-b border-[#21262d]">
        {GROUPS.map((g) => (
          <button
            key={g}
            onClick={() => setGroup(g)}
            className={`-mb-px border-b-2 px-3 py-1.5 text-sm ${
              group === g
                ? "border-[#6366f1] text-[#e6edf3]"
                : "border-transparent text-[#8b949e] hover:text-[#e6edf3]"
            }`}
          >
            {g}
          </button>
        ))}
      </div>

      {/* table */}
      <div className="overflow-x-auto rounded-lg border border-[#21262d]">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-[#161b22]">
              <th className="sticky left-0 bg-[#161b22] px-3 py-2 text-left text-xs font-semibold text-[#8b949e]">
                book
              </th>
              {/* Trades is always visible, whatever group is open. It is the one
                  number that changes how every other number should be read: 25
                  trades and 900 trades producing the same net are not equivalent
                  evidence, and hiding it behind a tab buries that. */}
              <th className="px-3 py-2 text-right">
                <button
                  onClick={() => onSort("n")}
                  title="Trade count. 25 trades and 900 trades making the same net are not equivalent evidence."
                  className={`text-xs font-semibold ${
                    sortKey === "n" ? "text-[#6366f1]" : "text-[#8b949e] hover:text-[#e6edf3]"
                  }`}
                >
                  Trades
                  {sortKey === "n" ? (sortDir === 1 ? " ↑" : " ↓") : ""}
                </button>
              </th>
              {shownMetrics.map((m) => (
                <th key={String(m.key)} className="px-3 py-2 text-right">
                  <button
                    onClick={() => onSort(m.key)}
                    title={m.hint}
                    className={`text-xs font-semibold ${
                      sortKey === m.key ? "text-[#6366f1]" : "text-[#8b949e] hover:text-[#e6edf3]"
                    }`}
                  >
                    {m.label}
                    {sortKey === m.key
                      ? sortDir === 1
                        ? " ↑"
                        : " ↓"
                      : m.lowerBetter
                        ? " ↓"
                        : ""}
                  </button>
                </th>
              ))}
              <th className="px-3 py-2 text-right">
                <button
                  onClick={() => onSort("__wins")}
                  title={"How many of the metrics open right now this book has the best value on. Only counts what is on screen, so switching the group changes the answer on purpose."}
                  className={`text-xs font-semibold ${
                    sortKey === "__wins"
                      ? "text-[#6366f1]"
                      : "text-[#8b949e] hover:text-[#e6edf3]"
                  }`}
                >
                   best on
                  {sortKey === "__wins" ? (sortDir === 1 ? " ↑" : " ↓") : ""}
                </button>
              </th>
              <th className="px-3 py-2 text-right text-xs font-semibold text-[#8b949e]">
                    sig
                  </th>
<th className="px-3 py-2 text-right text-xs font-semibold text-[#8b949e]">tags</th>
            </tr>
          </thead>
          <tbody>
            {books.map((b) => {
              const on = selected.includes(b.name);
              return (
                <tr
                  key={b.name}
                  className={`border-t border-[#21262d] ${
                    on ? "bg-[#161b22]" : "bg-[#0d1117]"
                  } ${b.name === SHIPPING ? "border-l-2 border-l-[#6366f1]" : ""}`}
                >
                  <td
                    className={`sticky left-0 cursor-pointer px-3 py-1.5 text-left ${
                      on ? "bg-[#161b22]" : "bg-[#0d1117]"
                    }`}
                    onClick={() => toggle(b.name)}
                  >
                    <span className="text-[#e6edf3]">{short(b.name)}</span>
                    {b.name === SHIPPING && (
                      <span className="ml-1.5 text-[10px] text-[#6366f1]">shipping</span>
                    )}
                    <span
                      className="ml-1.5 text-[10px] text-[#6e7681]"
                      title={
                        b.position_explicit
                          ? b.position_mode === "multi"
                            ? "Can hold several trades open at the same time"
                            : "One trade at a time - the next waits for the last to close"
                          : "The registry does not say - the engine default decides"
                      }
                    >
                      {b.position_mode === "multi"
                        ? "many at once"
                        : b.position_mode === "single"
                          ? "1 at a time"
                          : "not stated"}
                    </span>
                  </td>
                  <td
                    className={`px-3 py-1.5 text-right tabular-nums ${
                      on ? "bg-[#161b22]" : "bg-[#0d1117]"
                    }`}
                  >
                    {b.n}
                  </td>
                  {shownMetrics.map((m) => {
                    const v = b[m.key];
                    const num = typeof v === "number" ? v : null;
                    const isNet = m.key === "net" || m.key === "cost_2x" || m.key === "cost_3x";
                    // Amber flags a value that is legal but worth a look: a tail
                    // concentration in the framework's warning zone, or OOS
                    // retention that has decayed more than a third.
                    const bad =
                      num !== null &&
                      ((isNet && num < 0) ||
                        (m.key === "top5_contrib" && num >= 90) ||
                        (m.key === "retention" && num < 70));
                    const isTop = isBest(m, num, bestByKey[String(m.key)] ?? null);
                    return (
                      <td
                        key={String(m.key)}
                        title={isTop ? `Best ${m.lowerBetter ? "lowest" : "highest"} ${m.label} of the ${books.length} books in view` : undefined}
                        className={`px-3 py-1.5 text-right tabular-nums ${
                          isTop
                            ? "bg-[#1b2330] font-semibold text-[#3fb950]"
                            : isNet && num !== null
                              ? num >= 0
                                ? "text-[#3fb950]"
                                : "text-[#f85149]"
                              : bad
                                ? "text-[#d29922]"
                                : "text-[#e6edf3]"
                        }`}
                      >
                        {isTop && (
                          <span className="mr-0.5 text-[#3fb950]" aria-label="best in column"></span>
                        )}
                        {fmt(m, v)}
                      </td>
                    );
                  })}
                  <td className="px-3 py-1.5 text-right">
                    {b.null_sig ? (
                      <span
                        title={`significant in ${
                          b.null_sig_is && b.null_sig_oos
                            ? "BOTH eras"
                            : b.null_sig_is
                              ? "sample only"
                              : "out of sample only"
                        }`}
                        className="inline-block rounded bg-[#12351c] px-1.5 py-0.5 text-[10px] font-semibold text-[#3fb950]"
                      >
                        SIG</span>
                    ) : (
                      <span className="text-[10px] text-[#6e7681]">--</span>
                    )}
                  </td>
                  <td className="px-3 py-1.5 text-right">
                    <span className="inline-flex flex-wrap justify-end gap-1">
                      {b.tags
                        .filter((tg) => tg !== "2x-cost-death")
                        .slice(0, 3)
                        .map((tg) => (
                          <span
                            key={tg}
                            title={TAG_META[tg]?.hint}
                            className="rounded bg-[#12351c] px-1 py-0.5 text-[10px] text-[#3fb950] opacity-70"
                          >
                            {TAG_META[tg]?.label ?? tg}
                          </span>
                        ))}
                      {b.tags.includes("2x-cost-death") && (
                        <span
                          title={TAG_META["2x-cost-death"].hint}
                          className="rounded bg-[#3a1a1c] px-1 py-0.5 text-[10px] text-[#f85149]"
                        >
                          2x-cost-DEATH
                        </span>
                      )}
                    </span>
                  </td>
                  <td className="px-3 py-1.5 text-right tabular-nums">
                    <span
                      className={`inline-block min-w-[1.6rem] rounded px-1.5 py-0.5 text-xs font-semibold ${
                        winCounts[b.name] > 0
                          ? winCounts[b.name] === topWinCount
                            ? "bg-[#12351c] text-[#3fb950]"
                            : "bg-[#161b22] text-[#8b949e]"
                          : "text-[#6e7681]"
                      }`}
                    >
                      {winCounts[b.name]}/{shownMetrics.length}
                    </span>
                  </td>
                  <td className="px-3 py-1.5 text-right">
                    <span className="inline-flex flex-wrap justify-end gap-1">
                      {b.tags
                        .filter((t) => t !== "2x-cost-death")
                        .slice(0, 3)
                        .map((t) => (
                          <span
                            key={t}
                            title={TAG_META[t]?.hint}
                            className="rounded bg-[#12351c] px-1 py-0.5 text-[10px] text-[#3fb950] opacity-70"
                          >
                            {TAG_META[t]?.label ?? t}
                          </span>
                        ))}
                      {b.tags.includes("2x-cost-death") && (
                        <span
                          title={TAG_META["2x-cost-death"].hint}
                          className="rounded bg-[#3a1a1c] px-1 py-0.5 text-[10px] text-[#f85149]"
                        >
                          2x-cost-DEATH
                        </span>
                      )}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* equity curves */}
      <div className="rounded-lg border border-[#21262d] bg-[#161b22] p-4">
        <h2 className="text-sm font-semibold text-[#e6edf3]">
          Equity curves — selected ({chartBooks.length})
        </h2>
        <p className="mb-3 text-xs text-[#8b949e]">
          Cumulative R per trade, both eras merged in calendar order. A curve that looks like a
          staircase rising is the thing worth wanting.
        </p>
        {chartBooks.length ? (
          <EquityChart books={chartBooks} />
        ) : (
          <p className="text-sm text-[#8b949e]">Pick a book above to chart it.</p>
        )}
      </div>

      {/* period table */}
      <div className="rounded-lg border border-[#21262d] bg-[#161b22] p-4">
        <h2 className="text-sm font-semibold text-[#e6edf3]">
          Half-year cells — the owner&apos;s rule is zero negative
        </h2>
        <p className="mb-3 text-xs text-[#8b949e]">
          2021-22 is reused old data, not a holdout. A clean table is not evidence on its own —
          see the scorecard docs.
        </p>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr>
                <th className="px-2 py-1 text-left text-[#8b949e]">book</th>
                {books[0] && Object.keys(books[0].halfs).map((h) => (
                  <th key={h} className="px-2 py-1 text-right text-[#8b949e]">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {books.map((b) => (
                <tr key={b.name} className="border-t border-[#21262d]">
                  <td className="px-2 py-1 text-[#e6edf3]">{short(b.name)}</td>
                  {Object.keys(b.halfs).map((h) => {
                    const v = b.halfs[h];
                    return (
                      <td
                        key={h}
                        className={`px-2 py-1 text-right tabular-nums ${
                          v < 0 ? "bg-[#2d1618] text-[#f85149]" : "text-[#8b949e]"
                        }`}
                      >
                        {v >= 0 ? "+" : ""}
                        {v.toFixed(1)}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}