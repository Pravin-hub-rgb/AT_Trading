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
import type { EmaPoint } from "@/lib/ema";

interface Pt {
  x: number;
  y: number;
}

export class EMAPrimitive implements IPanePrimitive<Time> {
  private chart: IChartApi | null = null;
  private pts: Pt[] = [];

  constructor(
    private series: ISeriesApi<"Candlestick">,
    private points: EmaPoint[],
    private color: string = "#f59e0b",
    private lineWidth = 1.5,
  ) {}

  private recalc() {
    const chart = this.chart;
    if (!chart) return;
    const ts = chart.timeScale();
    const vr = ts.getVisibleLogicalRange();
    const from = vr ? Math.max(0, Math.floor(vr.from) - 10) : -Infinity;
    const to = vr ? Math.ceil(vr.to) + 10 : Infinity;
    const pts: Pt[] = [];
    let prev: Pt | null = null;
    for (const p of this.points) {
      if (p.idx < from || p.idx > to) {
        prev = null;
        continue;
      }
      const x = ts.logicalToCoordinate(p.idx as Logical);
      const y = this.series.priceToCoordinate(p.value);
      if (x == null || y == null) {
        prev = null;
        continue;
      }
      const cur: Pt = { x, y };
      if (prev) {
        pts.push(prev);
        pts.push(cur);
      }
      prev = cur;
    }
    this.pts = pts;
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
    return [new EMAPaneView(this.pts, this.color, this.lineWidth)];
  }
}

class EMAPaneView implements IPanePrimitivePaneView {
  constructor(
    private pts: Pt[],
    private color: string,
    private lineWidth = 1.5,
  ) {}

  renderer(): IPrimitivePaneRenderer | null {
    return new EMAPaneRenderer(this.pts, this.color, this.lineWidth);
  }
}

class EMAPaneRenderer implements IPrimitivePaneRenderer {
  constructor(
    private pts: Pt[],
    private color: string,
    private lineWidth = 1.5,
  ) {}

  zOrder(): PrimitivePaneViewZOrder {
    return "top";
  }

  draw(target: CanvasRenderingTarget2D): void {
    target.useMediaCoordinateSpace(({ context: ctx }) => {
      ctx.save();
      ctx.lineWidth = this.lineWidth;
      ctx.strokeStyle = this.color;
      ctx.lineCap = "round";
      ctx.lineJoin = "round";
      for (let i = 0; i + 1 < this.pts.length; i += 2) {
        const a = this.pts[i];
        const b = this.pts[i + 1];
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.stroke();
      }
      ctx.restore();
    });
  }
}
