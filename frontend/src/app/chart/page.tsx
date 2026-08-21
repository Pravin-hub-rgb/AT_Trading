"use client";

import { useEffect, useMemo, useState } from "react";
import StockChart from "@/components/StockChart";
import {
  Candle,
  Swing,
  getChartData,
  getSwings,
} from "@/lib/api";

const STORAGE_KEY = "chart_interval";
const VALID_INTERVALS = ["daily", "5min"] as const;
type ChartInterval = (typeof VALID_INTERVALS)[number];

const PIVOT = 10;
const LEVELS = 5;
const LOOKAHEAD = 5;

function loadInterval(): ChartInterval {
  if (typeof window === "undefined") return "daily";
  const saved = window.localStorage.getItem(STORAGE_KEY);
  return saved === "daily" || saved === "5min" ? saved : "daily";
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

  useEffect(() => {
    setInterval(loadInterval());
  }, []);

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

  const changeInterval = (iv: ChartInterval) => {
    window.localStorage.setItem(STORAGE_KEY, iv);
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
            {swingOn && swingCount > 0 ? ` · ${swingCount} swings (pivot ${PIVOT})` : ""}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex gap-1">
            {VALID_INTERVALS.map((iv) => (
              <button
                key={iv}
                onClick={() => changeInterval(iv)}
                className={`rounded-md border px-3 py-1.5 text-sm transition-colors ${
                  interval === iv
                    ? "border-[#6366f1] bg-[#6366f1]/20 text-[#e6edf3]"
                    : "border-[#30363d] text-[#8b949e] hover:text-[#e6edf3]"
                }`}
              >
                {iv === "daily" ? "Daily" : "5-min"}
              </button>
            ))}
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
          intraday={interval === "5min"}
          interval={interval}
          swings={swingOn ? displaySwings : undefined}
        />
      )}
    </div>
  );
}