"use client";

// First-Swing manual GT renderer with TradingView-style draggable endpoints.
// Renders thick yellow segments + hollow circle handles; exposes hitTest()
// for the host's DOM drag wiring and preview() for live drag feedback.

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

export interface FsSeg {
  day: string;
  startIdx: number;
  startPx: number;
  startKind: "H" | "L";
  endIdx: number;
  endPx: number;
  endKind: "H" | "L";
}

export interface FsHandle {
  x: number;
  y: number;
  day: string;
  which: "start" | "end";
}

interface Pt {
  x: number;
  y: number;
}

const COLOR = "#facc15";
const BG = "#0d1117";

export class FirstSwingPrimitive implements IPanePrimitive<Time> {
  private chart: IChartApi | null = null;
  private requestUpdateFn: (() => void) | null = null;
  private segs: FsSeg[];
  private coords: { a: Pt; b: Pt }[] = [];
  handles: FsHandle[] = [];

  constructor(
    private series: ISeriesApi<"Candlestick">,
    segs: FsSeg[],
    private lastIndex: number,
  ) {
    this.segs = segs.map((s) => ({ ...s }));
  }

  private recalc() {
    const chart = this.chart;
    if (!chart) return;
    const ts = chart.timeScale();

    const coords: { a: Pt; b: Pt }[] = [];
    const hs: FsHandle[] = [];
    for (const s of this.segs) {
      const ax = ts.logicalToCoordinate(Math.min(s.startIdx, this.lastIndex) as Logical);
      const bx = ts.logicalToCoordinate(Math.min(s.endIdx, this.lastIndex) as Logical);
      const ay = this.series.priceToCoordinate(s.startPx);
      const by = this.series.priceToCoordinate(s.endPx);
      if (ax == null || ay == null || bx == null || by == null) continue;
      coords.push({ a: { x: ax, y: ay }, b: { x: bx, y: by } });
      hs.push(
        { x: ax, y: ay, day: s.day, which: "start" },
        { x: bx, y: by, day: s.day, which: "end" },
      );
    }
    this.coords = coords;
    this.handles = hs;
  }

  // Replace all segments in place (no chart rebuild needed).
  setSegs(segs: FsSeg[]) {
    this.segs = segs.map((s) => ({ ...s }));
    this.recalc();
    this.requestUpdateFn?.();
  }

  segOf(day: string): FsSeg | undefined {
    return this.segs.find((s) => s.day === day);
  }

  // Live drag feedback: move one endpoint of the named day's segment.
  preview(day: string, which: "start" | "end", idx: number, px: number) {
    const s = this.segs.find((v) => v.day === day);
    if (!s) return;
    if (which === "start") {
      s.startIdx = idx;
      s.startPx = px;
    } else {
      s.endIdx = idx;
      s.endPx = px;
    }
    this.recalc();
    this.requestUpdateFn?.();
  }

  pickHandle(x: number, y: number, radius = 10): FsHandle | null {
    let best: FsHandle | null = null;
    let bestD = Infinity;
    for (const h of this.handles) {
      const d = (h.x - x) * (h.x - x) + (h.y - y) * (h.y - y);
      if (d <= radius * radius && d < bestD) {
        bestD = d;
        best = h;
      }
    }
    return best;
  }

  attached(param: { chart: IChartApi; requestUpdate: () => void }): void {
    this.chart = param.chart;
    this.requestUpdateFn = param.requestUpdate;
    this.recalc();
    param.requestUpdate();
  }

  updateAllViews(): void {
    this.recalc();
  }

  paneViews(): readonly IPanePrimitivePaneView[] {
    return [new FsPaneView(this.coords, this.handles)];
  }
}

class FsPaneView implements IPanePrimitivePaneView {
  constructor(
    private coords: { a: Pt; b: Pt }[],
    private handles: FsHandle[],
  ) {}

  renderer(): IPrimitivePaneRenderer | null {
    return new FsPaneRenderer(this.coords, this.handles);
  }
}

class FsPaneRenderer implements IPrimitivePaneRenderer {
  constructor(
    private coords: { a: Pt; b: Pt }[],
    private handles: FsHandle[],
  ) {}

  zOrder(): PrimitivePaneViewZOrder {
    return "top";
  }

  draw(target: CanvasRenderingTarget2D): void {
    target.useMediaCoordinateSpace(({ context: ctx }) => {
      ctx.save();
      // segments
      ctx.lineWidth = 4;
      ctx.lineCap = "round";
      ctx.strokeStyle = COLOR;
      for (const { a, b } of this.coords) {
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.stroke();
      }
      // endpoint handles (hollow circles)
      ctx.lineWidth = 2;
      ctx.strokeStyle = COLOR;
      ctx.fillStyle = BG;
      for (const h of this.handles) {
        ctx.beginPath();
        ctx.arc(h.x, h.y, 5, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();
      }
      ctx.restore();
    });
  }
}
