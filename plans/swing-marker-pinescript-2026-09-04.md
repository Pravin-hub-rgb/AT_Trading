# Plan: Simplified Swing Marker Pine Script

**Date:** 2026-09-04  
**Goal:** Create a clean Pine Script that marks swings only (B1, B2, FLIP, FS) without zigzag lines

---



## Current State

Existing `swing maker.pine` (407 lines) has:

- ✅ Walker engine with line drawing
- ✅ B1/B2/FLIP/FS markers
- ✅ Day reset toggle
- ✅ LTF intrabar resolution for double-break bars
- ❌ Line drawing code adds complexity
- ❌ Line limit issue for long-running charts

---

## Proposed: "Swing Marker Only" Script

### Scope

| Feature                | Included? | Notes                          |
| ---------------------- | --------- | ------------------------------ |
| B1 marker (1st break)  | ✅        | Grey arrow up                  |
| B2 marker (2nd break)  | ✅        | Blue arrow up                  |
| FLIP marker            | ✅        | Orange arrow up                |
| FS marker (swing seal) | ✅        | Cyan arrow down                |
| Day toggle             | ✅        | ON=daily reset, OFF=continuous |
| Any timeframe          | ✅        | Works on 1m, 5m, 15m, 1H, etc. |
| No candle limit        | ✅        | No max_lines_count constraint  |
| Zigzag lines           | ❌        | Removed for simplicity         |
| LTF intrabar           | ❌        | Removed (source of complexity) |

### Key Design Decisions

1. **Markers only** — Use `plotshape()` for B1/B2/FLIP/FS
   - Zero drift (sticks to candles)
   - No line limit issue
   - Simple and fast

2. **Day mode toggle**

   ```
   ON:  Reset walker state at each calendar day (for NSE equity)
   OFF: Continuous flow from first candle (for BTC 24/7)
   ```

3. **Walker engine preserved** — Core swing detection logic stays the same
   - Seed determination (green/red first candle)
   - Pending stack management
   - Break detection (B1, B2, FLIP)
   - First swing (FS) marking at pivot seal

4. **Simplified state** — Remove line-related state variables

### Variables to REMOVE (from current)

```pinescript
// These are no longer needed:
line   lastSegLn = na      // line drawing
array<float>  innerPx    // stack for line segments
array<int>    innerBar
array<string> innerKd
float  bandHi             // line band tracking
float  bandLo
line   lastSegLn
```

### Variables to KEEP

```pinescript
// Core swing state:
int    dir                // direction (1=up, -1=down, 0=unborn)
float  stampPx           // pivot stamp price
int    stampBar          // pivot stamp bar
float  prevHigh          // previous bar high
float  prevLow           // previous bar low
int    pendKind          // pending break kind
int    pendBar
float  pendPx
float  pendNear
float  hiPx / hiBar      // current high tracking
float  loPx / loBar
bool   hiGrn / loRed     // color tracking
int    pvBar             // last pivot bar
float  pvPx
string pvKind
int    sealKind          // for FS marker
int    breakKind         // for B1/B2/FLIP markers
```

### File Structure

```
docs/pinescript/swing maker/
├── swing_markers_only.pine    (NEW - simplified version)
└── swing maker.pine           (existing - keep for reference)
```

### Implementation Steps

1. Create `swing_markers_only.pine` based on existing walker logic
2. Remove all `line.new()`, `line.set_x2/y2` code
3. Remove `push()` method line-drawing parts
4. Remove `closeStack()`, `innerPx/Bar/Kd` arrays
5. Keep only marker output via `plotshape()`
6. Test on different timeframes

### Marker Configuration (inputs)

```pinescript
grpC = "Markers"
colB1  = input.color(#94a3b8, "B1 (1st break)", group=grpC)   // grey
colB2  = input.color(#60a5fa, "B2 (2nd break)", group=grpC)   // blue
colFLIP= input.color(#f97316, "FLIP marker", group=grpC)       // orange
colFS  = input.color(#22d3ee, "FS marker", group=grpC)          // cyan
showMark = input.bool(true, "Show B1/B2/FLIP markers", group=grpC)
showFS   = input.bool(true, "Show FS marker", group=grpC)

grpD = "Day isolation"
dayMode = input.bool(true, "Reset per day", group=grpD)
```

### Estimated Lines

| Component      | Lines             |
| -------------- | ----------------- |
| UDT + state    | ~40               |
| Walker methods | ~80               |
| Main loop      | ~120              |
| Markers        | ~15               |
| Inputs         | ~20               |
| **Total**      | **~275** (vs 407) |

---

## Questions for You

1. **Marker style**: Keep arrow up/down as is, or change to something else (label, circle, etc.)?
2. **Marker text**: Show "B1"/"B2"/"FLIP"/"FS" text on chart, or just the colored markers?
3. **Double-break bars (LTF)**: Current script uses lower timeframe to resolve bars where both high and low break. Should we keep or remove this feature?

---

## Next Steps

1. **You approve** → Switch to Code mode → Implement `swing_markers_only.pine`
2. **Feedback** → Modify plan before implementation
