"use client";

// BTC/USDT swing chart — continuous 24/7 walker on 1m/5m/15m CSV data.
// Reuses StockChart + WholeDaySwingPrimitive (untouched); zero Nifty logic.

import { useCallback, useEffect, useMemo, useState } from "react";
import StockChart from "@/components/StockChart";
import type { WholeDaySwingPoint } from "@/components/WholeDaySwingPrimitive";
import type { TradeBox } from "@/components/PositionPrimitive";
import type { FlowSegment } from "@/lib/flowline";
import {
  BTC_TFS,
  getBtcBacktest,
  getBtcChart,
  getBtcStatus,
  getBtcSummary,
  getBtcVersions,
  type BtcBacktestParams,
  type BtcBacktestResponse,
  type BtcChartResponse,
  type BtcMode,
  type BtcStatusResponse,
  type BtcSummaryResponse,
  type BtcTf,
  type BtcVersion,
} from "@/lib/btcApi";
import { BTC_MASTER_DEFAULT, BTC_MASTER_MODES } from "@/lib/btcMaster";

const TF_KEY = "btc_chart_tf";
const MODE_KEY = "btc_chart_mode";
const LIMIT_KEY = "btc_chart_limit";
const BT_KEY = "btc_bt_params";
const MASTER_KEY = "btc_master_mode";
const VER_KEY = "btc_version";
const HTF_KEY = "btc_htf_ltf";
const HTF_VER_KEY = "btc_htf_ltf_ver";

const BT_DEFAULTS: BtcBacktestParams = {
  entryBreak: "decisive",
  slMode: "swing",
  slPct: 0.5,
  rrTarget: 3,
  trailing: "off",
  trailDistanceR: 1,
  breakevenR: 1,
  bias: "off",
  minBars: 14,
  regime: "off",
  feePct: 0.05,
  slippagePts: 2,
};

const LIMITS: { label: string; value: number | null }[] = [
  { label: "500", value: 500 },
  { label: "1,000", value: 1000 },
  { label: "2,000", value: 2000 },
  { label: "5,000", value: 5000 },
  { label: "All", value: null },
];

/** epoch ts (wall-as-UTC) -> "MM-DD HH:MM" for the trade table. */
function fmtTs(ts: number): string {
  const d = new Date((ts + 19800) * 1000);
  const p = (n: number) => String(n).padStart(2, "0");
  return `${p(d.getUTCMonth() + 1)}-${p(d.getUTCDate())} ${p(d.getUTCHours())}:${p(d.getUTCMinutes())}`;
}

// Outcome chip colors — mirrors IntradayPanel's OUTCOME_STYLE (btc outcomes)
const OUTCOME_STYLE: Record<string, { color: string; label: string }> = {
  target: { color: "#10b981", label: "TARGET" },
  trail: { color: "#a78bfa", label: "TRAIL" },
  open: { color: "#3b82f6", label: "OPEN" },
  be: { color: "#8b949e", label: "BE" },
  sl: { color: "#ef4444", label: "SL" },
};

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

