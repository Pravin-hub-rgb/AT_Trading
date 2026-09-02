# Plan — 1-min Entry must be on a bar AFTER FS confirmation (not the FS-mark bar)

**Date:** 2026-09-01
**User settings:** `exec: precise 1min`, `entry: pivot break` (and any other 1-min config)
**Files:**

- [`backend/src/intraday.py`](backend/src/intraday.py)
- [`backend/src/intraday_1m.py`](backend/src/intraday_1m.py)

> **Scope rule (re-confirmed with user):**
> The rule applies **purely on the 1-min timeline**. There is **no 5-min gate involved** — `can_enter` and the 5-min `entry_swing_confirmed_idx` are irrelevant to this fix. The only thing that matters is: every 1-min entry fill must be on a 1-min bar whose index is **strictly greater than** the 1-min bar index at which FsV2 declared the relevant swing.

---

## Problem

**21 Aug 2026 example:** 09:40 trade is wrong.

- The 1-min bar at **09:39** breaks the most recent sealed pivot. This is the **FS-mark bar** — `FirstSwingEngine` confirms the first swing on it (or right around it).
- The **next 1-min bar (09:40)** has already passed the entry point — it's gone below the pivot and is running.
- Current behaviour: the engine fires at 09:39 (FS-mark bar). Wrong.

Per the user's rule: **"Enter on the FIRST 1-min candle AFTER the swing is confirmed by FS. If that candle has already passed entry, skip and look for next pullback."**

So on 21 Aug:

