"use client";

import type {
  IChartApi,
  IPanePrimitive,
  IPanePrimitivePaneView,
  IPrimitivePaneRenderer,
  ISeriesApi,
  Logical,
  Time,
  Coordinate,
} from "lightweight-charts";
import type { CanvasRenderingTarget2D } from "fancy-canvas";

/**
 * Session breaks: a full-height vertical dashed line at the first bar of each
 * trading day, so intraday charts visually separate one session from the next
 * (TradingView-style session separators).
 */
export class SessionBreakPrimitive implements IPanePrimitive<Time> {
  private chart: IChartApi | null = null;
  private xs: Coordinate[] = [];

  constructor(
    private series: ISeriesApi<"Candlestick">,
    private indices: number[],
  ) {}

  private recalc() {
    const ts = this.chart?.timeScale();
    if (!ts) return;
    this.xs = this.indices
      .map((i) => ts.logicalToCoordinate(i as Logical))
      .filter((x): x is Coordinate => x != null);
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
    return [new SessionBreakPaneView(this.xs)];
  }
}

class SessionBreakPaneView implements IPanePrimitivePaneView {
  constructor(private xs: number[]) {}

  renderer(): IPrimitivePaneRenderer | null {
    return new SessionBreakPaneRenderer(this.xs);
  }
}

class SessionBreakPaneRenderer implements IPrimitivePaneRenderer {
  constructor(private xs: number[]) {}

  draw(target: CanvasRenderingTarget2D): void {
    target.useMediaCoordinateSpace(({ context: ctx, mediaSize }) => {
      ctx.save();
      ctx.setLineDash([3, 4]);
      ctx.strokeStyle = "rgba(255, 255, 255, 1)";
      ctx.lineWidth = 1;
      for (const x of this.xs) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, mediaSize.height);
        ctx.stroke();
      }
      ctx.restore();
    });
  }
}
