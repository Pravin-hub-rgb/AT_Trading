"use client";

import { useMemo, useState } from "react";
import type {
  BacktestParams,
  IntradayBacktestResponse,
  IntradayDaySummary,
  TradeOutcome,
  BiasMode,
} from "@/lib/api";
import { BIAS_MODES } from "@/lib/api";
import { BIAS_PRESETS } from "@/lib/biasPresets";

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
  { value: "swing_end", label: "SL: Swing High/Low" },
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

const RR_MODES = [
  { value: "1", label: "Target: 1:1" },
  { value: "1.5", label: "Target: 1:1.5" },
  { value: "2", label: "Target: 1:2" },
  { value: "2.5", label: "Target: 1:2.5" },
  { value: "3", label: "Target: 1:3 (course)" },
  { value: "4", label: "Target: 1:4" },
];

const MIN_SL_MODES = [
  { value: "0", label: "Min SL: Off" },
  { value: "8", label: "Min SL: 8 pts" },
  { value: "10", label: "Min SL: 10 pts" },
  { value: "13", label: "Min SL: 13 pts (default)" },
  { value: "15", label: "Min SL: 15 pts" },
  { value: "20", label: "Min SL: 20 pts" },
];

const BREAKEVEN_MODES = [
  { value: "0", label: "Breakeven: Off" },
  { value: "1", label: "Breakeven: 1R (1:1)" },
  { value: "1.5", label: "Breakeven: 1.5R" },
  { value: "2", label: "Breakeven: 2R" },
];

const MAX_ENTRIES_MODES = [
  { value: "1", label: "Max Trades: 1" },
  { value: "2", label: "Max Trades: 2 (course)" },
];

const CUTOFF_MODES = [
  { value: "15:15", label: "Cutoff: 15:15 (all day)" },
  { value: "14:00", label: "Cutoff: 14:00" },
  { value: "13:00", label: "Cutoff: 13:00" },
  { value: "12:00", label: "Cutoff: 12:00" },
  { value: "11:30", label: "Cutoff: 11:30" },
];

const SECOND_TRADE_MODES = [
  { value: "sl_only", label: "2nd: Only after SL" },
  { value: "loss", label: "2nd: After loss (SL/FT-Fail/C2C)" },
  { value: "any_non_target", label: "2nd: Any non-target" },
  { value: "always", label: "2nd: Always" },
];

const STORAGE_KEY = "intraday_filters";

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

// Load saved filters from localStorage
function loadSavedFilters(): Partial<{
  caseValue: string;
  sl_mode: string;
  execution: string;
  trailing: string;
  gap_pct: string;
  ft_fail_enabled: boolean;
  entry_method: string;
  rr_target: number;
  swing_traverse: boolean;
  min_sl_pts: number;
  breakeven_r: number;
  need_opp_swing: boolean;
  max_entries: number;
  entry_cutoff: string;
  second_trade_after: string;
}> {
  if (typeof window === "undefined") return {};
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      return JSON.parse(saved);
    }
  } catch (e) {
    console.error("Failed to load saved filters:", e);
  }
  return {};
}

