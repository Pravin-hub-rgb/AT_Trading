"use client";

import { useEffect, useRef, useState } from "react";
import {
  createChart,
  ColorType,
  IChartApi,
  CandlestickSeries,
  TickMarkType,
  createSeriesMarkers,
  type Time,
  type SeriesMarker,
  type TimeRangeChangeEventHandler,
} from "lightweight-charts";
import type { Candle, BiasLabel } from "@/lib/api";
import { SwingSRPrimitive, SwingPoint } from "./SwingSRPrimitive";
import { PositionPrimitive, TradeBox } from "./PositionPrimitive";
import { SessionBreakPrimitive } from "./SessionBreakPrimitive";
import { FlowLinePrimitive, FlowSegment } from "./FlowLinePrimitive";
import { EnvelopePrimitive } from "./EnvelopePrimitive";
import type { EnvelopeViolation } from "@/lib/envelope";

interface Props {
  symbol: string;
  candles: Candle[];
  intraday?: boolean;
  interval?: string;
  height?: number;
  swings?: SwingPoint[];
  bias?: BiasLabel[];
  trades?: TradeBox[];
  sessionBreaks?: boolean;
  oneMinSwingN?: number;
  swingDots?: boolean;
  flowLine?: FlowSegment[] | null;
  algoFlowLine?: FlowSegment[] | null;
  envelope?: EnvelopeViolation[] | null;
}

