"use client";

import { useEffect, useRef, useState } from "react";
import {
  createChart,
  ColorType,
  IChartApi,
  CandlestickSeries,
  TickMarkType,
  type Time,
  type TimeRangeChangeEventHandler,
} from "lightweight-charts";
import type { Candle } from "@/lib/api";
import { SwingSRPrimitive, SwingPoint } from "./SwingSRPrimitive";

interface Props {
  symbol: string;
  candles: Candle[];
  intraday?: boolean;
  interval?: string;
  height?: number;
  swings?: SwingPoint[];
}

interface OHLCV {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

const IST_OFFSET = 5.5 * 3600;
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const VIEWS_KEY = "chart_views";

function istDate(time: number | string | { year: number; month: number; day: number }): Date {
  if (typeof time === "number") {
    return new Date((time + IST_OFFSET) * 1000);
  }
  if (typeof time === "string") {
    return new Date(`${time}T00:00:00Z`);
  }
  return new Date(Date.UTC(time.year, time.month - 1, time.day));
}

function fmtDay(d: Date): string {
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}`;
}

function fmtFull(d: Date): string {
  return `${fmtDay(d)} ${d.getUTCFullYear()}`;
}

function fmtTime(d: Date): string {
  const hh = String(d.getUTCHours()).padStart(2, "0");
  const mm = String(d.getUTCMinutes()).padStart(2, "0");
  return `${hh}:${mm}`;
}

function formatDateLabel(time: number | string | { year: number; month: number; day: number }): string {
  const d = istDate(time);
  return typeof time === "number" ? `${fmtFull(d)} ${fmtTime(d)}` : fmtFull(d);
}

function timeToSec(time: Time): number {
  if (typeof time === "number") return time;
  if (typeof time === "string") return Date.parse(`${time}T00:00:00Z`) / 1000;
  return Date.UTC(time.year, time.month - 1, time.day) / 1000;
}

function secToSeriesTime(sec: number, intraday: boolean): Time {
  if (intraday) return sec as Time;
  return new Date(sec * 1000).toISOString().slice(0, 10);
}

function loadViews(): Record<string, { from: number; to: number }> {
  try {
    const raw = window.localStorage.getItem(VIEWS_KEY);
    if (!raw) return {};
    const r = JSON.parse(raw);
    return r && typeof r === "object" ? r : {};
  } catch {
    return {};
  }
}

function saveView(interval: string, range: { from: number; to: number }) {
  try {
    const views = loadViews();
    views[interval] = range;
    window.localStorage.setItem(VIEWS_KEY, JSON.stringify(views));
  } catch {}
}

export default function StockChart({ symbol, candles, intraday = false, interval = "daily", height = 720, swings }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const [ohlcv, setOhlcv] = useState<OHLCV | null>(null);

  useEffect(() => {
    if (!containerRef.current || candles.length === 0) return;

    const prevRange = chartRef.current ? chartRef.current.timeScale().getVisibleRange() : null;

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height,
      layout: {
        background: { type: ColorType.Solid, color: "#0d1117" },
        textColor: "#94a3b8",
      },
      grid: {
        vertLines: { color: "#1e293b" },
        horzLines: { color: "#1e293b" },
      },
      crosshair: {
        mode: 0,
        vertLine: { color: "#6366f1", width: 1, style: 2, labelBackgroundColor: "#6366f1" },
        horzLine: { color: "#6366f1", width: 1, style: 2, labelBackgroundColor: "#6366f1" },
      },
      timeScale: {
        borderColor: "#334155",
        timeVisible: intraday,
        secondsVisible: false,
        tickMarkFormatter: (time: number | string, tickMarkType: TickMarkType) => {
          const d = istDate(time);
          switch (tickMarkType) {
            case TickMarkType.Year:
              return String(d.getUTCFullYear());
            case TickMarkType.Month:
              return `${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
            case TickMarkType.DayOfMonth:
              return fmtDay(d);
            case TickMarkType.TimeWithSeconds:
            case TickMarkType.Time:
              return fmtTime(d);
            default:
              return fmtFull(d);
          }
        },
      },
      localization: {
        timeFormatter: (time: number | string | { year: number; month: number; day: number }) =>
          formatDateLabel(time),
      },
      rightPriceScale: {
        borderColor: "#334155",
      },
    });

    chartRef.current = chart;

    const candleSer = chart.addSeries(CandlestickSeries, {
      upColor: "#10b981",
      downColor: "#ef4444",
      borderUpColor: "#10b981",
      borderDownColor: "#ef4444",
      wickUpColor: "#10b981",
      wickDownColor: "#ef4444",
    });

    const formatted = candles.map((c) => ({
      time: (intraday ? c.ts : c.date.slice(0, 10)) as any,
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close,
    }));

    candleSer.setData(formatted);

    const swingPrimitive = new SwingSRPrimitive(candleSer, swings ?? [], intraday);
    if (swings && swings.length > 0) {
      chart.panes()[0].attachPrimitive(swingPrimitive);
    }

    let saveTimer: ReturnType<typeof setTimeout> | null = null;
    const onVisibleTimeRangeChange: TimeRangeChangeEventHandler<Time> = (timeRange) => {
      if (!timeRange) return;
      if (saveTimer) clearTimeout(saveTimer);
      saveTimer = setTimeout(() => {
        saveView(interval, { from: timeToSec(timeRange.from), to: timeToSec(timeRange.to) });
      }, 400);
    };
    chart.timeScale().subscribeVisibleTimeRangeChange(onVisibleTimeRangeChange);

    const defaultView = () => {
      const lastIndex = formatted.length - 1;
      if (intraday) {
        chart.timeScale().setVisibleLogicalRange({ from: Math.max(0, lastIndex - 149), to: lastIndex + 1 });
      } else {
        chart.timeScale().fitContent();
      }
    };

    const views = loadViews();
    const anchor = views[interval] ?? views[interval === "5min" ? "daily" : "5min"] ?? null;
    const firstT = timeToSec(formatted[0].time);
    const lastT = timeToSec(formatted[formatted.length - 1].time);

    const applyRange = (fromSec: number, toSec: number) => {
      const from = Math.max(fromSec, firstT);
      const to = Math.min(toSec, lastT);
      if (to > from) {
        chart.timeScale().setVisibleRange({ from: secToSeriesTime(from, intraday), to: secToSeriesTime(to, intraday) });
        return true;
      }
      return false;
    };

    let restored = false;
    if (prevRange && prevRange.from && prevRange.to) {
      const pf = timeToSec(prevRange.from as Time);
      const pt = timeToSec(prevRange.to as Time);
      if (pt >= firstT && pf <= lastT) {
        restored = applyRange(pf, pt);
      }
    }
    if (!restored && anchor && anchor.to >= firstT && anchor.from <= lastT) {
      restored = applyRange(anchor.from, anchor.to);
    }
    if (!restored) {
      defaultView();
    }

    const setLast = () => {
      const last = candles[candles.length - 1];
      if (last) {
        setOhlcv({
          date: formatDateLabel(intraday ? last.ts : last.date.slice(0, 10)),
          open: last.open,
          high: last.high,
          low: last.low,
          close: last.close,
          volume: last.volume,
        });
      }
    };

    chart.subscribeCrosshairMove((param) => {
      if (!param.time) { setLast(); return; }
      const data = param.seriesData.get(candleSer) as any;
      if (!data) { setLast(); return; }
      const t = param.time;
      let match: Candle | undefined;
      if (typeof t === "number") {
        match = candles.find((c) => Math.abs(c.ts - t) < 30);
      } else {
        match = candles.find((c) => c.date.slice(0, 10) === t);
      }
      setOhlcv({
        date: formatDateLabel(t as number | string | { year: number; month: number; day: number }),
        open: data.open,
        high: data.high,
        low: data.low,
        close: data.close,
        volume: match?.volume ?? 0,
      });
    });

    setLast();

    const handleResize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      if (saveTimer) clearTimeout(saveTimer);
      const range = chart.timeScale().getVisibleRange();
      if (range) saveView(interval, { from: timeToSec(range.from), to: timeToSec(range.to) });
      chart.timeScale().unsubscribeVisibleTimeRangeChange(onVisibleTimeRangeChange);
      if (swings && swings.length > 0) {
        chart.panes()[0].detachPrimitive(swingPrimitive);
      }
      chart.remove();
      chartRef.current = null;
    };
  }, [symbol, candles, intraday, height, swings, interval]);

  return (
    <div style={{ position: "relative" }}>
      {ohlcv && (
        <div
          style={{
            position: "absolute",
            top: 8,
            left: 8,
            zIndex: 10,
            background: "rgba(13,17,23,0.85)",
            border: "1px solid #334155",
            borderRadius: 6,
            padding: "6px 10px",
            fontFamily: '"SF Mono", "Fira Code", monospace',
            fontSize: 11,
            lineHeight: "16px",
            pointerEvents: "none",
          }}
        >
          <div style={{ color: "#94a3b8", marginBottom: 2 }}>{ohlcv.date}</div>
          <div style={{ display: "flex", gap: 10 }}>
            <span style={{ color: "#e2e8f0" }}>O: <b>{ohlcv.open.toFixed(2)}</b></span>
            <span style={{ color: "#10b981" }}>H: <b>{ohlcv.high.toFixed(2)}</b></span>
            <span style={{ color: "#ef4444" }}>L: <b>{ohlcv.low.toFixed(2)}</b></span>
            <span style={{ color: "#e2e8f0" }}>C: <b>{ohlcv.close.toFixed(2)}</b></span>
            {ohlcv.volume > 0 && <span style={{ color: "#94a3b8" }}>Vol: <b>{ohlcv.volume.toLocaleString()}</b></span>}
          </div>
        </div>
      )}
      <div ref={containerRef} style={{ width: "100%", height }} />
    </div>
  );
}