"use client";

import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from "react";
import {
  createChart,
  ColorType,
  IChartApi,
  CandlestickSeries,
  TickMarkType,
  createSeriesMarkers,
  type ISeriesMarkersPluginApi,
  type Logical,
  type Time,
  type SeriesMarker,
  type TimeRangeChangeEventHandler,
  type MouseEventParams,
  type ISeriesApi,
} from "lightweight-charts";
import type { Candle, BiasLabel, FsDayMark, FsPoint } from "@/lib/api";
import { SwingSRPrimitive, SwingPoint } from "./SwingSRPrimitive";
import { PositionPrimitive, TradeBox } from "./PositionPrimitive";
import { SessionBreakPrimitive } from "./SessionBreakPrimitive";
import { FlowLinePrimitive, FlowSegment } from "./FlowLinePrimitive";
import { EnvelopePrimitive } from "./EnvelopePrimitive";
import { FirstSwingPrimitive, FsSeg } from "./FirstSwingPrimitive";
import { SyncCrosshairPrimitive } from "./SyncCrosshairPrimitive";
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
  algoFlowLine?: FlowSegment[] | null;
  envelope?: EnvelopeViolation[] | null;
  manualFirstSwing?: Record<string, FsDayMark> | null;
  algoFirstSwing?: (FlowSegment & { invalid?: boolean })[] | null;
  fsMarkers?: { idx: number; invalid: boolean; source?: "chop" | "sustain" | null; dir?: "up" | "down" | null }[] | null;
  fsBreaks?: { idx: number; time: string; kind: "B1" | "B2" | "FLIP"; dir: "up" | "down"; px: number }[] | null;
  drawMode?: boolean;
  onSwingDraw?: (mark: { day: string; start: FsPoint; end: FsPoint }) => void;
  onDrawStatus?: (status: string | null) => void;
  // Crosshair-sync hook: emitted with the hovered epoch sec (UTC) on every
  // crosshair move, null when the crosshair leaves the data. Keep stable
  // (useCallback) if provided — read via ref, so it never rebuilds the chart.
  onHoverTime?: (sec: number | null) => void;
}

