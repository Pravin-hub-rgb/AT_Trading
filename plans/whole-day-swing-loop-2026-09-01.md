# Whole-Day Swing Loop — Alternating Cyan/Yellow Marking

**Date:** 2026-09-01
**Status:** Implemented ✓ (Build passes, TypeScript clean)

## Goal

Detect and mark ALL swings for the entire trading day (9:15 → last bar), not just the first 2.
Each swing alternates between cyan and yellow colors — **default ON for 1min chart**:

```
Swing #0 (even) → cyan  (#22d3ee)
Swing #1 (odd)  → yellow (#facc15)
Swing #2 (even) → cyan
Swing #3 (odd)  → yellow
...and so on until market close.
```

## Architecture

### Key Design Decision: Separate Primitive File

**Critical:** DO NOT modify `SwingSRPrimitive.ts`. It handles daily pivots with `extendLines=true`
which draws lines from EVERY daily pivot to the last bar — this fills the canvas when used
for whole-day detection.

Instead, a **separate** primitive file was created that only renders the zigzag segments
for the current day range being displayed.

### Backend (Python)

**File:** `backend/src/swing_engine.py`

`compute_whole_day_swings()` function:

- Takes `FlowCandle[]` list + optional engine opts
- Groups candles by day
- For each day:
  - Creates a fresh `FsV2Engine` instance
  - Calls `reset()` after each swing completes
  - Tracks `swing_index` (0, 1, 2, ...) per day
  - Continues until no more swings can be found
- Returns list of swing dicts with `day`, `swing_index`, `seg`, `source`, `dir`

**File:** `backend/server.py`

`/api/swings/whole_day` endpoint:

- Query params: `interval` (1min/5min/daily), `sustain_bars` (default 7)
- Reads CSV data for the specified interval
- Calls `compute_whole_day_swings()`
- Returns `{ interval, sustain_bars, swings[] }`

### Frontend (TypeScript/React)

**File:** `frontend/src/components/WholeDaySwingPrimitive.ts` ← **NEW SEPARATE FILE**

```typescript
export interface WholeDaySwingPoint {
  dir: "B" | "S";
  start_idx: number;
  start_px: number;
  end_idx: number;
  end_px: number;
  swing_index: number;
}

const CYAN_COLOR = "#22d3ee";
const YELLOW_COLOR = "#facc15";

function colorForSwing(swing_index: number): string {
  return swing_index % 2 === 0 ? CYAN_COLOR : YELLOW_COLOR;
}

export class WholeDaySwingPrimitive implements IPanePrimitive<Time> {
  // Draws zigzag lines connecting consecutive swings
  // Each segment colored by swing_index parity
  // Small circles at turning points
  // zOrder: "top" (renders above candlesticks)
}
```

**File:** `frontend/src/components/StockChart.tsx`

- Added `wholeDaySwings?: WholeDaySwingPoint[]` to Props interface
- Added `const wholeDayPrimRef = useRef<WholeDaySwingPrimitive | null>(null);`
- Added useEffect to attach/detach primitive when `wholeDaySwings` changes:
  ```typescript
  useEffect(() => {
    const chart = chartRef.current;
    const ser = seriesRef.current;
    if (!chart || !ser || !intraday) return;
    if (!wholeDaySwings || wholeDaySwings.length === 0) return;
    const prim = new WholeDaySwingPrimitive(ser, wholeDaySwings);
    chart.panes()[0].attachPrimitive(prim);
    wholeDayPrimRef.current = prim;
    return () => {
      wholeDayPrimRef.current = null;
      try {
        chart.panes()[0].detachPrimitive(prim);
      } catch {}
    };
  }, [wholeDaySwings, intraday, candles]);
  ```

**File:** `frontend/src/lib/api.ts`

```typescript
export interface WholeDaySwing {
  day: string;
  swing_index: number;
  seg: {
    dir: "B" | "S";
    start_idx: number;
    start_px: number;
    end_idx: number;
    end_px: number;
  };
  source: "chop" | "sustain" | null;
  dir: "up" | "down";
}

export interface WholeDaySwingsResponse {
  interval: string;
  sustain_bars: number;
  swings: WholeDaySwing[];
}

export const getWholeDaySwings = (interval = "1min", sustainBars = 7) =>
  request<WholeDaySwingsResponse>(
    `/api/swings/whole_day?interval=${interval}&sustain_bars=${sustainBars}`,
  );
```

**File:** `frontend/src/app/chart/page.tsx`

```typescript
// State
const [wholeDaySwings, setWholeDaySwings] = useState<WholeDaySwingPoint[]>([]);
const [wholeDaySwingsB, setWholeDaySwingsB] = useState<WholeDaySwingPoint[]>([]);

// Pane A auto-fetch
useEffect(() => {
  if (interval !== "1min") { setWholeDaySwings([]); return; }
  let cancelled = false;
  getWholeDaySwings("1min")
    .then((res) => {
      if (cancelled) return;
      const points: WholeDaySwingPoint[] = res.swings.map((s: WholeDaySwing) => ({
        dir: s.seg.dir, start_idx: s.seg.start_idx, start_px: s.seg.start_px,
        end_idx: s.seg.end_idx, end_px: s.seg.end_px, swing_index: s.swing_index,
      }));
      setWholeDaySwings(points);
    })
    .catch(() => { if (cancelled) return; setWholeDaySwings([]); });
  return () => { cancelled = true; };
}, [interval]);

// JSX — both panes get the prop:
<StockChart ... wholeDaySwings={wholeDaySwings} ... />
<StockChart ... wholeDaySwings={wholeDaySwingsB} ... />
```

## Color Mapping

| swing_index | Color  | Hex     |
| ----------- | ------ | ------- |
| 0 (even)    | Cyan   | #22d3ee |
| 1 (odd)     | Yellow | #facc15 |
| 2 (even)    | Cyan   | #22d3ee |
| 3 (odd)     | Yellow | #facc15 |
| ...         | ...    | ...     |

## Key Implementation Details

- **Default ON**: The whole-day zigzag is auto-fetched when `interval === "1min"`. No toggle needed.
- **Rendering**: The primitive draws each swing segment as a line from `start_px` at `start_idx` to `end_px` at `end_idx`.
- **Coloring**: Uses `colorForSwing(swing_index)` — even index = cyan, odd = yellow.
- **Turning points**: Small filled circles drawn at each swing endpoint.
- **zOrder**: "top" so the zigzag renders above candlesticks.
- **Separation**: `SwingSRPrimitive.ts` is unchanged — it retains its original red/green S/R behavior for daily pivots.
- **Dual pane**: Both pane A and pane B get their own `wholeDaySwings` state, each tracking their respective interval.

## Testing

```bash
# Backend test
cd backend && python -m uvicorn src.server:app --reload --port 8003
curl "http://localhost:8003/api/swings/whole_day?interval=1min&sustain_bars=7"

# Frontend build
cd frontend && npm run build
```

## Files Changed

| File                                                | Action                                       |
| --------------------------------------------------- | -------------------------------------------- |
| `backend/src/swing_engine.py`                       | Added `compute_whole_day_swings()`           |
| `backend/server.py`                                 | Added `/api/swings/whole_day` endpoint       |
| `frontend/src/components/WholeDaySwingPrimitive.ts` | **NEW** — zigzag renderer                    |
| `frontend/src/components/StockChart.tsx`            | Added `wholeDaySwings` prop + useEffect      |
| `frontend/src/lib/api.ts`                           | Added `WholeDaySwing`, `getWholeDaySwings()` |
| `frontend/src/app/chart/page.tsx`                   | Added state, useEffects, wired to StockChart |
