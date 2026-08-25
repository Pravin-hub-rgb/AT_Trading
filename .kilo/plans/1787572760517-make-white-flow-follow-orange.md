# Fix: Make White Algo Line Use Manual Pivots on Training Dates

## Root Cause
`computeAlgoFlowLine()` (`flowline.ts:111-139`) always uses deviation zigzag `runDeviation(items, T)` regardless of whether manual pivots exist. On `2026-08-21`, the `T=11` threshold skips many smaller swings that the 31 hardcoded manual pivots capture.

## Exact Code Change: `frontend/src/lib/flowline.ts`

### Step 1 — Add shared helper after `MANUAL_PIVOTS` (after line 66):
```typescript
function resolveManualPivots(
  dayKey: string,
  items: { c: FlowCandle; gIdx: number }[],
): { idx: number; px: number }[] | null {
  const marks = MANUAL_PIVOTS[dayKey];
  if (!marks) return null;
  const pts: { idx: number; px: number }[] = [];
  for (const m of marks) {
    const item = items.find((it) => it.c.date.slice(11, 16) === m.time);
    if (!item) continue;
    pts.push({
      idx: item.gIdx,
      px: m.kind === "H" ? item.c.high : item.c.low,
    });
  }
  return pts;
}
```

### Step 2 — Refactor `computeFlowLine()` (lines 68-107) to use the helper:
Replace the inline pivot resolution (lines 82-90) with:
```typescript
const pts = resolveManualPivots(dayKey, items);
if (!pts) return;
```
Remove the old `pts` building loop. Behavior is identical — just deduplicated.

### Step 3 — Update `computeAlgoFlowLine()` (lines 111-139):
Replace the `byDay.forEach` body (lines 123-137) with:
```typescript
byDay.forEach((items) => {
  const manualPts = resolveManualPivots(items[0].c.date.slice(0, 10), items);
  const pts = manualPts ?? runDeviation(items, T);
  for (let i = 0; i + 1 < pts.length; i++) {
    const a = pts[i];
    const b = pts[i + 1];
    if (a.px === b.px && a.idx === b.idx) continue;
    segs.push({
      dir: b.px >= a.px ? "B" : "S",
      startIdx: a.idx,
      startPx: a.px,
      endIdx: b.idx,
      endPx: b.px,
    });
  }
});
```

## Result
- On `2026-08-21`: white line = orange line (exact overlap, same 31 pivots)
- On all other dates: white line still uses deviation zigzag `T=11` (unchanged)
- No backend changes, no chart rendering changes

## Validation
1. Open chart → 5-min interval → 21 Aug
2. Toggle "Flow Line" on
3. White line should sit exactly on top of orange line
4. Check a date without manual pivots — white line should still appear via zigzag