| Time                                    | What happens                                          | Correct?                                                |
| --------------------------------------- | ----------------------------------------------------- | ------------------------------------------------------- |
| 09:39                                   | 1-min bar breaks pivot (FS-mark bar)                  | Not yet eligible (FS not confirmed at this bar's close) |
| FS confirms (at 09:39 or shortly after) | Engine sees FS declared                               | —                                                       |
| 09:40                                   | First 1-min bar AFTER FS confirms, already past entry | MISSED — skip this break, wait for next pullback        |
| 09:45                                   | New pullback gives next setup                         | Enter here if pivot breaks again on a post-FS bar       |

## Where the bug lives

### Direct 1-min path (the smoking gun)

[`backend/src/intraday.py:1395-1421`](backend/src/intraday.py:1395) — detection loop finds `brk_m1`, the FIRST 1-min bar in the current 5-min window that breaks the pivot. No check that FS was already confirmed at that bar's index.

[`backend/src/intraday.py:1547`](backend/src/intraday.py:1547) — opens the trade on `brk_m1` directly. This is where the FS-mark-bar entry happens.

### Deferred 1-min path

[`backend/src/intraday.py:1567-1596`](backend/src/intraday.py:1567) — fallback `pending_direct` when `brk_m1` is None.

[`backend/src/intraday_1m.py:165-241`](backend/src/intraday_1m.py:165) — `resolve_pending_direct` returns the FIRST 1-min bar after `armed_ts` that breaks the pivot. `armed_ts` is set from the pivot-seal time, not from FS-confirm time.

The same logical gate must apply: a returned 1-min bar whose index is at-or-before the FS-confirm 1-min index is the FS-mark bar and must be skipped.

## The 1-min gate variables we already have

From [`backend/src/intraday.py:962-989`](backend/src/intraday.py:962) (already computed in `simulate_day`):

```python
fs1_1min_confirmed_idx: int = -1     # 1-min bar index where FS was declared
fs1_1min_end_idx: int = -1
fs1_1min_end_time: str = ""
```

And from the `detect_second_swing` block (used by conservative mode, also already computed):

```python
fs2_confirmed_idx: int = -1          # 5-min mapped, but the underlying eng2.confirmed_at_idx is 1-min
```

We need an **unmapped** 1-min index for FS2. `eng2.confirmed_at_idx` returns the 1-min bar index directly (the engine runs on `m1_candles`); we just need to surface it.

> **Key decision:** the gate is **`entry_m1_idx > fs_confirmed_m1_idx`** (1-min index, not 5-min). This is the simplest, most correct expression of the user's rule.

---

## Fix design (1-min timeline only)

### Step 1 — Expose `fs2_confirmed_m1_idx`

In the conservative branch of `simulate_day` ([`L1015-1057`](backend/src/intraday.py:1015)), `eng2.confirmed_at_idx` is already the 1-min index. Stash it:

```python
fs2_confirmed_m1_idx = eng2.confirmed_at_idx if eng2.declared else -1
result["fs2_confirmed_m1_idx"] = fs2_confirmed_m1_idx
```

For the fallback path at `L1060`, `detect_second_swing` returns the 1-min index too via `eng.confirmed_at_idx`; surface it similarly.

### Step 2 — Pick the right 1-min gate index

After both are computed, define:

```python
# 1-min gate: the entry-relevant swing's confirmed 1-min index
if trade_mode == "conservative" and fs2_confirmed_m1_idx >= 0:
    entry_swing_confirmed_m1_idx = fs2_confirmed_m1_idx
elif fs1_1min_confirmed_idx >= 0:
    entry_swing_confirmed_m1_idx = fs1_1min_confirmed_idx
else:
    # No 1-min FS declared → no 1-min gate (FS confirmation itself is the only prerequisite)
    entry_swing_confirmed_m1_idx = -1   # -1 means "no gate"
result["entry_swing_confirmed_m1_idx"] = entry_swing_confirmed_m1_idx
```

### Step 3 — Reject direct entry on FS-mark bar (`L1547`)

In the `if use_1m:` block, when `brk_m1_local` is found:

```python
brk_m1_local = locals().get("brk_m1")
if brk_m1_local is not None:
    brk_m1_idx = int(brk_m1_local.get("index", -1))
    # 1-min gate: must be STRICTLY AFTER the entry-swing's confirmation index
    gate_ok = (
        entry_swing_confirmed_m1_idx < 0
        or brk_m1_idx > entry_swing_confirmed_m1_idx
    )
    if not gate_ok:
        # brk_m1 is the FS-mark bar (or earlier). Skip it.
        # Defer: pin armed_ts to the 1-min bar STRICTLY AFTER fs-confirm,
        # so resolve_pending_direct returns the NEXT post-FS break of this pivot.
        pivot_arm_ts = (
            m1_candles[entry_swing_confirmed_m1_idx + 1]["ts"]
            if entry_swing_confirmed_m1_idx + 1 < len(m1_candles)
            else int(cur["ts"])
        )
        pending_direct = {
            "bar_idx": i,
            "trade_dir": trade_dir,
            "level": brk["level"],
            "break_type": brk["type"],
            "armed_ts": pivot_arm_ts,
            "fs_mark_bar_skipped": True,
        }
        result["events"].append({
            "type": "pending_direct_1m",
            "bar": i, "time": cur["time"],
            "ts": int(cur["ts"]),
            "level": round(brk["level"], 2),
            "break_type": brk["type"],
            "direct": False,
            "fs_mark_bar_skipped": True,
            "fs_confirmed_m1_idx": entry_swing_confirmed_m1_idx,
        })
        entered = False
    else:
        # brk_m1 is strictly after FS confirms → safe to enter directly
        if _open_trade(...): ...   # existing code
```

### Step 4 — Reject stale resolves in `pending_direct` path

In the resolve block at [`L1255-1275`](backend/src/intraday.py:1255), the `m1_bar` returned by `resolve_pending_direct` is the 1-min bar that broke the pivot. We need to re-verify its 1-min index is past the gate:

```python
m1_bar = resolve_pending_direct(pending_direct, m1_day, cur["ts"])
if m1_bar is not None and m1_bar["ts"] <= cur["ts"]:
    # 1-min gate re-check (defence-in-depth; resolver also filters)
    if (entry_swing_confirmed_m1_idx >= 0
        and m1_bar.get("index", -1) <= entry_swing_confirmed_m1_idx):
        result["events"].append({
            "type": "setup_disarmed_pre_fs",
            "bar": i, "time": cur["time"],
            "reason": "resolved_bar_is_fs_mark",
            "resolved_idx": m1_bar.get("index"),
            "fs_confirmed_idx": entry_swing_confirmed_m1_idx,
        })
        pending_direct = None
    else:
        # ... existing _open_trade call
```

### Step 5 — Filter FS-mark bars in `resolve_pending_direct`

In [`backend/src/intraday_1m.py:165-241`](backend/src/intraday_1m.py:165), add an optional `fs_confirmed_m1_idx` param. Bars at or before that index are skipped:

```python
def resolve_pending_direct(pending, m1_day, upto_ts, fs_confirmed_m1_idx=-1):
    ...
    for _, bar in rows.iterrows():
        bar_idx = int(bar.name) if bar.name is not None else 0
        if bar_idx <= skip_until_idx:
            continue
        # 1-min gate: skip the FS-mark bar and any earlier bars
        if fs_confirmed_m1_idx >= 0 and bar_idx <= fs_confirmed_m1_idx:
            continue
        if trade_dir == -1 and bar["low"] < level:
            return {...}
        ...
```

Caller in `intraday.py` passes `entry_swing_confirmed_m1_idx`.

---

## Files to change

| File                                                                   | Change                                                                                         |
| ---------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| [`backend/src/intraday.py:962-989`](backend/src/intraday.py:962)       | Stash `fs2_confirmed_m1_idx` on result; define `entry_swing_confirmed_m1_idx`                  |
| [`backend/src/intraday.py:1539-1605`](backend/src/intraday.py:1539)    | 1-min gate check on `brk_m1`; defer with `pivot_arm_ts = m1_candles[fs+1].ts` if pre-FS        |
| [`backend/src/intraday.py:1255-1275`](backend/src/intraday.py:1255)    | Re-verify gate on resolved `m1_bar` index                                                      |
| [`backend/src/intraday_1m.py:165-241`](backend/src/intraday_1m.py:165) | `resolve_pending_direct(pending, m1_day, upto_ts, fs_confirmed_m1_idx=-1)` filters pre-FS bars |

**No frontend changes.** Same pattern as FsV2 gate — hard-coded safety rule, no UI toggle.

---

## Verification

1. **`backend/debug/_check_fs_timing.py`** — extend to also check `entry_m1_idx > fs_confirmed_m1_idx` for every 1-min entry. Should print 0 violations.
2. **21 Aug 2026 trace** — manual check:
   - 09:39 break should be flagged `fs_mark_bar_skipped: true` (deferred).
   - No entry at 09:39 or 09:40.
   - Next pullback entry fires only on a post-FS 1-min bar that breaks a pivot.
3. **Re-run `_ss_test.py`** — 30-day backtest stats:
   - Trade count may drop slightly on days where the FS-mark-bar entry was a loser.
   - R-multiple should improve (FS-mark-bar entries are usually late / against momentum).
4. **Edge case: 28 Aug** — FS confirms at 09:30 on 1-min chart, 10:30 1-min break should still fire (post-FS). Verify no regression.
5. **Edge case: trade where FS confirms very early (e.g. 09:20)** — first post-FS 1-min break is still detected and entered.

## Out of scope

- 5-min execution path (untouched).
- `can_enter` and the 5-min `entry_swing_confirmed_idx` gate (orthogonal; this is purely a 1-min entry-fill rule).
- Conservative/aggressive gate semantics change (only fixing the pre-FS same-bar entry).
- UI / config exposure (hard safety rule).
