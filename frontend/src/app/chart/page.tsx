"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import StockChart, { type StockChartHandle } from "@/components/StockChart";
import { buildTimes, nearestSec } from "@/lib/chartSync";
import IntradayPanel from "@/components/IntradayPanel";
import type { SwingPoint } from "@/components/SwingSRPrimitive";
import { computeFlowLine, computeAlgoFlowLine, computeFsV2Results, type FlowSegment } from "@/lib/flowline";
import { computeEnvelopeViolations } from "@/lib/envelope";
import {
  Candle,
  Swing,
  BiasLabel,
  BacktestParams,
  DEFAULT_BT_PARAMS,
  IntradayBacktestResponse,
  getChartData,
  getSwings,
  getBias,
  getIntradayBacktest,
  FsDayMark,
  getFirstSwingManual,
  saveFirstSwingDay,
} from "@/lib/api";

const STORAGE_KEY = "chart_interval";
const INTERVAL_B_KEY = "chart_interval_b";
const LAYOUT_KEY = "chart_layout";
const BT_KEY = "intraday_bt_on";
const SWING_N_KEY = "chart_1min_swing_n";
const DOTS_KEY = "chart_hhll_dots";
const FLOW_KEY = "chart_flow_line";
const ENV_KEY = "chart_envelope_on";
const FS_KEY = "chart_first_swing_on";
const FS_REV_KEY = "chart_fs_rev_pct";
const FS_REV_DEFAULT = 10;
const SWING_N_DEFAULT = 12;

function clampSwingN(v: number): number {
  if (!Number.isFinite(v)) return SWING_N_DEFAULT;
  return Math.max(2, Math.min(60, Math.floor(v)));
}
const VALID_INTERVALS = ["daily", "5min", "1min"] as const;
type ChartInterval = (typeof VALID_INTERVALS)[number];

const INTERVAL_LABELS: Record<ChartInterval, string> = {
  daily: "Daily",
  "5min": "5-Min",
  "1min": "1-Min",
};

const SELECT_CLS =
  "rounded-md border border-[#30363d] bg-[#161b22] px-2 py-1 text-sm text-[#e6edf3] outline-none focus:border-[#6366f1]";

// 1-min history is large (~97k rows); load a recent window so the chart stays snappy
const ONE_MIN_LIMIT = 25000;

const PIVOT = 10;
const LEVELS = 5;
const LOOKAHEAD = 5;

function loadInterval(): ChartInterval {
  if (typeof window === "undefined") return "daily";
  const saved = window.localStorage.getItem(STORAGE_KEY);
  return saved === "daily" || saved === "5min" || saved === "1min" ? saved : "daily";
}

