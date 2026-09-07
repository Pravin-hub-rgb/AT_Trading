"use client";

import type {
  IChartApi,
  IPanePrimitive,
  IPanePrimitivePaneView,
  IPrimitivePaneRenderer,
  ISeriesApi,
  Time,
} from "lightweight-charts";
import type { CanvasRenderingTarget2D } from "fancy-canvas";

export interface TradeBox {
  dir: "long" | "short";
  entryTs: number;
  exitTs: number;
  entryPrice: number;
  slPrice: number;
  targetPrice: number;
  /** realized exit price — trail/SL/BE exits differ from the static target */
  exitPrice: number;
  outcome: string;
  rMultiple: number;
}

interface BoxItem {
  x1: number;
  x2: number;
  yEntry: number;
  yExit: number;
  ySl: number;
  isLong: boolean;
  label: string;
  win: boolean;
}

const GREEN = "#10b981";
const RED = "#ef4444";
const ENTRY_ARROW = "#fde047"; // yellow-300

/**
 * TradingView-style position tool: translucent green box entry -> target,
 * red box entry -> SL, and a small downward arrow at the entry price to
 * mark where the trade was taken.
 */
export class PositionPrimitive implements IPanePrimitive<Time> {
  private chart: IChartApi | null = null;
  private items: BoxItem[] = [];

  constructor(
    private series: ISeriesApi<"Candlestick">,
    private trades: TradeBox[],
  ) {}

  private recalc() {
    const chart = this.chart;
    if (!chart) return;
    const ts = chart.timeScale();

    const items: BoxItem[] = [];
    for (const t of this.trades) {
      const x1 = ts.timeToCoordinate(t.entryTs as Time);
      const x2 = ts.timeToCoordinate(t.exitTs as Time);
      const ye = this.series.priceToCoordinate(t.entryPrice);
      const yt = this.series.priceToCoordinate(t.exitPrice);
      const ys = this.series.priceToCoordinate(t.slPrice);
      if (x1 == null || x2 == null || ye == null || yt == null || ys == null)
        continue;
      const r = t.rMultiple ?? 0;
      items.push({
        x1,
        x2,
        yEntry: ye,
        yExit: yt,
        ySl: ys,
        isLong: t.dir === "long",
        label: `${t.dir === "long" ? "L" : "S"} ${r >= 0 ? "+" : ""}${r.toFixed(1)}R ${t.outcome}`,
        win: r > 0,
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
    return [new PositionPaneView(this.items)];
  }
}

class PositionPaneView implements IPanePrimitivePaneView {
  constructor(private items: BoxItem[]) {}

  renderer(): IPrimitivePaneRenderer | null {
    return new PositionPaneRenderer(this.items);
  }
}

class PositionPaneRenderer implements IPrimitivePaneRenderer {
  constructor(private items: BoxItem[]) {}

  draw(target: CanvasRenderingTarget2D): void {
    target.useMediaCoordinateSpace(({ context: ctx }) => {
      ctx.font = "bold 11px ui-monospace, SFMono-Regular, Menlo, monospace";
      ctx.textBaseline = "middle";
      ctx.textAlign = "left";

      for (const it of this.items) {
        // realized zone (entry -> actual exit): green if won, red if lost.
        // Trail/SL/BE exits land wherever the market took them - the box must
        // show the REAL result, not the static 3R target.
        ctx.fillStyle = it.win
          ? "rgba(16, 185, 129, 0.13)"
          : "rgba(239, 68, 68, 0.12)";
        ctx.fillRect(
          it.x1,
          Math.min(it.yEntry, it.yExit),
          Math.max(it.x2 - it.x1, 2),
          Math.abs(it.yExit - it.yEntry),
        );
        // risk zone (entry -> SL)
        ctx.fillStyle = "rgba(239, 68, 68, 0.10)";
        ctx.fillRect(
          it.x1,
          Math.min(it.yEntry, it.ySl),
          Math.max(it.x2 - it.x1, 2),
          Math.abs(it.ySl - it.yEntry),
        );

        // level edges
        ctx.lineWidth = 1;
        ctx.strokeStyle = it.win
          ? "rgba(16, 185, 129, 0.55)"
          : "rgba(239, 68, 68, 0.55)";
        hline(ctx, it.x1, it.x2, it.yExit);
        ctx.strokeStyle = "rgba(239, 68, 68, 0.55)";
        hline(ctx, it.x1, it.x2, it.ySl);

        // entry line — thin white dotted line spanning the box so you can
        // instantly see where the trade was taken relative to exit + SL
        ctx.save();
        ctx.setLineDash([3, 3]);
        ctx.strokeStyle = "rgba(255, 255, 255, 0.55)";
        ctx.lineWidth = 1;
        hline(ctx, it.x1, it.x2, it.yEntry);
        ctx.restore();

        // L/S entry badge — big, bold, colored by direction, so you can
        // instantly tell long vs short without reading the R label
        const badge = it.isLong ? "L" : "S";
        const badgeColor = it.isLong ? "#10b981" : "#ef4444";
        const bx = it.x1 + 4;
        const by = it.yEntry - 12;
        ctx.font = "bold 13px ui-monospace, SFMono-Regular, Menlo, monospace";
        ctx.textBaseline = "middle";
        ctx.textAlign = "left";
        // badge background pill
        const badgeW = 14;
        const badgeH = 16;
        ctx.fillStyle = "#0d1117";
        ctx.fillRect(bx - 2, by - badgeH / 2, badgeW, badgeH);
        ctx.strokeStyle = badgeColor;
        ctx.lineWidth = 1.5;
        ctx.strokeRect(bx - 2, by - badgeH / 2, badgeW, badgeH);
        // badge text
        ctx.fillStyle = badgeColor;
        ctx.fillText(badge, bx + 1, by + 1);

        // small downward arrow at entry price (marks entry candle)
        drawEntryArrow(ctx, it.x1, it.yEntry, ENTRY_ARROW);

        // R tag near the TARGET line
        const color = it.win ? GREEN : RED;
        const ty = it.isLong ? it.yExit - 8 : it.yExit + 10;
        ctx.font = "bold 11px ui-monospace, SFMono-Regular, Menlo, monospace";
        ctx.strokeStyle = "#0d1117";
        ctx.lineWidth = 3;
        ctx.strokeText(it.label, it.x1 + 22, ty);
        ctx.fillStyle = color;
        ctx.fillText(it.label, it.x1 + 22, ty);
      }
    });
  }
}

function hline(
  ctx: CanvasRenderingContext2D,
  x1: number,
  x2: number,
  y: number,
) {
  ctx.beginPath();
  ctx.moveTo(x1, y);
  ctx.lineTo(x2, y);
  ctx.stroke();
}

/** Draw a small filled downward-pointing triangle above (x, y). */
function drawEntryArrow(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  color: string,
) {
  const size = 8; // half-width of triangle
  ctx.beginPath();
  ctx.moveTo(x, y); // tip at entry price
  ctx.lineTo(x - size, y - size - 4); // bottom-left
  ctx.lineTo(x + size, y - size - 4); // bottom-right
  ctx.closePath();
  ctx.fillStyle = color;
  ctx.fill();
  ctx.strokeStyle = "#0d1117";
  ctx.lineWidth = 1.5;
  ctx.stroke();
}
