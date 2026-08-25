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
import type { EnvelopeViolation } from "@/lib/envelope";

interface Box {
  x: number;
  yTop: number;
  yBot: number;
}

// Draws a translucent red box around each candle that breaches the envelope
// law, plus a thin tick at the breached marker price for context.
export class EnvelopePrimitive implements IPanePrimitive<Time> {
  private chart: IChartApi | null = null;
  private boxes: Box[] = [];

  constructor(
    private series: ISeriesApi<"Candlestick">,
    private violations: EnvelopeViolation[],
    private lastIndex: number,
  ) {}

  private recalc() {
    const chart = this.chart;
    if (!chart) return;
    const ts = chart.timeScale();

    const vr = ts.getVisibleLogicalRange();
    const from = vr ? Math.max(0, Math.floor(vr.from) - 10) : -Infinity;
    const to = vr ? Math.ceil(vr.to) + 10 : Infinity;

    const boxes: Box[] = [];
    for (const v of this.violations) {
      if (v.idx < from || v.idx > Math.min(to, this.lastIndex)) continue;
      const x = ts.logicalToCoordinate(v.idx as Logical);
      if (x == null) continue;
      // pad the box vertically so the full wick is clearly enclosed
      const span = Math.abs(v.px - v.markerPx);
      const pad = Math.max(1.5, span * 0.15);
      const yA = this.series.priceToCoordinate(v.px + pad);
      const yB = this.series.priceToCoordinate(Math.min(v.px, v.markerPx) - pad);
      if (yA == null || yB == null) continue;
      boxes.push({ x, yTop: Math.min(yA, yB), yBot: Math.max(yA, yB) });
    }
    this.boxes = boxes;
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
    return [new EnvelopePaneView(this.boxes)];
  }
}

class EnvelopePaneView implements IPanePrimitivePaneView {
  constructor(private boxes: Box[]) {}

  renderer(): IPrimitivePaneRenderer | null {
    return new EnvelopePaneRenderer(this.boxes);
  }
}

class EnvelopePaneRenderer implements IPrimitivePaneRenderer {
  private halfW = 5; // half bar width guess; refined below in draw

  constructor(private boxes: Box[]) {}

  zOrder(): PrimitivePaneViewZOrder {
    return "top";
  }

  draw(target: CanvasRenderingTarget2D): void {
    target.useMediaCoordinateSpace(({ context: ctx }) => {
      ctx.save();
      for (const b of this.boxes) {
        ctx.fillStyle = "rgba(239, 68, 68, 0.14)";
        ctx.strokeStyle = "rgba(239, 68, 68, 0.85)";
        ctx.lineWidth = 1.25;
        const x0 = b.x - this.halfW;
        const w = this.halfW * 2;
        ctx.fillRect(x0, b.yTop, w, b.yBot - b.yTop);
        ctx.strokeRect(x0, b.yTop, w, b.yBot - b.yTop);
      }
      ctx.restore();
    });
  }
}
