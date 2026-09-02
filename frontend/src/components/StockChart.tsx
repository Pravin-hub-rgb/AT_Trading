"use client";

import {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
} from "react";
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
import type { Candle, BiasLabel } from "@/lib/api";
import { SwingSRPrimitive, SwingPoint } from "./SwingSRPrimitive";
import {
  WholeDaySwingPrimitive,
  type WholeDaySwingPoint,
} from "./WholeDaySwingPrimitive";
import { PositionPrimitive, TradeBox } from "./PositionPrimitive";
import { SessionBreakPrimitive } from "./SessionBreakPrimitive";
import { FlowLinePrimitive, FlowSegment } from "./FlowLinePrimitive";
import { EnvelopePrimitive } from "./EnvelopePrimitive";
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
  algoFlowLine?: FlowSegment[] | null;
  envelope?: EnvelopeViolation[] | null;
  algoFirstSwing?: (FlowSegment & { invalid?: boolean })[] | null;
  algoSecondSwing?: (FlowSegment & { fs1Dir?: "up" | "down" | null })[] | null;
  /** Whole-day swings with zigzag line rendering (cyan/yellow alternating).
   *  Default ON — renders automatically on 1min intraday chart. */
  wholeDaySwings?: WholeDaySwingPoint[];
  // Per-date trade_mode map from intraday backtest (aggressive/conservative/skip)
  tradeMode?: Record<string, string | null>;
  algoSecondSwingMarkers?:
    | {
        idx: number;
        invalid: boolean;
        source?: "chop" | "sustain" | null;
        dir?: "up" | "down" | null;
      }[]
    | null;
  algoSecondSwingBreaks?:
    | {
        idx: number;
        time: string;
        kind: "B1" | "B2" | "FLIP";
        dir: "up" | "down";
        px: number;
      }[]
    | null;
  fsMarkers?:
    | {
        idx: number;
        invalid: boolean;
        source?: "chop" | "sustain" | null;
        dir?: "up" | "down" | null;
      }[]
    | null;
  fsBreaks?:
    | {
        idx: number;
        time: string;
        kind: "B1" | "B2" | "FLIP";
        dir: "up" | "down";
        px: number;
      }[]
    | null;
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
  // Trade mode for the *session/day* the candle belongs to.
  // "aggressive" ⚡, "conservative" 🐢, "skip" (no entry). From intraday
  // backtest's per-day trade_mode field. Hovered candle drives the lookup;
  // null while no backtest is loaded.
  tradeMode?: string | null;
}

const IST_OFFSET = 5.5 * 3600;
const MONTHS = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];
const VIEWS_KEY = "chart_views";

