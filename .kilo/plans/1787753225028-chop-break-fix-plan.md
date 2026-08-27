# Plan: Fix FsV2Engine — Chop-Break Logic + Time Cap

## Context / Existing Implementation

- **`zonePct`** (default 25 in engine, **10** in chart via `FS_REV_DEFAULT`): Deep-zone % of range. Price entering ≤ zonePct% from bottom (selling) or ≥ 100-zonePct% (buying) triggers zone conversion to stage-2.
- **`armBars: 5`** and **`armRangePts: 20`**: Zone rules only arm after 5 bars AND range ≥ 20 points.
- **`simpleMode: true`** (always used in chart): Skips stage counting from walker E-pivot seals and zone-based invalidation. Engine relies on v3 fast-path (single E-break lock) + zone conversion.
- **No existing time-cap logic** — no filtering of early 9:15–9:29 noise.

---

## Problem 1: Chop-Break Fires on Normal Pivot Break

On 28 July, chop-break fires at 09:22 when a normal L-pivot (24024.30 @ 09:19) is broken. The E-high (24040.90) and E-low (23968.15) were never broken. The user requires breaking the **current extreme (E-high/E-low) twice** — first break sets a new extreme, second break of that new extreme confirms.

## Fix 1: Chop-Break = Double Extreme Break

### File: `frontend/src/lib/flowline.ts`

#### Step 1: Add `chopBreakCount` and `preConfirmSource` to FsV2Engine state

```typescript
private chopBreakCount = 0;
private preConfirmSource: "chop" | "sustain" | null = null;
```

#### Step 2: Reset `chopBreakCount` when swing initiates

In `initiate()` (around line 1144), add `this.chopBreakCount = 0`.

#### Step 3: Increment `chopBreakCount` when opposite extreme is broken

In the halves loop where `eHi`/`eLo` are updated (lines 968-975):
- For **selling swings** (`this.dir === "down"`): when `eHi.px` increases (new E-high printed), increment `this.chopBreakCount`
- For **buying swings** (`this.dir === "up"`): when `eLo.px` decreases (new E-low printed), increment `this.chopBreakCount`

#### Step 4: Reset `chopBreakCount` on new extreme during swing

In the sustain block (around line 1116), when `madeNewExtreme` is true, also reset `this.chopBreakCount = 0`.

#### Step 5: Replace normal-pivot chop-break with extreme-break chop-break

Replace lines 1067-1099 (the "final confirmation: ANY FRESH normal OPPOSITE pivot crossed by wick" block) with:

```typescript
// CHOP-BREAK: opposite extreme broken twice → first break = new extreme, second = confirm
if ((this.stage >= 2 || this.locked) && this.chopBreakCount >= 2) {
  this.confirmSource = "chop";
  this.confirm(gIdx, t);
  return;
}
```

---

## Problem 2: Early-Market Noise (9:15–9:29)

Swing confirmations that happen before 09:29 are unreliable due to opening-range noise. Before 09:29, no swing markers should be shown. If a swing reaches confirmation before 09:29, it should be held until 09:29. During the hold, if the swing continues in the same direction (new extremes), the end updates. If it reverses, it's killed.

## Fix 2: Time-Cap Logic

### File: `frontend/src/lib/flowline.ts`

#### Step 6: Add `timeCap` to `FsV2Opts`

```typescript
timeCap?: string; // "HH:MM", default "09:29"
```

#### Step 7: Add time-cap fields to `FsV2Engine`

```typescript
private timeCap = "09:29";
private preConfirmed = false;
private preInvalidated = false;
```

#### Step 8: Initialize `timeCap` in constructor

```typescript
constructor(private opts: FsV2Opts = {}) {
  this.timeCap = this.opts.timeCap ?? "09:29";
}
```

#### Step 9: Modify `confirm()` to check time cap

```typescript
private confirm(gIdx: number, t: string) {
  if (t < this.timeCap) {
    this.preConfirmed = true;
    this.preConfirmSource = this.confirmSource;
    return;
  }
  this.declared = true;
  this.endIdx = this.candIdx;
  this.endTime = this.candTime;
  this.endPx = this.candPx;
  this.confirmedAtTime = t;
  this.confirmedAtIdx = gIdx;
}
```

#### Step 10: Modify invalidation points to check time cap

Lines 1047 and 1060 — wrap `this.invalidated = true`:

```typescript
if (hit) {
  if (t < this.timeCap) {
    this.preInvalidated = true;
    return;
  }
  this.invalidated = true;
  return;
}
```

#### Step 11: Add time-cap flush at end of `processBar`

After the sustain block (after line 1130), before `debugPools()`:

```typescript
// ---- Z) time-cap flush: resolve pending confirm/invalidate at time cap ----
if (t >= this.timeCap) {
  if (this.preInvalidated && !this.declared) {
    this.invalidated = true;
    this.preInvalidated = false;
  } else if (this.preConfirmed && !this.declared && !this.invalidated) {
    this.confirmSource = this.preConfirmSource;
    this.confirm(gIdx, t);
    this.preConfirmed = false;
    this.preConfirmSource = null;
  }
}
```

**Priority:** `preInvalidated` takes precedence over `preConfirmed`. If both are true, the swing is killed.

---

## Chart Page Integration

### File: `frontend/src/app/chart/page.tsx`

#### Step 12: Pass `timeCap` to engine

In the `computeFsV2Results` call (around line 321), add:

```typescript
timeCap: "09:29",
```

---

## Validation

1. Run full test suite: `npm test` (expect 75/75 passing)
2. Run 28 July diagnostic: verify chop no longer fires at 09:22
3. Run 31 July diagnostic: verify swing still works correctly
4. Verify pre-09:29 swings are not shown before 09:29
5. Verify a swing that confirms at 09:15 but continues to 09:29 shows the updated end

## Constraints

- Do NOT edit flowline visualization (user explicitly said don't edit flowline)
- Chart config: zonePct=10, simpleMode=true, armBars=5, armRangePts=20, timeCap=09:29
