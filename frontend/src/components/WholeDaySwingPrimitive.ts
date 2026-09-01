"use client";

import type {
  IChartApi,
  IPanePrimitive,
  IPanePrimitivePaneView,
  IPrimitivePaneRenderer,
  ISeriesApi,
  Logical,
  PrimitivePaneViewZOrder,
  Time,
} from "lightweight-charts";
import type { CanvasRenderingTarget2D } from "fancy-canvas";

/**
 * A single marked break (B1 / B2 / FLIP) at its own global bar index & price.
 */
export interface WholeDayBreakMark {
  /** Global bar index where this break occurred. */
  idx: number;
  /** HH:MM time of the break. */
  time: string;
  kind: "B1" | "B2" | "FLIP";
  dir: "up" | "down";
  px: number;
}

/**
 * A single whole-day swing point.
 * dir: "B" (buy/up) means the swing is going UP — start_px < end_px
 * dir: "S" (sell/down) means the swing is going DOWN — start_px > end_px
 *
 * For drawing a zigzag: each swing has a start and end. Consecutive swings
 * share a turning point — swing N's end is swing N+1's start.
 */
export interface WholeDaySwingPoint {
  dir: "B" | "S";
  /** Global bar index where this swing starts. */
  start_idx: number;
  /** Price at swing start. */
  start_px: number;
  /** Global bar index where this swing ends (turning point). */
  end_idx: number;
  /** Price at swing end (turning point). */
  end_px: number;
  /** Per-day swing index (0, 1, 2, ...). Even → cyan, odd → yellow. */
  swing_index: number;
  /** "SUS" or "FS" — label at the confirmation/turning point. */
  kind: string;
  /** "B1", "B2", "FLIP" or null — first break marker kind. */
  break_kind: "B1" | "B2" | "FLIP" | null;
  /** Full ordered list of break marks for this swing (each drawn at its own bar). */
  breaks: WholeDayBreakMark[];
  /** Global bar index where the swing was confirmed/declared. */
  confirmed_at_idx: number;
  /** HH:MM of confirmation — where the "FS"/"SUS" label is drawn. */
  confirmed_at_time: string;
  /**
   * Global bar index of the swing's OWN structural completion (first opposing
   * pivot-break at/after the swing end). FS/SUS should be drawn here.
   */
  fs_at_idx?: number;
  fs_at_time?: string;
}

interface ZigzagSegment {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  color: string;
  swing_index: number;
}

const CYAN_COLOR = "#22d3ee";
const YELLOW_COLOR = "#facc15";

function colorForSwing(swing_index: number): string {
  return swing_index % 2 === 0 ? CYAN_COLOR : YELLOW_COLOR;
}

/**
 * Whole-day swing primitive.
 *
 * Draws ZIGZAG LINES connecting consecutive swings detected for the day:
 *
 *   swing0 start → swing0 end
 *   swing0 end   → swing1 end   (shared turning point)
 *   swing1 end   → swing2 end
 *   ... and so on
 *
 * Each zigzag segment is colored based on its starting swing's swing_index.
 * Even swing_index → cyan (#22d3ee)
 * Odd  swing_index → yellow (#facc15)
 *
 * Small filled circles mark each turning point.
 */
export class WholeDaySwingPrimitive implements IPanePrimitive<Time> {
  private chart: IChartApi | null = null;
  private segments: ZigzagSegment[] = [];
  private dots: Array<{ x: number; y: number; color: string }> = [];

  constructor(
    private series: ISeriesApi<"Candlestick">,
    private swings: WholeDaySwingPoint[],
  ) {}

  private recalc() {
    const chart = this.chart;
    if (!chart) return;
    const ts = chart.timeScale();

    // Sort by start_idx just in case backend returns them out of order.
    const sorted = [...this.swings].sort((a, b) => a.start_idx - b.start_idx);

    const segments: ZigzagSegment[] = [];
    const dots: Array<{ x: number; y: number; color: string }> = [];
    // Deduplicate turning-point dots (swing N end == swing N+1 start)
    const seenDots = new Set<string>();

    for (let i = 0; i < sorted.length; i++) {
      const s = sorted[i];
      // Lightweight-charts logical index equals array position in the full
      // 1min dataset (no limit). Backend start_idx/end_idx are global idxs
      // (position in CSV). This matches StockChart's bsMarkers pattern
      // (candles[b.idx]). If data were ever limited, we'd need time-based
      // mapping; logical fallback covers the current full-data case.
      const x1 = ts.logicalToCoordinate(s.start_idx as Logical);
      const y1 = this.series.priceToCoordinate(s.start_px);
      const x2 = ts.logicalToCoordinate(s.end_idx as Logical);
      const y2 = this.series.priceToCoordinate(s.end_px);
      if (x1 == null || y1 == null || x2 == null || y2 == null) continue;

      const color = colorForSwing(s.swing_index);
      segments.push({ x1, y1, x2, y2, color, swing_index: s.swing_index });

      // Deduplicate dots at turning points (each joint appears twice otherwise)
      const k1 = `${s.start_idx}:${s.start_px}`;
      const k2 = `${s.end_idx}:${s.end_px}`;
      if (!seenDots.has(k1)) {
        seenDots.add(k1);
        dots.push({ x: x1, y: y1, color });
      }
      if (!seenDots.has(k2)) {
        seenDots.add(k2);
        dots.push({ x: x2, y: y2, color });
      }
    }

    this.segments = segments;
    this.dots = dots;
  }

  attached(param: { chart: IChartApi; requestUpdate: () => void }): void {
    this.chart = param.chart;
    this.recalc();
    param.requestUpdate();
  }

  updateAllViews(): void {
    this.recalc();
  }

  paneViews(): readonly IPanePrimitivePaneView[] {
    return [new WholeDaySwingPaneView(this.segments, this.dots)];
  }
}

class WholeDaySwingPaneView implements IPanePrimitivePaneView {
  constructor(
    private segments: ZigzagSegment[],
    private dots: Array<{ x: number; y: number; color: string }>,
  ) {}

  renderer(): IPrimitivePaneRenderer | null {
    return new WholeDaySwingPaneRenderer(this.segments, this.dots);
  }
}

class WholeDaySwingPaneRenderer implements IPrimitivePaneRenderer {
  constructor(
    private segments: ZigzagSegment[],
    private dots: Array<{ x: number; y: number; color: string }>,
  ) {}

  zOrder(): PrimitivePaneViewZOrder {
    return "top";
  }

  draw(target: CanvasRenderingTarget2D): void {
    target.useMediaCoordinateSpace(({ context: ctx }) => {
      // Draw the zigzag segments
      ctx.lineWidth = 2;
      for (const seg of this.segments) {
        ctx.strokeStyle = seg.color;
        ctx.globalAlpha = 0.95;
        ctx.beginPath();
        ctx.moveTo(seg.x1, seg.y1);
        ctx.lineTo(seg.x2, seg.y2);
        ctx.stroke();
      }
      ctx.globalAlpha = 1;

      // Draw small filled circles at each turning point
      for (const d of this.dots) {
        ctx.fillStyle = d.color;
        ctx.beginPath();
        ctx.arc(d.x, d.y, 3, 0, Math.PI * 2);
        ctx.fill();
      }
    });
  }
}
