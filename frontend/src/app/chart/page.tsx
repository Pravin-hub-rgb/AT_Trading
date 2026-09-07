"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import StockChart, { type StockChartHandle } from "@/components/StockChart";
import { buildTimes, nearestSec } from "@/lib/chartSync";
import IntradayPanel from "@/components/IntradayPanel";
import type { SwingPoint } from "@/components/SwingSRPrimitive";
import type { WholeDaySwingPoint } from "@/components/WholeDaySwingPrimitive";
import {
  computeAlgoFlowLine,
  type FlowSegment,
} from "@/lib/flowline";
import { computeEnvelopeViolations } from "@/lib/envelope";
import { computeEMA } from "@/lib/ema";
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
  getWholeDaySwings,
  postFirstSecond,
  type WholeDaySwing,
  type FirstSecondResponse,
} from "@/lib/api";

const STORAGE_KEY = "chart_interval";
const INTERVAL_B_KEY = "chart_interval_b";
const LAYOUT_KEY = "chart_layout";
const BT_KEY = "intraday_bt_on";
const SWING_N_KEY = "chart_1min_swing_n";
const ALL_SWINGS_KEY = "chart_all_swings";
const FLOW_KEY = "chart_flow_line";
const ENV_KEY = "chart_envelope_on";
const FS_KEY = "chart_first_swing_on";
const FS_REV_KEY = "chart_fs_rev_pct";
const FS_REV_DEFAULT = 15;
const SWING_N_DEFAULT = 3;
const HHLL_KEY = "chart_hhll_tags_on";

// localStorage key shared with IntradayPanel — restores saved filter config
const INTRADAY_FILTERS_KEY = "intraday_filters";

/** Load saved intraday backtest filters from localStorage. */
function loadSavedIntradayFilters(): { params: BacktestParams; case: string } {
  const defaults = { params: DEFAULT_BT_PARAMS, case: "all" };
  if (typeof window === "undefined") return defaults;
  try {
    const raw = window.localStorage.getItem(INTRADAY_FILTERS_KEY);
    if (!raw) return defaults;
    const saved = JSON.parse(raw) as Record<string, unknown>;
    const params: BacktestParams = {
      ...DEFAULT_BT_PARAMS,
      sl_mode:
        typeof saved.sl_mode === "string"
          ? saved.sl_mode
          : DEFAULT_BT_PARAMS.sl_mode,
      execution:
        typeof saved.execution === "string"
          ? saved.execution
          : DEFAULT_BT_PARAMS.execution,
      trailing:
        typeof saved.trailing === "string"
          ? saved.trailing
          : DEFAULT_BT_PARAMS.trailing,
      gap_pct:
        typeof saved.gap_pct === "string"
          ? saved.gap_pct
          : DEFAULT_BT_PARAMS.gap_pct,
      ft_fail_enabled:
        typeof saved.ft_fail_enabled === "boolean"
          ? saved.ft_fail_enabled
          : DEFAULT_BT_PARAMS.ft_fail_enabled,
      entry_method:
        typeof saved.entry_method === "string"
          ? saved.entry_method
          : (DEFAULT_BT_PARAMS.entry_method ?? "pivot_break"),
      rr_target:
        typeof saved.rr_target === "number"
          ? saved.rr_target
          : (DEFAULT_BT_PARAMS.rr_target ?? 3.0),
      swing_traverse:
        typeof saved.swing_traverse === "boolean"
          ? saved.swing_traverse
          : (DEFAULT_BT_PARAMS.swing_traverse ?? true),
      min_sl_pts:
        typeof saved.min_sl_pts === "number"
          ? saved.min_sl_pts
          : (DEFAULT_BT_PARAMS.min_sl_pts ?? 13.0),
      breakeven_r:
        typeof saved.breakeven_r === "number"
          ? saved.breakeven_r
          : ((DEFAULT_BT_PARAMS as any).breakeven_r ?? 1.0),
      need_opp_swing:
        typeof saved.need_opp_swing === "boolean"
          ? saved.need_opp_swing
          : ((DEFAULT_BT_PARAMS as any).need_opp_swing ?? true),
      max_entries:
        typeof saved.max_entries === "number"
          ? saved.max_entries
          : ((DEFAULT_BT_PARAMS as any).max_entries ?? 2),
      entry_cutoff:
        typeof saved.entry_cutoff === "string"
          ? saved.entry_cutoff
          : ((DEFAULT_BT_PARAMS as any).entry_cutoff ?? "15:15"),
      second_trade_after:
        typeof saved.second_trade_after === "string"
          ? saved.second_trade_after
          : ((DEFAULT_BT_PARAMS as any).second_trade_after ?? "sl_only"),
    };
    const caseValue =
      typeof saved.caseValue === "string" ? saved.caseValue : "all";
    return { params, case: caseValue };
  } catch {
    return defaults;
  }
}

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

const PIVOT = 10;
const LEVELS = 5;
const LOOKAHEAD = 5;