function istDate(
  time: number | string | { year: number; month: number; day: number },
): Date {
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

function formatDateLabel(
  time: number | string | { year: number; month: number; day: number },
): string {
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

const StockChart = forwardRef<StockChartHandle, Props>(function StockChart(
  {
    symbol,
    candles,
    intraday = false,
    interval = "daily",
    height = 720,
    swings,
    bias,
    trades,
    sessionBreaks,
    algoFlowLine,
    envelope,
    algoFirstSwing,
    algoSecondSwing,
    algoSecondSwingMarkers,
    algoSecondSwingBreaks,
    wholeDaySwings,
    fsMarkers,
    fsBreaks,
    tradeMode,
    onHoverTime,
  }: Props,
  ref,
) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const syncPrimRef = useRef<SyncCrosshairPrimitive | null>(null);
  const positionPrimRef = useRef<PositionPrimitive | null>(null);
  const wholeDayPrimRef = useRef<WholeDaySwingPrimitive | null>(null);
  const hoverCbRef = useRef(onHoverTime);
  useEffect(() => {
    hoverCbRef.current = onHoverTime;
  });
  const biasMapsRef = useRef<{
    m: Map<string, BiasLabel>;
    n: Map<string, BiasLabel>;
  }>({
    m: new Map(),
    n: new Map(),
  });

  // bias lookup maps for the crosshair tooltip - mirrored via ref so bias
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

  // tradeMode map (date -> aggressive/conservative/skip) - mirrored into a
  // ref so the chart's setLast() and crosshair callback always see the
  // current value even if the prop arrives after mount.
  const tradeModeRef = useRef<Record<string, string | null> | undefined>(
    undefined,
  );
  useEffect(() => {
    tradeModeRef.current = tradeMode;
    // After tradeMode arrives (or changes), refresh the ohlcv display so the
    // newly-available per-day mode is shown for the currently-hovered candle.
    setOhlcv((prev) =>
      prev
        ? { ...prev, tradeMode: tradeMode?.[prev.nextBiasDate ?? ""] ?? null }
        : prev,
    );
  }, [tradeMode]);
  const [ohlcv, setOhlcv] = useState<OHLCV | null>(null);
  const [biasTip, setBiasTip] = useState<{
    x: number;
    y: number;
    paneW: number;
    label: BiasLabel;
  } | null>(null);
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

    const prevRange = chartRef.current
      ? chartRef.current.timeScale().getVisibleRange()
      : null;

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
        vertLine: {
          color: "#6366f1",
          width: 1,
          style: 2,
          labelBackgroundColor: "#6366f1",
        },
        horzLine: {
          color: "#6366f1",
          width: 1,
          style: 2,
          labelBackgroundColor: "#6366f1",
        },
      },
      timeScale: {
        borderColor: "#334155",
        timeVisible: intraday,
        secondsVisible: false,
        tickMarkFormatter: (
          time: number | string,
          tickMarkType: TickMarkType,
        ) => {
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
        timeFormatter: (
          time: number | string | { year: number; month: number; day: number },
        ) => formatDateLabel(time),
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
    const onVisibleTimeRangeChange: TimeRangeChangeEventHandler<Time> = (
      timeRange,
    ) => {
      if (!timeRange) return;
      if (saveTimer) clearTimeout(saveTimer);
      saveTimer = setTimeout(() => {
        saveView(interval, {
          from: timeToSec(timeRange.from),
          to: timeToSec(timeRange.to),
        });
      }, 400);
    };
    chart.timeScale().subscribeVisibleTimeRangeChange(onVisibleTimeRangeChange);

    const defaultView = () => {
      const lastIndex = formatted.length - 1;
      if (intraday) {
        chart.timeScale().setVisibleLogicalRange({
          from: Math.max(0, lastIndex - 149),
          to: lastIndex + 1,
        });
      } else {
        chart.timeScale().fitContent();
      }
    };

    const views = loadViews();
    const anchor =
      views[interval] ?? views[interval === "5min" ? "daily" : "5min"] ?? null;
    const firstT = timeToSec(formatted[0].time);
    const lastT = timeToSec(formatted[formatted.length - 1].time);

    const applyRange = (fromSec: number, toSec: number) => {
      const from = Math.max(fromSec, firstT);
      const to = Math.min(toSec, lastT);
      if (to > from) {
        chart.timeScale().setVisibleRange({
          from: secToSeriesTime(from, intraday),
          to: secToSeriesTime(to, intraday),
        });
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
        const tmMap = tradeModeRef.current;
        const tm = tmMap?.[lastDate] ?? null;
        setOhlcv({
          date: formatDateLabel(intraday ? last.ts : last.date.slice(0, 10)),
          open: last.open,
          high: last.high,
          low: last.low,
          close: last.close,
          volume: last.volume,
          nextBias: biasMapsRef.current.m.get(lastDate)?.bias ?? null,
          nextBiasDate: lastDate,
          tradeMode: tm,
        });
      }
    };

    chart.subscribeCrosshairMove((param) => {
      if (!param.time) {
        setLast();
        setBiasTip(null);
        hoverCbRef.current?.(null);
        return;
      }
      const data = param.seriesData.get(candleSer) as any;
      if (!data) {
        setLast();
        setBiasTip(null);
        hoverCbRef.current?.(null);
        return;
      }
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
        date: formatDateLabel(
          t as number | string | { year: number; month: number; day: number },
        ),
        open: data.open,
        high: data.high,
        low: data.low,
        close: data.close,
        volume: match?.volume ?? 0,
        nextBias: hoveredDate
          ? (biasMapsRef.current.m.get(hoveredDate)?.bias ?? null)
          : null,
        nextBiasDate: hoveredDate ?? null,
        tradeMode: hoveredDate
          ? (tradeModeRef.current?.[hoveredDate] ?? null)
          : null,
      });
      const isLast =
        !!match &&
        !!hoveredDate &&
        lastByDate.get(hoveredDate)?.ts === match.ts;
      const nextLb =
        intraday && isLast && hoveredDate
          ? biasMapsRef.current.n.get(hoveredDate)
          : undefined;
      if (nextLb && param.point) {
        const paneW = containerRef.current?.clientWidth ?? 800;
        setBiasTip({
          x: param.point.x,
          y: param.point.y,
          label: nextLb,
          paneW,
        });
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
      if (range)
        saveView(interval, {
          from: timeToSec(range.from),
          to: timeToSec(range.to),
        });
      chart
        .timeScale()
        .unsubscribeVisibleTimeRangeChange(onVisibleTimeRangeChange);
      seriesRef.current = null;
      try {
        chart.panes()[0].detachPrimitive(syncPrim);
      } catch {}
      syncPrimRef.current = null;
      if (positionPrimRef.current) {
        try {
          chart.panes()[0].detachPrimitive(positionPrimRef.current);
        } catch {}
        positionPrimRef.current = null;
      }
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
        const t = intraday
          ? (sec as Time)
          : (new Date(sec * 1000)
              .toISOString()
              .slice(0, 10) as unknown as Time);
        prim.setTime(t);
      },
      clearCrosshair() {
        syncPrimRef.current?.setTime(null);
      },
    }),
    [intraday],
  );

  // ── overlay: ALL markers (consolidated into single effect to prevent interference) ──
  // This combines: bias arrows, Williams fractal tags, fsBreaks (B1/B2/FLIP), and fsMarkers (FS/SUS)

  // Filter intermediate marks: keep only the first B1 + the last decisive break
  // (last FLIP/B2). Engine may emit FLIP@10:16 + FLIP@10:17 whipsaw — only
  // FLIP@10:17 (last) matters on the chart.
  const filterBreaks = <
    T extends { kind: "B1" | "B2" | "FLIP"; idx: number },
  >(
    breaks: T[],
  ): T[] => {
    if (breaks.length <= 1) return breaks;
    const first = breaks.find((b) => b.kind === "B1") ?? breaks[0];
    const nonB1 = breaks.filter((b) => b.kind !== "B1");
    if (nonB1.length === 0) return [first];
    const last = nonB1[nonB1.length - 1];
    return [first, last];
  };

  useEffect(() => {
    const ser = seriesRef.current;
    if (!ser || !intraday) return;
    const markers: SeriesMarker<Time>[] = [];

    // 1. Bias arrows (prev-day bias arrows)
    if (bias && bias.length > 0) {
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
          lb.bias === "bullish"
            ? "#10b981"
            : lb.bias === "bearish"
              ? "#ef4444"
              : "#8b949e";
        const shape =
          lb.bias === "bullish"
            ? "arrowUp"
            : lb.bias === "bearish"
              ? "arrowDown"
              : "circle";
        markers.push({
          time: c.ts as Time,
          position: "belowBar",
          shape,
          color,
          size: 2,
        });
      });

      // 5-min HH/HL/LH/LL swing tags from bias
      if (interval === "5min") {
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
    }

    // 2. Break markers (B1/B2/FLIP) - added first so they render below
    // Filtering is done per-swing in page.tsx before flatMap; do NOT
    // re-filter globally here or multi-day B1s get dropped.
    for (const b of fsBreaks ?? []) {
      const cc = candles[b.idx];
      if (!cc) continue;
      markers.push({
        time: cc.ts as Time,
        position: "belowBar",
        shape: "arrowUp",
        color:
          b.kind === "FLIP"
            ? "#f97316"
            : b.kind === "B2"
              ? "#60a5fa"
              : "#94a3b8",
        text: b.kind,
        size: 1,
      });
    }

    // 4. FS/SUS markers - added last so they render on top
    if (fsMarkers && fsMarkers.length > 0) {
      for (const mk of fsMarkers) {
        const cc = candles[mk.idx];
        if (!cc) continue;
        const isSustain = mk.source === "sustain";
        markers.push({
          time: cc.ts as Time,
          position: "belowBar",
          shape: "arrowUp",
          color: mk.invalid ? "#ef4444" : isSustain ? "#a78bfa" : "#22d3ee",
          text: mk.invalid ? "FS" : isSustain ? "SUS" : "FS",
          size: 1,
        });
      }
    }

    // 5. Second-swing break markers (B1/B2/FLIP) — yellow/gold palette to
    //    distinguish from cyan first-swing breaks above. Labels mirror
    //    first-swing ("B1"/"B2"/"FLIP") — only the colour identifies the
    //    swing, the kind stays the same.
    for (const b of algoSecondSwingBreaks ?? []) {
      const cc = candles[b.idx];
      if (!cc) continue;
      markers.push({
        time: cc.ts as Time,
        position: "aboveBar",
        shape: "arrowDown",
        color:
          b.kind === "FLIP"
            ? "#eab308"
            : b.kind === "B2"
              ? "#fde047"
              : "#facc15",
        text: b.kind,
        size: 1,
      });
    }

    // 6. Second-swing FS/SUS markers — yellow/orange palette.
    if (algoSecondSwingMarkers && algoSecondSwingMarkers.length > 0) {
      for (const mk of algoSecondSwingMarkers) {
        const cc = candles[mk.idx];
        if (!cc) continue;
        const isSustain = mk.source === "sustain";
        markers.push({
          time: cc.ts as Time,
          position: "aboveBar",
          shape: "arrowDown",
          color: mk.invalid ? "#ef4444" : isSustain ? "#fb923c" : "#facc15",
          text: mk.invalid ? "FS2" : isSustain ? "SUS2" : "FS2",
          size: 1,
        });
      }
    }

    // Sort markers by time for consistent rendering
    markers.sort((a, b) => timeToSec(a.time) - timeToSec(b.time));

    const api = markers.length > 0 ? createSeriesMarkers(ser, markers) : null;
    return () => {
      try {
        api?.setMarkers([]);
      } catch {}
    };
  }, [
    intraday,
    interval,
    bias,
    candles,
    fsMarkers,
    fsBreaks,
    algoSecondSwingMarkers,
    algoSecondSwingBreaks,
  ]);

  // ── overlay: whole-day swing arrow markers ──
  // Mirrors the exact shape/color/text convention used by fsMarkers/fsBreaks:
  //   • each B1/B2/FLIP → arrowUp, belowBar, at the break's ACTUAL bar
  //     FLIP → orange (#f97316), B2 → blue (#60a5fa), B1 → grey (#94a3b8)
  //   • FS/SUS → arrowDown, aboveBar, at the swing's confirmation bar
  //     SUS → violet (#a78bfa), FS → the swing's line tone (cyan/yellow)
  // Previously the decisive break was drawn once at the swing's END bar, which
  // made e.g. a FLIP appear at the swing end instead of its true bar — now each
  // mark (B1/B2/FLIP) is drawn at its own bar + the FS/SUS at the confirmed bar.
  useEffect(() => {
    const ser = seriesRef.current;
    if (!ser || !intraday) return;
    if (!wholeDaySwings || wholeDaySwings.length === 0) return;

    const markers: SeriesMarker<Time>[] = [];
    for (const s of wholeDaySwings) {
      // Skip swing_index 0 and 1 — those already have fsMarkers/fsBreaks markers.
      if (s.swing_index < 2) continue;

      // Human swing number: swing_index 0 = 1st, 1 = 2nd, 2 = 3rd, 3 = 4th ...
      // Every mark below is suffixed with this so you always know which swing
      // a B1/B2/FLIP/FS/SUS belongs to (e.g. "B1-3", "FLIP-3", "FS-3").
      const swingNo = s.swing_index + 1;

      // Break markers (B1/B2/FLIP) — one arrow per break at its actual bar.
      // Defensive fallback for older backend responses that lack `breaks`:
      // draw the decisive break at the swing's end bar so marks are never missing.
      const brks: {
        idx: number;
        time?: string;
        kind: "B1" | "B2" | "FLIP";
        dir: "up" | "down";
        px: number;
      }[] =
        Array.isArray(s.breaks) && s.breaks.length > 0
          ? s.breaks
          : s.break_kind
            ? [
                {
                  idx: s.end_idx,
                  kind: s.break_kind,
                  dir: s.dir === "B" ? "up" : "down",
                  px: s.end_px,
                },
              ]
            : [];
      for (const b of filterBreaks(brks)) {
        const cc = candles[b.idx];
        if (!cc) continue;
        markers.push({
          time: cc.ts as Time,
          position: "belowBar",
          shape: "arrowUp",
          color:
            b.kind === "FLIP"
              ? "#f97316"
              : b.kind === "B2"
                ? "#60a5fa"
                : "#94a3b8",
          text: `${b.kind}-${swingNo}`,
          size: 1,
        });
      }

      // Confirmation marker (FS / SUS) — at the swing's OWN structural completion
      // bar (fs_at_idx, the opposing pivot-break) when available, else the
      // confirmed bar, else the swing end.
      if (s.kind) {
        const confIdx =
          (s.fs_at_idx ?? -1) >= 0
            ? (s.fs_at_idx as number)
            : s.confirmed_at_idx >= 0
              ? s.confirmed_at_idx
              : s.end_idx;
        const cc = candles[confIdx];
        if (cc) {
          const isSustain = s.kind === "SUS";
          const lineTone = s.swing_index % 2 === 0 ? "#22d3ee" : "#facc15"; // cyan/yellow
          markers.push({
            time: cc.ts as Time,
            position: "aboveBar",
            shape: "arrowDown",
            color: isSustain ? "#a78bfa" : lineTone,
            text: `${s.kind}-${swingNo}`,
            size: 1,
          });
        }
      }
    }

    markers.sort((a, b) => timeToSec(a.time) - timeToSec(b.time));
    const api = markers.length > 0 ? createSeriesMarkers(ser, markers) : null;
    return () => {
      try {
        api?.setMarkers([]);
      } catch {}
    };
  }, [wholeDaySwings, intraday, candles]);

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

    // Detach the previous position primitive if it exists
    if (positionPrimRef.current) {
      try {
        chart.panes()[0].detachPrimitive(positionPrimRef.current);
      } catch {}
    }

    const prim = new PositionPrimitive(ser, trades);
    chart.panes()[0].attachPrimitive(prim);
    positionPrimRef.current = prim;

    return () => {
      positionPrimRef.current = null;
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
      algoPrim = new FlowLinePrimitive(
        ser,
        algoFlowLine,
        candles.length - 1,
        "#ffffff",
      );
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
    if (!chart || !ser || !intraday || !envelope || envelope.length === 0)
      return;
    const prim = new EnvelopePrimitive(ser, envelope, candles.length - 1);
    chart.panes()[0].attachPrimitive(prim);
    return () => {
      try {
        chart.panes()[0].detachPrimitive(prim);
      } catch {}
    };
  }, [envelope, intraday, candles]);

  // ── overlay: Whole-day swing zigzag (cyan/yellow alternating) ──
  useEffect(() => {
    const chart = chartRef.current;
    const ser = seriesRef.current;
    if (!chart || !ser || !intraday) return;
    if (!wholeDaySwings || wholeDaySwings.length === 0) return;

    const prim = new WholeDaySwingPrimitive(ser, wholeDaySwings);
    chart.panes()[0].attachPrimitive(prim);
    wholeDayPrimRef.current = prim;
    return () => {
      wholeDayPrimRef.current = null;
      try {
        chart.panes()[0].detachPrimitive(prim);
      } catch {}
    };
  }, [wholeDaySwings, intraday, candles]);

  // ── overlay: First-Swing ALGO flow lines (cyan = declared, red = invalid) ──
  useEffect(() => {
    const ser = seriesRef.current;
    if (!ser || !intraday || !algoFirstSwing || algoFirstSwing.length === 0)
      return;
    const okSegs = algoFirstSwing.filter((s) => !s.invalid);
    const badSegs = algoFirstSwing.filter((s) => s.invalid);
    const prims: FlowLinePrimitive[] = [];
    if (okSegs.length > 0) {
      const p = new FlowLinePrimitive(
        ser,
        okSegs,
        candles.length - 1,
        "#22d3ee",
        2,
      );
      ser.attachPrimitive(p);
      prims.push(p);
    }
    if (badSegs.length > 0) {
      const p = new FlowLinePrimitive(
        ser,
        badSegs,
        candles.length - 1,
        "#ef4444",
        2,
      );
      ser.attachPrimitive(p);
      prims.push(p);
    }
    return () => {
      for (const p of prims) {
        try {
          ser.detachPrimitive(p);
        } catch {}
      }
    };
  }, [algoFirstSwing, intraday, candles]);

  // ── overlay: Second-Swing flow lines (yellow) ──
  useEffect(() => {
    const ser = seriesRef.current;
    if (!ser || !intraday || !algoSecondSwing || algoSecondSwing.length === 0)
      return;
    const prims: FlowLinePrimitive[] = [];
    const p = new FlowLinePrimitive(
      ser,
      algoSecondSwing,
      candles.length - 1,
      "#eab308",
      2,
    );
    ser.attachPrimitive(p);
    prims.push(p);
    return () => {
      for (const prim of prims) {
        try {
          ser.detachPrimitive(prim);
        } catch {}
      }
    };
  }, [algoSecondSwing, intraday, candles]);

  // On-chart diagnostic: proves whether break marks reached the chart
  const fsBreakCount = fsBreaks?.length ?? 0;
  const fsMarkCount = fsMarkers?.length ?? 0;

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
            <span style={{ color: "#e2e8f0" }}>
              O: <b>{ohlcv.open.toFixed(2)}</b>
            </span>
            <span style={{ color: "#10b981" }}>
              H: <b>{ohlcv.high.toFixed(2)}</b>
            </span>
            <span style={{ color: "#ef4444" }}>
              L: <b>{ohlcv.low.toFixed(2)}</b>
            </span>
            <span style={{ color: "#e2e8f0" }}>
              C: <b>{ohlcv.close.toFixed(2)}</b>
            </span>
            {ohlcv.volume > 0 && (
              <span style={{ color: "#94a3b8" }}>
                Vol: <b>{ohlcv.volume.toLocaleString()}</b>
              </span>
            )}
          </div>
          {fsMarkCount > 0 && (
            <div style={{ marginTop: 2, color: "#94a3b8" }}>
              FS/SUS: <b style={{ color: "#22d3ee" }}>{fsMarkCount}</b>
              {"  |  B-marks: "}
              <b style={{ color: fsBreakCount > 0 ? "#facc15" : "#ef4444" }}>
                {fsBreakCount}
              </b>
              {fsBreakCount === 0 && (
                <span style={{ color: "#ef4444" }}> (none received!)</span>
              )}
            </div>
          )}
          {ohlcv.nextBias && (
            <div
              style={{
                color:
                  ohlcv.nextBias === "bullish"
                    ? "#10b981"
                    : ohlcv.nextBias === "bearish"
                      ? "#ef4444"
                      : "#9ca3af",
                marginTop: 2,
                fontWeight: 600,
              }}
            >
              {ohlcv.nextBias === "bullish"
                ? "\u25B2"
                : ohlcv.nextBias === "bearish"
                  ? "\u25BC"
                  : "\u25CF"}{" "}
              Bias: {ohlcv.nextBias}
            </div>
          )}
          {tradeMode !== undefined && (
            <div
              style={{
                color:
                  ohlcv.tradeMode === "aggressive"
                    ? "#fbbf24" // amber for aggressive ⚡
                    : ohlcv.tradeMode === "conservative"
                      ? "#a78bfa" // violet for conservative 🐢
                      : ohlcv.tradeMode === "skip"
                        ? "#6b7280" // grey for skip
                        : "#94a3b8", // muted grey for unknown / no-data
                marginTop: 2,
                fontWeight: 600,
              }}
              title={
                ohlcv.tradeMode === "aggressive"
                  ? "Aggressive mode: 2nd pivot break of first swing (FS opposite bias)"
                  : ohlcv.tradeMode === "conservative"
                    ? "Conservative mode: 2nd pivot break of opposite swing (FS same as bias)"
                    : ohlcv.tradeMode === "skip"
                      ? "Skip: no trade today (unbiased or no setup)"
                      : "No trade_mode data for this day (backtest not loaded)"
              }
            >
              {ohlcv.tradeMode === "aggressive"
                ? "\u26A1"
                : ohlcv.tradeMode === "conservative"
                  ? "\uD83D\uDC22"
                  : ohlcv.tradeMode === "skip"
                    ? "\u2715"
                    : "\u2014"}{" "}
              {ohlcv.tradeMode
                ? ohlcv.tradeMode[0].toUpperCase() + ohlcv.tradeMode.slice(1)
                : "No mode"}
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
      {(pinnedBiasTip ?? biasTip) &&
        (() => {
          const tip = pinnedBiasTip ?? biasTip!;
          const pinned = !!pinnedBiasTip;
          return (
            <div
              style={{
                position: "absolute",
                left: Math.min(
                  Math.max(tip.x + 14, 8),
                  Math.max(tip.paneW - 330, 8),
                ),
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
                  onClick={(e) => {
                    e.stopPropagation();
                    setPinnedBiasTip(null);
                  }}
                  style={{
                    position: "absolute",
                    top: 4,
                    right: 8,
                    cursor: "pointer",
                    color: "#94a3b8",
                    fontSize: 12,
                    lineHeight: "12px",
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
                {pinned ? "\uD83D\uDCCC " : ""}Bias for {tip.label.date}:{" "}
                {tip.label.bias}
              </div>
              {tip.label.overview?.sh_price !== undefined &&
                tip.label.overview?.sl_price !== undefined && (
                  <div style={{ color: "#79c0ff", marginBottom: 2 }}>
                    <b>ZONES:</b> {tip.label.overview.zone ?? "-"} Ã‚Â· pos{" "}
                    {tip.label.overview.pos_pct ?? "?"}% | SL{" "}
                    {tip.label.overview.sl_price} ({tip.label.overview.sl_date})
                    {" \u2190 "}
                    {tip.label.overview.pos_pct ?? "?"}%{" \u2192 "}SH{" "}
                    {tip.label.overview.sh_price} ({tip.label.overview.sh_date})
                  </div>
                )}
              {tip.label.prev_day?.structure && (
                <div style={{ color: "#d29922", marginBottom: 2 }}>
                  <b>CLOSING SESSION:</b> structure{" "}
                  {tip.label.prev_day.structure}
                  {tip.label.prev_day.sustain
                    ? ` Ã‚Â· sustain ${tip.label.prev_day.sustain}`
                    : ""}
                  {tip.label.prev_day.close_pos_pct != null
                    ? ` (close at ${tip.label.prev_day.close_pos_pct}%)`
                    : ""}
                  {tip.label.prev_day.summary
                    ? ` Ã¢Â€Â” ${tip.label.prev_day.summary}`
                    : ""}
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