interface OHLCV {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  nextBias?: string | null;
  nextBiasDate?: string | null;
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

export default function StockChart({ symbol, candles, intraday = false, interval = "daily", height = 720, swings, bias, trades, sessionBreaks, oneMinSwingN, swingDots = true, flowLine, algoFlowLine, envelope }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const [ohlcv, setOhlcv] = useState<OHLCV | null>(null);
  const [biasTip, setBiasTip] = useState<{ x: number; y: number; paneW: number; label: BiasLabel } | null>(null);
  const [pinnedBiasTip, setPinnedBiasTip] = useState<typeof biasTip>(null);

  useEffect(() => {
    if (!containerRef.current || candles.length === 0) return;

    // date -> last candle of that day (marker anchor) + bias lookup
    const lastByDate = new Map<string, Candle>();
    candles.forEach((c) => {
      const d = c.date.slice(0, 10);
      lastByDate.set(d, c); // always overwrite -> last one wins
    });
    // O(1) crosshair lookups Ã¢Â€Â” linear find() over 19k+ candles janks the UI
    const byTs = new Map<number, Candle>();
    if (intraday) {
      candles.forEach((c) => byTs.set(c.ts, c));
    }
    const biasMap = new Map<string, BiasLabel>((bias ?? []).map((b) => [b.date, b]));
    // date (prev) -> bias for the NEXT day (marker on last candle shows what it decided)
    const nextBiasMap = new Map<string, BiasLabel>();
    bias?.forEach((lb) => {
      const prevDate = lb.details?.prev_date;
      if (prevDate) nextBiasMap.set(prevDate, lb);
    });

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

    // Bias markers: one per day, under the LAST candle (3:30 PM) Ã¢Â€Â” shows next-day bias
    if (intraday && bias && bias.length > 0) {
      const markers: SeriesMarker<Time>[] = [];
      lastByDate.forEach((c, d) => {
        const lb = nextBiasMap.get(d);
        if (!lb) return;
        const color =
          lb.bias === "bullish" ? "#10b981" : lb.bias === "bearish" ? "#ef4444" : "#8b949e";
        const shape = lb.bias === "bullish" ? "arrowUp" : lb.bias === "bearish" ? "arrowDown" : "circle";
        markers.push({
          time: c.ts as Time,
          position: "belowBar",
          shape,
          color,
          size: 2,
        });
      });

      // Prev-day intraday swing dots with HH/HL/LH/LL tags Ã¢Â€Â” these are 5-min
      // pivots from the bias engine, so they only belong on the 5-min chart.
      // The 1-min chart gets its own true 1-minute structure tags instead.
      if (interval === "5min" && swingDots) {
        bias.forEach((lb) => {
          (lb.prev_day?.swings ?? []).forEach((s) => {
            const tagColor =
              s.tag === "HH" || s.tag === "HL"
                ? "#10b981"
                : s.tag === "LH" || s.tag === "LL"
                  ? "#f97316"
                  : "#8b949e";
            markers.push({
              time: s.ts as Time,
              position: s.kind === "high" ? "aboveBar" : "belowBar",
              shape: "circle",
              color: tagColor,
              text: s.tag ?? "",
              size: 0.5,
            });
          });
        });
      }

      markers.sort((a, b) => timeToSec(a.time) - timeToSec(b.time));
      if (markers.length > 0) createSeriesMarkers(candleSer, markers);
    }

    // True intraday structure: per-day Williams fractals (user-set n) tagged
    // HH/HL/LH/LL in sequence — works on both 5-min and 1-min charts.
    if (intraday && swingDots) {
      const N = Math.max(2, Math.floor(oneMinSwingN ?? 12));
      const byDate = new Map<string, number[]>();
      candles.forEach((c, gi) => {
        const d = c.date.slice(0, 10);
        if (!byDate.has(d)) byDate.set(d, []);
        byDate.get(d)!.push(gi);
      });

      const tagMarkers: SeriesMarker<Time>[] = [];
      byDate.forEach((idxs) => {
        const arr = idxs.map((gi) => candles[gi]);
        if (arr.length < 2 * N + 1) return;

        type Pivot = { g: number; kind: "high" | "low"; price: number };
        const pivots: Pivot[] = [];
        for (let k = N; k < arr.length - N; k++) {
          let isHigh = true;
          let isLow = true;
          for (let m = k - N; m <= k + N; m++) {
            if (m === k) continue;
            if (arr[m].high >= arr[k].high) isHigh = false;
            if (arr[m].low <= arr[k].low) isLow = false;
          }
          if (isHigh) pivots.push({ g: idxs[k], kind: "high", price: arr[k].high });
          else if (isLow) pivots.push({ g: idxs[k], kind: "low", price: arr[k].low });
        }

        let lastHigh: number | null = null;
        let lastLow: number | null = null;
        for (const p of pivots) {
          let tag: string | null = null;
          if (p.kind === "high") {
            if (lastHigh != null) tag = p.price > lastHigh ? "HH" : "LH";
            lastHigh = p.price;
          } else {
            if (lastLow != null) tag = p.price > lastLow ? "HL" : "LL";
            lastLow = p.price;
          }
          if (!tag) continue;
          const ts = candles[p.g].ts as Time;
          tagMarkers.push({
            time: ts,
            position: p.kind === "high" ? "aboveBar" : "belowBar",
            shape: "circle",
            color: tag === "HH" || tag === "HL" ? "#10b981" : "#f97316",
            text: tag,
            size: 0.5,
          });
        }
      });

      if (tagMarkers.length > 0) createSeriesMarkers(candleSer, tagMarkers);
    }

    const swingPrimitive = new SwingSRPrimitive(candleSer, swings ?? [], intraday);
    if (swings && swings.length > 0) {
      chart.panes()[0].attachPrimitive(swingPrimitive);
    }

    const posPrimitive = new PositionPrimitive(candleSer, trades ?? []);
    if (intraday && trades && trades.length > 0) {
      chart.panes()[0].attachPrimitive(posPrimitive);
    }

    // session breaks: first bar of every day except the chart's very first
    let sbPrimitive: SessionBreakPrimitive | null = null;
    if (intraday && sessionBreaks) {
      const dayStarts: number[] = [];
      let prevDate = "";
      candles.forEach((c, idx) => {
        const d = c.date.slice(0, 10);
        if (d !== prevDate) {
          dayStarts.push(idx);
          prevDate = d;
        }
      });
      const boundaryIdx = dayStarts.slice(1);
      if (boundaryIdx.length > 0) {
        sbPrimitive = new SessionBreakPrimitive(candleSer, boundaryIdx);
        chart.panes()[0].attachPrimitive(sbPrimitive);
      }
    }

    // Flow-Line — attach order = paint order: WHITE (algo) first, then
    // ORANGE (manual ground truth) last so it stays visible on top.
    // Each day is drawn separately; segments never connect across days.
    let algoPrimitive: FlowLinePrimitive | null = null;
    if (intraday && algoFlowLine && algoFlowLine.length > 0) {
      algoPrimitive = new FlowLinePrimitive(candleSer, algoFlowLine, candles.length - 1, "#ffffff");
      candleSer.attachPrimitive(algoPrimitive);
    }

    let flowPrimitive: FlowLinePrimitive | null = null;
    if (intraday && flowLine && flowLine.length > 0) {
      flowPrimitive = new FlowLinePrimitive(candleSer, flowLine, candles.length - 1, "#fb923c");
      candleSer.attachPrimitive(flowPrimitive);
    }

    let envPrimitive: EnvelopePrimitive | null = null;
    if (intraday && envelope && envelope.length > 0) {
      envPrimitive = new EnvelopePrimitive(candleSer, envelope, candles.length - 1);
      chart.panes()[0].attachPrimitive(envPrimitive);
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
        const lastDate = last.date.slice(0, 10);
        setOhlcv({
          date: formatDateLabel(intraday ? last.ts : last.date.slice(0, 10)),
          open: last.open,
          high: last.high,
          low: last.low,
          close: last.close,
          volume: last.volume,
          nextBias: biasMap.get(lastDate)?.bias ?? null,
          nextBiasDate: lastDate,
        });
      }
    };

    chart.subscribeCrosshairMove((param) => {
      if (!param.time) { setLast(); setBiasTip(null); return; }
      const data = param.seriesData.get(candleSer) as any;
      if (!data) { setLast(); setBiasTip(null); return; }
      const t = param.time;
      let match: Candle | undefined;
      let hoveredDate: string | undefined;
      if (typeof t === "number") {
        match = byTs.get(t);
        hoveredDate = match?.date.slice(0, 10);
      } else {
        hoveredDate = String(t);
        match = candles.find((c) => c.date.slice(0, 10) === t);
      }
      setOhlcv({
        date: formatDateLabel(t as number | string | { year: number; month: number; day: number }),
        open: data.open,
        high: data.high,
        low: data.low,
        close: data.close,
        volume: match?.volume ?? 0,
        nextBias: hoveredDate ? biasMap.get(hoveredDate)?.bias ?? null : null,
        nextBiasDate: hoveredDate ?? null,
      });
      const isLast = !!match && !!hoveredDate && lastByDate.get(hoveredDate)?.ts === match.ts;
      const nextLb = intraday && isLast && hoveredDate ? nextBiasMap.get(hoveredDate) : undefined;
      if (nextLb && param.point) {
        const paneW = containerRef.current?.clientWidth ?? 800;
        setBiasTip({ x: param.point.x, y: param.point.y, label: nextLb, paneW });
      } else {
        setBiasTip(null);
      }
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
      if (intraday && trades && trades.length > 0) {
        chart.panes()[0].detachPrimitive(posPrimitive);
      }
      if (sbPrimitive) {
        chart.panes()[0].detachPrimitive(sbPrimitive);
      }
      if (flowPrimitive) {
        candleSer.detachPrimitive(flowPrimitive);
      }
      if (algoPrimitive) {
        candleSer.detachPrimitive(algoPrimitive);
      }
      if (envPrimitive) {
        chart.panes()[0].detachPrimitive(envPrimitive);
      }
      chart.remove();
      chartRef.current = null;
    };
  }, [symbol, candles, intraday, height, swings, bias, trades, sessionBreaks, oneMinSwingN, swingDots, flowLine, algoFlowLine, envelope, interval]);

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
          {ohlcv.nextBias && (
            <div style={{
              color: ohlcv.nextBias === "bullish" ? "#10b981" : ohlcv.nextBias === "bearish" ? "#ef4444" : "#9ca3af",
              marginTop: 2,
              fontWeight: 600,
            }}>
              {ohlcv.nextBias === "bullish" ? "\u25B2" : ohlcv.nextBias === "bearish" ? "\u25BC" : "\u25CF"} Bias: {ohlcv.nextBias}
            </div>
          )}
        </div>
      )}
      <div
        ref={containerRef}
        style={{ width: "100%", height }}
        onClick={() => {
          if (pinnedBiasTip) {
            setPinnedBiasTip(null);
          } else if (biasTip) {
            setPinnedBiasTip(biasTip);
            setBiasTip(null);
          }
        }}
      />
      {(pinnedBiasTip ?? biasTip) && (() => {
        const tip = pinnedBiasTip ?? biasTip!;
        const pinned = !!pinnedBiasTip;
        return (
        <div
          style={{
            position: "absolute",
            left: Math.min(Math.max(tip.x + 14, 8), Math.max(tip.paneW - 330, 8)),
            top: tip.y + 14,
            zIndex: 20,
            maxWidth: 320,
            background: "rgba(13,17,23,0.95)",
            border: pinned
              ? "1px solid #e2e8f0"
              : `1px solid ${
                  tip.label.bias === "bullish"
                    ? "#10b981"
                    : tip.label.bias === "bearish"
                      ? "#ef4444"
                      : "#6b7280"
                }`,
            borderRadius: 6,
            padding: "6px 10px",
            fontSize: 11,
            lineHeight: "15px",
            pointerEvents: pinned ? "auto" : "none",
            userSelect: pinned ? "text" : "none",
            boxShadow: pinned ? "0 4px 16px rgba(0,0,0,0.5)" : "none",
          }}
        >
          {pinned && (
            <div
              onClick={(e) => { e.stopPropagation(); setPinnedBiasTip(null); }}
              style={{
                position: "absolute", top: 4, right: 8, cursor: "pointer",
                color: "#94a3b8", fontSize: 12, lineHeight: "12px",
              }}
            >
              &#x2715;
            </div>
          )}
          <div
            style={{
              color:
                tip.label.bias === "bullish"
                  ? "#10b981"
                  : tip.label.bias === "bearish"
                    ? "#ef4444"
                    : "#9ca3af",
              fontWeight: 600,
              marginBottom: 2,
              paddingRight: pinned ? 16 : 0,
            }}
          >
            {pinned ? "\uD83D\uDCCC " : ""}Bias for {tip.label.date}: {tip.label.bias}
          </div>
          {tip.label.overview?.sh_price !== undefined && tip.label.overview?.sl_price !== undefined && (
            <div style={{ color: "#79c0ff", marginBottom: 2 }}>
              <b>ZONES:</b> {tip.label.overview.zone ?? "-"} Ã‚Â· pos{" "}
              {tip.label.overview.pos_pct ?? "?"}% | SL{" "}
              {tip.label.overview.sl_price} ({tip.label.overview.sl_date})
              {" \u2190 "}{tip.label.overview.pos_pct ?? "?"}%{" \u2192 "}SH{" "}
              {tip.label.overview.sh_price} ({tip.label.overview.sh_date})
            </div>
          )}
          {tip.label.prev_day?.structure && (
            <div style={{ color: "#d29922", marginBottom: 2 }}>
              <b>CLOSING SESSION:</b> structure {tip.label.prev_day.structure}
              {tip.label.prev_day.sustain ? ` Ã‚Â· sustain ${tip.label.prev_day.sustain}` : ""}
              {tip.label.prev_day.close_pos_pct != null ? ` (close at ${tip.label.prev_day.close_pos_pct}%)` : ""}
              {tip.label.prev_day.summary ? ` Ã¢Â€Â” ${tip.label.prev_day.summary}` : ""}
            </div>
          )}
          <div style={{ color: "#94a3b8" }}>{tip.label.reason}</div>
        </div>
        );
      })()}
    </div>
  );
}
