"use client";

import type {
  IChartApi,
  IPanePrimitive,
  IPanePrimitivePaneView,
  IPrimitivePaneRenderer,
  ISeriesApi,
  Time,
  Logical,
} from "lightweight-charts";
import type { CanvasRenderingTarget2D } from "fancy-canvas";

export interface HTFWindowRect {
  startTime: number;
  endTime: number;
  isLong: boolean;
  entryPrice?: number;
  slPrice?: number;
}

interface WindowItem {
  openX: number;
  closeX: number | null;
  isLong: boolean;
  yEntry: number | null;
  ySl: number | null;
  yTp15: number | null;
  yTp3: number | null;
}

const LONG_OPEN = "rgba(34, 197, 94, 1.0)";
const LONG_CLOSE = "rgba(255, 255, 255, 0.9)";
const SHORT_OPEN = "rgba(239, 68, 68, 1.0)";
const SHORT_CLOSE = "rgba(59, 130, 246, 0.9)";
const R_SL = "rgba(239, 68, 68, 0.7)";
const R_TP_LONG = "rgba(59, 130, 246, 0.7)";
const R_TP_SHORT = "rgba(239, 68, 68, 0.7)";

function drawEdgeArrow(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  dir: "left" | "right",
  color: string,
) {
  const size = 8;
  ctx.fillStyle = color;
  ctx.beginPath();
  if (dir === "right") {
    ctx.moveTo(x, y - size);
    ctx.lineTo(x + size, y);
    ctx.lineTo(x, y + size);
  } else {
    ctx.moveTo(x, y - size);
    ctx.lineTo(x - size, y);
    ctx.lineTo(x, y + size);
  }
  ctx.closePath();
  ctx.fill();
}

export class HTFWindowPrimitive implements IPanePrimitive<Time> {
  private chart: IChartApi | null = null;
  private items: WindowItem[] = [];

  /**
   * Draw the per-window entry/SL/TP horizontal lines in addition to the window
   * boundaries. Off by default.
   *
   * With ~179 windows that is four extra horizontal lines each - 700+ lines
   * competing with the candles. The start/end boundaries are the signal; the R
   * levels are detail that belongs on inspection, not on every glance. Pass
   * true to the constructor to get them.
   */
  private readonly showRLevels: boolean;

  constructor(
    private series: ISeriesApi<"Candlestick">,
    private windows: HTFWindowRect[],
    showRLevels = false,
  ) {
    this.showRLevels = showRLevels;
  }

  private recalc() {
    const chart = this.chart;
    if (!chart) return;
    const ts = chart.timeScale();

    const items: WindowItem[] = [];
    for (const w of this.windows) {
      const oIdx = ts.timeToIndex(w.startTime as Time, true);
      const cIdx = ts.timeToIndex(w.endTime as Time, true);

      if (oIdx == null) continue;

      const openX = ts.logicalToCoordinate(oIdx as unknown as Logical);
      const closeX = cIdx != null ? ts.logicalToCoordinate(cIdx as unknown as Logical) : null;

      if (openX == null) continue;

      // R-level price coords
      let yEntry: number | null = null;
      let ySl: number | null = null;
      let yTp15: number | null = null;
      let yTp3: number | null = null;

      if (w.entryPrice != null && w.slPrice != null && w.entryPrice > 0 && w.slPrice > 0) {
        const R = Math.abs(w.entryPrice - w.slPrice);
        const dir = w.isLong ? 1 : -1;
        yEntry = this.series.priceToCoordinate(w.entryPrice);
        ySl = this.series.priceToCoordinate(w.slPrice);
        yTp15 = this.series.priceToCoordinate(w.entryPrice + dir * 1.5 * R);
        yTp3 = this.series.priceToCoordinate(w.entryPrice + dir * 3 * R);
      }

      items.push({
        openX,
        closeX,
        isLong: w.isLong,
        yEntry,
        ySl,
        yTp15,
        yTp3,
      });
    }
    this.items = items;
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
    return [new HTFWindowPaneView(this.items, this.showRLevels)];
  }
}

