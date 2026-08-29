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
  outcome: string;
  rMultiple: number;
}

interface BoxItem {
  x1: number;
  x2: number;
  yEntry: number;
  yTarget: number;
  ySl: number;
  isLong: boolean;
  label: string;
  win: boolean;
}

const GREEN = "#10b981";
const RED = "#ef4444";
const ENTRY_LINE = "#cbd5e1";
const ENTRY_MARKER = "#fde047"; // bright yellow

/**
 * TradingView-style position tool: translucent green box entry -> target,
 * red box entry -> SL, dashed entry line, an R-multiple tag, and a
 * bright yellow vertical "ENTRY" marker at the entry bar so the entry
 * bar is instantly visible. One box per simulated trade, drawn between
 * the entry bar and the exit bar.
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
      const yt = this.series.priceToCoordinate(t.targetPrice);
      const ys = this.series.priceToCoordinate(t.slPrice);
      if (x1 == null || x2 == null || ye == null || yt == null || ys == null)
        continue;
      const r = t.rMultiple ?? 0;
      items.push({
        x1,
        x2,
        yEntry: ye,
        yTarget: yt,
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
    target.useMediaCoordinateSpace(({ context: ctx, mediaSize }) => {
      ctx.font = "bold 11px ui-monospace, SFMono-Regular, Menlo, monospace";
      ctx.textBaseline = "middle";
      ctx.textAlign = "left";
      const h = mediaSize.height;

      for (const it of this.items) {
        // profit zone (entry -> target)
        ctx.fillStyle = "rgba(16, 185, 129, 0.13)";
        ctx.fillRect(
          it.x1,
          Math.min(it.yEntry, it.yTarget),
          Math.max(it.x2 - it.x1, 2),
          Math.abs(it.yTarget - it.yEntry),
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
        ctx.strokeStyle = "rgba(16, 185, 129, 0.55)";
        hline(ctx, it.x1, it.x2, it.yTarget);
        ctx.strokeStyle = "rgba(239, 68, 68, 0.55)";
        hline(ctx, it.x1, it.x2, it.ySl);

        // ENTRY marker — bright yellow vertical line spanning the whole pane
        ctx.strokeStyle = ENTRY_MARKER;
        ctx.lineWidth = 2;
        ctx.setLineDash([]);
        vline(ctx, it.x1, 0, h);

        // "ENTRY" label at top of pane, right of the vertical bar
        ctx.font = "bold 10px ui-monospace, SFMono-Regular, Menlo, monospace";
        ctx.strokeStyle = "#0d1117";
        ctx.lineWidth = 3;
        ctx.strokeText("ENTRY", it.x1 + 4, 12);
        ctx.fillStyle = ENTRY_MARKER;
        ctx.fillText("ENTRY", it.x1 + 4, 12);
        ctx.font = "bold 11px ui-monospace, SFMono-Regular, Menlo, monospace";

        // R tag near the TARGET line
        const color = it.win ? GREEN : RED;
        const ty = it.isLong ? it.yTarget - 8 : it.yTarget + 10;
        ctx.strokeStyle = "#0d1117";
        ctx.lineWidth = 3;
        ctx.strokeText(it.label, it.x1 + 2, ty);
        ctx.fillStyle = color;
        ctx.fillText(it.label, it.x1 + 2, ty);
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

function vline(
  ctx: CanvasRenderingContext2D,
  x: number,
  y1: number,
  y2: number,
) {
  ctx.beginPath();
  ctx.moveTo(x, y1);
  ctx.lineTo(x, y2);
  ctx.stroke();
}