export default function BtcPage() {
  const [tf, setTf] = useState<BtcTf>("5m");
  const [mode, setMode] = useState<BtcMode>("continuous");
  const [limit, setLimit] = useState<number | null>(2000);
  const [hydrated, setHydrated] = useState(false);
  const [data, setData] = useState<BtcChartResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tradesOn, setTradesOn] = useState(true);
  const [flowOn, setFlowOn] = useState(true);
  const [btParams, setBtParams] = useState<BtcBacktestParams>(BT_DEFAULTS);
  const [btData, setBtData] = useState<BtcBacktestResponse | null>(null);
  const [btError, setBtError] = useState<string | null>(null);
  const [summaryData, setSummaryData] = useState<BtcSummaryResponse | null>(null);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [status, setStatus] = useState<BtcStatusResponse | null>(null);
  const [master, setMaster] = useState<string>(BTC_MASTER_DEFAULT);
  const [showMasterInfo, setShowMasterInfo] = useState(true);
  const [htfLtf, setHtfLtf] = useState<"off" | "5m" | "15m">("off");
  const [htfLtfVer, setHtfLtfVer] = useState<"v1" | "v3" | "v5" | "v6">("v1");
  const [version, setVersion] = useState<BtcVersion>("v1");
  const [versionLabels, setVersionLabels] = useState<Record<string, string>>({
    v1: "v1 Honest (touchable + one-swing-one-trade) — cap 16d for 1h Flip",
    v2: "v2 Chandelier ATR k=3.0",
    v3: "v3 HTF 1h Trail",
    v4: "v4 Partial 50/50",
    v5: "v5 BE1 (breakeven 1R)",
    v6: "v6 ADX>25 — BEST +90.5 net",
    v7: "v7 TimeCap 16d (1h Flip) — BEST +57.8 net",
    v8: "v8 Break High/Low + Opposite Cancel",
    v9: "v9 Conditional Cap 2R→30d",
    v10: "v10 Flip Strength Body/ATR",
  });

  // restore saved prefs (localStorage only on client)
  useEffect(() => {
    const t = window.localStorage.getItem(TF_KEY) as BtcTf | null;
    const m = window.localStorage.getItem(MODE_KEY) as BtcMode | null;
    const l = window.localStorage.getItem(LIMIT_KEY);
    if (t && (BTC_TFS as string[]).includes(t)) setTf(t);
    if (m === "continuous" || m === "daily") setMode(m);
    if (l === "all") setLimit(null);
    else if (l) {
      const n = Number(l);
      if (Number.isFinite(n) && n > 0) setLimit(n);
    }
    const v = window.localStorage.getItem(VER_KEY) as BtcVersion | null;
    if (v && ["v1","v2","v3","v4","v5","v6","v7","v8","v9","v10"].includes(v)) setVersion(v);
    const htf = window.localStorage.getItem(HTF_KEY) as "off" | "5m" | "15m" | null;
    if (htf && ["off","5m","15m"].includes(htf)) setHtfLtf(htf as any);
    const htfVer = window.localStorage.getItem(HTF_VER_KEY) as "v1" | "v3" | "v5" | "v6" | null;
    if (htfVer && ["v1","v3","v5","v6"].includes(htfVer)) setHtfLtfVer(htfVer);
    const mm = window.localStorage.getItem(MASTER_KEY);
    const modeM = mm ? BTC_MASTER_MODES.find((x) => x.value === mm) : undefined;
    // MASTER always wins: the params must match the selected strategy, otherwise
    // the dropdown shows #1 but old bt_params (from another preset) run the
    // backtest. Force the master preset on hydration (saved master, or the
    // DEFAULT if nothing saved) so the two can never desync.
    const masterM = modeM ?? BTC_MASTER_MODES.find((x) => x.value === BTC_MASTER_DEFAULT)!;
    setMaster(masterM.value);
    const next = { ...BT_DEFAULTS, ...masterM.preset } as BtcBacktestParams;
    setBtParams(next);
    window.localStorage.setItem(MASTER_KEY, masterM.value);
    window.localStorage.setItem(BT_KEY, JSON.stringify(next));
    setHydrated(true);
  }, []);

  // versions
  useEffect(() => {
    getBtcVersions().then((r) => setVersionLabels(r.labels)).catch(() => {});
  }, []);

  // full-dataset coverage (kahan se kahan tak data hai) — independent of window
  useEffect(() => {
    if (!hydrated) return;
    let cancelled = false;
    getBtcStatus()
      .then((res) => {
        if (!cancelled) setStatus(res);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [hydrated]);

  // HTF-LTF: the chart swing overlay must show the chain the strategy actually
  // trades on - the 15m LTF book lives on minBars=50, the 5m book on 14, the
  // 1h HTF book on 20. Otherwise B2/FLIP entry marks and FS confirmations on
  // screen come from a chain the engine never uses (chart default was 14).
  const strategyChainMinBars =
    htfLtf !== "off"
      ? tf === "15m"
        ? 50
        : tf === "5m"
          ? 14
          : tf === "1h"
            ? 20
            : btParams.minBars
      : btParams.minBars;

  useEffect(() => {
    if (!hydrated) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    getBtcChart(tf, mode, limit, strategyChainMinBars)
      .then((res) => {
        if (!cancelled) setData(res);
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : String(e));
          setData(null);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [tf, mode, limit, strategyChainMinBars, hydrated]);

  const changeTf = (v: BtcTf) => {
    window.localStorage.setItem(TF_KEY, v);
    setTf(v);
  };

  // ── position engine ──
  const setBt = <K extends keyof BtcBacktestParams>(
    k: K,
    v: BtcBacktestParams[K],
  ) => {
    setBtParams((prev) => {
      const next = { ...prev, [k]: v };
      window.localStorage.setItem(BT_KEY, JSON.stringify(next));
      return next;
    });
  };

  const changeVersion = (v: BtcVersion) => {
    window.localStorage.setItem(VER_KEY, v);
    setVersion(v);
  };
  const changeHtfLtf = (v: "off" | "5m" | "15m") => {
    window.localStorage.setItem(HTF_KEY, v);
    setHtfLtf(v);
  };
  const changeHtfLtfVer = (v: "v1" | "v3" | "v5" | "v6") => {
    window.localStorage.setItem(HTF_VER_KEY, v);
    setHtfLtfVer(v);
  };

  useEffect(() => {
    if (!hydrated || !tradesOn) return;
    let cancelled = false;
    setBtError(null);
    getBtcBacktest(tf, mode, limit, btParams, version, htfLtf, htfLtfVer)
      .then((res) => {
        if (!cancelled) setBtData(res);
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          setBtError(e instanceof Error ? e.message : String(e));
          setBtData(null);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [tradesOn, hydrated, tf, mode, limit, btParams, version, htfLtf, htfLtfVer]);

  // "konsi best hai" — every master preset on the SAME window, ranked by NET R
  useEffect(() => {
    if (!hydrated || !tradesOn) return;
    let cancelled = false;
    setSummaryError(null);
    getBtcSummary(tf, mode, limit, btParams.feePct, btParams.slippagePts, version)
      .then((res) => {
        if (!cancelled) setSummaryData(res);
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          setSummaryError(e instanceof Error ? e.message : String(e));
          setSummaryData(null);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [tradesOn, hydrated, tf, mode, limit, btParams.feePct, btParams.slippagePts, version]);

  const changeMode = (v: BtcMode) => {
    window.localStorage.setItem(MODE_KEY, v);
    setMode(v);
  };

  const changeLimit = (v: number | null) => {
    window.localStorage.setItem(LIMIT_KEY, v === null ? "all" : String(v));
    setLimit(v);
  };

  // ── master presets (fix/btc_ideas.md sweep winners) — instant apply ──
  const applyMaster = (v: string) => {
    const mode = BTC_MASTER_MODES.find((x) => x.value === v);
    if (!mode) return;
    setMaster(v);
    window.localStorage.setItem(MASTER_KEY, v);
    // strategy is measured on its reference TF — switch the chart there too
    changeTf(mode.bestTf);
    // presets are ranked on the FULL window — jump there so the chart trade
    // count matches the summary card / dropdown ref numbers exactly
    changeLimit(null);
    const next = { ...BT_DEFAULTS, ...mode.preset } as BtcBacktestParams;
    setBtParams(next);
    window.localStorage.setItem(BT_KEY, JSON.stringify(next));
    // master exists to show its trades — turn the position engine on
    setTradesOn(true);
  };
// APPEND_MARKER
  // Backend swings -> WholeDaySwingPoint (seg indices == candle array positions).
  // Full chain: FS/SUS kind, B1/B2/FLIP break marks + fs_at structural completion
  // — StockChart draws zigzag lines AND (with swingMarkers) the break markers.
  const swings: WholeDaySwingPoint[] = useMemo(
    () =>
      (data?.swings ?? []).map((s) => ({
        dir: s.seg.dir,
        start_idx: s.seg.start_idx,
        start_px: s.seg.start_px,
        end_idx: s.seg.end_idx,
        end_px: s.seg.end_px,
        swing_index: s.swing_index,
        kind: s.kind,
        break_kind: s.break_kind,
        breaks: s.breaks as WholeDaySwingPoint["breaks"],
        confirmed_at_idx: s.confirmed_at_idx,
        confirmed_at_time: s.confirmed_at_time,
        fs_at_idx: s.fs_at_idx,
        fs_at_time: s.fs_at_time,
      })),
    [data],
  );

  const breakCount = useMemo(
    () => (data?.swings ?? []).reduce((n, s) => n + s.breaks.length, 0),
    [data],
  );

  const candleTsList = useMemo(
    () => (data?.candles ?? []).map((c) => c.ts),
    [data],
  );

  // 1m-precise exit timestamps fall BETWEEN chart candles — the chart time
  // scale only knows candle-open times, so snap box edges to the containing
  // candle (the trade table still shows the exact 1m exit time).
  const snapTs = useCallback(
    (ts: number): number => {
      const arr = candleTsList;
      if (arr.length === 0 || ts <= arr[0]) return arr[0] ?? ts;
      let lo = 0;
      let hi = arr.length - 1;
      let ans = arr[arr.length - 1];
      while (lo <= hi) {
        const mid = (lo + hi) >> 1;
        if (arr[mid] <= ts) {
          ans = arr[mid];
          lo = mid + 1;
        } else {
          hi = mid - 1;
        }
      }
      return ans;
    },
    [candleTsList],
  );

  // Trades -> PositionPrimitive boxes (open trades draw to their last bar)
  // HTF-LTF on a chart finer than the LTF: snap the entry edge to the actual
  // FILL moment (signal-bar close: entry_ts + 900s for 15m / +300s for 5m)
  // instead of the signal bar open. Exits are already 1m-precise (fine fills).
  const ltfBarSec = htfLtf === "15m" ? 900 : htfLtf === "5m" ? 300 : 0;
  const finerChart =
    htfLtf !== "off" && (tf === "1m" || (tf === "5m" && htfLtf === "15m"));
  const tradeBoxes: TradeBox[] = useMemo(
    () =>
      (btData?.trades ?? []).map((t) => ({
        dir: t.dir,
        entryTs: snapTs(t.entry_ts + (finerChart ? ltfBarSec : 0)),
        exitTs: snapTs(t.exit_ts),
        entryPrice: t.entry_price,
        slPrice: t.sl,
        targetPrice: t.target,
        exitPrice: t.exit_price,
        outcome: t.outcome,
        rMultiple: t.r_multiple,
      })),
    [btData, snapTs, finerChart, ltfBarSec],
  );

  const tableTrades = useMemo(
    () => [...(btData?.trades ?? [])].reverse().slice(0, 50),
    [btData],
  );

  const currentMaster = useMemo(
    () => BTC_MASTER_MODES.find((m) => m.value === master) ?? BTC_MASTER_MODES[0],
    [master],
  );

  const barsPerDay =
    tf === "1m" ? 1440 : tf === "5m" ? 288 : tf === "15m" ? 96 : tf === "1h" ? 24 : 6;
  const windowDays = data ? `${(data.count / barsPerDay).toFixed(1)}` : "—";

  // White walker flow-line (pivot-to-pivot path) — same shape as Nifty's
  // FlowSegment; continuous mode chains across midnight.
  const flowSegs: FlowSegment[] = useMemo(
    () =>
      (data?.flow ?? []).map((f) => ({
        dir: f.dir,
        startIdx: f.startIdx,
        startPx: f.startPx,
        endIdx: f.endIdx,
        endPx: f.endPx,
      })),
    [data],
  );


  const groupBtn = (
    active: boolean,
    onClick: () => void,
    text: string,
    borderL = false,
  ) => (
    <button
      key={text}
      onClick={onClick}
      className={`px-3 py-1.5 text-sm transition-colors ${
        active
          ? "bg-[#6366f1] text-white"
          : "bg-[#161b22] text-[#8b949e] hover:text-[#e6edf3]"
      } ${borderL ? "border-l border-[#30363d]" : ""}`}
    >
      {text}
    </button>
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-[#e6edf3]">
            BTC/USDT Swing Chart
          </h1>
          <p className="text-sm text-[#8b949e]">
            {loading
              ? "Loading..."
              : data
                ? `${data.count} candles · ${data.swings.length} swings · ${breakCount} break marks`
                : "—"}
            {data ? ` · window: ${data.first_ts ?? ""} → ${data.last_ts ?? ""}` : ""}
          </p>
          {status?.tfs?.[tf]?.exists ? (
            <p className="text-xs text-[#6e7681]">
              Data:{" "}
              <span className="text-[#8b949e]">
                {status.tfs[tf].first_ts?.slice(0, 16)} →{" "}
                {status.tfs[tf].last_ts?.slice(0, 16)}
              </span>{" "}
              · {status.tfs[tf].rows.toLocaleString()} × {tf}
            </p>
          ) : null}
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* timeframe */}
          <div
            className="flex overflow-hidden rounded-md border border-[#30363d]"
            role="group"
            aria-label="Timeframe"
          >
            {BTC_TFS.map((v, i) => (
              <button
                key={v}
                onClick={() => changeTf(v)}
                className={`px-3 py-1.5 text-sm transition-colors ${
                  tf === v
                    ? "bg-[#6366f1] text-white"
                    : "bg-[#161b22] text-[#8b949e] hover:text-[#e6edf3]"
                } ${i > 0 ? "border-l border-[#30363d]" : ""}`}
              >
                {v}
              </button>
            ))}
          </div>

          {/* walker mode */}
          <div
            className="flex overflow-hidden rounded-md border border-[#30363d]"
            role="group"
            aria-label="Walker mode"
          >
            {(["continuous", "daily"] as BtcMode[]).map((v) => (
              <button
                key={v}
                onClick={() => changeMode(v)}
                className={`px-3 py-1.5 text-sm transition-colors ${
                  mode === v
                    ? "bg-[#6366f1] text-white"
                    : "bg-[#161b22] text-[#8b949e] hover:text-[#e6edf3]"
                } ${v === "daily" ? "border-l border-[#30363d]" : ""}`}
                title={
                  v === "continuous"
                    ? "One 24/7 walk from the first candle (BTC default)"
                    : "Walker re-seeds each calendar day (NSE-style comparison)"
                }
              >
                {v === "continuous" ? "24/7 Continuous" : "Day Reset"}
              </button>
            ))}
          </div>

          {/* window size */}
          <div
            className="flex overflow-hidden rounded-md border border-[#30363d]"
            role="group"
            aria-label="Window"
          >
            {LIMITS.map((l, i) => groupBtn(limit === l.value, () => changeLimit(l.value), l.label, i > 0))}
          </div>

          {/* walker flow-line toggle */}
          <button
            onClick={() => setFlowOn((v) => !v)}
            className={`flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm transition-colors ${
              flowOn
                ? "border-[#e6edf3] text-[#e6edf3]"
                : "border-[#30363d] text-[#8b949e]"
            }`}
            title="Walker flow-line (white pivot-to-pivot path)"
          >
            <span
              className={`h-2 w-2 rounded-full ${flowOn ? "bg-[#e6edf3]" : "bg-[#8b949e]"}`}
            />
            Flow
          </button>

          {/* position engine toggle */}
          <button
            onClick={() => setTradesOn((v) => !v)}
            className={`flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm transition-colors ${
              tradesOn
                ? "border-[#10b981] text-[#e6edf3]"
                : "border-[#30363d] text-[#8b949e]"
            }`}
            title="Position engine: entries on swing breaks with SL/trailing/breakeven"
          >
            <span
              className={`h-2 w-2 rounded-full ${tradesOn ? "bg-[#10b981]" : "bg-[#8b949e]"}`}
            />
            Trades
          </button>

          {/* VERSION — crazy ideas v1..v7, each isolated engine */}
          <div className="flex flex-wrap items-center gap-2 rounded-md border border-[#f59e0b]/50 bg-[#f59e0b]/10 px-3 py-1.5">
            <span className="text-xs font-bold uppercase tracking-wide text-[#f59e0b]">Ver</span>
            <select
              value={version}
              onChange={(e) => changeVersion(e.target.value as BtcVersion)}
              className="rounded border border-[#f59e0b] bg-[#161b22] px-2 py-1 text-xs font-semibold text-[#e6edf3] outline-none focus:border-[#f59e0b]"
              title="Crazy-ideas version — v1 lock cap16, v2 Chandelier, v3 HTF, v4 Partial, v5 BE1, v6 ADX, v7 TimeCap. Each has its own engine, never disturbs v1."
            >
              {(["v1","v2","v3","v4","v5","v6","v7","v8","v9","v10"] as BtcVersion[]).map((v) => (
                <option key={v} value={v}>
                  {v} {versionLabels[v] ? `— ${versionLabels[v]}` : ""}
                </option>
              ))}
            </select>
            <span className="hidden text-[10px] text-[#8b949e] lg:inline">{versionLabels[version]}</span>
          </div>

          {/* HTF-LTF — 1h flip + 15m/5m execution inside HTF window */}
          <div className="flex flex-wrap items-center gap-2 rounded-md border border-[#10b981]/50 bg-[#10b981]/10 px-3 py-1.5">
            <span className="text-xs font-bold uppercase tracking-wide text-[#10b981]">HTF-LTF</span>
            <select
              value={htfLtf}
              onChange={(e) => changeHtfLtf(e.target.value as any)}
              className="rounded border border-[#10b981] bg-[#161b22] px-2 py-1 text-xs font-semibold text-[#e6edf3] outline-none focus:border-[#10b981]"
              title="Multi TF — 1h Flip cap16 window me 15m/5m Decisive execution. off=normal, 15m/5m = lower TF inside HTF (new strategy, doc: multi tf 1hour flip and lower tf execution.md)"
            >
              <option value="off">off</option>
              <option value="15m">15m inside 1h</option>
              <option value="5m">5m inside 1h</option>
            </select>
            {htfLtf !== "off" && (
              <select
                value={htfLtfVer}
                onChange={(e) => changeHtfLtfVer(e.target.value as "v1" | "v3" | "v5" | "v6")}
                className="rounded border border-[#10b981] bg-[#161b22] px-2 py-1 text-xs font-semibold text-[#e6edf3] outline-none focus:border-[#10b981]"
                title="HTF-LTF engine version — v3 Extension Stop: no new same-dir LTF entries once the 1h leg is beyond +1.5R unrealized. Research: 187tr 32.6% +139.95 net PF 2.47 maxDD 13.15R (v1: 204tr 30.9% +127.49 PF 2.25 maxDD 17.52R). IS+OOS both improve."
              >
                <option value="v1">v1 plain</option>
                <option value="v3">v3 ext-stop 1.5R</option>
                <option value="v5">v5 buf-SL 0.25ATR</option>
                <option value="v6">v6 hhll-30 SL</option>
              </select>
            )}
            {htfLtf !== "off" && (
              <span
                className="rounded bg-[#10b981]/20 px-1.5 py-0.5 text-[10px] font-semibold text-[#10b981]"
                title="Swing overlay is locked to the strategy chain so every B2/FLIP entry mark and FS confirmation you see comes from the same chain the engine trades. (15m: mb50, 5m: mb14, 1h: mb20)"
              >
                overlay: strategy chain (mb{tf === "15m" ? 50 : tf === "5m" ? 14 : tf === "1h" ? 20 : "?"})
              </span>
            )}
            <span className="hidden text-[10px] text-[#8b949e] lg:inline">{htfLtf==="off"?"normal":`1h → ${htfLtf} execution`}</span>
          </div>

          {/* MASTER strategy — sweep winners from fix/btc_ideas.md, instant apply */}
          <div className="flex flex-wrap items-center gap-2 rounded-md border border-[#6366f1]/50 bg-[#6366f1]/10 px-3 py-1.5">
            <span className="text-xs font-bold uppercase tracking-wide text-[#6366f1]">
              Master
            </span>
            <select
              value={master}
              onChange={(e) => applyMaster(e.target.value)}
              className="rounded border border-[#6366f1] bg-[#161b22] px-2 py-1 text-xs font-semibold text-[#e6edf3] outline-none focus:border-[#6366f1]"
              title="Master strategy — each option instantly applies its sweep-best params (fix/btc_ideas.md) and shows its trades on the chart."
            >
              {BTC_MASTER_MODES.map((m) => (
                <option key={m.value} value={m.value}>
                  {m.label}
                </option>
              ))}
            </select>
            <span className="hidden text-[10px] text-[#8b949e] lg:inline">
              {BTC_MASTER_MODES.find((m) => m.value === master)?.hint ?? ""}
            </span>
          </div>
        </div>
      </div>

      {error ? (
        <div className="rounded-md border border-[#f85149] bg-[#f851491a] px-4 py-3 text-sm text-[#f85149]">
          {error}
        </div>
      ) : null}

      {tradesOn && btError ? (
        <div className="rounded-md border border-[#f85149] bg-[#f851491a] px-4 py-3 text-sm text-[#f85149]">
          {btError}
        </div>
      ) : null}

      <StockChart
        symbol="BTC/USDT"
        candles={data?.candles ?? []}
        interval={tf}
        intraday
        wholeDaySwings={swings}
        swingMarkers
        trades={tradesOn ? tradeBoxes : undefined}
        algoFlowLine={flowOn && flowSegs.length > 0 ? flowSegs : null}
        height={720}
      />

      {/* ── position engine filters (below chart, like Nifty's IntradayPanel) ── */}
      {tradesOn ? (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[#6e7681]">
              Entry
            </span>
            <div
              className="flex overflow-hidden rounded-md border border-[#30363d]"
              role="group"
              aria-label="Entry break"
            >
              {(["decisive", "b2", "flip"] as const).map((v, i) =>
                groupBtn(btParams.entryBreak === v, () => setBt("entryBreak", v), v, i > 0),
              )}
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[#6e7681]">
              Stoploss
            </span>
            <div
              className="flex overflow-hidden rounded-md border border-[#30363d]"
              role="group"
              aria-label="Stop loss mode"
            >
              {groupBtn(btParams.slMode === "swing", () => setBt("slMode", "swing"), "swing pivot")}
              {groupBtn(btParams.slMode === "pct", () => setBt("slMode", "pct"), `${btParams.slPct}%`)}
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[#6e7681]">
              Trailing
            </span>
            <div
              className="flex overflow-hidden rounded-md border border-[#30363d]"
              role="group"
              aria-label="Trailing"
            >
              {(["off", "r", "swing"] as const).map((v, i) =>
                groupBtn(
                  btParams.trailing === v,
                  () => setBt("trailing", v),
                  v === "off" ? "off" : v === "r" ? `R-trail ${btParams.trailDistanceR}R` : "swing pivots",
                  i > 0,
                ),
              )}
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[#6e7681]">
              Bias
            </span>
            <div
              className="flex overflow-hidden rounded-md border border-[#30363d]"
              role="group"
              aria-label="Bias"
            >
              {groupBtn(btParams.bias === "off", () => setBt("bias", "off"), "off")}
              {groupBtn(
                btParams.bias === "15m",
                () => setBt("bias", "15m"),
                "15m swings",
              )}
            </div>
          </div>

          <label className="flex items-center gap-1.5 text-xs text-[#8b949e]">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[#6e7681]">
              Target
            </span>
            <span className="text-[10px] text-[#6e7681]">1:</span>
            <input
              type="number"
              step="0.5"
              min="0.5"
              value={btParams.rrTarget}
              onChange={(e) =>
                setBt("rrTarget", Number(e.target.value) > 0 ? Number(e.target.value) : 3)
              }
              className="w-14 rounded border border-[#30363d] bg-[#161b22] px-1.5 py-1 text-sm text-[#e6edf3]"
            />
          </label>

          <label className="flex items-center gap-1.5 text-xs text-[#8b949e]">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[#6e7681]">
              Breakeven
            </span>
            <input
              type="number"
              step="0.25"
              min="0"
              value={btParams.breakevenR}
              onChange={(e) =>
                setBt("breakevenR", Number(e.target.value) >= 0 ? Number(e.target.value) : 0)
              }
              className="w-14 rounded border border-[#30363d] bg-[#161b22] px-1.5 py-1 text-sm text-[#e6edf3]"
            />
            <span className="text-[10px] text-[#6e7681]">R (0 = off)</span>
          </label>

          <label className="flex items-center gap-1.5 text-xs text-[#8b949e]">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[#6e7681]">
              Fees %
            </span>
            <input
              type="number"
              step="0.01"
              min="0"
              value={btParams.feePct}
              onChange={(e) =>
                setBt("feePct", Number(e.target.value) >= 0 ? Number(e.target.value) : 0)
              }
              className="w-16 rounded border border-[#30363d] bg-[#161b22] px-1.5 py-1 text-sm text-[#e6edf3]"
            />
            <span className="text-[10px] text-[#6e7681]">/side</span>
          </label>

          <label className="flex items-center gap-1.5 text-xs text-[#8b949e]">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[#6e7681]">
              Slip
            </span>
            <input
              type="number"
              step="1"
              min="0"
              value={btParams.slippagePts}
              onChange={(e) =>
                setBt("slippagePts", Number(e.target.value) >= 0 ? Number(e.target.value) : 0)
              }
              className="w-16 rounded border border-[#30363d] bg-[#161b22] px-1.5 py-1 text-sm text-[#e6edf3]"
            />
            <span className="text-[10px] text-[#6e7681]">pts</span>
          </label>
        </div>
      ) : null}

      {/* applied filters + stats grid (mirrors Nifty's IntradayPanel) */}
      {tradesOn && btData ? (
        <>
          <div className="text-xs leading-relaxed text-[#8b949e]">
            Filters applied:{" "}
            <span className="text-[#c9d1d9]">
              {btData.params.htf_ltf && btData.params.htf_ltf !== "off" ? (
                <span className="text-[#10b981]">
                  HTF-LTF 1h→{btData.params.htf_ltf} {btData.params.htf_ltf_ver ?? "v1"}
                  {btData.params.ext_stop_r ? ` (ext-stop ${btData.params.ext_stop_r}R)` : ""}
                  {btData.params.sl_buf_atr ? ` · SL pivot+${btData.params.sl_buf_atr}ATR` : ""}
                  {btData.params.sl_hhll_n ? ` · SL hhll-${btData.params.sl_hhll_n}` : ""} ·{" "}
                </span>
              ) : null}
              {btData.params.htf_ltf && btData.params.htf_ltf !== "off"
                ? `executions on ${btData.params.tf}`
                : `${btData.params.tf}`} ·{" "}
              {btData.params.mode === "continuous" ? "24/7 continuous" : "day reset"} ·{" "}
              fees {btData.params.fee_pct}%/side + {btData.params.slippage_pts}pt slip ·{" "}
              {btData.params.fill_tf === "1m" ? "1m-precise fills · " : ""}
              window {btData.count} bars · {btData.swings_used} swings ·{" "}
              <span className="text-[#facc15]">
                entry = swing's decisive break (B2/FLIP) close · from swing #2
                (1st swing = bias only, no trade)
              </span>{" "}
              · SL{" "}
              {btData.params.sl_mode === "swing"
                ? "swing start pivot"
                : `${btData.params.sl_pct}%`}{" "}
              · RR 1:{btData.params.rr_target} · trailing {btData.params.trailing}
              {btData.params.trailing === "r"
                ? ` (${btData.params.trail_distance_r}R)`
                : ""}{" "}
              · breakeven{" "}
              {btData.params.breakeven_r > 0 ? `${btData.params.breakeven_r}R` : "off"}{" "}
              · bias{" "}
              {btData.params.bias === "15m"
                ? btData.params.bias_applied
                  ? "15m swings (active)"
                  : "15m swings (n/a on 15m chart)"
                : "off"}
              {" "}· minBars {btData.params.min_bars}
              {btData.params.regime === "streak_311" ? " · streak 3-1-1 regime (active)" : ""}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-8">
            <Stat
              label="Trades"
              value={`${btData.stats.closed}${btData.stats.open ? ` +${btData.stats.open} open` : ""}`}
            />
            <Stat
              label="Win rate"
              value={`${btData.stats.win_rate}%`}
              accent={btData.stats.win_rate >= 40 ? "#10b981" : "#ef4444"}
            />
            <Stat
              label="Total R"
              value={`${btData.stats.total_r >= 0 ? "+" : ""}${btData.stats.total_r}`}
              accent={btData.stats.total_r >= 0 ? "#10b981" : "#ef4444"}
            />
            {(btData.stats.total_costs_r ?? 0) > 0 ? (
              <Stat
                label={`Net R (after ${(btData.params.fee_pct ?? 0)}%+${btData.params.slippage_pts ?? 0}pt)`}
                value={`${(btData.stats.net_total_r ?? 0) >= 0 ? "+" : ""}${(btData.stats.net_total_r ?? 0).toFixed(2)}`}
                accent={(btData.stats.net_total_r ?? 0) >= 0 ? "#10b981" : "#ef4444"}
              />
            ) : null}
            <Stat
              label="Avg R"
              value={`${btData.stats.avg_r >= 0 ? "+" : ""}${btData.stats.avg_r}`}
              accent={btData.stats.avg_r >= 0 ? "#10b981" : "#ef4444"}
            />
            <Stat
              label="Max DD"
              value={`${btData.stats.max_drawdown_r}R`}
              accent="#f97316"
            />
            <Stat
              label="PF"
              value={`${(btData.stats as any).profit_factor ?? "-"}`}
              accent={(btData.stats as any).profit_factor >= 1.5 ? "#10b981" : "#ef4444"}
            />
            <Stat
              label="Max Cons Loss"
              value={`${(btData.stats as any).max_consecutive_losses ?? "-"}L`}
              accent="#ef4444"
            />
            <Stat
              label="DD Dur"
              value={`${(btData.stats as any).max_drawdown_duration_trades ?? "-"}tr`}
              accent="#f97316"
            />
            <Stat
              label="Avg Hold"
              value={`${(btData.stats as any).avg_bars_held ?? "-"} bars`}
            />
            <Stat
              label="Long / Short"
              value={`${btData.stats.longs}/${btData.stats.shorts}`}
            />
            {Object.entries(btData.stats.outcomes)
              .slice(0, 2)
              .map(([k, v]) => (
                <Stat
                  key={k}
                  label={OUTCOME_STYLE[k]?.label ?? k}
                  value={String(v)}
                />
              ))}
          </div>
        </>
      ) : null}

      {tradesOn && tableTrades.length > 0 ? (
        <div className="max-h-64 overflow-y-auto rounded-md border border-[#30363d]">
          <table className="w-full text-left text-xs">
            <thead className="sticky top-0 bg-[#161b22] text-[#8b949e]">
              <tr>
                <th className="px-2 py-1.5">#</th>
                <th className="py-1.5">Dir</th>
                <th className="py-1.5">Kind</th>
                <th className="py-1.5">Entry</th>
                <th className="py-1.5">Exit</th>
                <th className="py-1.5 text-right">Entry px</th>
                <th className="py-1.5 text-right">Exit px</th>
                <th className="py-1.5 text-right">R</th>
                <th className="py-1.5">Outcome</th>
              </tr>
            </thead>
            <tbody>
              {tableTrades.map((t) => (
                <tr key={t.trade_no} className="border-t border-[#21262d] text-[#e6edf3]">
                  <td className="px-2 py-1 text-[#8b949e]">{t.trade_no}</td>
                  <td className={`py-1 font-medium ${t.dir === "long" ? "text-[#10b981]" : "text-[#ef4444]"}`}>
                    {t.dir === "long" ? "L" : "S"}
                  </td>
                  <td className="py-1 text-[#8b949e]">{t.break_kind}</td>
                  <td className="py-1">{fmtTs(t.entry_ts)}</td>
                  <td className="py-1">{t.outcome === "open" ? "—" : fmtTs(t.exit_ts)}</td>
                  <td className="py-1 text-right">{t.entry_price}</td>
                  <td className="py-1 text-right">{t.exit_price}</td>
                  <td
                    className={`py-1 text-right font-medium ${
                      t.r_multiple >= 0 ? "text-[#10b981]" : "text-[#ef4444]"
                    }`}
                  >
                    {t.r_multiple > 0 ? "+" : ""}
                    {t.r_multiple.toFixed(2)}
                  </td>
                  <td className="py-1">
                    <OutcomeChip outcome={t.outcome} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {/* ── strategy summary ("konsi best hai") — every preset ranked by NET R ── */}
      {tradesOn ? (
        <div className="rounded-md border border-[#6366f1]/40 bg-[#0d1117] px-4 py-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="rounded bg-[#6366f1] px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-white">
                Strategy Summary
              </span>
              <span className="text-xs text-[#8b949e]">
                each preset on its OWN reference TF · full data window · ranked by NET R after{" "}
                {btParams.feePct}%/side fees + {btParams.slippagePts}pt slippage — click a row to load its trades
              </span>
            </div>
            {summaryData?.best ? (
              <span className="text-xs text-[#10b981]">
                BEST: {summaryData.rows.find((r) => r.key === summaryData.best)?.label}
              </span>
            ) : null}
          </div>
          {summaryError ? (
            <p className="mt-2 text-xs text-[#ef4444]">{summaryError}</p>
          ) : null}
          {summaryData ? (
            <div className="mt-2 overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="text-[#8b949e]">
                  <tr>
                    <th className="py-1.5 pr-2">#</th>
                    <th className="py-1.5 pr-2">Strategy</th>
                    <th className="py-1.5 pr-2 text-right">TF</th>
                    <th className="py-1.5 pr-2 text-right">Trades</th>
                    <th className="py-1.5 pr-2 text-right">Win%</th>
                    <th className="py-1.5 pr-2 text-right">Base R</th>
                    <th className="py-1.5 pr-2 text-right">Costs R</th>
                    <th className="py-1.5 pr-2 text-right">Net R</th>
                    <th className="py-1.5">Verdict</th>
                  </tr>
                </thead>
                <tbody>
                  {summaryData.rows.map((r) => (
                    <tr
                      key={r.key}
                      onClick={() => applyMaster(r.key)}
                      title={`Load ${r.label} — jumps TF to ${r.tf} + full window`}
                      className={`border-t border-[#21262d] cursor-pointer hover:bg-[#161b22] ${
                        r.key === summaryData.best ? "bg-[#10b981]/10" : ""
                      } text-[#e6edf3]`}
                    >
                      <td className="py-1 pr-2 text-[#8b949e]">{r.rank}</td>
                      <td className="py-1 pr-2">
                        <span className="font-medium">{r.label}</span>
                        <span className="ml-1.5 text-[10px] text-[#6e7681]">
                          {r.entry_break}·mb{r.min_bars}
                          {r.trailing !== "off" ? "·trail" : ""}
                          {r.bias !== "off" ? "·bias" : ""}
                          {r.regime !== "off" ? "·regime" : ""}
                          {r.breakeven_r > 0 ? `·BE${r.breakeven_r}` : "·BE0"}
                        </span>
                      </td>
                      <td className="py-1 pr-2 text-right">
                        <span className="rounded bg-[#21262d] px-1.5 py-0.5 text-[10px] font-semibold text-[#c9d1d9]">
                          {r.tf}
                        </span>
                      </td>
                      <td className="py-1 pr-2 text-right">{r.trades}</td>
                      <td className="py-1 pr-2 text-right">{r.win_rate}%</td>
                      <td className="py-1 pr-2 text-right text-[#8b949e]">
                        {r.base_r >= 0 ? "+" : ""}
                        {r.base_r.toFixed(1)}
                      </td>
                      <td className="py-1 pr-2 text-right text-[#f97316]">
                        −{r.costs_r.toFixed(1)}
                      </td>
                      <td
                        className={`py-1 pr-2 text-right font-semibold ${
                          r.net_r >= 0 ? "text-[#10b981]" : "text-[#ef4444]"
                        }`}
                      >
                        {r.net_r >= 0 ? "+" : ""}
                        {r.net_r.toFixed(1)}
                      </td>
                      <td className="py-1 text-[10px]">
                        {r.net_r >= 50
                          ? "✅ strong (costs survived)"
                          : r.net_r >= 0
                            ? "⚠️ thin edge (costs survived, barely)"
                            : r.base_r > 0
                              ? "❌ zero-cost hero, fees kill it"
                              : "❌ no edge"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="mt-2 text-[10px] leading-relaxed text-[#6e7681]">
                Base R = what the raw sim made (zero cost). Costs R = round-trip fee+slippage
                per trade expressed in R. Net R = Base − Costs. Every row is measured on the
                preset's OWN reference TF (15m/1h/5m) over the FULL data window (Jan-2025 → Sep-2026,
                bull + bear), with 1m-precise fills + stream entries — so the Trades/Net R here
                match exactly what you get when you click the row. The 2025 presets were tuned
                in-sample; the Flip/Decisive Trail & Sniper presets are the ones verified
                out-of-sample (bear market Oct-25 → Sep-26).
              </p>
              {/* Crazy Lab — v1..v6 inside same Strategy Summary box */}
              <div className="mt-4 rounded-md border border-[#f59e0b]/30 bg-[#f59e0b]/5 px-3 py-2">
                <div className="flex items-center gap-2">
                  <span className="rounded bg-[#f59e0b] px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-white">Crazy Lab</span>
                  <span className="text-xs font-semibold text-[#e6edf3]">15m Decisive50 — v1..v6 (honest FULL window, 0.05%+2pt)</span>
                  <span className="text-[10px] text-[#8b949e]">— click Ver to load</span>
                </div>
                <div className="mt-2 overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="text-[#8b949e]">
                      <tr>
                        <th className="py-1 pr-2">Ver</th>
                        <th className="py-1 pr-2">Engine</th>
                        <th className="py-1 pr-2 text-right">Trades</th>
                        <th className="py-1 pr-2 text-right">Win%</th>
                        <th className="py-1 pr-2 text-right">BaseR</th>
                        <th className="py-1 pr-2 text-right">NetR</th>
                        <th className="py-1 pr-2 text-right">PF</th>
                        <th className="py-1 pr-2 text-right">maxDD</th>
                        <th className="py-1">Verdict</th>
                      </tr>
                    </thead>
                    <tbody className="text-[#e6edf3]">
                      <tr className={`border-t border-[#21262d] ${version==="v1"?"bg-[#f59e0b]/10":""}`}>
                        <td className="py-1 pr-2 font-mono"><button onClick={()=>changeVersion("v1")} className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${version==="v1"?"bg-[#f59e0b] text-white":"bg-[#21262d] text-[#8b949e]"}`}>v1</button></td>
                        <td className="py-1 pr-2">Honest pivot</td><td className="py-1 pr-2 text-right">446</td><td className="py-1 pr-2 text-right">22.0%</td><td className="py-1 pr-2 text-right">+91.0</td><td className="py-1 pr-2 text-right font-semibold text-[#f59e0b]">+5.4</td><td className="py-1 pr-2 text-right">1.30</td><td className="py-1 pr-2 text-right">40.3</td><td className="py-1 text-[10px]">Locked</td>
                      </tr>
                      <tr className={`border-t border-[#21262d] ${version==="v2"?"bg-[#f59e0b]/10":""}`}>
                        <td className="py-1 pr-2"><button onClick={()=>changeVersion("v2")} className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${version==="v2"?"bg-[#f59e0b] text-white":"bg-[#21262d] text-[#8b949e]"}`}>v2</button></td>
                        <td className="py-1 pr-2">Chandelier</td><td className="py-1 pr-2 text-right">1302</td><td className="py-1 pr-2 text-right">35.3%</td><td className="py-1 pr-2 text-right">-12.7</td><td className="py-1 pr-2 text-right font-semibold text-[#ef4444]">-269</td><td className="py-1 pr-2 text-right">0.90</td><td className="py-1 pr-2 text-right">20.3</td><td className="py-1 text-[10px]">Too tight</td>
                      </tr>
                      <tr className={`border-t border-[#21262d] ${version==="v3"?"bg-[#f59e0b]/10":""}`}>
                        <td className="py-1 pr-2"><button onClick={()=>changeVersion("v3")} className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${version==="v3"?"bg-[#f59e0b] text-white":"bg-[#21262d] text-[#8b949e]"}`}>v3</button></td>
                        <td className="py-1 pr-2">HTF 1h</td><td className="py-1 pr-2 text-right">236</td><td className="py-1 pr-2 text-right">15.7%</td><td className="py-1 pr-2 text-right">-34.1</td><td className="py-1 pr-2 text-right font-semibold text-[#ef4444]">-74</td><td className="py-1 pr-2 text-right">0.86</td><td className="py-1 pr-2 text-right">53.5</td><td className="py-1 text-[10px]">Too slow</td>
                      </tr>
                      <tr className={`border-t border-[#21262d] ${version==="v4"?"bg-[#f59e0b]/10":""}`}>
                        <td className="py-1 pr-2"><button onClick={()=>changeVersion("v4")} className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${version==="v4"?"bg-[#f59e0b] text-white":"bg-[#21262d] text-[#8b949e]"}`}>v4</button></td>
                        <td className="py-1 pr-2">Partial</td><td className="py-1 pr-2 text-right">350</td><td className="py-1 pr-2 text-right">25.4%</td><td className="py-1 pr-2 text-right">-14.0</td><td className="py-1 pr-2 text-right font-semibold text-[#ef4444]">-71</td><td className="py-1 pr-2 text-right">0.94</td><td className="py-1 pr-2 text-right">33.2</td><td className="py-1 text-[10px]">Blend</td>
                      </tr>
                      <tr className={`border-t border-[#21262d] ${version==="v5"?"bg-[#f59e0b]/10":""}`}>
                        <td className="py-1 pr-2"><button onClick={()=>changeVersion("v5")} className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${version==="v5"?"bg-[#f59e0b] text-white":"bg-[#21262d] text-[#8b949e]"}`}>v5</button></td>
                        <td className="py-1 pr-2">BE1</td><td className="py-1 pr-2 text-right">515</td><td className="py-1 pr-2 text-right">17.5%</td><td className="py-1 pr-2 text-right">+84.8</td><td className="py-1 pr-2 text-right font-semibold text-[#ef4444]">-10</td><td className="py-1 pr-2 text-right">1.35</td><td className="py-1 pr-2 text-right">30.4</td><td className="py-1 text-[10px]">Maker</td>
                      </tr>
                      <tr className={`border-t border-[#21262d] ${version==="v6"?"bg-[#f59e0b]/10":""}`}>
                        <td className="py-1 pr-2"><button onClick={()=>changeVersion("v6")} className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${version==="v6"?"bg-[#f59e0b] text-white":"bg-[#21262d] text-[#8b949e]"}`}>v6</button></td>
                        <td className="py-1 pr-2">ADX&gt;25</td><td className="py-1 pr-2 text-right">337</td><td className="py-1 pr-2 text-right">23.4%</td><td className="py-1 pr-2 text-right">+159.4</td><td className="py-1 pr-2 text-right font-semibold text-[#10b981]">+90.5</td><td className="py-1 pr-2 text-right">1.68</td><td className="py-1 pr-2 text-right">23.9</td><td className="py-1 text-[10px]">✅ BEST</td>
                      </tr>
                    </tbody>
                  </table>
                  <p className="mt-1 text-[10px] text-[#6e7681]">Click Ver → chart + summary update via <code>?version=v6</code> — each <code>v*.py</code> isolated, <code>v1</code> never disturbed. Doc: <code>fix/btc_15m_trail_decisive_crazy_ideas.md</code></p>
                </div>
              </div>
              {/* 1h Flip Fixed — v1..v6 versions */}
              <div className="mt-3 rounded-md border border-[#6366f1]/30 bg-[#6366f1]/5 px-3 py-2">
                <div className="flex items-center gap-2">
                  <span className="rounded bg-[#6366f1] px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-white">1h Flip</span>
                  <span className="text-xs font-semibold text-[#e6edf3]">Flip Fixed 3R (1h) — v1..v6 (honest FULL window, 0.05%+2pt)</span>
                  <span className="text-[10px] text-[#8b949e]">— best v1 cap16</span>
                </div>
                <div className="mt-2 overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="text-[#8b949e]">
                      <tr>
                        <th className="py-1 pr-2">Ver</th>
                        <th className="py-1 pr-2">Engine</th>
                        <th className="py-1 pr-2 text-right">Trades</th>
                        <th className="py-1 pr-2 text-right">Win%</th>
                        <th className="py-1 pr-2 text-right">BaseR</th>
                        <th className="py-1 pr-2 text-right">NetR</th>
                        <th className="py-1 pr-2 text-right">PF</th>
                        <th className="py-1 pr-2 text-right">maxDD</th>
                        <th className="py-1">Verdict</th>
                      </tr>
                    </thead>
                    <tbody className="text-[#e6edf3]">
                      <tr className={`border-t border-[#21262d] ${version==="v1"?"bg-[#6366f1]/10":""}`}>
                        <td className="py-1 pr-2"><button onClick={()=>changeVersion("v1")} className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${version==="v1"?"bg-[#6366f1] text-white":"bg-[#21262d] text-[#8b949e]"}`}>v1</button></td>
                        <td className="py-1 pr-2">Cap 16d ⭐</td><td className="py-1 pr-2 text-right">151</td><td className="py-1 pr-2 text-right">39.7%</td><td className="py-1 pr-2 text-right">+74.0</td><td className="py-1 pr-2 text-right font-bold text-[#10b981]">+57.8</td><td className="py-1 pr-2 text-right">1.78</td><td className="py-1 pr-2 text-right">10.0</td><td className="py-1 text-[10px]">✅ BEST</td>
                      </tr>
                      <tr className="border-t border-[#21262d]">
                        <td className="py-1 pr-2"><button onClick={()=>changeVersion("v2")} className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${version==="v2"?"bg-[#6366f1] text-white":"bg-[#21262d] text-[#8b949e]"}`}>v2</button></td>
                        <td className="py-1 pr-2">Chandelier</td><td className="py-1 pr-2 text-right">363</td><td className="py-1 pr-2 text-right">38.3%</td><td className="py-1 pr-2 text-right">-6.5</td><td className="py-1 pr-2 text-right font-semibold text-[#ef4444]">-50</td><td className="py-1 pr-2 text-right">0.86</td><td className="py-1 pr-2 text-right">13.3</td><td className="py-1 text-[10px]">Too many</td>
                      </tr>
                      <tr className="border-t border-[#21262d]">
                        <td className="py-1 pr-2"><button onClick={()=>changeVersion("v3")} className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${version==="v3"?"bg-[#6366f1] text-white":"bg-[#21262d] text-[#8b949e]"}`}>v3</button></td>
                        <td className="py-1 pr-2">HTF 4h</td><td className="py-1 pr-2 text-right">190</td><td className="py-1 pr-2 text-right">38.4%</td><td className="py-1 pr-2 text-right">+61.9</td><td className="py-1 pr-2 text-right font-semibold text-[#10b981]">+41.7</td><td className="py-1 pr-2 text-right">1.55</td><td className="py-1 pr-2 text-right">11.7</td><td className="py-1 text-[10px]">2nd best</td>
                      </tr>
                      <tr className="border-t border-[#21262d]">
                        <td className="py-1 pr-2"><button onClick={()=>changeVersion("v4")} className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${version==="v4"?"bg-[#6366f1] text-white":"bg-[#21262d] text-[#8b949e]"}`}>v4</button></td>
                        <td className="py-1 pr-2">Partial</td><td className="py-1 pr-2 text-right">23</td><td className="py-1 pr-2 text-right">43.5%</td><td className="py-1 pr-2 text-right">-3.0</td><td className="py-1 pr-2 text-right font-semibold text-[#ef4444]">-5</td><td className="py-1 pr-2 text-right">0.77</td><td className="py-1 pr-2 text-right">5.0</td><td className="py-1 text-[10px]">Few</td>
                      </tr>
                      <tr className="border-t border-[#21262d]">
                        <td className="py-1 pr-2"><button onClick={()=>changeVersion("v5")} className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${version==="v5"?"bg-[#6366f1] text-white":"bg-[#21262d] text-[#8b949e]"}`}>v5</button></td>
                        <td className="py-1 pr-2">BE1</td><td className="py-1 pr-2 text-right">146</td><td className="py-1 pr-2 text-right">22.6%</td><td className="py-1 pr-2 text-right">+25.9</td><td className="py-1 pr-2 text-right">+10.2</td><td className="py-1 pr-2 text-right">1.36</td><td className="py-1 pr-2 text-right">13.0</td><td className="py-1 text-[10px]"></td>
                      </tr>
                      <tr className="border-t border-[#21262d]">
                        <td className="py-1 pr-2"><button onClick={()=>changeVersion("v6")} className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${version==="v6"?"bg-[#6366f1] text-white":"bg-[#21262d] text-[#8b949e]"}`}>v6</button></td>
                        <td className="py-1 pr-2">ADX</td><td className="py-1 pr-2 text-right">94</td><td className="py-1 pr-2 text-right">26.6%</td><td className="py-1 pr-2 text-right">+5.6</td><td className="py-1 pr-2 text-right font-semibold text-[#ef4444]">-4.8</td><td className="py-1 pr-2 text-right">1.08</td><td className="py-1 pr-2 text-right">14.4</td><td className="py-1 text-[10px]">No</td>
                      </tr>
                    </tbody>
                  </table>
                  <p className="mt-1 text-[10px] text-[#6e7681]">All honest <code>stream+touchable+one-swing-one-trade+1m fills</code> FULL Jan-25→Sep-26 `1h` `flip` `0.05%+2pt` — click Ver to load. Cap sweep: 15d +57.4, 16d ⭐+57.8, 30d +50.5. Doc: <code>fix/btc_1h_flip_fixed_crazy_ideas.md</code></p>
                </div>
              </div>
            </div>
          ) : null}
        </div>
      ) : null}

      {/* HTF-LTF Crazy Lab - own version track: ?htf_ltf=15m&htf_ltf_ver=v1|v3 */}
      <div className="rounded-md border border-[#10b981]/40 bg-[#0d1117] px-4 py-3 text-xs text-[#c9d1d9]">
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded bg-[#10b981] px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-white">Crazy Lab</span>
          <span className="text-xs font-semibold text-[#e6edf3]">HTF-LTF — 1h Flip cap16 + 15m Decisive inside (honest FULL window, 0.05%+2pt)</span>
          <span className="text-[10px] text-[#8b949e]">— click Ver to load (sets HTF-LTF 15m + version)</span>
        </div>
        <div className="mt-2 overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="text-[#8b949e]">
              <tr>
                <th className="py-1 pr-2">Ver</th>
                <th className="py-1 pr-2">Engine</th>
                <th className="py-1 pr-2 text-right">Trades</th>
                <th className="py-1 pr-2 text-right">Win%</th>
                <th className="py-1 pr-2 text-right">BaseR</th>
                <th className="py-1 pr-2 text-right">NetR</th>
                <th className="py-1 pr-2 text-right">PF</th>
                <th className="py-1 pr-2 text-right">maxDD</th>
                <th className="py-1">Verdict</th>
              </tr>
            </thead>
            <tbody className="text-[#e6edf3]">
              <tr className={`border-t border-[#21262d] ${htfLtf!=="off"&&htfLtfVer==="v1"?"bg-[#10b981]/10":""}`}>
                <td className="py-1 pr-2 font-mono"><button onClick={()=>{if(htfLtf==="off")changeHtfLtf("15m");changeHtfLtfVer("v1");}} className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${htfLtf!=="off"&&htfLtfVer==="v1"?"bg-[#10b981] text-white":"bg-[#21262d] text-[#8b949e]"}`}>v1</button></td>
                <td className="py-1 pr-2">Plain window gate</td><td className="py-1 pr-2 text-right">204</td><td className="py-1 pr-2 text-right">30.9%</td><td className="py-1 pr-2 text-right">+165.5</td><td className="py-1 pr-2 text-right font-semibold text-[#10b981]">+127.5</td><td className="py-1 pr-2 text-right">2.25</td><td className="py-1 pr-2 text-right">17.5</td><td className="py-1 text-[10px]">Baseline (locked)</td>
              </tr>
              <tr className={`border-t border-[#21262d] ${htfLtf!=="off"&&htfLtfVer==="v3"?"bg-[#10b981]/10":""}`}>
                <td className="py-1 pr-2 font-mono"><button onClick={()=>{if(htfLtf==="off")changeHtfLtf("15m");changeHtfLtfVer("v3");}} className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${htfLtf!=="off"&&htfLtfVer==="v3"?"bg-[#10b981] text-white":"bg-[#21262d] text-[#8b949e]"}`}>v3</button></td>
                <td className="py-1 pr-2">Ext-Stop 1.5R</td><td className="py-1 pr-2 text-right">187</td><td className="py-1 pr-2 text-right">32.6%</td><td className="py-1 pr-2 text-right">+175.9</td><td className="py-1 pr-2 text-right font-semibold text-[#10b981]">+140.0</td><td className="py-1 pr-2 text-right">2.47</td><td className="py-1 pr-2 text-right">13.2</td><td className="py-1 text-[10px]">✅ BEST — IS+OOS both beat v1</td>
              </tr>
              <tr className="border-t border-[#21262d] opacity-60">
                <td className="py-1 pr-2 font-mono">v4</td>
                <td className="py-1 pr-2">CHOP&lt;=61.8 gate</td><td className="py-1 pr-2 text-right">202</td><td className="py-1 pr-2 text-right">30.2%</td><td className="py-1 pr-2 text-right">—</td><td className="py-1 pr-2 text-right font-semibold text-[#ef4444]">+121.8</td><td className="py-1 pr-2 text-right">2.20</td><td className="py-1 pr-2 text-right">17.5</td><td className="py-1 text-[10px]">❌ rejected — busy-chain artifact</td>
              </tr>
              <tr className={`border-t border-[#21262d] ${htfLtf!=="off"&&htfLtfVer==="v5"?"bg-[#10b981]/10":""}`}>
                <td className="py-1 pr-2 font-mono"><button onClick={()=>{if(htfLtf==="off")changeHtfLtf("15m");changeHtfLtfVer("v5");}} className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${htfLtf!=="off"&&htfLtfVer==="v5"?"bg-[#10b981] text-white":"bg-[#21262d] text-[#8b949e]"}`}>v5</button></td>
                <td className="py-1 pr-2">Ext-Stop + SL pivot+0.25ATR</td><td className="py-1 pr-2 text-right">179</td><td className="py-1 pr-2 text-right">34.6%</td><td className="py-1 pr-2 text-right">+182.4</td><td className="py-1 pr-2 text-right font-semibold text-[#10b981]">+152.8</td><td className="py-1 pr-2 text-right">2.70</td><td className="py-1 pr-2 text-right">11.2</td><td className="py-1 text-[10px]">✅ BEST net — maxL 10 (IS maxL 7)</td>
              </tr>
              <tr className={`border-t border-[#21262d] ${htfLtf!=="off"&&htfLtfVer==="v6"?"bg-[#10b981]/10":""}`}>
                <td className="py-1 pr-2 font-mono"><button onClick={()=>{if(htfLtf==="off")changeHtfLtf("15m");changeHtfLtfVer("v6");}} className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${htfLtf!=="off"&&htfLtfVer==="v6"?"bg-[#10b981] text-white":"bg-[#21262d] text-[#8b949e]"}`}>v6</button></td>
                <td className="py-1 pr-2">Ext-Stop + SL hhll-30</td><td className="py-1 pr-2 text-right">169</td><td className="py-1 pr-2 text-right">39.6%</td><td className="py-1 pr-2 text-right">+161.8</td><td className="py-1 pr-2 text-right font-semibold text-[#10b981]">+138.4</td><td className="py-1 pr-2 text-right">2.87</td><td className="py-1 pr-2 text-right">9.3</td><td className="py-1 text-[10px]">✅ smooth mode — WR 40%, maxL 9</td>
              </tr>
            </tbody>
          </table>
          <p className="mt-1 text-[10px] text-[#6e7681]">
            LTF-leg stats (1m fills, stream, touchable SL, swing trail).
            v3 Extension Stop: no new same-dir 15m entries once the 1h leg is &gt;+1.5R unrealized — removes the 8-14% WR late-entry zone; IS +56.3 / OOS +83.7, both beat v1 (+51.4 / +76.1).
            Rejected 2026-09-07: 4h bias agree, wait-for-+1R, fresh-window-only, HTF breakeven, fade-when-extended (PF 0.54), partial/secure exits, CHOP gate (v4). Sizing study: v3 at full size already best net/DD 8.69 — no downsizing needed. Doc: <code>fix/multi tf 1hour flip and lower tf execution.md</code>
          </p>
        </div>
      </div>

      {/* MASTER strategy — "how it works" card (fix/btc_ideas.md sweep winners) */}
      {tradesOn && currentMaster ? (
        <div className="rounded-md border border-[#6366f1]/40 bg-[#0d1117] px-4 py-3 text-xs text-[#c9d1d9]">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="rounded bg-[#6366f1] px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-white">
                {currentMaster.label}
              </span>
              <span className="text-[#8b949e]">how it works</span>
            </div>
            <button
              onClick={() => setShowMasterInfo((v) => !v)}
              className="text-[#8b949e] hover:text-[#e6edf3]"
              title="Toggle strategy description"
            >
              {showMasterInfo ? "Hide ▾" : "Show ▸"}
            </button>
          </div>
          {showMasterInfo ? (
            <div className="mt-2 space-y-1.5">
              <ul className="list-disc space-y-1 pl-4">
                {currentMaster.desc.map((d) => (
                  <li key={d}>{d}</li>
                ))}
              </ul>
              <p className="text-[#8b949e]">
                Reference timeframe:{" "}
                <span className="text-[#e6edf3]">{currentMaster.bestTf}</span>
                {" · "}you are viewing{" "}
                <span className={tf === currentMaster.bestTf ? "text-[#10b981]" : "text-[#facc15]"}>
                  {tf}
                </span>
                {tf !== currentMaster.bestTf ? (
                  <> ({windowDays} days of history) — the stats below scale to this window. Dropdown picks auto-jump here.</>
                ) : null}
                {currentMaster.preset.bias === "15m" && tf === "15m" ? (
                  <span className="text-[#facc15]">
                    {" "}⚠ The 15m bias gate is INACTIVE on the 15m chart — pick a master again or use 5m/1m.
                  </span>
                ) : null}
              </p>
              <p className="text-[#8b949e]">
                Full-dataset reference (window = All):{" "}
                <span className="text-[#facc15]">{currentMaster.ref}</span>
              </p>
              <p className="text-[#8b949e]">
                This window: {data?.count ?? "—"} bars ({windowDays} days) — the stats below are
                scaled to THIS window only. Set the Window control to{" "}
                <span className="text-[#e6edf3]">All</span> for the full 272-day backtest.
              </p>
            </div>
          ) : null}
        </div>
      ) : null}

      {/* VERSION — how it works (crazy ideas v1..v7) */}
      <div className="rounded-md border border-[#f59e0b]/40 bg-[#0d1117] px-4 py-3 text-xs text-[#c9d1d9]">
        <div className="flex items-center gap-2">
          <span className="rounded bg-[#f59e0b] px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-white">Ver {version}</span>
          <span className="text-[#8b949e]">{versionLabels[version] || version}</span>
          <span className="text-[#6e7681]">— how it works</span>
        </div>
        <div className="mt-2 space-y-1 text-[11px] leading-relaxed text-[#8b949e]">
          {version === "v1" && <p><b className="text-[#e6edf3]">v1 Honest — cap 16d for 1h Flip</b> — one swing one trade <code>btc_engine.py:93</code> + touchable SL <code>max high since prev_end</code> <code>btc_engine.py:128</code> + 1m fills <code>btc_engine.py:195</code> + <b>time cap 16d</b> <code>v7_timecap.py:1</code> for 1h Flip Fixed 3R (old cap 0 101tr +51.2 removed). 1h Flip now <code>151tr +57.8 net PF0.78</code> vs cap0 +51.2.</p>}
          {version === "v2" && <p><b className="text-[#e6edf3]">v2 Chandelier k=3.0</b> — same entry/SL as v1, trailing = <code>highestHigh - k*ATR14</code> / <code>lowestLow + kATR</code> <code>v2_chandelier.py:1</code>. Vol-adaptive, wide in bear. Sweep k=2.5/3.0/3.5.</p>}
          {version === "v3" && <p><b className="text-[#e6edf3]">v3 HTF 1h Trail</b> — 15m entries, 1h swing pivots <code>btc_swing.py:156</code> <code>v3_htf_trail.py:1</code>. Fewer pivots 14715 vs 58780 → slower ratchet.</p>}
          {version === "v4" && <p><b className="text-[#e6edf3]">v4 Partial 50/50</b> — half qty fixed 3R target + half swing trail <code>v4_partial.py:1</code>. Fee per half. Blend <code>split*Rf + (1-split)*Rt</code>.</p>}
          {version === "v5" && <p><b className="text-[#e6edf3]">v5 BE1</b> — same as v1 but <code>breakeven 1R</code> <code>v5_be1.py:1</code> <code>sl=entry</code> after +1R.</p>}
          {version === "v6" && <p><b className="text-[#e6edf3]">v6 ADX&gt;25</b> — <code>ADX14 Wilder</code> <code>v6_adx.py:1</code> gate at entry bar, else skip. Filters chop, best on 15m decisive: <code>337tr +90.5 net PF1.68</code> vs v1 +5.4.</p>}
          {version === "v7" && <p><b className="text-[#e6edf3]">v7 TimeCap 16d (1h Flip)</b> — <code>cap_days 16</code> <code>v7_timecap.py:1</code> <code>market exit</code> at cap, <code>151tr +57.8 net PF0.78 maxDD10</code> vs cap0 <code>101tr +51.2 PF1.97</code> — 27 Jan 114d -1R → 16d +0.289R, best net. Isolated, v1 15m never disturbed.</p>}
          {version === "v8" && <p><b className="text-[#e6edf3]">v8 Break High/Low</b> — <code>v8_break_entry.py:1</code> <code>entry high/low break</code> `confirm_bars 3` next 1h must break entry high/low without opposite breach — 13 Feb 06:30 & 17 Mar 19:30 cases. <code>95tr +16.0 net PF1.37</code> vs v1 151tr +57.8 — worse, break entry loses edge.</p>}
          {version === "v9" && <p><b className="text-[#e6edf3]">v9 Conditional Cap 2R→30d</b> — <code>v9_conditional_cap.py:1</code> <code>cap 16d if &lt;2R at 16d cut, else extend to 30d</code> `thr 2.5` `148tr +58.3 PF1.73` vs v1 +57.8 — marginal +0.5R.</p>}
          {version === "v10" && <p><b className="text-[#e6edf3]">v10 Flip Strength</b> — <code>v10_strength.py:1</code> `body&gt;=0.5 ATR wick&lt;=1.0 ATR` `angle` `leg/bars/ATR` `min_swing_angle`. <code>129tr +37.3 PF1.47</code> `body 0.3` vs `122tr +26.9` `0.5` `99tr +4.2` `0.8` — strength filter cuts trades -20R.</p>}
          <p className="text-[#6e7681]">Switch Ver dropdown up top — chart trades + Strategy Summary update via <code>?version={version}</code> <code>GET /api/btc/backtest</code> &amp; <code>/summary</code>. Each version has its own file <code>backend/src/btc/engines/v*.py</code>, never disturbs <code>v1</code> (except 1h Flip now cap16). Log: <code>fix/btc_15m_trail_decisive_crazy_ideas.md</code> + <code>fix/btc_1h_flip_fixed_crazy_ideas.md</code></p>
        </div>
      </div>

    </div>
  );
}

