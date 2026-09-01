"use client";

import type {
  IChartApi,
  IPanePrimitive,
  IPanePrimitivePaneView,
  IPrimitivePaneRenderer,
  ISeriesApi,
  Logical,
  Time,
} from "lightweight-charts";
import type { CanvasRenderingTarget2D } from "fancy-canvas";

export interface SwingPoint {
  kind: "high" | "low";
  index: number;
  price: number;
  /** Optional fixed line length end (bar index). Line drawn index → end_index. */
  end_index?: number;
}

interface TextItem {
  x: number;
  y: number;
  kind: "high" | "low";
  x2?: number | null;
}

const HIGH_COLOR = "#ef4444";
const LOW_COLOR = "#10b981";

/**
 * Marks swing points with a small "SH"/"SL" text label. On the 5-min chart
 * (`extendLines`) also draws long horizontal S/R lines from the swing bar to
 * the right edge (red at swing highs, green at swing lows).
 */
export class SwingSRPrimitive implements IPanePrimitive<Time> {
  private chart: IChartApi | null = null;
  private texts: TextItem[] = [];

  constructor(
    private series: ISeriesApi<"Candlestick">,
    private points: SwingPoint[],
    private extendLines = false,
  ) {}

  private recalc() {
    const chart = this.chart;
    if (!chart) return;
    const ts = chart.timeScale();
    const lastIndex = this.series.data().length - 1;

    const texts: TextItem[] = [];
    for (const p of this.points) {
      const x = ts.logicalToCoordinate(p.index as Logical);
      const y = this.series.priceToCoordinate(p.price);
      if (x != null && y != null) {
        let x2: number | undefined;
        if (this.extendLines && p.end_index != null) {
          const end = Math.min(p.end_index, lastIndex);
          const ex = ts.logicalToCoordinate(end as Logical);
          if (ex != null) x2 = ex;
        }
        texts.push({ x, y, kind: p.kind, x2 });
      }
    }
    this.texts = texts;
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
    return [new SwingSRPaneView(this.texts, this.extendLines)];
  }
}

class SwingSRPaneView implements IPanePrimitivePaneView {
  constructor(
    private texts: TextItem[],
    private extendLines: boolean,
  ) {}

  renderer(): IPrimitivePaneRenderer | null {
    return new SwingSRPaneRenderer(this.texts, this.extendLines);
  }
}

class SwingSRPaneRenderer implements IPrimitivePaneRenderer {
  constructor(
    private texts: TextItem[],
    private extendLines: boolean,
  ) {}

  draw(target: CanvasRenderingTarget2D): void {
    target.useMediaCoordinateSpace(({ context: ctx }) => {
      if (this.extendLines) {
        ctx.lineWidth = 2;
        for (const t of this.texts) {
          if (t.x2 == null) continue;
          ctx.strokeStyle = t.kind === "high" ? HIGH_COLOR : LOW_COLOR;
          ctx.globalAlpha = 0.7;
          ctx.beginPath();
          ctx.moveTo(t.x, t.y);
          ctx.lineTo(t.x2, t.y);
          ctx.stroke();
          ctx.globalAlpha = 1;
        }
      }

      ctx.font = "bold 12px ui-monospace, SFMono-Regular, Menlo, monospace";
      ctx.textAlign = "center";
      ctx.textBaseline = "alphabetic";
      for (const t of this.texts) {
        const label = t.kind === "high" ? "SH" : "SL";
        const y = t.kind === "high" ? t.y - 6 : t.y + 18;
        ctx.strokeStyle = "#0d1117";
        ctx.lineWidth = 3;
        ctx.strokeText(label, t.x, y);
        ctx.fillStyle = t.kind === "high" ? HIGH_COLOR : LOW_COLOR;
        ctx.fillText(label, t.x, y);
      }
    });
  }
}