export default function ChartPage() {
  const [interval, setInterval] = useState<ChartInterval>("daily");
  const [data, setData] = useState<Candle[]>([]);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [swingOn, setSwingOn] = useState(true);
  const [swings, setSwings] = useState<Swing[]>([]);
  const [swingCount, setSwingCount] = useState(0);

  const [biasOn, setBiasOn] = useState(true);
  const [biasLabels, setBiasLabels] = useState<BiasLabel[]>([]);
  const [biasSummary, setBiasSummary] = useState<Record<string, number>>({});

  const [btOn, setBtOn] = useState(false);
  const [btData, setBtData] = useState<IntradayBacktestResponse | null>(null);
  const [btError, setBtError] = useState<string | null>(null);
  const [btParams, setBtParams] = useState<BacktestParams>(DEFAULT_BT_PARAMS);
  const [btCase, setBtCase] = useState<string>("all");
  const [swingN, setSwingN] = useState(SWING_N_DEFAULT);
  const [dotsOn, setDotsOn] = useState(true);
  const [flowOn, setFlowOn] = useState(true);
  const [envOn, setEnvOn] = useState(false);
  const [fsRevPct, setFsRevPct] = useState(FS_REV_DEFAULT);
  const [fsOn, setFsOn] = useState(false);
  const [fsDraw, setFsDraw] = useState(false);
  const [fsMarks, setFsMarks] = useState<Record<string, FsDayMark>>({});
  const [fsDrawStatus, setFsDrawStatus] = useState<string | null>(null);

  // dual-chart layout
  const [dual, setDual] = useState(false);
  const [intervalB, setIntervalB] = useState<ChartInterval>("5min");
  const [dataB, setDataB] = useState<Candle[]>([]);
  const [countB, setCountB] = useState(0);
  const [loadingB, setLoadingB] = useState(false);
  const [errorB, setErrorB] = useState<string | null>(null);
  const chartARef = useRef<StockChartHandle | null>(null);
  const chartBRef = useRef<StockChartHandle | null>(null);

  const btLoading = btOn && !btData && !btError;

  useEffect(() => {
    setInterval(loadInterval());
    if (typeof window !== "undefined") {
      setBtOn(window.localStorage.getItem(BT_KEY) === "1");
      const nRaw = window.localStorage.getItem(SWING_N_KEY);
      if (nRaw) setSwingN(clampSwingN(Number(nRaw)));
      setDotsOn(window.localStorage.getItem(DOTS_KEY) !== "0");
      setFlowOn(window.localStorage.getItem(FLOW_KEY) !== "0");
      setEnvOn(window.localStorage.getItem(ENV_KEY) === "1");
      setFsOn(window.localStorage.getItem(FS_KEY) === "1");
      const rvRaw = window.localStorage.getItem(FS_REV_KEY);
      if (rvRaw && Number.isFinite(Number(rvRaw))) setFsRevPct(Math.min(50, Math.max(1, Number(rvRaw))));
      setDual(window.localStorage.getItem(LAYOUT_KEY) === "2");
      const savedIvB = window.localStorage.getItem(INTERVAL_B_KEY);
      if (savedIvB === "daily" || savedIvB === "5min" || savedIvB === "1min") setIntervalB(savedIvB);
    }
  }, []);

  // load hand-drawn GT marks once (backend JSON file)
  useEffect(() => {
    let cancelled = false;
    getFirstSwingManual()
      .then((res) => {
        if (!cancelled) setFsMarks(res.days ?? {});
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  const changeSwingN = (v: number) => {
    const clamped = clampSwingN(v);
    setSwingN(clamped);
    window.localStorage.setItem(SWING_N_KEY, String(clamped));
  };

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    getChartData(interval, interval === "1min" ? ONE_MIN_LIMIT : undefined)
      .then((res) => {
        if (cancelled) return;
        setData(res.candles);
        setCount(res.count);
      })
      .catch((e) => {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : String(e));
        setData([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [interval]);

  // pane B candles (dual mode)
  useEffect(() => {
    let cancelled = false;
    setLoadingB(true);
    setErrorB(null);
    getChartData(intervalB, intervalB === "1min" ? ONE_MIN_LIMIT : undefined)
      .then((res) => {
        if (cancelled) return;
        setDataB(res.candles);
        setCountB(res.count);
      })
      .catch((e) => {
        if (cancelled) return;
        setErrorB(e instanceof Error ? e.message : String(e));
        setDataB([]);
      })
      .finally(() => {
        if (!cancelled) setLoadingB(false);
      });
    return () => {
      cancelled = true;
    };
  }, [intervalB]);

  useEffect(() => {
    let cancelled = false;
    getSwings("daily", PIVOT, LEVELS, LOOKAHEAD)
      .then((res) => {
        if (cancelled) return;
        setSwings(res.swings);
        setSwingCount(res.swings.length);
      })
      .catch(() => {
        if (cancelled) return;
        setSwings([]);
        setSwingCount(0);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    getBias()
      .then((res) => {
        if (cancelled) return;
        setBiasLabels(res.bias);
        setBiasSummary(res.summary);
      })
      .catch(() => {
        if (cancelled) return;
        setBiasLabels([]);
        setBiasSummary({});
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!btOn) return;
    let cancelled = false;
    getIntradayBacktest(btParams)
      .then((res) => {
        if (cancelled) return;
        setBtData(res);
      })
      .catch((e) => {
        if (cancelled) return;
        setBtError(e instanceof Error ? e.message : String(e));
      });
    return () => {
      cancelled = true;
    };
  }, [btOn, btParams]);

  const allTrades = useMemo(() => {
    if (!btOn || !btData) return undefined;
    return btData.days
      .filter((d) => btCase === "all" || d.case === btCase)
      .flatMap((d) =>
        d.trades
          .filter((t) => t.exit_ts != null)
          .map((t) => ({
            dir: t.dir,
            entryTs: t.entry_ts,
            exitTs: t.exit_ts as number,
            entryPrice: t.entry_price,
            slPrice: t.sl,
            targetPrice: t.target,
            outcome: t.outcome ?? "eod",
            rMultiple: t.r_multiple ?? 0,
          })),
      );
  }, [btOn, btData, btCase]);

  // Per-pane overlay bundle: computes every optional overlay for one pane's
  // interval/data so dual mode costs exactly two computations.
  const buildPaneOverlays = useCallback(
    (iv: ChartInterval, d: Candle[]) => {
      const isIntraday = iv !== "daily";

      // intraday swings are date-mapped projections of the daily pivots
      let dispSwings: SwingPoint[] | undefined;
      if (swingOn) {
        if (iv === "daily") {
          dispSwings = swings;
        } else {
          // map daily swing dates onto this pane's intraday candles
          const dates: string[] = [];
          const lastIdxByDate = new Map<string, number>();
          const maxHighIdx: Record<string, number> = {};
          const minLowIdx: Record<string, number> = {};
          d.forEach((c, i) => {
            const day = c.date.slice(0, 10);
            if (!lastIdxByDate.has(day)) dates.push(day);
            lastIdxByDate.set(day, i);
            const hi = maxHighIdx[day];
            const lo = minLowIdx[day];
            if (hi === undefined || c.high >= d[hi].high) maxHighIdx[day] = i;
            if (lo === undefined || c.low <= d[lo].low) minLowIdx[day] = i;
          });
          dispSwings = swings
            .map((s) => {
              const idx = s.kind === "high" ? maxHighIdx[s.date_only] : minLowIdx[s.date_only];
              if (idx === undefined) return null;
              const k = dates.indexOf(s.date_only);
              const endDate = k < 0 ? s.date_only : dates[Math.min(k + LOOKAHEAD, dates.length - 1)];
              const endIndex = lastIdxByDate.get(endDate) ?? idx;
              return {
                kind: s.kind,
                index: idx,
                price: s.price,
                end_index: endIndex,
              };
            })
            .filter((s): s is { kind: "high" | "low"; index: number; price: number; end_index: number } => s !== null);
        }
      }

      return {
        swings: dispSwings,
        bias: isIntraday && biasOn ? biasLabels : undefined,
        trades: isIntraday ? allTrades : undefined,
        sessionBreaks: isIntraday,
        flowLine: flowOn && isIntraday && d.length >= 2 ? computeFlowLine(d) : null,
        algoFlowLine: flowOn && isIntraday && d.length >= 2 ? computeAlgoFlowLine(d) : null,
        envelope: envOn && iv === "5min" && d.length >= 2 ? computeEnvelopeViolations(d) : null,
        ...(fsOn && iv === "1min" && d.length >= 2
          ? (() => {
              const res = computeFsV2Results(d, {
                zonePct: fsRevPct,
                simpleMode: true,
                armBars: 5,
                armRangePts: 20,
              });
              return {
                algoFirstSwing: res.map((r) => ({ ...r.seg, invalid: r.invalid })),
                fsMarkers: res.filter((r) => r.confIdx >= 0).map((r) => ({ idx: r.confIdx, invalid: r.invalid })),
              };
            })()
          : { algoFirstSwing: null as (FlowSegment & { invalid?: boolean })[] | null, fsMarkers: null as { idx: number; invalid: boolean }[] | null }),
        manualFirstSwing: isIntraday && fsOn ? fsMarks : null,
      };
    },
    [swings, swingOn, biasOn, biasLabels, allTrades, flowOn, envOn, fsOn, fsRevPct, fsMarks],
  );

  const overlaysA = useMemo(() => buildPaneOverlays(interval, data), [buildPaneOverlays, interval, data]);
  const overlaysB = useMemo(() => buildPaneOverlays(intervalB, dataB), [buildPaneOverlays, intervalB, dataB]);

  // ── crosshair sync between panes (dual mode) ──
  // Remote panes draw a silent vertical sync line via SyncCrosshairPrimitive
  // (not the real crosshair), so no echo events can loop back — direct wiring.
  const timesA = useMemo(() => buildTimes(data, interval !== "daily"), [data, interval]);
  const timesB = useMemo(() => buildTimes(dataB, intervalB !== "daily"), [dataB, intervalB]);

  const onHoverA = useCallback(
    (sec: number | null) => {
      if (!dual) return;
      const handle = chartBRef.current;
      if (!handle) return;
      const t = sec == null ? null : nearestSec(timesB, sec);
      if (t == null) handle.clearCrosshair();
      else handle.setCrosshairAt(t);
    },
    [dual, timesB],
  );

  const onHoverB = useCallback(
    (sec: number | null) => {
      if (!dual) return;
      const handle = chartARef.current;
      if (!handle) return;
      const t = sec == null ? null : nearestSec(timesA, sec);
      if (t == null) handle.clearCrosshair();
      else handle.setCrosshairAt(t);
    },
    [dual, timesA],
  );

  const changeFsRevPct = (v: number) => {
    const clamped = Number.isFinite(v) ? Math.min(50, Math.max(1, Math.round(v))) : FS_REV_DEFAULT;
    setFsRevPct(clamped);
    window.localStorage.setItem(FS_REV_KEY, String(clamped));
  };

  const handleSwingDraw = useCallback((mark: { day: string; start: FsDayMark["start"]; end: FsDayMark["end"] }) => {
    saveFirstSwingDay(mark.day, mark)
      .then(() => setFsMarks((prev) => ({ ...prev, [mark.day]: mark })))
      .catch((e) => setFsDrawStatus(e instanceof Error ? e.message : String(e)));
  }, []);

  const handleDrawStatus = useCallback((s: string | null) => setFsDrawStatus(s), []);



  const changeInterval = (iv: ChartInterval) => {
    window.localStorage.setItem(STORAGE_KEY, iv);
    setData([]);
    setInterval(iv);
  };

  const changeIntervalB = (iv: ChartInterval) => {
    window.localStorage.setItem(INTERVAL_B_KEY, iv);
    setDataB([]);
    setIntervalB(iv);
  };

  const changeLayout = (d: boolean) => {
    window.localStorage.setItem(LAYOUT_KEY, d ? "2" : "1");
    if (d) setFsDraw(false); // draw mode is single-chart only
    setDual(d);
  };

  const envCount =
    (overlaysA.envelope?.length ?? 0) + (dual ? overlaysB.envelope?.length ?? 0 : 0);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-[#e6edf3]">Nifty 50 Chart</h1>
          <p className="text-sm text-[#8b949e]">
            {loading ? "Loading..." : `${count} candles loaded`}
            {swingOn && swingCount > 0 ? ` Â· ${swingCount} swings (pivot ${PIVOT})` : ""}
            {interval !== "daily" && biasOn && biasSummary.bullish !== undefined
              ? ` Â· bias â–²${biasSummary.bullish ?? 0} â–¼${biasSummary.bearish ?? 0} â—${biasSummary.unbiased ?? 0}`
              : ""}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <div
            className="flex overflow-hidden rounded-md border border-[#30363d]"
            role="group"
            aria-label="Chart layout"
          >
            <button
              onClick={() => changeLayout(false)}
              className={`px-3 py-1.5 text-sm transition-colors ${
                !dual ? "bg-[#6366f1] text-white" : "bg-[#161b22] text-[#8b949e] hover:text-[#e6edf3]"
              }`}
              title="Single chart"
            >
              1 Chart
            </button>
            <button
              onClick={() => changeLayout(true)}
              className={`border-l border-[#30363d] px-3 py-1.5 text-sm transition-colors ${
                dual ? "bg-[#6366f1] text-white" : "bg-[#161b22] text-[#8b949e] hover:text-[#e6edf3]"
              }`}
              title="Two charts side by side (crosshair synced)"
            >
              2 Charts
            </button>
          </div>

          <button
            onClick={() => setSwingOn((v) => !v)}
            className={`flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm transition-colors ${
              swingOn
                ? "border-[#10b981] text-[#e6edf3]"
                : "border-[#30363d] text-[#8b949e]"
            }`}
          >
            <span
              className={`h-2 w-2 rounded-full ${swingOn ? "bg-[#10b981]" : "bg-[#8b949e]"}`}
            />
            Swing S/R
          </button>

          <button
            onClick={() => {
              setBiasOn((v) => !v);
            }}
            className={`flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm transition-colors ${
              biasOn && interval !== "daily"
                ? "border-[#f59e0b] text-[#e6edf3]"
                : "border-[#30363d] text-[#8b949e]"
            }`}
            title="Initial bias per day (pre-open, from previous-day close reads) â€” 5-min chart only"
          >
            <span
              className={`h-2 w-2 rounded-full ${biasOn ? "bg-[#f59e0b]" : "bg-[#8b949e]"}`}
            />
            Bias
          </button>

          <button
            onClick={() => {
              setDotsOn((v) => {
                window.localStorage.setItem(DOTS_KEY, v ? "0" : "1");
                return !v;
              });
            }}
            className={`flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm transition-colors ${
              dotsOn && interval !== "daily"
                ? "border-[#fb923c] text-[#e6edf3]"
                : "border-[#30363d] text-[#8b949e]"
            }`}
            title="HH/HL/LH/LL swing tags (5-min: prev-day pivots Â· 1-min: live fractals)"
          >
            <span
              className={`h-2 w-2 rounded-full ${dotsOn ? "bg-[#fb923c]" : "bg-[#8b949e]"}`}
            />
            HH/LL Tags
          </button>

          <button
            onClick={() => {
              setFlowOn((v) => {
                window.localStorage.setItem(FLOW_KEY, v ? "0" : "1");
                return !v;
              });
            }}
            className={`flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm transition-colors ${
              flowOn && interval !== "daily"
                ? "border-[#a78bfa] text-[#e6edf3]"
                : "border-[#30363d] text-[#8b949e]"
            }`}
            title="Trailing swing-structure line (live-safe, candle-by-candle)"
          >
            <span
              className={`h-2 w-2 rounded-full ${flowOn ? "bg-[#a78bfa]" : "bg-[#8b949e]"}`}
            />
            Flow Line
          </button>

          <button
            onClick={() => {
              setEnvOn((v) => {
                window.localStorage.setItem(ENV_KEY, v ? "0" : "1");
                return !v;
              });
            }}
            className={`flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm transition-colors ${
              envOn && interval === "5min"
                ? "border-[#ef4444] text-[#e6edf3]"
                : "border-[#30363d] text-[#8b949e]"
            }`}
            title="Envelope-law audit: red boxes on candles breaching the algo line's marked extremes (5-min chart only)"
          >
            <span
              className={`h-2 w-2 rounded-full ${envOn ? "bg-[#ef4444]" : "bg-[#8b949e]"}`}
            />
            Env{envOn && envCount > 0 ? ` (${envCount})` : ""}
          </button>

          <button
            onClick={() => {
              setFsOn((v) => {
                window.localStorage.setItem(FS_KEY, v ? "0" : "1");
                return !v;
              });
            }}
            className={`flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm transition-colors ${
              fsOn && (interval === "5min" || interval === "1min")
                ? "border-[#facc15] text-[#e6edf3]"
                : "border-[#30363d] text-[#8b949e]"
            }`}
            title="First Swing: your hand-drawn GT (thick yellow) vs flow-walker candidate (cyan)"
          >
            <span
              className={`h-2 w-2 rounded-full ${fsOn ? "bg-[#facc15]" : "bg-[#8b949e]"}`}
            />
            FS{interval === "5min" && Object.keys(fsMarks).length > 0
              ? ` (${Object.keys(fsMarks).length})`
              : ""}
          </button>

          {fsOn && (interval === "5min" || interval === "1min") && (
            <>
              <button
                onClick={() => setFsDraw((v) => !v)}
                disabled={dual}
                className={`flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm transition-colors ${
                  fsDraw && !dual
                    ? "border-[#facc15] bg-[#facc15]/10 text-[#e6edf3]"
                    : dual
                      ? "cursor-not-allowed border-[#30363d] text-[#8b949e] opacity-40"
                      : "border-[#30363d] text-[#8b949e]"
                }`}
                title={dual ? "Draw mode: single-chart layout only" : "Draw mode: click START candle then END candle on the chart \u2014 auto-saves"}
              >
                <span
                  className={`h-2 w-2 rounded-full ${fsDraw ? "bg-[#facc15]" : "bg-[#8b949e]"}`}
                />
                Draw
              </button>
              <div className="flex items-center gap-1.5">
                <span className="text-xs text-[#8b949e]">Rev %</span>
                <input
                  type="number"
                  min={1}
                  max={50}
                  value={fsRevPct}
                  onChange={(e) => changeFsRevPct(Number(e.target.value))}
                  className="w-14 rounded-md border border-[#30363d] bg-[#0d1117] px-2 py-1.5 text-sm text-[#e6edf3] outline-none focus:border-[#22d3ee]"
                  title="Reversal zone: price entering this deep-% of the session range flips direction (lock). Lower = stricter."
                />
              </div>
            </>
          )}

          <button
            onClick={() => {
              setBtOn((v) => {
                window.localStorage.setItem(BT_KEY, v ? "0" : "1");
                return !v;
              });
              setBtError(null);
            }}
            className={`flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm transition-colors ${
              btOn && interval !== "daily"
                ? "border-[#6366f1] text-[#e6edf3]"
                : "border-[#30363d] text-[#8b949e]"
            }`}
            title="Intraday backtest: simulated entries/exits per day (5-min chart only)"
          >
            <span
              className={`h-2 w-2 rounded-full ${btOn ? "bg-[#6366f1]" : "bg-[#8b949e]"}`}
            />
            Intraday BT
          </button>

          {interval === "1min" && (
            <div className="flex items-center gap-1.5">
              <span className="text-xs text-[#8b949e]">Swing n</span>
              <input
                type="number"
                min={2}
                max={60}
                value={swingN}
                onChange={(e) => changeSwingN(Number(e.target.value))}
                className="w-16 rounded-md border border-[#30363d] bg-[#0d1117] px-2 py-1.5 text-sm text-[#e6edf3] outline-none focus:border-[#22d3ee]"
                title="1-min swing pivot length (bars each side)"
              />
            </div>
          )}
        </div>
      </div>

      {error && (
        <div className="rounded-md border border-[#ef4444]/50 bg-[#ef4444]/10 px-4 py-3 text-sm text-[#ef4444]">
          Chart A: {error}
        </div>
      )}
      {fsDraw && !dual && (interval === "5min" || interval === "1min") && (
        <div className="flex items-center gap-2 rounded-md border border-[#facc15]/40 bg-[#facc15]/5 px-4 py-2 text-sm">
          <span className="text-[#facc15]">
            {fsDrawStatus ?? "Draw mode: click START candle, then END candle (same day). Auto-saves."}
          </span>
          <button
            onClick={() => setFsDraw(false)}
            className="ml-auto rounded border border-[#30363d] px-2 py-0.5 text-xs text-[#8b949e] hover:text-[#e6edf3]"
          >
            Done
          </button>
        </div>
      )}

      <div className={dual ? "flex items-start gap-3" : ""}>
        {/* Pane A */}
        <div className={dual ? "w-1/2 min-w-0" : "w-full"}>
          <div className="mb-1.5 flex items-center gap-2">
            <span className="text-xs font-bold tracking-wider text-[#6366f1]">A</span>
            <select
              value={interval}
              onChange={(e) => changeInterval(e.target.value as ChartInterval)}
              className={SELECT_CLS}
              title="Chart A timeframe"
            >
              {VALID_INTERVALS.map((iv) => (
                <option key={iv} value={iv}>{INTERVAL_LABELS[iv]}</option>
              ))}
            </select>
            <span className="text-xs text-[#8b949e]">
              {loading ? "Loading..." : `${count} candles`}
            </span>
          </div>
          <StockChart
            ref={chartARef}
            symbol="NIFTY 50"
            candles={data}
            intraday={interval !== "daily"}
            interval={interval}
            swings={overlaysA.swings}
            bias={overlaysA.bias}
            trades={overlaysA.trades}
            sessionBreaks={overlaysA.sessionBreaks}
            oneMinSwingN={swingN}
            swingDots={dotsOn}
            flowLine={overlaysA.flowLine}
            algoFlowLine={overlaysA.algoFlowLine}
            envelope={overlaysA.envelope}
            manualFirstSwing={overlaysA.manualFirstSwing}
            algoFirstSwing={overlaysA.algoFirstSwing}
            fsMarkers={overlaysA.fsMarkers}
            drawMode={fsDraw && !dual && (interval === "5min" || interval === "1min")}
            onSwingDraw={handleSwingDraw}
            onDrawStatus={handleDrawStatus}
            onHoverTime={onHoverA}
            height={dual ? 620 : 720}
          />
        </div>

        {/* Pane B (dual mode only) */}
        {dual && (
          <div className="w-1/2 min-w-0">
            {errorB && (
              <div className="mb-2 rounded-md border border-[#ef4444]/50 bg-[#ef4444]/10 px-3 py-2 text-xs text-[#ef4444]">
                Chart B: {errorB}
              </div>
            )}
            <div className="mb-1.5 flex items-center gap-2">
              <span className="text-xs font-bold tracking-wider text-[#22d3ee]">B</span>
              <select
                value={intervalB}
                onChange={(e) => changeIntervalB(e.target.value as ChartInterval)}
                className={SELECT_CLS}
                title="Chart B timeframe"
              >
                {VALID_INTERVALS.map((iv) => (
                  <option key={iv} value={iv}>{INTERVAL_LABELS[iv]}</option>
                ))}
              </select>
              <span className="text-xs text-[#8b949e]">
                {loadingB ? "Loading..." : `${countB} candles`}
              </span>
            </div>
            <StockChart
              ref={chartBRef}
              symbol="NIFTY 50"
              candles={dataB}
              intraday={intervalB !== "daily"}
              interval={intervalB}
              swings={overlaysB.swings}
              bias={overlaysB.bias}
              trades={overlaysB.trades}
              sessionBreaks={overlaysB.sessionBreaks}
              oneMinSwingN={swingN}
              swingDots={dotsOn}
              flowLine={overlaysB.flowLine}
              algoFlowLine={overlaysB.algoFlowLine}
              envelope={overlaysB.envelope}
              manualFirstSwing={overlaysB.manualFirstSwing}
              algoFirstSwing={overlaysB.algoFirstSwing}
            fsMarkers={overlaysB.fsMarkers}
              onHoverTime={onHoverB}
              height={620}
            />
          </div>
        )}
      </div>

      {btOn && (interval !== "daily" || (dual && intervalB !== "daily")) && (
        <IntradayPanel
          backtest={btData}
          loading={btLoading}
          error={btError}
          params={btParams}
          onParamsChange={(p) => {
            setBtParams(p);
            setBtData(null);
            setBtError(null);
          }}
          selectedCase={btCase}
          onCaseChange={(c) => setBtCase(c)}
        />
      )}
    </div>
  );
}

