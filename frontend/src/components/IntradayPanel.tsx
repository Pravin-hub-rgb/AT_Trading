"use client";

import { useMemo, useState } from "react";
import type {
  BacktestParams,
  IntradayBacktestResponse,
  IntradayDaySummary,
  TradeOutcome,
} from "@/lib/api";

interface Props {
  backtest: IntradayBacktestResponse | null;
  loading: boolean;
  error: string | null;
  params: BacktestParams;
  onParamsChange: (p: BacktestParams) => void;
  selectedCase: string; // "all" | "B1" | ...
  onCaseChange: (c: string) => void;
}

const OUTCOME_STYLE: Record<string, { color: string; label: string }> = {
  target: { color: "#10b981", label: "TARGET" },
  trail: { color: "#a78bfa", label: "TRAIL" },
  eod: { color: "#3b82f6", label: "EOD" },
  "cost-to-cost": { color: "#8b949e", label: "C2C" },
  ft_fail: { color: "#f97316", label: "FT-FAIL" },
  no_momentum: { color: "#f59e0b", label: "NO-MOM" },
  sl: { color: "#ef4444", label: "SL" },
};

const SL_MODES = [
  { value: "avg", label: "SL: Avg ×1.0 (course)" },
  { value: "avg075", label: "SL: Avg ×0.75" },
  { value: "avg05", label: "SL: Avg ×0.5" },
  { value: "fixed8", label: "SL: Fixed 8 pt" },
  { value: "prev_pivot", label: "SL: Pivot / ECL ± 1pt" },
];

const EXECUTION_MODES = [
  { value: "5min", label: "Exec: Conservative 5-Min" },
  { value: "1min", label: "Exec: Precise 1-Min" },
];

const TRAILING_MODES = [
  { value: "off", label: "Trail: Off (course)" },
  { value: "ladder", label: "Trail: Ladder (R-steps)" },
];

const GAP_MODES = [
  { value: "0.27", label: "Gap ≥ 0.27% (researched)" },
  { value: "0.15", label: "Gap ≥ 0.15% (old)" },
  { value: "0.20", label: "Gap ≥ 0.20%" },
  { value: "0.35", label: "Gap ≥ 0.35%" },
];

const ENTRY_METHODS = [
  { value: "pace_break", label: "Entry: Pace Break (course)" },
  { value: "pivot_break", label: "Entry: Pivot Break" },
];

const SWING_MODES = [
  { value: "none", label: "Swing: No Gate (1min)" },
  { value: "opposite_swing_needed", label: "Swing: Opposite Required (1min)" },
];

function OutcomeChip({ outcome }: { outcome: string }) {
  const s = OUTCOME_STYLE[outcome] ?? {
    color: "#8b949e",
    label: outcome.toUpperCase(),
  };
  return (
    <span
      className="rounded px-1.5 py-0.5 font-mono text-[10px] font-bold"
      style={{
        color: s.color,
        border: `1px solid ${s.color}55`,
        background: `${s.color}14`,
      }}
    >
      {s.label}
    </span>
  );
}

