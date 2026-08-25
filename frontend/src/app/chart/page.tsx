"use client";

import { useEffect, useMemo, useState } from "react";
import StockChart from "@/components/StockChart";
import IntradayPanel from "@/components/IntradayPanel";
import { computeFlowLine, computeAlgoFlowLine } from "@/lib/flowline";
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
} from "@/lib/api";

const STORAGE_KEY = "chart_interval";
const BT_KEY = "intraday_bt_on";
const SWING_N_KEY = "chart_1min_swing_n";
const DOTS_KEY = "chart_hhll_dots";
const FLOW_KEY = "chart_flow_line";
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
  const btLoading = btOn && !btData && !btError;

  useEffect(() => {
    setInterval(loadInterval());
    if (typeof window !== "undefined") {
      setBtOn(window.localStorage.getItem(BT_KEY) === "1");
      const nRaw = window.localStorage.getItem(SWING_N_KEY);
      if (nRaw) setSwingN(clampSwingN(Number(nRaw)));
      setDotsOn(window.localStorage.getItem(DOTS_KEY) !== "0");
      setFlowOn(window.localStorage.getItem(FLOW_KEY) !== "0");
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

  const displaySwings = useMemo(() => {
    if (interval === "daily") return swings;
    const dates: string[] = [];
    const lastIdxByDate = new Map<string, number>();
    const maxHighIdx: Record<string, number> = {};
    const minLowIdx: Record<string, number> = {};
    data.forEach((c, i) => {
      const d = c.date.slice(0, 10);
      if (!lastIdxByDate.has(d)) dates.push(d);
      lastIdxByDate.set(d, i);
      const hi = maxHighIdx[d];
      const lo = minLowIdx[d];
      if (hi === undefined || c.high >= data[hi].high) maxHighIdx[d] = i;
      if (lo === undefined || c.low <= data[lo].low) minLowIdx[d] = i;
    });
    return swings
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
  }, [interval, swings, data]);

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

  const flowSegments = useMemo(() => {
    if (!flowOn || interval === "daily" || data.length < 2) return null;
    const segs = computeFlowLine(data);
    return segs;
  }, [flowOn, interval, data]);

  // TRAINED ALGO: deviation zigzag T=11 (white line â€” manual/orange ke against compare)
  const algoSegments = useMemo(() => {
    if (!flowOn || interval === "daily" || data.length < 2) return null;
    return computeAlgoFlowLine(data);
  }, [flowOn, interval, data]);

  const changeInterval = (iv: ChartInterval) => {    window.localStorage.setItem(STORAGE_KEY, iv);
    setData([]);
    setInterval(iv);
  };

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
          <select
            value={interval}
            onChange={(e) => changeInterval(e.target.value as ChartInterval)}
            className="rounded-md border border-[#30363d] bg-[#161b22] px-3 py-1.5 text-sm text-[#e6edf3] outline-none focus:border-[#6366f1]"
            title="Chart timeframe"
          >
            {VALID_INTERVALS.map((iv) => (
              <option key={iv} value={iv}>{INTERVAL_LABELS[iv]}</option>
            ))}
          </select>

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

      {error ? (
        <div className="rounded-md border border-[#ef4444]/50 bg-[#ef4444]/10 px-4 py-3 text-sm text-[#ef4444]">
          {error}
        </div>
      ) : (
        <StockChart
          symbol="NIFTY 50"
          candles={data}
          intraday={interval !== "daily"}
          interval={interval}
          swings={swingOn ? displaySwings : undefined}
          bias={interval !== "daily" && biasOn ? biasLabels : undefined}
          trades={interval !== "daily" ? allTrades : undefined}
          sessionBreaks={interval !== "daily"}
          oneMinSwingN={swingN}
          swingDots={dotsOn}
          flowLine={flowSegments}
          algoFlowLine={algoSegments}
        />
      )}

      {interval !== "daily" && btOn && (
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