// Imperative API for crosshair sync between two StockChart instances.
export interface StockChartHandle {
  setCrosshairAt(sec: number): void;
  clearCrosshair(): void;
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

// Pure mapper: hand-drawn marks -> renderable segments (snaps to candle indices).
function fsSegsFromMarks(candles: Candle[], marks: Record<string, FsDayMark>): FsSeg[] {
  const days = new Set(Object.keys(marks));
  if (days.size === 0) return [];
  const idxByDT = new Map<string, number>();
  candles.forEach((c, gi) => {
    const d = c.date.slice(0, 10);
    if (!days.has(d)) return;
    idxByDT.set(`${d} ${c.date.slice(11, 16)}`, gi);
  });
  const segs: FsSeg[] = [];
  for (const [day, m] of Object.entries(marks)) {
    const si = idxByDT.get(`${day} ${m.start.time}`);
    const ei = idxByDT.get(`${day} ${m.end.time}`);
    if (si === undefined || ei === undefined) continue;
    segs.push({
      day,
      startIdx: si,
      startPx: m.start.px,
      startKind: m.start.kind,
      endIdx: ei,
      endPx: m.end.px,
      endKind: m.end.kind,
    });
  }
  return segs;
}

const StockChart = forwardRef<StockChartHandle, Props>(function StockChart({ symbol, candles, intraday = false, interval = "daily", height = 720, swings, bias, trades, sessionBreaks, oneMinSwingN, swingDots = true, algoFlowLine, envelope, manualFirstSwing, algoFirstSwing, fsMarkers, fsBreaks, drawMode = false, onSwingDraw, onDrawStatus, onHoverTime }: Props, ref) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const fsPrimRef = useRef<FirstSwingPrimitive | null>(null);
  const syncPrimRef = useRef<SyncCrosshairPrimitive | null>(null);
  const hoverCbRef = useRef(onHoverTime);
  useEffect(() => {
    hoverCbRef.current = onHoverTime;
  });
  const biasMapsRef = useRef<{ m: Map<string, BiasLabel>; n: Map<string, BiasLabel> }>({
    m: new Map(),
    n: new Map(),
  });

  // bias lookup maps for the crosshair tooltip — mirrored via ref so bias
  // loading/toggling never rebuilds the chart
  useEffect(() => {
    const m = new Map<string, BiasLabel>((bias ?? []).map((b) => [b.date, b]));
    const n = new Map<string, BiasLabel>();
    bias?.forEach((lb) => {
      const prevDate = lb.details?.prev_date;
      if (prevDate) n.set(prevDate, lb);
    });
    biasMapsRef.current = { m, n };
  }, [bias]);
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
    // O(1) crosshair lookups — linear find() over 19k+ candles janks the UI
    const byTs = new Map<number, Candle>();
    if (intraday) {
      candles.forEach((c) => byTs.set(c.ts, c));
    }

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
    seriesRef.current = candleSer;

    const formatted = candles.map((c) => ({
      time: (intraday ? c.ts : c.date.slice(0, 10)) as any,
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close,
    }));

    candleSer.setData(formatted);

    // remote-pane sync cursor (vertical-only linked crosshair)
    const syncPrim = new SyncCrosshairPrimitive();
    chart.panes()[0].attachPrimitive(syncPrim);
    syncPrimRef.current = syncPrim;

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
          nextBias: biasMapsRef.current.m.get(lastDate)?.bias ?? null,
          nextBiasDate: lastDate,
        });
      }
    };

    chart.subscribeCrosshairMove((param) => {
      if (!param.time) { setLast(); setBiasTip(null); hoverCbRef.current?.(null); return; }
      const data = param.seriesData.get(candleSer) as any;
      if (!data) { setLast(); setBiasTip(null); hoverCbRef.current?.(null); return; }
      const t = param.time;
      hoverCbRef.current?.(timeToSec(t as Time));
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
        nextBias: hoveredDate ? biasMapsRef.current.m.get(hoveredDate)?.bias ?? null : null,
        nextBiasDate: hoveredDate ?? null,
      });
      const isLast = !!match && !!hoveredDate && lastByDate.get(hoveredDate)?.ts === match.ts;
      const nextLb = intraday && isLast && hoveredDate ? biasMapsRef.current.n.get(hoveredDate) : undefined;
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
        // both axes: layout toggle changes container height too — resize the
        // chart in place instead of rebuilding it (rebuild would dispose the
        // chart the overlay primitives are attached to)
        chart.applyOptions({
          width: containerRef.current.clientWidth,
          height: containerRef.current.clientHeight,
        });
      }
    };
    window.addEventListener("resize", handleResize);
    // container-width changes without a window resize (single <-> dual layout)
    const ro = new ResizeObserver(handleResize);
    if (containerRef.current) ro.observe(containerRef.current);

    return () => {
      window.removeEventListener("resize", handleResize);
      ro.disconnect();
      if (saveTimer) clearTimeout(saveTimer);
      const range = chart.timeScale().getVisibleRange();
      if (range) saveView(interval, { from: timeToSec(range.from), to: timeToSec(range.to) });
      chart.timeScale().unsubscribeVisibleTimeRangeChange(onVisibleTimeRangeChange);
      seriesRef.current = null;
      fsPrimRef.current = null;
      try {
        chart.panes()[0].detachPrimitive(syncPrim);
      } catch {}
      syncPrimRef.current = null;
      chartRef.current = null;
      // lightweight-charts v5.2.1 bug: a pending draw frame can execute AFTER
      // remove() and hit disposed canvases -> "Object is disposed" (crashes
      // layout switching when a pane unmounts mid-resize). Let any in-flight
      // frame flush against the still-alive chart, THEN dispose.
      const doomed = chart;
      let dropped = false;
      const drop = () => {
        if (dropped) return;
        dropped = true;
        try {
          doomed.remove();
        } catch {}
      };
      const rafId = requestAnimationFrame(drop);
      setTimeout(() => {
        cancelAnimationFrame(rafId);
        drop();
      }, 120);
    };
  }, [symbol, candles, intraday, interval]);
  // Lifecycle deps are DELIBERATELY minimal: every toggleable overlay lives in
  // its own effect below, so toggling anything never rebuilds this chart and
  // pan/zoom always survives. `height` is intentionally excluded — the initial
  // value is used at creation and later changes flow through the ResizeObserver
  // (applyOptions) so a layout toggle never disposes the chart the overlay
  // effects captured in their closures.
  // onSwingDraw / onDrawStatus must stay stable (useCallback) — page contract.

  // ── imperative crosshair-sync API (StockChartHandle) ──
  // Draws the remote sync line (vertical only — price axes are independent
  // per pane). Uses the custom primitive, NOT chart.setCrosshairPosition, so
  // the remote pane's own cursor/legend is never hijacked and no echo events
  // fire back.
  useImperativeHandle(
    ref,
    () => ({
      setCrosshairAt(sec: number) {
        const prim = syncPrimRef.current;
        if (!prim || !Number.isFinite(sec)) return;
        const t = intraday ? (sec as Time) : (new Date(sec * 1000).toISOString().slice(0, 10) as unknown as Time);
        prim.setTime(t);
      },
      clearCrosshair() {
        syncPrimRef.current?.setTime(null);
      },
    }),
    [intraday],
  );

  // ── overlay: prev-day bias arrows + 5-min HH/HL/LH/LL swing tags ──
  useEffect(() => {
    const ser = seriesRef.current;
    if (!ser || !intraday || !bias || bias.length === 0) return;
    const markers: SeriesMarker<Time>[] = [];

    const lastByDate = new Map<string, Candle>();
    candles.forEach((c) => {
      lastByDate.set(c.date.slice(0, 10), c);
    });
    const nextBiasMap = new Map<string, BiasLabel>();
    bias.forEach((lb) => {
      const prevDate = lb.details?.prev_date;
      if (prevDate) nextBiasMap.set(prevDate, lb);
    });

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
    const api = markers.length > 0 ? createSeriesMarkers(ser, markers) : null;
    return () => {
      try {
        api?.setMarkers([]);
      } catch {}
    };
  }, [intraday, interval, swingDots, bias, candles]);

  // ── overlay: per-day Williams fractal HH/HL/LH/LL tags (5-min + 1-min) ──
  useEffect(() => {
    const ser = seriesRef.current;
    if (!ser || !intraday || !swingDots) return;
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
        tagMarkers.push({
          time: candles[p.g].ts as Time,
          position: p.kind === "high" ? "aboveBar" : "belowBar",
          shape: "circle",
          color: tag === "HH" || tag === "HL" ? "#10b981" : "#f97316",
          text: tag,
          size: 0.5,
        });
      }
    });

    const api = tagMarkers.length > 0 ? createSeriesMarkers(ser, tagMarkers) : null;
    return () => {
      try {
        api?.setMarkers([]);
      } catch {}
    };
  }, [intraday, swingDots, oneMinSwingN, candles]);

  // ── overlay: Swing S/R labels & levels ──
  useEffect(() => {
    const chart = chartRef.current;
    const ser = seriesRef.current;
    if (!chart || !ser || !swings || swings.length === 0) return;
    const prim = new SwingSRPrimitive(ser, swings, intraday);
    chart.panes()[0].attachPrimitive(prim);
    return () => {
      try {
        chart.panes()[0].detachPrimitive(prim);
      } catch {}
    };
  }, [swings, intraday, candles]);

  // ── overlay: intraday backtest position boxes ──
  useEffect(() => {
    const chart = chartRef.current;
    const ser = seriesRef.current;
    if (!chart || !ser || !intraday || !trades || trades.length === 0) return;
    const prim = new PositionPrimitive(ser, trades);
    chart.panes()[0].attachPrimitive(prim);
    return () => {
      try {
        chart.panes()[0].detachPrimitive(prim);
      } catch {}
    };
  }, [trades, intraday, candles]);

  // ── overlay: session-break verticals ──
  useEffect(() => {
    const chart = chartRef.current;
    const ser = seriesRef.current;
    if (!chart || !ser || !intraday || !sessionBreaks) return;
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
    if (boundaryIdx.length === 0) return;
    const prim = new SessionBreakPrimitive(ser, boundaryIdx);
    chart.panes()[0].attachPrimitive(prim);
    return () => {
      try {
        chart.panes()[0].detachPrimitive(prim);
      } catch {}
    };
  }, [sessionBreaks, intraday, candles]);

  // ── overlay: algo flow-line (white) ──
  useEffect(() => {
    const ser = seriesRef.current;
    if (!ser || !intraday) return;
    let algoPrim: FlowLinePrimitive | null = null;
    if (algoFlowLine && algoFlowLine.length > 0) {
      algoPrim = new FlowLinePrimitive(ser, algoFlowLine, candles.length - 1, "#ffffff");
      ser.attachPrimitive(algoPrim);
    }
    return () => {
      try {
        if (algoPrim) ser.detachPrimitive(algoPrim);
      } catch {}
    };
  }, [algoFlowLine, intraday, candles]);

  // ── overlay: envelope-law red boxes ──
  useEffect(() => {
    const chart = chartRef.current;
    const ser = seriesRef.current;
    if (!chart || !ser || !intraday || !envelope || envelope.length === 0) return;
    const prim = new EnvelopePrimitive(ser, envelope, candles.length - 1);
    chart.panes()[0].attachPrimitive(prim);
    return () => {
      try {
        chart.panes()[0].detachPrimitive(prim);
      } catch {}
    };
  }, [envelope, intraday, candles]);

  // ── overlay: manual First-Swing GT (persistent primitive; marks sync via
  // setSegs below so saving/dragging never touches chart lifecycle) ──
  const fsActive = manualFirstSwing != null;
  useEffect(() => {
    const chart = chartRef.current;
    const ser = seriesRef.current;
    if (!chart || !ser || !intraday || !fsActive) return;
    const prim = new FirstSwingPrimitive(
      ser,
      manualFirstSwing ? fsSegsFromMarks(candles, manualFirstSwing) : [],
      candles.length - 1,
    );
    ser.attachPrimitive(prim);
    fsPrimRef.current = prim;
    return () => {
      try {
        ser.detachPrimitive(prim);
      } catch {}
      if (fsPrimRef.current === prim) fsPrimRef.current = null;
    };
    // manualFirstSwing contents intentionally excluded — see sync effect below
  }, [fsActive, intraday, candles]);

  // Live-sync FS segments into the persistent primitive (no chart rebuild).
  useEffect(() => {
    const prim = fsPrimRef.current;
    if (!prim || !intraday || !manualFirstSwing) return;
    prim.setSegs(fsSegsFromMarks(candles, manualFirstSwing));
  }, [manualFirstSwing, candles, intraday]);


  // ── interaction: FS draw-mode clicks + draggable endpoint handles ──
  // Lives on its own effect: toggling Draw never rebuilds the chart either.
  useEffect(() => {
    const chart = chartRef.current;
    const ser = seriesRef.current;
    const containerEl = containerRef.current;
    if (!chart || !ser || !containerEl || !intraday) return;

    const byTs = new Map<number, Candle>();
    candles.forEach((c) => byTs.set(c.ts, c));
    const dayIdxs = new Map<string, number[]>();
    candles.forEach((c, gi) => {
      const d = c.date.slice(0, 10);
      let arr = dayIdxs.get(d);
      if (!arr) {
        arr = [];
        dayIdxs.set(d, arr);
      }
      arr.push(gi);
    });

    // ---- two-click draw ----
    let pendingClick: number | null = null;
    let suppressClickUntil = 0;
    const handleChartClick = (param: MouseEventParams<Time>) => {
      if (!drawMode || !param.point || param.time == null) return;
      if (performance.now() < suppressClickUntil) return;
      const t = typeof param.time === "number" ? param.time : NaN;
      const c2 = Number.isFinite(t) ? byTs.get(t) : undefined;
      if (!c2) return;

      if (pendingClick == null) {
        pendingClick = t;
        onDrawStatus?.(
          `FS draw ${c2.date.slice(0, 10)}: start=${c2.date.slice(11, 16)} — click END candle`,
        );
        return;
      }

      const c1 = byTs.get(pendingClick);
      pendingClick = null;
      if (!c1) return;
      const day1 = c1.date.slice(0, 10);
      const day2 = c2.date.slice(0, 10);
      if (day1 !== day2 || c1.ts === c2.ts) {
        onDrawStatus?.("FS draw: start & end must be different candles of the SAME day — redraw");
        return;
      }
      const up = c2.close >= c1.close;
      const mark = {
        start: { time: c1.date.slice(11, 16), kind: up ? ("L" as const) : ("H" as const), px: up ? c1.low : c1.high },
        end: { time: c2.date.slice(11, 16), kind: up ? ("H" as const) : ("L" as const), px: up ? c2.high : c2.low },
      };
      onDrawStatus?.(
        `Saved ${day1}: ${mark.start.kind}@${mark.start.time} → ${mark.end.kind}@${mark.end.time}`,
      );
      onSwingDraw?.({ day: day1, start: mark.start, end: mark.end });
    };
    if (drawMode) chart.subscribeClick(handleChartClick);

    // ---- endpoint drag ----
    let dragState: { day: string; which: "start" | "end" } | null = null;
    let lastPreview: { day: string; which: "start" | "end"; idx: number; px: number } | null = null;

    const relPos = (e: MouseEvent) => {
      const r = containerEl.getBoundingClientRect();
      return { x: e.clientX - r.left, y: e.clientY - r.top };
    };

    const onMouseDown = (e: MouseEvent) => {
      const prim = fsPrimRef.current;
      if (!drawMode || !prim || e.button !== 0) return;
      const { x, y } = relPos(e);
      const h = prim.pickHandle(x, y);
      if (!h) return;
      e.preventDefault();
      dragState = { day: h.day, which: h.which };
      lastPreview = null;
      chart.applyOptions({
        handleScroll: { horzTouchDrag: false, vertTouchDrag: false, mouseWheel: false, pressedMouseMove: false },
      });
      containerEl.style.cursor = "grabbing";
    };

    const onMouseMove = (e: MouseEvent) => {
      const prim = fsPrimRef.current;
      if (!prim) return;
      const { x, y } = relPos(e);
      if (dragState) {
        const logical = chart.timeScale().coordinateToLogical(x as Logical);
        if (logical == null) return;
        const bounds = dayIdxs.get(dragState.day);
        if (!bounds || bounds.length === 0) return;
        const idx = Math.min(Math.max(Math.round(logical), bounds[0]), bounds[bounds.length - 1]);
        const candle = candles[idx];
        const cur = prim.segOf(dragState.day);
        if (!cur) return;
        const kind = dragState.which === "start" ? cur.startKind : cur.endKind;
        const px = kind === "L" ? candle.low : candle.high;
        lastPreview = { day: dragState.day, which: dragState.which, idx, px };
        prim.preview(dragState.day, dragState.which, idx, px);
      } else {
        const h = drawMode ? prim.pickHandle(x, y) : null;
        containerEl.style.cursor = h ? "grab" : "";
      }
    };

    const finishDrag = () => {
      const prim = fsPrimRef.current;
      if (dragState && lastPreview && prim) {
        const cur = prim.segOf(lastPreview.day);
        const s = cur ? candles[cur.startIdx] : undefined;
        const e = cur ? candles[cur.endIdx] : undefined;
        if (cur && s && e) {
          const updated = {
            start: { time: s.date.slice(11, 16), kind: cur.startKind, px: cur.startPx },
            end: { time: e.date.slice(11, 16), kind: cur.endKind, px: cur.endPx },
          };
          onDrawStatus?.(
            `Updated ${lastPreview.day}: ${updated.start.kind}@${updated.start.time} → ${updated.end.kind}@${updated.end.time}`,
          );
          onSwingDraw?.({ day: lastPreview.day, ...updated });
          suppressClickUntil = performance.now() + 250;
        }
      }
      dragState = null;
      lastPreview = null;
      chart.applyOptions({
        handleScroll: { horzTouchDrag: true, vertTouchDrag: true, mouseWheel: true, pressedMouseMove: true },
      });
      containerEl.style.cursor = "";
    };

    const onMouseUp = () => {
      if (dragState) finishDrag();
    };
    const onMouseLeave = () => {
      if (!dragState) containerEl.style.cursor = "";
    };

    if (drawMode) {
      containerEl.addEventListener("mousedown", onMouseDown);
      containerEl.addEventListener("mousemove", onMouseMove);
      containerEl.addEventListener("mouseup", onMouseUp);
      containerEl.addEventListener("mouseleave", onMouseLeave);
    }

    return () => {
      try {
        chart.unsubscribeClick(handleChartClick);
      } catch {}
      containerEl.removeEventListener("mousedown", onMouseDown);
      containerEl.removeEventListener("mousemove", onMouseMove);
      containerEl.removeEventListener("mouseup", onMouseUp);
      containerEl.removeEventListener("mouseleave", onMouseLeave);
      containerEl.style.cursor = "";
    };
  }, [drawMode, intraday, candles]);

  // ── overlay: First-Swing ALGO candidate — cyan = declared, red = invalid ──
  useEffect(() => {
    const ser = seriesRef.current;
    if (!ser || !intraday || !algoFirstSwing || algoFirstSwing.length === 0) return;
    let mkApi: ISeriesMarkersPluginApi<Time> | null = null;
    // break markers first (B1/B2/FLIP) so FS/SUS arrows stay visually on top
    const ms: SeriesMarker<Time>[] = [];
    for (const b of fsBreaks ?? []) {
      const cc = candles[b.idx];
      if (!cc) continue;
      ms.push({
        time: cc.ts as Time,
        position: b.dir === "up" ? "aboveBar" : "belowBar",
        shape: "circle",
        color: b.kind === "FLIP" ? "#f97316" : "#64748b",
        text: b.kind,
        size: 1,
      });
    }
    if (fsMarkers && fsMarkers.length > 0) {
      for (const mk of fsMarkers) {
        const cc = candles[mk.idx];
        if (!cc) continue;
        const isSustain = mk.source === "sustain";
        ms.push({
          time: cc.ts as Time,
          position: "belowBar",
          shape: "arrowUp",
          color: mk.invalid ? "#ef4444" : isSustain ? "#a78bfa" : "#22d3ee",
          text: mk.invalid ? "FS" : isSustain ? "SUS" : "FS",
          size: 1,
        });
      }
    }
    if (ms.length > 0) mkApi = createSeriesMarkers(ser, ms);
    const okSegs = algoFirstSwing.filter((s) => !s.invalid);
    const badSegs = algoFirstSwing.filter((s) => s.invalid);
    const prims: FlowLinePrimitive[] = [];
    if (okSegs.length > 0) {
      const p = new FlowLinePrimitive(ser, okSegs, candles.length - 1, "#22d3ee", 2);
      ser.attachPrimitive(p);
      prims.push(p);
    }
    if (badSegs.length > 0) {
      const p = new FlowLinePrimitive(ser, badSegs, candles.length - 1, "#ef4444", 2);
      ser.attachPrimitive(p);
      prims.push(p);
    }
    return () => {
      for (const p of prims) {
        try {
          ser.detachPrimitive(p);
        } catch {}
      }
      mkApi?.setMarkers([]);
    };
  }, [algoFirstSwing, fsMarkers, fsBreaks, intraday, candles]);

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
});

export default StockChart;
