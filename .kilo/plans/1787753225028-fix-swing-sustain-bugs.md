# Distinguish FS Marker Type: Chop-Break vs Sustain

## Context
On 29 July, the FS marker appears at 9:48, which is the 7th bar after the swing low — meaning the swing was confirmed by **sustain**, not chop-break. But the chart shows the same "FS" label for both confirmation types.

User's earlier design intent (from chat dump):
> "A) Dono tareeke rahenge, bas chart pe alag naam — uchhal wala ▲FS, tik-jaane wala ◆SUS"
> - ▲FS = chop-break (price "jumps" up to break pivot)
> - ◆SUS = sustain (price "ticks" and holds above/below extreme for 7 bars)

## Current State
- `FsV2Engine.lastConfirmHit` tracks chop-break pool (`normal` | `micro`) but **does not mark sustain path**
- `FsV2Result` → `fsMarkers` only carries `{ idx, invalid }`, no source info
- `StockChart.tsx:873-887` renders all markers as `arrowUp` + "FS" text in cyan
- Sustain confirmation path doesn't set any field identifying itself

## Plan

### Step 1: Track confirm source in `FsV2Engine`
- Add `confirmSource: "chop" | "sustain" | null` field (set in the two `confirm()` call sites)
- `frontend/src/lib/flowline.ts:1064-1090` (chop-break): set `this.confirmSource = "chop"` before `this.confirm()`
- `frontend/src/lib/flowline.ts:1115-1117` (sustain): set `this.confirmSource = "sustain"` before `this.confirm()`

### Step 2: Propagate to `FsV2Result` and `fsMarkers`
- `FsV2Result` interface: add `source: "chop" | "sustain"`
- `computeFsV2Results` (flowline.ts:1169+): include `source: eng.confirmSource`
- `page.tsx:329`: pass `source` through to `fsMarkers`
- Type: `fsMarkers: { idx: number; invalid: boolean; source: "chop" | "sustain" }[] | null`

### Step 3: Render different markers in `StockChart.tsx`
- `StockChart.tsx:873-887`: branch on `mk.source`
  - `"chop"` → `arrowUp` + "FS" + `#22d3ee` (cyan, current behavior)
  - `"sustain"` → `arrowUp` + "SUS" + `#a78bfa` (purple, new)
- Keep invalid marker (red) unchanged

### Step 4: Validate
- `bun frontend/algotest.ts` → 75/75 still passes
- `bun frontend/fsv2.test.ts` → sweep still works (no logic change, just marker labeling)
- `npx -p typescript tsc --noEmit` → clean
- Manual: refresh 29 July, 31 July — markers should now show SUS where sustain confirmed

## Risk
- None to logic — this is purely a labeling/display change
- One backward-compat note: `fsMarkers` shape changes; any other consumer would need the `source` field added (currently only `StockChart.tsx` uses it)

## Out of Scope
- Changing which path confirms (chop-break vs sustain) — current ordering is fine
- Any changes to the sustain streak logic — already fixed
- Other marker types (manualFirstSwing, invalid) — unchanged
