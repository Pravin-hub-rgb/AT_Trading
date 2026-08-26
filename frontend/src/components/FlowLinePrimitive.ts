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

export interface FlowSegment {
  dir: "B" | "S";
  startIdx: number;
  startPx: number;
  endIdx: number;
  endPx: number;
}

interface Pt {
  x: number;
  y: number;
}

export class FlowLinePrimitive implements IPanePrimitive<Time> {
  private chart: IChartApi | null = null;
  private pts: Pt[] = [];

  constructor(
    private series: ISeriesApi<"Candlestick">,
    private segments: FlowSegment[],
    private lastIndex: number,
    private lineColor: string = "#ffffff",
    private lineWidth = 2,
  ) {}

  private recalc() {
    const chart = this.chart;
    if (!chart) return;
    const ts = chart.timeScale();

    const vr = ts.getVisibleLogicalRange();
    const from = vr ? Math.max(0, Math.floor(vr.from) - 10) : -Infinity;
    const to = vr ? Math.ceil(vr.to) + 10 : Infinity;

    const pts: Pt[] = [];
    for (const s of this.segments) {
      if (s.endIdx < from && s.startIdx < from) continue;
      if (s.startIdx > to && s.endIdx > to) continue;

      const x1 = ts.logicalToCoordinate(s.startIdx as Logical);
      const y1 = this.series.priceToCoordinate(s.startPx);
      const endIdx = Math.min(s.endIdx, this.lastIndex);
      const x2 = ts.logicalToCoordinate(endIdx as Logical);
      const y2 = this.series.priceToCoordinate(s.endPx);
      if (x1 == null || y1 == null || x2 == null || y2 == null) continue;
      pts.push({ x: x1, y: y1 });
      pts.push({ x: x2, y: y2 });
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
    return [new FlowLinePaneView(this.pts, this.lineColor, this.lineWidth)];
  }
}

class FlowLinePaneView implements IPanePrimitivePaneView {
  constructor(
    private pts: Pt[],
    private color: string,
    private lineWidth = 2,
  ) {}

  renderer(): IPrimitivePaneRenderer | null {
    return new FlowLinePaneRenderer(this.pts, this.color, this.lineWidth);
  }
}

class FlowLinePaneRenderer implements IPrimitivePaneRenderer {
  constructor(
    private pts: Pt[],
    private color: string,
    private lineWidth = 2,
  ) {}

  zOrder(): PrimitivePaneViewZOrder {
    return "top";
  }

  draw(target: CanvasRenderingTarget2D): void {
    target.useMediaCoordinateSpace(({ context: ctx }) => {
      ctx.save();
      ctx.lineWidth = this.lineWidth;
      ctx.lineCap = "round";
      ctx.strokeStyle = this.color;
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
