"use client";

import type {
  IChartApi,
  IPanePrimitive,
  IPanePrimitivePaneView,
  IPrimitivePaneRenderer,
  Time,
} from "lightweight-charts";
import type { CanvasRenderingTarget2D } from "fancy-canvas";

/**
 * Remote-pane sync cursor (TradingView-style linked crosshair): a single
 * full-height vertical line marking the TIME hovered on the other chart.
 * Only the time dimension syncs — each pane keeps its own independent price
 * axis, so no horizontal line is drawn here.
 *
 * When the mapped time falls outside this pane's visible window, the line is
 * clamped to the nearest edge and dimmed, so the link stays perceptible
 * without hijacking the pane's zoom/pan.
 */
export class SyncCrosshairPrimitive implements IPanePrimitive<Time> {
  private chart: IChartApi | null = null;
  private req: (() => void) | null = null;
  private time: Time | null = null;
  x: number | null = null;
  exact = false;

  attached(param: { chart: IChartApi; requestUpdate: () => void }): void {
    this.chart = param.chart;
    this.req = param.requestUpdate;
    this.recalc();
    param.requestUpdate();
  }

  detached(): void {
    this.chart = null;
    this.req = null;
  }

  setTime(t: Time | null): void {
    if (this.time === t) return;
    this.time = t;
    this.recalc();
    this.req?.();
  }

  private recalc() {
    const ts = this.chart?.timeScale();
    if (!ts || this.time == null) {
      this.x = null;
      this.exact = false;
      return;
    }
    const c = ts.timeToCoordinate(this.time);
    if (c == null) {
      // time not present in this pane's data at all
      this.x = null;
      this.exact = false;
      return;
    }
    const w = ts.width();
    this.exact = c >= 0 && c <= w;
    // keep clamped line 1px inside the pane so it isn't half-clipped at the border
    this.x = Math.min(Math.max(c, 1), w - 1);
  }

  updateAllViews(): void {
    this.recalc();
  }

  paneViews(): readonly IPanePrimitivePaneView[] {
    return [new SyncLinePaneView(this)];
  }
}

class SyncLinePaneView implements IPanePrimitivePaneView {
  constructor(private src: SyncCrosshairPrimitive) {}

  renderer(): IPrimitivePaneRenderer | null {
    return new SyncLinePaneRenderer(this.src.x, this.src.exact);
  }
}

class SyncLinePaneRenderer implements IPrimitivePaneRenderer {
  constructor(
    private x: number | null,
    private exact: boolean,
  ) {}

  draw(target: CanvasRenderingTarget2D): void {
    if (this.x == null) return;
    target.useMediaCoordinateSpace(({ context: ctx, mediaSize }) => {
      ctx.save();
      ctx.setLineDash(this.exact ? [5, 3] : [3, 3]);
      ctx.strokeStyle = this.exact ? "rgba(99, 102, 241, 0.95)" : "rgba(99, 102, 241, 0.75)";
      ctx.lineWidth = 1;
      const x = Math.round(this.x!) + 0.5;
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, mediaSize.height);
      ctx.stroke();
      ctx.restore();
    });
  }
}