// Save filters to localStorage
function saveFilters(filters: {
  caseValue: string;
  sl_mode: string;
  execution: string;
  trailing: string;
  gap_pct: string;
  ft_fail_enabled: boolean;
  entry_method: string;
  rr_target: number;
  swing_traverse: boolean;
  min_sl_pts: number;
  breakeven_r: number;
  need_opp_swing: boolean;
  max_entries: number;
  entry_cutoff: string;
  second_trade_after: string;
}) {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(filters));
  } catch (e) {
    console.error("Failed to save filters:", e);
  }
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

  // Load saved filters or use defaults from params
  const saved = loadSavedFilters();

  // Local state for ALL filters — applied together when user clicks Apply
  // Initialize from localStorage if available, otherwise from current params
  const [localCase, setLocalCase] = useState(saved.caseValue ?? selectedCase);
  const [localSlMode, setLocalSlMode] = useState(
    saved.sl_mode ?? params.sl_mode,
  );
  const [localExecution, setLocalExecution] = useState(
    saved.execution ?? params.execution,
  );
  const [localTrailing, setLocalTrailing] = useState(
    saved.trailing ?? params.trailing,
  );
  const [localGapPct, setLocalGapPct] = useState(
    saved.gap_pct ?? params.gap_pct,
  );
  const [localFtFail, setLocalFtFail] = useState(
    saved.ft_fail_enabled ?? params.ft_fail_enabled,
  );
  const [localEntryMethod, setLocalEntryMethod] = useState(
    saved.entry_method ?? params.entry_method ?? "pivot_break",
  );
  const [localRR, setLocalRR] = useState(
    String(saved.rr_target ?? params.rr_target ?? 3.0),
  );
  const [localTraverse, setLocalTraverse] = useState(
    saved.swing_traverse ?? params.swing_traverse ?? true,
  );
  const [localMinSl, setLocalMinSl] = useState(
    String(saved.min_sl_pts ?? params.min_sl_pts ?? 13.0),
  );
  const [localBreakeven, setLocalBreakeven] = useState(
    String(saved.breakeven_r ?? (params as any).breakeven_r ?? 1.0),
  );
  const [localNeedOpp, setLocalNeedOpp] = useState(
    saved.need_opp_swing ?? (params as any).need_opp_swing ?? true,
  );
  const [localMaxEntries, setLocalMaxEntries] = useState(
    String(saved.max_entries ?? (params as any).max_entries ?? 2),
  );
  const [localCutoff, setLocalCutoff] = useState(
    saved.entry_cutoff ?? (params as any).entry_cutoff ?? "15:15",
  );
  const [localSecondAfter, setLocalSecondAfter] = useState(
    saved.second_trade_after ?? (params as any).second_trade_after ?? "sl_only",
  );
  const [localBiasMode, setLocalBiasMode] = useState<BiasMode>(
    (saved as any).bias_mode ?? (params as any).bias_mode ?? "daily_swing",
  );

  // Check if any local value differs from the current applied params
  const hasChanges =
    localCase !== selectedCase ||
    localSlMode !== params.sl_mode ||
    localExecution !== params.execution ||
    localTrailing !== params.trailing ||
    localGapPct !== params.gap_pct ||
    localFtFail !== params.ft_fail_enabled ||
    localEntryMethod !== (params.entry_method ?? "pivot_break") ||
    localRR !== String(params.rr_target ?? 3.0) ||
    localTraverse !== (params.swing_traverse ?? true) ||
    localMinSl !== String(params.min_sl_pts ?? 13.0) ||
    localBreakeven !== String((params as any).breakeven_r ?? 1.0) ||
    localNeedOpp !== ((params as any).need_opp_swing ?? true) ||
    localMaxEntries !== String((params as any).max_entries ?? 2) ||
    localCutoff !== ((params as any).entry_cutoff ?? "15:15") ||
    localSecondAfter !== ((params as any).second_trade_after ?? "sl_only") ||
    localBiasMode !== ((params as any).bias_mode ?? "daily_swing");

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

  const handleApply = () => {
    // Save to localStorage first
    saveFilters({
      caseValue: localCase,
      sl_mode: localSlMode,
      execution: localExecution,
      trailing: localTrailing,
      gap_pct: localGapPct,
      ft_fail_enabled: localFtFail,
      entry_method: localEntryMethod,
      rr_target: Number(localRR),
      swing_traverse: localTraverse,
      min_sl_pts: Number(localMinSl),
      breakeven_r: Number(localBreakeven),
      need_opp_swing: localNeedOpp,
      max_entries: Number(localMaxEntries),
      entry_cutoff: localCutoff,
      second_trade_after: localSecondAfter,
      bias_mode: localBiasMode,
    } as any);
    // Apply all filters in one go
    onCaseChange(localCase);
    onParamsChange({
      ...params,
      sl_mode: localSlMode,
      execution: localExecution,
      trailing: localTrailing,
      gap_pct: localGapPct,
      ft_fail_enabled: localFtFail,
      entry_method: localEntryMethod,
      rr_target: Number(localRR),
      swing_traverse: localTraverse,
      min_sl_pts: Number(localMinSl),
      breakeven_r: Number(localBreakeven),
      need_opp_swing: localNeedOpp,
      max_entries: Number(localMaxEntries),
      entry_cutoff: localCutoff,
      second_trade_after: localSecondAfter,
      bias_mode: localBiasMode,
    } as any);
  };

  return (
    <div className="space-y-3">
      {/* MASTER BIAS — clean separation: daily_swing vs ema based etc */}
      <div className="flex flex-wrap items-center gap-2 rounded-md border border-[#6366f1]/50 bg-[#6366f1]/10 px-3 py-2">
        <span className="text-xs font-bold uppercase tracking-wide text-[#6366f1]">
          Master Bias
        </span>
        <select
          value={localBiasMode}
          onChange={(e) => {
            const v = e.target.value as BiasMode;
            setLocalBiasMode(v);
            const preset = (BIAS_PRESETS as any)[v];
            if (preset) {
              if (preset.sl_mode) setLocalSlMode(preset.sl_mode);
              if (preset.rr_target !== undefined) setLocalRR(String(preset.rr_target));
              if (preset.min_sl_pts !== undefined) setLocalMinSl(String(preset.min_sl_pts));
              if (preset.breakeven_r !== undefined) setLocalBreakeven(String(preset.breakeven_r));
              if (preset.gap_pct !== undefined) setLocalGapPct(String(preset.gap_pct));
              if (preset.ft_fail_enabled !== undefined) setLocalFtFail(preset.ft_fail_enabled);
              if (preset.max_entries !== undefined) setLocalMaxEntries(String(preset.max_entries));
              if (preset.entry_cutoff !== undefined) setLocalCutoff(String(preset.entry_cutoff));
              if (preset.second_trade_after !== undefined) setLocalSecondAfter(String(preset.second_trade_after));
              if (preset.swing_traverse !== undefined) setLocalTraverse(preset.swing_traverse);
              if (preset.need_opp_swing !== undefined) setLocalNeedOpp(preset.need_opp_swing);
            }
            // Immediate apply — so MASTER change instantly updates chart + trades, no extra Apply click needed
            const next = { ...params, ...(preset || {}), bias_mode: v } as any;
            // keep case
            onCaseChange(localCase);
            onParamsChange(next);
            try {
              window.localStorage.setItem(
                "intraday_filters",
                JSON.stringify({ ...JSON.parse(window.localStorage.getItem("intraday_filters") || "{}"), ...(preset || {}), bias_mode: v, caseValue: localCase }),
              );
              if (v.startsWith("ema")) window.localStorage.setItem("chart_ema_on", "1");
            } catch {}
          }}
          className="rounded border border-[#6366f1] bg-[#161b22] px-2 py-1.5 text-xs font-semibold text-[#e6edf3] outline-none focus:border-[#6366f1]"
          title="Master bias mode — daily_swing is original (bias.py), ema_* are pure EMA, opposite/streak are research modes. Clean separation, not messed. Auto-applies its best preset instantly."
        >
          {BIAS_MODES.map((m) => (
            <option key={m.value} value={m.value}>
              {m.label}
            </option>
          ))}
        </select>
        <span className="text-[10px] text-[#8b949e]">
          {localBiasMode === "daily_swing"
            ? "Original daily swing + closing (bias.py)"
            : localBiasMode.startsWith("ema")
              ? "Pure EMA trend — no overview/flow"
              : localBiasMode === "opposite_first"
                ? "Opposite of 1st swing — ignores bias.py"
                : "Streak 3-1-1 daily color regime"}
        </span>
      </div>
      {/* All filters in one row — applied together with the Apply button */}
      <div className="flex flex-wrap items-center gap-2 rounded-md border border-[#30363d] bg-[#0d1117] px-3 py-2">
        <span className="text-xs font-semibold uppercase tracking-wide text-[#8b949e]">
          Experiment
        </span>
        <select
          value={localCase}
          onChange={(e) => setLocalCase(e.target.value)}
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
          value={localSlMode}
          onChange={(e) => setLocalSlMode(e.target.value)}
          className={selectCls}
        >
          {SL_MODES.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
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
          value={localRR}
          onChange={(e) => setLocalRR(e.target.value)}
          className={selectCls}
          title="Fixed target in R (only used when trailing is off)"
        >
          {RR_MODES.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <select
          value={localTrailing}
          onChange={(e) => setLocalTrailing(e.target.value)}
          className={selectCls}
        >
          {TRAILING_MODES.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <select
          value={localGapPct}
          onChange={(e) => setLocalGapPct(e.target.value)}
          className={selectCls}
          title="Minimum |open - prev close| for a move to count as a gap (case classification)"
        >
          {GAP_MODES.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <select
          value={localMinSl}
          onChange={(e) => setLocalMinSl(e.target.value)}
          className={selectCls}
          title="Widen the SL to at least this many points (target recomputes from the widened risk)"
        >
          {MIN_SL_MODES.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <select
          value={localBreakeven}
          onChange={(e) => setLocalBreakeven(e.target.value)}
          className={selectCls}
          title="Breakeven exit: when MFE >= this R and price returns to entry, close at entry. Only when < Target and Target>=1:3 (1:2 target with 2R breakeven is disabled)"
        >
          {BREAKEVEN_MODES.map((o) => (
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
            checked={localFtFail}
            onChange={(e) => setLocalFtFail(e.target.checked)}
            className="accent-[#f59e0b]"
          />
          FT-fail early exit
        </label>
        <label
          className="flex items-center gap-1.5 rounded-md border border-[#30363d] bg-[#0d1117] px-2 py-1.5 text-xs text-[#c9d1d9] cursor-pointer hover:border-[#58a6ff]"
          title="When ON, the reference swing follows extensions (price beyond swing end re-arms to the next swing, 3rd/4th/... nth). When OFF, the reference freezes at the first desired swing (old doc behaviour)."
        >
          <input
            type="checkbox"
            checked={localTraverse}
            onChange={(e) => setLocalTraverse(e.target.checked)}
            className="accent-[#f59e0b]"
          />
          Swing traverse
        </label>
        <label
          className="flex items-center gap-1.5 rounded-md border border-[#30363d] bg-[#0d1117] px-2 py-1.5 text-xs text-[#c9d1d9] cursor-pointer hover:border-[#58a6ff]"
          title="When ON (default), 1min precise waits for opposite swing: buy only after selling FS (FS2), sell only after buying FS. Covers B7/Bc7 extremes. OFF keeps legacy aggressive B7/Bc7 on 1st break. 5min ignores."
        >
          <input
            type="checkbox"
            checked={localNeedOpp}
            onChange={(e) => setLocalNeedOpp(e.target.checked)}
            className="accent-[#6366f1]"
            disabled={localExecution !== "1min"}
          />
          Need opposite swing
        </label>
        <select
          value={localMaxEntries}
          onChange={(e) => setLocalMaxEntries(e.target.value)}
          className={selectCls}
          title="Max trades per day (1 = one-and-done regardless, 2 = allow 2nd per rule)"
        >
          {MAX_ENTRIES_MODES.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <select
          value={localSecondAfter}
          onChange={(e) => setLocalSecondAfter(e.target.value)}
          className={selectCls}
          title="When max=2, when is 2nd allowed? sl_only (default), loss (SL/FT-Fail/C2C), any_non_target, always"
          disabled={localMaxEntries === "1"}
        >
          {SECOND_TRADE_MODES.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <select
          value={localCutoff}
          onChange={(e) => setLocalCutoff(e.target.value)}
          className={selectCls}
          title="No new entries at or after this time (open trade still to SL/target/EOD)"
        >
          {CUTOFF_MODES.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <button
          onClick={handleApply}
          disabled={!hasChanges}
          className={`ml-auto px-3 py-1 rounded border text-xs font-semibold transition-colors ${
            hasChanges
              ? "border-[#6366f1] bg-[#6366f1] text-white hover:bg-[#4f46e5] cursor-pointer"
              : "border-[#30363d] bg-[#21262d] text-[#6e7681] cursor-not-allowed"
          }`}
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
                {d.trade_mode === "aggressive"
                  ? "⚡"
                  : d.trade_mode === "conservative"
                    ? "🐢"
                    : ""}
                {d.case ?? ""} ·{" "}
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