export default function IntradayPanel({
  backtest,
  loading,
  error,
  params,
  onParamsChange,
  selectedCase,
  onCaseChange,
}: Props) {
  const tradedDays = useMemo(
    () => (backtest?.days ?? []).filter((d) => d.n_trades > 0),
    [backtest],
  );

  // client-side case filtering: stats + days + trades all respect the dropdown
  const view = useMemo(() => {
    if (!backtest) return null;
    if (selectedCase === "all") {
      return { stats: backtest.stats, days: tradedDays };
    }
    const days = tradedDays.filter((d) => d.case === selectedCase);
    const allT = days.flatMap((d) => d.trades);
    const wins = allT.filter((t) => (t.r_multiple ?? 0) > 0).length;
    const totalR = allT.reduce((a, t) => a + (t.r_multiple ?? 0), 0);
    const outcomes: Record<string, number> = {};
    allT.forEach((t) => {
      const o = t.outcome ?? "eod";
      outcomes[o] = (outcomes[o] ?? 0) + 1;
    });
    const stats = {
      ...backtest.stats,
      days_traded: days.length,
      trades: allT.length,
      wins,
      win_rate: allT.length ? Math.round((wins / allT.length) * 1000) / 10 : 0,
      total_r: Math.round(totalR * 100) / 100,
      avg_r: allT.length ? Math.round((totalR / allT.length) * 100) / 100 : 0,
      outcomes,
      longs: allT.filter((t) => t.dir === "long").length,
      shorts: allT.filter((t) => t.dir === "short").length,
    };
    return { stats, days };
  }, [backtest, tradedDays, selectedCase]);

  const caseOptions = useMemo(() => {
    const fromStats = Object.keys(backtest?.stats.cases ?? {});
    if (fromStats.length) return fromStats;
    // fallback: derive from per-trade case tags if stats.cases absent
    const s = new Set<string>();
    (backtest?.days ?? []).forEach((d) =>
      d.trades.forEach((t) => {
        if (t.case) s.add(t.case);
      }),
    );
    return Array.from(s).sort();
  }, [backtest]);

  const [selectedDate, setSelectedDate] = useState<string | null>(null);

  // Local state for the three key filters that will be applied together
  const [localExecution, setLocalExecution] = useState(params.execution);
  const [localEntryMethod, setLocalEntryMethod] = useState(
    params.entry_method ?? "pace_break",
  );
  const [localSwingMode, setLocalSwingMode] = useState(
    params.swing_mode ?? "opposite_swing_needed",
  );

  const activeDate =
    selectedDate ?? view?.days[view.days.length - 1]?.date ?? null;
  const activeDay: IntradayDaySummary | null =
    view?.days.find((d) => d.date === activeDate) ?? null;

  if (loading) {
    return (
      <div className="rounded-md border border-[#30363d] bg-[#0d1117] px-4 py-3 text-sm text-[#8b949e]">
        Running intraday backtest...
      </div>
    );
  }
  if (error) {
    return (
      <div className="rounded-md border border-[#ef4444]/50 bg-[#ef4444]/10 px-4 py-3 text-sm text-[#ef4444]">
        {error}
      </div>
    );
  }
  if (!backtest) return null;

  const s = view?.stats ?? backtest.stats;
  const viewDays = view?.days ?? [];

  const selectCls =
    "rounded border border-[#30363d] bg-[#161b22] px-2 py-1 text-xs text-[#e6edf3] outline-none focus:border-[#6366f1]";

  return (
    <div className="space-y-3">
      {/* Experiment switches — best-combo search */}
      <div className="flex flex-wrap items-center gap-2 rounded-md border border-[#30363d] bg-[#0d1117] px-3 py-2">
        <span className="text-xs font-semibold uppercase tracking-wide text-[#8b949e]">
          Experiment
        </span>
        <select
          value={selectedCase}
          onChange={(e) => onCaseChange(e.target.value)}
          className={selectCls}
          title="Filter stats, table and chart boxes by case (master list in explained doc)"
        >
          <option value="all">Case: All</option>
          {caseOptions.map((c) => {
            const cs = backtest.stats.cases?.[c];
            return (
              <option key={c} value={c}>
                Case: {c}
                {cs
                  ? ` (${cs.trades}T ${cs.total_r >= 0 ? "+" : ""}${cs.total_r}R)`
                  : ""}
              </option>
            );
          })}
        </select>
        <select
          value={params.sl_mode}
          onChange={(e) =>
            onParamsChange({ ...params, sl_mode: e.target.value })
          }
          className={selectCls}
        >
          {SL_MODES.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <select
          value={params.trailing}
          onChange={(e) =>
            onParamsChange({ ...params, trailing: e.target.value })
          }
          className={selectCls}
        >
          {TRAILING_MODES.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <select
          value={params.gap_pct}
          onChange={(e) =>
            onParamsChange({ ...params, gap_pct: e.target.value })
          }
          className={selectCls}
          title="Minimum |open - prev close| for a move to count as a gap (case classification)"
        >
          {GAP_MODES.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <label
          className="flex items-center gap-1.5 rounded-md border border-[#30363d] bg-[#0d1117] px-2 py-1.5 text-xs text-[#c9d1d9] cursor-pointer hover:border-[#58a6ff]"
          title="Early exit when close goes beyond dom_level within 2 bars of entry (S5:98 follow-through rule). When OFF, trades run until SL/target/EOD."
        >
          <input
            type="checkbox"
            checked={params.ft_fail_enabled}
            onChange={(e) =>
              onParamsChange({ ...params, ft_fail_enabled: e.target.checked })
            }
            className="accent-[#f59e0b]"
          />
          FT-fail early exit
        </label>
      </div>

      {/* Apply button section for the three key filters */}
      <div className="flex flex-wrap items-center gap-2 rounded-md border border-[#30363d] bg-[#0d1117] px-3 py-2">
        <span className="text-xs font-semibold uppercase tracking-wide text-[#8b949e]">
          Core Settings
        </span>
        <select
          value={localExecution}
          onChange={(e) => setLocalExecution(e.target.value)}
          className={selectCls}
        >
          {EXECUTION_MODES.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <select
          value={localEntryMethod}
          onChange={(e) => setLocalEntryMethod(e.target.value)}
          className={selectCls}
        >
          {ENTRY_METHODS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <select
          value={localSwingMode}
          onChange={(e) => setLocalSwingMode(e.target.value)}
          className={selectCls}
        >
          {SWING_MODES.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <button
          onClick={() => {
            onParamsChange({
              ...params,
              execution: localExecution,
              entry_method: localEntryMethod,
              swing_mode: localSwingMode,
            });
          }}
          className="ml-2 px-3 py-1 rounded border border-[#6366f1] bg-[#6366f1]/20 text-xs font-semibold hover:bg-[#6366f1]/30"
        >
          Apply
        </button>
      </div>

      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-8">
        <Stat label="Trades" value={String(s.trades)} />
        <Stat
          label="Win rate"
          value={`${s.win_rate}%`}
          accent={s.win_rate >= 25 ? "#10b981" : "#ef4444"}
        />
        <Stat
          label="Total R"
          value={`${s.total_r >= 0 ? "+" : ""}${s.total_r}`}
          accent={s.total_r >= 0 ? "#10b981" : "#ef4444"}
        />
        <Stat
          label="Avg R"
          value={`${s.avg_r >= 0 ? "+" : ""}${s.avg_r}`}
          accent={s.avg_r >= 0 ? "#10b981" : "#ef4444"}
        />
        <Stat label="Days" value={`${s.days_traded}/${s.days_total}`} />
        <Stat label="Long / Short" value={`${s.longs}/${s.shorts}`} />
        {Object.entries(s.outcomes)
          .sort((a, b) => b[1] - a[1])
          .slice(0, 2)
          .map(([k, v]) => (
            <Stat
              key={k}
              label={OUTCOME_STYLE[k]?.label ?? k}
              value={String(v)}
            />
          ))}
      </div>

      <div className="rounded-md border border-[#30363d] bg-[#0d1117]">
        <div className="flex flex-wrap items-center gap-2 border-b border-[#30363d] px-3 py-2">
          <span className="text-xs font-semibold uppercase tracking-wide text-[#8b949e]">
            Trades
          </span>
          <select
            value={activeDate ?? ""}
            onChange={(e) => setSelectedDate(e.target.value || null)}
            className="rounded border border-[#30363d] bg-[#161b22] px-2 py-1 text-xs text-[#e6edf3]"
          >
            {viewDays.map((d) => (
              <option key={d.date} value={d.date}>
                {d.date} ·{" "}
                {d.bias === "bullish" ? "▲" : d.bias === "bearish" ? "▼" : "●"}{" "}
                · {d.n_trades}T ·{" "}
                {d.outcomes.map((o) => OUTCOME_STYLE[o]?.label ?? o).join(",")}
              </option>
            ))}
          </select>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left font-mono text-xs">
            <thead>
              <tr className="text-[10px] uppercase tracking-wider text-[#6e7681]">
                <th className="px-3 py-1.5">#</th>
                <th className="px-3 py-1.5">Dir</th>
                <th className="px-3 py-1.5">Entry</th>
                <th className="px-3 py-1.5">SL</th>
                <th className="px-3 py-1.5">Target</th>
                <th className="px-3 py-1.5">Exit</th>
                <th className="px-3 py-1.5">R</th>
                <th className="px-3 py-1.5">Break</th>
                <th className="px-3 py-1.5">Outcome</th>
              </tr>
            </thead>
            <tbody>
              {(activeDay?.trades ?? []).map((t, idx) => {
                const r = t.r_multiple ?? 0;
                return (
                  <tr
                    key={idx}
                    className="border-t border-[#21262d] text-[#c9d1d9]"
                  >
                    <td className="px-3 py-1.5 text-[#6e7681]">{idx + 1}</td>
                    <td
                      className={`px-3 py-1.5 font-bold ${t.dir === "long" ? "text-[#10b981]" : "text-[#ef4444]"}`}
                    >
                      {t.dir.toUpperCase()}
                    </td>
                    <td className="px-3 py-1.5">
                      {t.entry_time} @{t.entry_price}
                    </td>
                    <td className="px-3 py-1.5 text-[#ef4444]/80">{t.sl}</td>
                    <td className="px-3 py-1.5 text-[#10b981]/80">
                      {t.target}
                    </td>
                    <td className="px-3 py-1.5">
                      {t.exit_time ?? "-"} @{t.exit_price ?? "-"}
                    </td>
                    <td
                      className={`px-3 py-1.5 font-bold ${r > 0 ? "text-[#10b981]" : r < 0 ? "text-[#ef4444]" : "text-[#8b949e]"}`}
                    >
                      {r >= 0 ? "+" : ""}
                      {r.toFixed(2)}
                    </td>
                    <td className="px-3 py-1.5 text-[10px] text-[#8b949e]">
                      {t.pace_break_type}
                    </td>
                    <td className="px-3 py-1.5">
                      <OutcomeChip outcome={t.outcome as TradeOutcome} />
                    </td>
                  </tr>
                );
              })}
              {!activeDay && (
                <tr>
                  <td
                    colSpan={9}
                    className="px-3 py-3 text-center text-[#8b949e]"
                  >
                    No trades recorded.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent?: string;
}) {
  return (
    <div className="rounded-md border border-[#30363d] bg-[#0d1117] px-3 py-2">
      <div className="text-[10px] uppercase tracking-wider text-[#6e7681]">
        {label}
      </div>
      <div
        className="font-mono text-base font-semibold"
        style={{ color: accent ?? "#e6edf3" }}
      >
        {value}
      </div>
    </div>
  );
}