class HTFWindowPaneView implements IPanePrimitivePaneView {
  constructor(
    private items: WindowItem[],
    private showRLevels: boolean,
  ) {}
  renderer(): IPrimitivePaneRenderer | null {
    return new HTFWindowPaneRenderer(this.items, this.showRLevels);
  }
}

class HTFWindowPaneRenderer implements IPrimitivePaneRenderer {
  constructor(
    private items: WindowItem[],
    private showRLevels: boolean,
  ) {}

  draw(target: CanvasRenderingTarget2D): void {
    target.useMediaCoordinateSpace(({ context: ctx }) => {
      const W = ctx.canvas.width;
      const H = ctx.canvas.height;

      for (const it of this.items) {
        ctx.lineWidth = 2;
        ctx.setLineDash([8, 4]);

        // Open vertical
        ctx.strokeStyle = it.isLong ? LONG_OPEN : SHORT_OPEN;
        ctx.beginPath();
        ctx.moveTo(it.openX, 0);
        ctx.lineTo(it.openX, H);
        ctx.stroke();

        // Close: on-screen → dashed line, off-screen → edge arrows
        if (it.closeX == null) {
          // No close timestamp resolved
        } else if (it.closeX > W) {
          const color = it.isLong ? LONG_CLOSE : SHORT_CLOSE;
          drawEdgeArrow(ctx, W - 6, H / 2 - 15, "right", color);
          drawEdgeArrow(ctx, W - 6, H / 2, "right", color);
          drawEdgeArrow(ctx, W - 6, H / 2 + 15, "right", color);
        } else if (it.closeX < 0) {
          const color = it.isLong ? LONG_CLOSE : SHORT_CLOSE;
          drawEdgeArrow(ctx, 6, H / 2 - 15, "left", color);
          drawEdgeArrow(ctx, 6, H / 2, "left", color);
          drawEdgeArrow(ctx, 6, H / 2 + 15, "left", color);
        } else {
          ctx.strokeStyle = it.isLong ? LONG_CLOSE : SHORT_CLOSE;
          ctx.setLineDash([4, 4]);
          ctx.beginPath();
          ctx.moveTo(it.closeX, 0);
          ctx.lineTo(it.closeX, H);
          ctx.stroke();
        }

        // R-level horizontal lines - distinct colors regardless of direction.
        // `continue`, never `return`: this sits inside the per-window loop, and
        // returning here would abandon every remaining window, not just this one.
        if (!this.showRLevels) continue;
        if (it.yEntry == null || it.ySl == null) continue;
        // A window's R levels belong to that window. Without a resolved end there
        // is no window to belong to, so draw nothing - do not stretch to the canvas
        // edge, which is what made these run off past the window.
        if (it.closeX == null || it.closeX <= it.openX) continue;
        const x1 = Math.max(0, it.openX);
        const x2 = Math.min(W, it.closeX);

        ctx.lineWidth = 1;
        ctx.setLineDash([4, 4]);

        // Entry — always WHITE (neutral reference)
        ctx.strokeStyle = "rgba(255, 255, 255, 0.8)";
        ctx.beginPath();
        ctx.moveTo(x1, it.yEntry);
        ctx.lineTo(x2, it.yEntry);
        ctx.stroke();

        // SL (-1R) — always RED (loss zone)
        ctx.strokeStyle = "rgba(239, 68, 68, 0.85)";
        ctx.beginPath();
        ctx.moveTo(x1, it.ySl);
        ctx.lineTo(x2, it.ySl);
        ctx.stroke();

        // 1.5R deliberately not drawn - see the note at the constructor.

        // +3R — always YELLOW (extended profit)
        if (it.yTp3 != null) {
          ctx.strokeStyle = "rgba(234, 179, 8, 0.75)";
          ctx.beginPath();
          ctx.moveTo(x1, it.yTp3);
          ctx.lineTo(x2, it.yTp3);
          ctx.stroke();
        }
      }
    });
  }
}