function loadInterval(): ChartInterval {
  if (typeof window === "undefined") return "daily";
  const saved = window.localStorage.getItem(STORAGE_KEY);
  return saved === "daily" || saved === "5min" || saved === "1min"
    ? saved
    : "daily";
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
  const [hhllOn, setHhllOn] = useState(false);
  const [biasLabels, setBiasLabels] = useState<BiasLabel[]>([]);
  const [biasSummary, setBiasSummary] = useState<Record<string, number>>({});

  const [btOn, setBtOn] = useState(false);
  const [btData, setBtData] = useState<IntradayBacktestResponse | null>(null);
  const [btError, setBtError] = useState<string | null>(null);
  const [btParams, setBtParams] = useState<BacktestParams>(DEFAULT_BT_PARAMS);
  const [btCase, setBtCase] = useState<string>("all");
  const [emaOn, setEmaOn] = useState(false);

  // Hydration-safe: load saved filters only on client after mount so server and
  // initial client HTML match (loadSavedIntradayFilters reads window.localStorage
  // which is missing on server and would otherwise cause hydration mismatch).
  useEffect(() => {
    const saved = loadSavedIntradayFilters();
    setBtParams(saved.params);
    setBtCase(saved.case);
    if (typeof window !== "undefined") {
      setEmaOn(window.localStorage.getItem("chart_ema_on") === "1");
    }
  }, []);
  const [swingN, setSwingN] = useState(SWING_N_DEFAULT);
  const [allSwings, setAllSwings] = useState(true);
  const [flowOn, setFlowOn] = useState(true);
  const [envOn, setEnvOn] = useState(false);
  const [fsRevPct, setFsRevPct] = useState(FS_REV_DEFAULT);
  const [fsOn, setFsOn] = useState(false);

  // 1-min candle data (fetched when fsOn is on, used for first-swing on 5min pane)
  const [data1min, setData1min] = useState<Candle[]>([]);

  // Daily and 5min data for correct EMA timeframe (for overlay on 1min)
  const [dailyEmaData, setDailyEmaData] = useState<Candle[]>([]);
  const [fiveMinEmaData, setFiveMinEmaData] = useState<Candle[]>([]);
  // Whole-day swings — fetched automatically for 1min chart (default ON)
  const [wholeDaySwings, setWholeDaySwings] = useState<WholeDaySwingPoint[]>(
    [],
  );
  // Pane B whole-day swings
  const [wholeDaySwingsB, setWholeDaySwingsB] = useState<WholeDaySwingPoint[]>(
    [],
  );

  // Single source of truth — Python engine via backend. Fetched first+second swing results.
  // Falls back to in-browser TS engine if backend unavailable.
  const [fsBackendA, setFsBackendA] = useState<import("@/lib/api").FirstSecondResponse | null>(null);
  const [fsBackendB, setFsBackendB] = useState<import("@/lib/api").FirstSecondResponse | null>(null);

  // dual-chart layout
  const [dual, setDual] = useState(false);
  const [intervalB, setIntervalB] = useState<ChartInterval>("5min");
  const [dataB, setDataB] = useState<Candle[]>([]);
  const [countB, setCountB] = useState(0);
  const [loadingB, setLoadingB] = useState(false);
  const [errorB, setErrorB] = useState<string | null>(null);
  const chartARef = useRef<StockChartHandle | null>(null);
  const chartBRef = useRef<StockChartHandle | null>(null);

  // Go-to-date: picked calendar date per pane + feedback when the exact date
  // has no candles (holiday/weekend) and the chart snaps to the nearest day.
  const [goDateA, setGoDateA] = useState("");
  const [goDateB, setGoDateB] = useState("");
  const [jumpInfoA, setJumpInfoA] = useState<string | null>(null);
  const [jumpInfoB, setJumpInfoB] = useState<string | null>(null);

  const btLoading = btOn && !btData && !btError;

  // Loaded candle date range per pane — clamps the calendar picker so an
  // out-of-range date can't even be picked.
  const minDateA = data.length ? data[0].date.slice(0, 10) : "";
  const maxDateA = data.length ? data[data.length - 1].date.slice(0, 10) : "";
  const minDateB = dataB.length ? dataB[0].date.slice(0, 10) : "";
  const maxDateB = dataB.length ? dataB[dataB.length - 1].date.slice(0, 10) : "";

  const goTo = (
    date: string,
    handle: StockChartHandle | null,
    setInfo: (v: string | null) => void,
  ) => {
    if (!date) return;
    const actual = handle?.goToDate(date) ?? null;
    if (!actual) return;
    // Silent on an exact hit; surface the snap when the picked day had no data.
    setInfo(
      actual === date
        ? null
        : `No data — nearest: ${new Date(`${actual}T00:00:00Z`)
            .toUTCString()
            .slice(5, 16)}`,
    );
  };

  useEffect(() => {
    setInterval(loadInterval());
    if (typeof window !== "undefined") {
      setBtOn(window.localStorage.getItem(BT_KEY) === "1");
      const nRaw = window.localStorage.getItem(SWING_N_KEY);
      if (nRaw) setSwingN(clampSwingN(Number(nRaw)));
      setAllSwings(window.localStorage.getItem(ALL_SWINGS_KEY) !== "0");
      setFlowOn(window.localStorage.getItem(FLOW_KEY) !== "0");
      setEnvOn(window.localStorage.getItem(ENV_KEY) === "1");
      setFsOn(window.localStorage.getItem(FS_KEY) === "1");
      const rvRaw = window.localStorage.getItem(FS_REV_KEY);
      if (rvRaw && Number.isFinite(Number(rvRaw)))
        setFsRevPct(Math.min(50, Math.max(1, Number(rvRaw))));
      setDual(window.localStorage.getItem(LAYOUT_KEY) === "2");
      const savedIvB = window.localStorage.getItem(INTERVAL_B_KEY);
      if (savedIvB === "daily" || savedIvB === "5min" || savedIvB === "1min")
        setIntervalB(savedIvB);
      setHhllOn(window.localStorage.getItem(HHLL_KEY) === "1");
    }
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
    getChartData(interval)
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
    getChartData(intervalB)
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

  // 1-min data for first-swing on 5min pane (dual mode: 1min pane A drives the FS display on pane B)
  useEffect(() => {
    if (!fsOn) {
      setData1min([]);
      return;
    }
    let cancelled = false;
    getChartData("1min")
      .then((res) => {
        if (cancelled) return;
        setData1min(res.candles);
      })
      .catch(() => {
        if (cancelled) return;
        setData1min([]);
      });
    return () => {
      cancelled = true;
    };
  }, [fsOn]);

  // Whole-day swings — fetched automatically when on 1min chart (default ON).
  // Returns all detected swings for the visible day range; rendered as a
  // cyan/yellow alternating zigzag line on top of the candles.
  useEffect(() => {
    if (interval !== "1min") {
      setWholeDaySwings([]);
      return;
    }
    let cancelled = false;
    const sc = allSwings ? "whole" : swingN;
    getWholeDaySwings("1min", 7, sc)
      .then((res) => {
        if (cancelled) return;
        const points: WholeDaySwingPoint[] = res.swings.map(
          (s: WholeDaySwing) => ({
            dir: s.seg.dir,
            start_idx: s.seg.start_idx,
            start_px: s.seg.start_px,
            end_idx: s.seg.end_idx,
            end_px: s.seg.end_px,
            swing_index: s.swing_index,
            kind: s.kind,
            break_kind: s.break_kind,
            breaks: s.breaks ?? [],
            confirmed_at_idx: s.confirmed_at_idx,
            confirmed_at_time: s.confirmed_at_time,
            fs_at_idx: s.fs_at_idx,
            fs_at_time: s.fs_at_time,
          }),
        );
        setWholeDaySwings(points);
      })
      .catch(() => {
        if (cancelled) return;
        setWholeDaySwings([]);
      });
    return () => {
      cancelled = true;
    };
  }, [interval, swingN, allSwings]);

  // Pane B whole-day swings — fetched when intervalB is 1min
  useEffect(() => {
    if (intervalB !== "1min") {
      setWholeDaySwingsB([]);
      return;
    }
    let cancelled = false;
    const sc = allSwings ? "whole" : swingN;
    getWholeDaySwings("1min", 7, sc)
      .then((res) => {
        if (cancelled) return;
        const points: WholeDaySwingPoint[] = res.swings.map(
          (s: WholeDaySwing) => ({
            dir: s.seg.dir,
            start_idx: s.seg.start_idx,
            start_px: s.seg.start_px,
            end_idx: s.seg.end_idx,
            end_px: s.seg.end_px,
            swing_index: s.swing_index,
            kind: s.kind,
            break_kind: s.break_kind,
            breaks: s.breaks ?? [],
            confirmed_at_idx: s.confirmed_at_idx,
            confirmed_at_time: s.confirmed_at_time,
            fs_at_idx: s.fs_at_idx,
            fs_at_time: s.fs_at_time,
          }),
        );
        setWholeDaySwingsB(points);
      })
      .catch(() => {
        if (cancelled) return;
        setWholeDaySwingsB([]);
      });
    return () => {
      cancelled = true;
    };
  }, [intervalB, swingN, allSwings]);

  // EMA data for correct timeframe overlay (daily EMA on 1min etc.)
  useEffect(() => {
    if (!emaOn) {
      setDailyEmaData([]);
      setFiveMinEmaData([]);
      return;
    }
    let cancelled = false;
    getChartData("daily")
      .then((res) => {
        if (cancelled) return;
        setDailyEmaData(res.candles);
      })
      .catch(() => {
        if (cancelled) return;
        setDailyEmaData([]);
      });
    getChartData("5min")
      .then((res) => {
        if (cancelled) return;
        setFiveMinEmaData(res.candles);
      })
      .catch(() => {
        if (cancelled) return;
        setFiveMinEmaData([]);
      });
    return () => {
      cancelled = true;
    };
  }, [emaOn]);

  // Single source of truth — Python engine via backend for first/second swings.
  // Falls back to in-browser TS engine if backend unavailable.
  useEffect(() => {
    if (!fsOn || (interval !== "1min" && interval !== "5min")) {
      setFsBackendA(null);
      return;
    }
    const sourceCandles: Candle[] = interval === "1min" ? data : data1min;
    if (sourceCandles.length < 2) {
      setFsBackendA(null);
      return;
    }
    let cancelled = false;
    const payload = sourceCandles.map((c) => ({
      date: c.date,
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close,
    }));
    postFirstSecond(payload, { timeCap: "09:29" }, true)
      .then((res) => {
        if (cancelled) return;
        setFsBackendA(res);
      })
      .catch(() => {
        if (cancelled) return;
        setFsBackendA(null);
      });
    return () => {
      cancelled = true;
    };
  }, [fsOn, interval, data, data1min]);

  useEffect(() => {
    if (!fsOn || (intervalB !== "1min" && intervalB !== "5min")) {
      setFsBackendB(null);
      return;
    }
    const sourceCandlesB: Candle[] = intervalB === "1min" ? dataB : data1min;
    if (sourceCandlesB.length < 2) {
      setFsBackendB(null);
      return;
    }
    let cancelled = false;
    const payloadB = sourceCandlesB.map((c) => ({
      date: c.date,
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close,
    }));
    postFirstSecond(payloadB, { timeCap: "09:29" }, true)
      .then((res) => {
        if (cancelled) return;
        setFsBackendB(res);
      })
      .catch(() => {
        if (cancelled) return;
        setFsBackendB(null);
      });
    return () => {
      cancelled = true;
    };
  }, [fsOn, intervalB, dataB, data1min]);

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
    getBias(undefined, (btParams as any).bias_mode ?? "daily_swing")
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
  }, [(btParams as any).bias_mode]);

  // Auto EMA for ema modes
  useEffect(() => {
    const bm = (btParams as any).bias_mode ?? "daily_swing";
    if (bm.startsWith("ema")) {
      setEmaOn(true);
      window.localStorage.setItem("chart_ema_on", "1");
    }
  }, [(btParams as any).bias_mode]);

  // Load intraday backtest whenever we're in intraday mode (so the chart
  // overlay can show trade_mode / case without forcing the user to enable
  // the BT panel). The BT panel just toggles display + heavier work on top
  // of this always-on cache.
  useEffect(() => {
    if (interval === "daily" && (!dual || intervalB === "daily")) {
      return;
    }
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
  }, [btParams, interval, dual, intervalB]);
  // Keep btOn on the dependency chain so toggling BT also refreshes the
  // backtest parameters (separate from the always-on initial load).
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
            exitPrice: t.exit_price ?? t.target,
            outcome: t.outcome ?? "eod",
            rMultiple: t.r_multiple ?? 0,
          })),
      );
  }, [btOn, btData, btCase]);

  // Per-pane overlay bundle: computes every optional overlay for one pane's
  // interval/data so dual mode costs exactly two computations.
  // Now uses Python backend as single source of truth via /api/swings/first_second.
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
              const idx =
                s.kind === "high"
                  ? maxHighIdx[s.date_only]
                  : minLowIdx[s.date_only];
              if (idx === undefined) return null;
              const k = dates.indexOf(s.date_only);
              const endDate =
                k < 0
                  ? s.date_only
                  : dates[Math.min(k + LOOKAHEAD, dates.length - 1)];
              const endIndex = lastIdxByDate.get(endDate) ?? idx;
              return {
                kind: s.kind,
                index: idx,
                price: s.price,
                end_index: endIndex,
              };
            })
            .filter(
              (
                s,
              ): s is {
                kind: "high" | "low";
                index: number;
                price: number;
                end_index: number;
              } => s !== null,
            );
        }
      }

      return {
        swings: dispSwings,
        bias: isIntraday && biasOn ? biasLabels : undefined,
        hhllBias: isIntraday && hhllOn ? biasLabels : undefined,
        trades: isIntraday ? allTrades : undefined,
        sessionBreaks: isIntraday,
        algoFlowLine:
          flowOn && isIntraday && d.length >= 2 ? computeAlgoFlowLine(d) : null,
        envelope:
          envOn && iv === "5min" && d.length >= 2
            ? computeEnvelopeViolations(d)
            : null,
        ...(fsOn && (iv === "1min" || iv === "5min") && d.length >= 2
          ? (() => {
              // 1min pane: run FsV2 directly on its own candles.
              // 5min pane: run FsV2 on 1min candles (source of truth) and
              // project startIdx/confIdx/breaks onto the 5min candles by
              // matching each 1min timestamp to the containing 5min bar.
              const sourceCandles: Candle[] = iv === "1min" ? d : data1min;
              if (sourceCandles.length < 2) {
                return {
                  algoFirstSwing: null,
                  fsMarkers: null,
                  fsBreaks: null,
                  tradeMode: btData
                    ? Object.fromEntries(
                        btData.days.map((d) => [d.date, d.trade_mode ?? null]),
                      )
                    : undefined,
                };
              }
              // Per-swing filter: engine may emit multiple B1s (pre-confirm re-locks)
              // or multiple FLIPs (whipsaw like FLIP@10:16 + FLIP@10:17) — keep
              // only the first B1 + the last decisive break (last non-B1) per swing.
              // FlatMap-then-filter globally would drop B1s for later days — must filter per result.
              const filterBreaksPerSwing = (breaks: any[]): any[] => {
                if (breaks.length <= 1) return breaks;
                const first = breaks.find((b: any) => b.kind === "B1") ?? breaks[0];
                const nonB1 = breaks.filter((b: any) => b.kind !== "B1");
                if (nonB1.length === 0) return [first];
                const last = nonB1[nonB1.length - 1];
                // A B2 that got flip-cancelled still happened and must stay
                // visible (1 Sep 2026: B2@11:25 swallowed by FLIP@11:28).
                const lastFlip = [...nonB1].reverse().find((b: any) => b.kind === "FLIP");
                const lastB2 = [...nonB1].reverse().find((b: any) => b.kind === "B2");
                const out: any[] = [first];
                // Fake-out FLIP before the confirming B2 still happened - keep it
                // visible (1 Sep 2026 swing 6: B1@11:55 -> FLIP@12:01 -> B2@12:05).
                if (lastFlip && lastFlip !== last && lastFlip !== first) out.push(lastFlip);
                if (lastB2 && lastB2 !== last && lastB2 !== first) out.push(lastB2);
                out.push(last);
                return out;
              };
              // Single source of truth: Python backend if available, else fallback to TS engine
              const backendRes =
                d === data ? fsBackendA : d === dataB ? fsBackendB : null;
              const hasBackend = !!(
                backendRes && Array.isArray((backendRes as any).first)
              );
              let valid: any[] = [];
              let ss2Valid: any[] = [];
              if (hasBackend) {
                const mapR = (r: any) => ({
                  ...r,
                  confIdx: r.conf_idx ?? r.confIdx,
                  seg: r.seg
                    ? {
                        ...r.seg,
                        startIdx: r.seg.start_idx ?? r.seg.startIdx,
                        startPx: r.seg.start_px ?? r.seg.startPx,
                        endIdx: r.seg.end_idx ?? r.seg.endIdx,
                        endPx: r.seg.end_px ?? r.seg.endPx,
                      }
                    : null,
                  breaks: r.breaks ?? [],
                  source: r.source,
                  dir: r.dir,
                  day: r.day,
                  outcome: r.outcome,
                });
                valid = (backendRes as any).first
                  .map(mapR)
                  .filter((r: any) => r.seg !== null && r.confIdx >= 0);
                ss2Valid = (backendRes as any).second
                  .map(mapR)
                  .filter((r: any) => r.seg !== null && r.confIdx >= 0);
              } else {
                valid = [];
                ss2Valid = [];
              }
              if (iv === "1min") {
                return {
                  algoFirstSwing: valid.map((r) => r.seg!),
                  algoSecondSwing: ss2Valid.map((r) => r.seg!),
                  fsMarkers: valid.map((r) => ({
                    idx: r.confIdx,
                    invalid: false,
                    source: r.source,
                    dir: r.dir,
                  })),
                  fsBreaks: valid.flatMap((r) =>
                    filterBreaksPerSwing(r.breaks ?? []),
                  ),
                  algoSecondSwingMarkers: ss2Valid.map((r) => ({
                    idx: r.confIdx,
                    invalid: false,
                    source: r.source,
                    dir: r.dir,
                  })),
                  algoSecondSwingBreaks: ss2Valid.flatMap((r) =>
                    filterBreaksPerSwing(r.breaks ?? []),
                  ),
                  tradeMode: btData
                    ? Object.fromEntries(
                        btData.days.map((d) => [d.date, d.trade_mode ?? null]),
                      )
                    : undefined,
                };
              }
              // 5min: project each 1min index onto the 5min bar that
              // contains its timestamp. d are the 5min candles of THIS pane.
              const min5: Candle[] = d;
              // build a fast lookup: for each 5min candle, store [open_ts, close_ts]
              const m5IndexByTs = new Map<number, number>();
              const m5Ranges: {
                openTs: number;
                closeTs: number;
                idx: number;
              }[] = [];
              min5.forEach((c5, i5) => {
                const openTs = Math.floor(new Date(c5.date).getTime() / 1000);
                const closeTs = openTs + 5 * 60;
                m5IndexByTs.set(openTs, i5);
                m5Ranges.push({ openTs, closeTs, idx: i5 });
              });
              const find5minIdx = (ts: number): number => {
                // binary search by openTs
                let lo = 0,
                  hi = m5Ranges.length - 1;
                while (lo <= hi) {
                  const mid = (lo + hi) >> 1;
                  if (m5Ranges[mid].openTs === ts) return m5Ranges[mid].idx;
                  if (m5Ranges[mid].openTs < ts) lo = mid + 1;
                  else hi = mid - 1;
                }
                // ts is between two 5min bars; pick the one whose range contains it
                const i = Math.min(lo, m5Ranges.length - 1);
                for (
                  let k = Math.max(0, i - 1);
                  k <= Math.min(m5Ranges.length - 1, i + 1);
                  k++
                ) {
                  const r = m5Ranges[k];
                  if (ts >= r.openTs && ts < r.closeTs) return r.idx;
                }
                return -1;
              };
              const algoFirstSwing5 = valid
                .map((r) => {
                  const sIdx = find5minIdx(
                    Math.floor(
                      new Date(sourceCandles[r.seg!.startIdx].date).getTime() /
                        1000,
                    ),
                  );
                  const eIdx = find5minIdx(
                    Math.floor(
                      new Date(sourceCandles[r.seg!.endIdx].date).getTime() /
                        1000,
                    ),
                  );
                  if (sIdx < 0 || eIdx < 0) return null;
                  return { ...r.seg!, startIdx: sIdx, endIdx: eIdx };
                })
                .filter((s): s is FlowSegment => s !== null);
              const fsMarkers5 = valid
                .map((r) => {
                  const cIdx = find5minIdx(
                    Math.floor(
                      new Date(sourceCandles[r.confIdx].date).getTime() / 1000,
                    ),
                  );
                  if (cIdx < 0) return null;
                  return {
                    idx: cIdx,
                    invalid: false,
                    source: r.source,
                    dir: r.dir,
                  };
                })
                .filter(
                  (
                    m,
                  ): m is {
                    idx: number;
                    invalid: boolean;
                    source: "chop" | "sustain" | null;
                    dir: "up" | "down" | null;
                  } => m !== null,
                );
              const fsBreaks5 = valid
                .flatMap((r) => filterBreaksPerSwing(r.breaks ?? []))
                .map((b) => {
                  const bIdx = find5minIdx(
                    Math.floor(
                      new Date(sourceCandles[b.idx].date).getTime() / 1000,
                    ),
                  );
                  return bIdx < 0 ? null : { ...b, idx: bIdx };
                })
                .filter(
                  (
                    b,
                  ): b is {
                    idx: number;
                    time: string;
                    kind: "B1" | "B2" | "FLIP";
                    dir: "up" | "down";
                    px: number;
                  } => b !== null,
                );
              // Second swing projected onto 5min indices (reuse ss2Valid already computed above)
              const algoSecondSwing5 = ss2Valid
                .map((r) => {
                  const sIdx = find5minIdx(
                    Math.floor(
                      new Date(sourceCandles[r.seg!.startIdx].date).getTime() /
                        1000,
                    ),
                  );
                  const eIdx = find5minIdx(
                    Math.floor(
                      new Date(sourceCandles[r.seg!.endIdx].date).getTime() /
                        1000,
                    ),
                  );
                  if (sIdx < 0 || eIdx < 0) return null;
                  return { ...r.seg!, startIdx: sIdx, endIdx: eIdx };
                })
                .filter((s): s is FlowSegment => s !== null);
              // Second-swing markers projected onto 5min
              const algoSecondSwingMarkers5 = ss2Valid
                .map((r) => {
                  const cIdx = find5minIdx(
                    Math.floor(
                      new Date(sourceCandles[r.confIdx].date).getTime() / 1000,
                    ),
                  );
                  if (cIdx < 0) return null;
                  return {
                    idx: cIdx,
                    invalid: false,
                    source: r.source,
                    dir: r.dir,
                  };
                })
                .filter(
                  (
                    m,
                  ): m is {
                    idx: number;
                    invalid: boolean;
                    source: "chop" | "sustain" | null;
                    dir: "up" | "down" | null;
                  } => m !== null,
                );
              const algoSecondSwingBreaks5 = ss2Valid
                .flatMap((r) => filterBreaksPerSwing(r.breaks ?? []))
                .map((b) => {
                  const bIdx = find5minIdx(
                    Math.floor(
                      new Date(sourceCandles[b.idx].date).getTime() / 1000,
                    ),
                  );
                  return bIdx < 0 ? null : { ...b, idx: bIdx };
                })
                .filter(
                  (
                    b,
                  ): b is {
                    idx: number;
                    time: string;
                    kind: "B1" | "B2" | "FLIP";
                    dir: "up" | "down";
                    px: number;
                  } => b !== null,
                );
              // 5-min: only swing lines, no markers (per your call — markers only on 1-min)
              return {
                algoFirstSwing: algoFirstSwing5,
                algoSecondSwing: algoSecondSwing5,
                fsMarkers: null,
                fsBreaks: null,
                algoSecondSwingMarkers: null,
                algoSecondSwingBreaks: null,
                tradeMode: btData
                  ? Object.fromEntries(
                      btData.days.map((d) => [d.date, d.trade_mode ?? null]),
                    )
                  : undefined,
              };
            })()
          : {
              algoFirstSwing: null as
                | (FlowSegment & { invalid?: boolean })[]
                | null,
              algoSecondSwing: null as
                | (FlowSegment & { fs1Dir?: "up" | "down" | null })[]
                | null,
              fsMarkers: null as
                | {
                    idx: number;
                    invalid: boolean;
                    source: "chop" | "sustain" | null;
                    dir: "up" | "down" | null;
                  }[]
                | null,
              fsBreaks: null as
                | {
                    idx: number;
                    time: string;
                    kind: "B1" | "B2" | "FLIP";
                    dir: "up" | "down";
                    px: number;
                  }[]
                | null,
              algoSecondSwingMarkers: null as
                | {
                    idx: number;
                    invalid: boolean;
                    source: "chop" | "sustain" | null;
                    dir: "up" | "down" | null;
                  }[]
                | null,
              algoSecondSwingBreaks: null as
                | {
                    idx: number;
                    time: string;
                    kind: "B1" | "B2" | "FLIP";
                    dir: "up" | "down";
                    px: number;
                  }[]
                | null,
              tradeMode: btData
                ? Object.fromEntries(
                    btData.days.map((d) => [d.date, d.trade_mode ?? null]),
                  )
                : undefined,
            }),
      };
    },
    [
      swings,
      swingOn,
      biasOn,
      hhllOn,
      biasLabels,
      allTrades,
      flowOn,
      envOn,
      fsOn,
      fsRevPct,
      data,
      dataB,
      data1min,
      btData,
      fsBackendA,
      fsBackendB,
    ],
  );

  const overlaysA = useMemo(
    () => buildPaneOverlays(interval, data),
    [buildPaneOverlays, interval, data],
  );
  const overlaysB = useMemo(
    () => buildPaneOverlays(intervalB, dataB),
    [buildPaneOverlays, intervalB, dataB],
  );

  // ── EMA lines (toggleable) — timeframe-correct: daily EMA on 1min uses daily data, not 1min 10-period
  const emaLinesA = useMemo(() => {
    if (!emaOn) return null;
    const biasMode = (btParams as any).bias_mode ?? "daily_swing";
    if (!biasMode.startsWith("ema")) return null;
    // Daily EMA modes (including far and inverse): ema_daily_10, ema_daily_10_far_50, ema_daily_10_inverse, etc.
    if (biasMode.startsWith("ema_daily")) {
      const span = biasMode.includes("ema_daily_5") ? 5 : 10;
      if (interval === "daily") {
        if (data.length < span) return null;
        return { [span]: computeEMA(data, span) } as Record<number, ReturnType<typeof computeEMA>>;
      }
      if (dailyEmaData.length < span) return null;
      const dailyEma = computeEMA(dailyEmaData, span);
      const dailyByDate = new Map<string, number>();
      dailyEmaData.forEach((c, idx) => {
        const emaVal = dailyEma[idx]?.value;
        if (emaVal !== undefined) dailyByDate.set(c.date.slice(0, 10), emaVal);
      });
      const points: ReturnType<typeof computeEMA> = [];
      let lastVal: number | null = null;
      data.forEach((c, idx) => {
        const d = c.date.slice(0, 10);
        if (dailyByDate.has(d)) lastVal = dailyByDate.get(d)!;
        if (lastVal !== null) points.push({ idx, value: lastVal });
      });
      return points.length ? ({ [span]: points } as Record<number, ReturnType<typeof computeEMA>>) : null;
    }
    if (biasMode.startsWith("ema_5min")) {
      if (interval === "5min") {
        if (data.length < 50) return null;
        return { 20: computeEMA(data, 20), 50: computeEMA(data, 50) } as Record<number, ReturnType<typeof computeEMA>>;
      }
      if (interval === "1min") {
        if (fiveMinEmaData.length < 50) return null;
        const ema20 = computeEMA(fiveMinEmaData, 20);
        const ema50 = computeEMA(fiveMinEmaData, 50);
        const fiveByTs = new Map<number, { e20: number; e50: number }>();
        fiveMinEmaData.forEach((c, idx) => {
          const e20 = ema20[idx]?.value;
          const e50 = ema50[idx]?.value;
          if (e20 !== undefined && e50 !== undefined) fiveByTs.set(c.ts, { e20, e50 });
        });
        const sortedFiveTs = Array.from(fiveByTs.keys()).sort((a, b) => a - b);
        const points20: ReturnType<typeof computeEMA> = [];
        const points50: ReturnType<typeof computeEMA> = [];
        let ptr = 0;
        let last20: number | null = null;
        let last50: number | null = null;
        data.forEach((c, idx) => {
          while (ptr < sortedFiveTs.length && sortedFiveTs[ptr] <= c.ts) {
            const v = fiveByTs.get(sortedFiveTs[ptr])!;
            last20 = v.e20;
            last50 = v.e50;
            ptr++;
          }
          if (last20 !== null) points20.push({ idx, value: last20 });
          if (last50 !== null) points50.push({ idx, value: last50 });
        });
        return points20.length ? ({ 20: points20, 50: points50 } as Record<number, ReturnType<typeof computeEMA>>) : null;
      }
      return null;
    }
    if (biasMode.startsWith("ema_1min")) {
      const span = biasMode.includes("ema_1min_5") ? 5 : 10;
      if (data.length < span) return null;
      return { [span]: computeEMA(data, span) } as Record<number, ReturnType<typeof computeEMA>>;
    }
    if (data.length < 10) return null;
    return { 10: computeEMA(data, 10) } as Record<number, ReturnType<typeof computeEMA>>;
  }, [emaOn, data, interval, dailyEmaData, fiveMinEmaData, (btParams as any).bias_mode]);

  const emaLinesB = useMemo(() => {
    if (!emaOn) return null;
    const biasMode = (btParams as any).bias_mode ?? "daily_swing";
    if (!biasMode.startsWith("ema")) return null;
    if (biasMode.startsWith("ema_daily")) {
      const span = biasMode.includes("ema_daily_5") ? 5 : 10;
      if (intervalB === "daily") {
        if (dataB.length < span) return null;
        return { [span]: computeEMA(dataB, span) } as Record<number, ReturnType<typeof computeEMA>>;
      }
      if (dailyEmaData.length < span) return null;
      const dailyEma = computeEMA(dailyEmaData, span);
      const dailyByDate = new Map<string, number>();
      dailyEmaData.forEach((c, idx) => {
        const emaVal = dailyEma[idx]?.value;
        if (emaVal !== undefined) dailyByDate.set(c.date.slice(0, 10), emaVal);
      });
      const points: ReturnType<typeof computeEMA> = [];
      let lastVal: number | null = null;
      dataB.forEach((c, idx) => {
        const d = c.date.slice(0, 10);
        if (dailyByDate.has(d)) lastVal = dailyByDate.get(d)!;
        if (lastVal !== null) points.push({ idx, value: lastVal });
      });
      return points.length ? ({ [span]: points } as Record<number, ReturnType<typeof computeEMA>>) : null;
    }
    if (biasMode.startsWith("ema_5min")) {
      if (intervalB === "5min") {
        if (dataB.length < 50) return null;
        return { 20: computeEMA(dataB, 20), 50: computeEMA(dataB, 50) } as Record<number, ReturnType<typeof computeEMA>>;
      }
      if (intervalB === "1min") {
        if (fiveMinEmaData.length < 50) return null;
        const ema20 = computeEMA(fiveMinEmaData, 20);
        const ema50 = computeEMA(fiveMinEmaData, 50);
        const fiveByTs = new Map<number, { e20: number; e50: number }>();
        fiveMinEmaData.forEach((c, idx) => {
          const e20 = ema20[idx]?.value;
          const e50 = ema50[idx]?.value;
          if (e20 !== undefined && e50 !== undefined) fiveByTs.set(c.ts, { e20, e50 });
        });
        const sortedFiveTs = Array.from(fiveByTs.keys()).sort((a, b) => a - b);
        const points20: ReturnType<typeof computeEMA> = [];
        const points50: ReturnType<typeof computeEMA> = [];
        let ptr = 0;
        let last20: number | null = null;
        let last50: number | null = null;
        dataB.forEach((c, idx) => {
          while (ptr < sortedFiveTs.length && sortedFiveTs[ptr] <= c.ts) {
            const v = fiveByTs.get(sortedFiveTs[ptr])!;
            last20 = v.e20;
            last50 = v.e50;
            ptr++;
          }
          if (last20 !== null) points20.push({ idx, value: last20 });
          if (last50 !== null) points50.push({ idx, value: last50 });
        });
        return points20.length ? ({ 20: points20, 50: points50 } as Record<number, ReturnType<typeof computeEMA>>) : null;
      }
      return null;
    }
    if (biasMode.startsWith("ema_1min")) {
      const span = biasMode.includes("ema_1min_5") ? 5 : 10;
      if (dataB.length < span) return null;
      return { [span]: computeEMA(dataB, span) } as Record<number, ReturnType<typeof computeEMA>>;
    }
    if (dataB.length < 10) return null;
    return { 10: computeEMA(dataB, 10) } as Record<number, ReturnType<typeof computeEMA>>;
  }, [emaOn, dataB, intervalB, dailyEmaData, fiveMinEmaData, (btParams as any).bias_mode]);

  // ── crosshair sync between panes (dual mode) ──
  // Remote panes draw a silent vertical sync line via SyncCrosshairPrimitive
  // (not the real crosshair), so no echo events can loop back — direct wiring.
  const timesA = useMemo(
    () => buildTimes(data, interval !== "daily"),
    [data, interval],
  );
  const timesB = useMemo(
    () => buildTimes(dataB, intervalB !== "daily"),
    [dataB, intervalB],
  );

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
    const clamped = Number.isFinite(v)
      ? Math.min(50, Math.max(1, Math.round(v)))
      : FS_REV_DEFAULT;
    setFsRevPct(clamped);
    window.localStorage.setItem(FS_REV_KEY, String(clamped));
  };

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
    setDual(d);
  };

  const envCount =
    (overlaysA.envelope?.length ?? 0) +
    (dual ? (overlaysB.envelope?.length ?? 0) : 0);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-[#e6edf3]">
            Nifty 50 Chart
          </h1>
          <p className="text-sm text-[#8b949e]">
            {loading ? "Loading..." : `${count} candles loaded`}
            {swingOn && swingCount > 0
              ? ` Â· ${swingCount} swings (pivot ${PIVOT})`
              : ""}
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
                !dual
                  ? "bg-[#6366f1] text-white"
                  : "bg-[#161b22] text-[#8b949e] hover:text-[#e6edf3]"
              }`}
              title="Single chart"
            >
              1 Chart
            </button>
            <button
              onClick={() => changeLayout(true)}
              className={`border-l border-[#30363d] px-3 py-1.5 text-sm transition-colors ${
                dual
                  ? "bg-[#6366f1] text-white"
                  : "bg-[#161b22] text-[#8b949e] hover:text-[#e6edf3]"
              }`}
              title="Two charts side by side (crosshair synced)"
            >
              2 Charts
            </button>
          </div>

          <button
            onClick={() => {
              setEmaOn((v) => {
                const nv = !v;
                window.localStorage.setItem("chart_ema_on", nv ? "1" : "0");
                return nv;
              });
            }}
            className={`flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm transition-colors ${
              emaOn ? "border-[#f59e0b] text-[#e6edf3]" : "border-[#30363d] text-[#8b949e]"
            }`}
            title="EMA lines — toggleable, only shows selected bias's EMA (clean)"
          >
            <span className={`h-2 w-2 rounded-full ${emaOn ? "bg-[#f59e0b]" : "bg-[#8b949e]"}`} />
            EMA
          </button>
          {emaOn && (
            <span className="flex items-center gap-2 text-xs text-[#8b949e]">
              {((btParams as any).bias_mode === "ema_daily_10" || (btParams as any).bias_mode === "ema_daily_10_far_50") && (
                <>
                  <span className="h-2 w-4 rounded" style={{ background: "#10b981" }} /> EMA10
                  {(btParams as any).bias_mode.includes("far") && <span className="text-[10px]">FAR 50</span>}
                </>
              )}
              {((btParams as any).bias_mode === "ema_daily_5" || (btParams as any).bias_mode === "ema_daily_5_far_50") && (
                <>
                  <span className="h-2 w-4 rounded" style={{ background: "#f59e0b" }} /> EMA5
                  {(btParams as any).bias_mode.includes("far") && <span className="text-[10px]">FAR 50</span>}
                </>
              )}
              {((btParams as any).bias_mode === "ema_5min_20_50" || (btParams as any).bias_mode === "ema_5min_20_50_far_30") && (
                <>
                  <span className="h-2 w-4 rounded" style={{ background: "#60a5fa" }} /> EMA20{" "}
                  <span className="h-2 w-4 rounded" style={{ background: "#a78bfa" }} /> EMA50
                  {(btParams as any).bias_mode.includes("far") && <span className="text-[10px]">FAR 30</span>}
                </>
              )}
              {((btParams as any).bias_mode === "ema_1min_5_far_20") && (
                <>
                  <span className="h-2 w-4 rounded" style={{ background: "#f59e0b" }} /> EMA5 (1min) FAR20
                </>
              )}
              {((btParams as any).bias_mode === "ema_1min_10_far_30") && (
                <>
                  <span className="h-2 w-4 rounded" style={{ background: "#10b981" }} /> EMA10 (1min) FAR30
                </>
              )}
              {!(btParams as any).bias_mode?.startsWith("ema") && <span className="text-[10px]">EMA (no EMA bias selected)</span>}
            </span>
          )}

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
            title="Initial bias per day (pre-open, from previous-day close reads) — arrow only, HH/LL hidden"
          >
            <span
              className={`h-2 w-2 rounded-full ${biasOn ? "bg-[#f59e0b]" : "bg-[#8b949e]"}`}
            />
            Bias
          </button>

          <button
            onClick={() => {
              setHhllOn((v) => {
                window.localStorage.setItem(HHLL_KEY, v ? "0" : "1");
                return !v;
              });
            }}
            className={`flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm transition-colors ${
              hhllOn && interval === "5min"
                ? "border-[#f97316] text-[#e6edf3]"
                : "border-[#30363d] text-[#8b949e]"
            }`}
            title="Prev-day HH/HL/LH/LL swing tags from bias structure (5-min chart only, detached from Bias arrow)"
          >
            <span
              className={`h-2 w-2 rounded-full ${hhllOn ? "bg-[#f97316]" : "bg-[#8b949e]"}`}
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
            title="First Swing: flow-walker candidate (cyan)"
          >
            <span
              className={`h-2 w-2 rounded-full ${fsOn ? "bg-[#22d3ee]" : "bg-[#8b949e]"}`}
            />
            FS
          </button>

          {fsOn && (interval === "5min" || interval === "1min") && (
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
              <span className="text-xs text-[#8b949e]">Swings</span>
              <button
                onClick={() => {
                  setAllSwings((v) => {
                    window.localStorage.setItem(ALL_SWINGS_KEY, v ? "0" : "1");
                    return !v;
                  });
                }}
                className={`rounded-md border px-2 py-1 text-xs transition-colors ${
                  allSwings
                    ? "border-[#22d3ee] text-[#e6edf3]"
                    : "border-[#30363d] text-[#8b949e]"
                }`}
                title="Show all swings for the day"
              >
                All
              </button>
              <input
                type="number"
                min={1}
                max={50}
                value={swingN}
                onChange={(e) => changeSwingN(Number(e.target.value))}
                disabled={allSwings}
                className="w-14 rounded-md border border-[#30363d] bg-[#0d1117] px-2 py-1 text-xs text-[#e6edf3] outline-none focus:border-[#22d3ee] disabled:opacity-40"
                title="Number of swings to display"
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

      <div className={dual ? "flex items-start gap-3" : ""}>
        {/* Pane A */}
        <div className={dual ? "w-1/2 min-w-0" : "w-full"}>
          <div className="mb-1.5 flex items-center gap-2">
            <span className="text-xs font-bold tracking-wider text-[#6366f1]">
              A
            </span>
            <select
              value={interval}
              onChange={(e) => changeInterval(e.target.value as ChartInterval)}
              className={SELECT_CLS}
              title="Chart A timeframe"
            >
              {VALID_INTERVALS.map((iv) => (
                <option key={iv} value={iv}>
                  {INTERVAL_LABELS[iv]}
                </option>
              ))}
            </select>
            <span className="text-xs text-[#8b949e]">
              {loading ? "Loading..." : `${count} candles`}
            </span>
            <div className="ml-auto flex items-center gap-1.5">
              {jumpInfoA && (
                <span
                  className="text-xs text-amber-400/90"
                  title="Selected date has no candles"
                >
                  {jumpInfoA}
                </span>
              )}
              <input
                type="date"
                value={goDateA}
                min={minDateA || undefined}
                max={maxDateA || undefined}
                onChange={(e) => {
                  setGoDateA(e.target.value);
                  setJumpInfoA(null);
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter")
                    goTo(goDateA, chartARef.current, setJumpInfoA);
                }}
                disabled={!minDateA}
                suppressHydrationWarning
                style={{ colorScheme: "dark" }}
                className={SELECT_CLS}
                title="Pick a date, then Go — chart A jumps to that trading day"
              />
              <button
                onClick={() => goTo(goDateA, chartARef.current, setJumpInfoA)}
                disabled={!goDateA || !minDateA}
                suppressHydrationWarning
                className="rounded-md border border-[#30363d] px-2 py-1 text-xs text-[#8b949e] transition-colors hover:border-[#6366f1] hover:text-[#e6edf3] disabled:opacity-40"
                title="Jump chart A to the selected date"
              >
                Go
              </button>
            </div>
          </div>
          <StockChart
            ref={chartARef}
            symbol="NIFTY 50"
            candles={data}
            intraday={interval !== "daily"}
            interval={interval}
            swings={overlaysA.swings}
            bias={overlaysA.bias}
            hhllBias={overlaysA.hhllBias}
            trades={overlaysA.trades}
            sessionBreaks={overlaysA.sessionBreaks}
            algoFlowLine={overlaysA.algoFlowLine}
            envelope={overlaysA.envelope}
            algoFirstSwing={overlaysA.algoFirstSwing}
            algoSecondSwing={overlaysA.algoSecondSwing}
            algoSecondSwingMarkers={overlaysA.algoSecondSwingMarkers}
            algoSecondSwingBreaks={overlaysA.algoSecondSwingBreaks}
            fsMarkers={overlaysA.fsMarkers}
            fsBreaks={overlaysA.fsBreaks}
            tradeMode={overlaysA.tradeMode}
            onHoverTime={onHoverA}
            wholeDaySwings={wholeDaySwings}
            emaLines={emaLinesA}
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
              <span className="text-xs font-bold tracking-wider text-[#22d3ee]">
                B
              </span>
              <select
                value={intervalB}
                onChange={(e) =>
                  changeIntervalB(e.target.value as ChartInterval)
                }
                className={SELECT_CLS}
                title="Chart B timeframe"
              >
                {VALID_INTERVALS.map((iv) => (
                  <option key={iv} value={iv}>
                    {INTERVAL_LABELS[iv]}
                  </option>
                ))}
              </select>
              <span className="text-xs text-[#8b949e]">
                {loadingB ? "Loading..." : `${countB} candles`}
              </span>
              <div className="ml-auto flex items-center gap-1.5">
                {jumpInfoB && (
                  <span
                    className="text-xs text-amber-400/90"
                    title="Selected date has no candles"
                  >
                    {jumpInfoB}
                  </span>
                )}
                <input
                  type="date"
                  value={goDateB}
                  min={minDateB || undefined}
                  max={maxDateB || undefined}
                  onChange={(e) => {
                    setGoDateB(e.target.value);
                    setJumpInfoB(null);
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter")
                      goTo(goDateB, chartBRef.current, setJumpInfoB);
                  }}
                  disabled={!minDateB}
                  suppressHydrationWarning
                  style={{ colorScheme: "dark" }}
                  className={SELECT_CLS}
                  title="Pick a date, then Go — chart B jumps to that trading day"
                />
                <button
                  onClick={() => goTo(goDateB, chartBRef.current, setJumpInfoB)}
                  disabled={!goDateB || !minDateB}
                  suppressHydrationWarning
                  className="rounded-md border border-[#30363d] px-2 py-1 text-xs text-[#8b949e] transition-colors hover:border-[#22d3ee] hover:text-[#e6edf3] disabled:opacity-40"
                  title="Jump chart B to the selected date"
                >
                  Go
                </button>
              </div>
            </div>
            <StockChart
              ref={chartBRef}
              symbol="NIFTY 50"
              candles={dataB}
              intraday={intervalB !== "daily"}
              interval={intervalB}
              swings={overlaysB.swings}
              bias={overlaysB.bias}
              hhllBias={overlaysB.hhllBias}
              trades={overlaysB.trades}
              sessionBreaks={overlaysB.sessionBreaks}
              algoFlowLine={overlaysB.algoFlowLine}
              envelope={overlaysB.envelope}
              algoFirstSwing={overlaysB.algoFirstSwing}
              algoSecondSwing={overlaysB.algoSecondSwing}
              algoSecondSwingMarkers={overlaysB.algoSecondSwingMarkers}
              algoSecondSwingBreaks={overlaysB.algoSecondSwingBreaks}
              fsMarkers={overlaysB.fsMarkers}
              fsBreaks={overlaysB.fsBreaks}
              tradeMode={overlaysB.tradeMode}
              onHoverTime={onHoverB}
              wholeDaySwings={wholeDaySwingsB}
              emaLines={emaLinesB}
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
