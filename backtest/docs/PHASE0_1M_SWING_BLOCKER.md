# PHASE 0 — the 1m swing blocker is SOLVED, and the handover premise was wrong

Date: 2026-09-28. Commit at time of writing: `4ee4a8b`.
Script: `backtest/tests/phase0_1m_swing_diag.py`
Report: `backtest/tests/_phase0_1m_swing_diag.json`

## The claim being tested

`HANDOVER_SESSION.md` §7 recorded this BLOCKER:

> `_compute_swings(fine, "continuous", min_bars=N)` over the full 1.95M bars
> did not finish in ~2 minutes and the process died — memory-bound.
> **Solve this first; everything else is wasted until then.**

It also listed three Phase 0 options as "none chosen, all plausible":
(a) chunked/windowed swing computation, (b) pre-filter 1m bars,
(c) keep swing detection on 15m and map only entry *timing* onto 1m.

## The measurement

I did not implement any of (a)/(b)/(c) first. I measured the actual call on
growing prefixes of the real 1m file, which is the only way to tell a real
memory wall from a slow machine or a bad harness.

| bars | swings | time_s | µs/bar | bars/swing |
|---|---|---|---|---|
| 14,400 | 397 | 0.10 | 7.09 | 36.3 |
| 43,200 | 1,730 | 0.33 | 7.55 | 25.0 |
| 86,400 | 3,711 | 0.68 | 7.90 | 23.3 |
| 172,800 | 7,601 | 1.38 | 7.99 | 22.7 |
| 345,600 | 14,719 | 2.68 | 7.75 | 23.5 |
| **1,946,042 (full)** | **90,991** | **18.49** | **9.50** | **21.4** |

Time ratios track bar ratios almost exactly at every step (x3.26 for x3.0,
x2.07 for x2.0, x2.03 for x2.0, x1.94 for x2.0). **The cost is linear.**
µs/bar drifts only 7.1 → 9.5 across a 135× range, which is cache drift, not a
growing term.

**The full 1,946,042-bar run completes in 18.5 seconds** and returns
**90,991 swings**.

## Where the memory actually goes

Working set peaks at **957 MB**, and only **162 MB** of that is the swing
computation — the other 760 MB is the 1.95M `FlowCandle` objects, which are
already resident before the engine is called. tracemalloc peak for the whole
swing call is **177 MB**. Top sites are all proportional to the *output*:

| MB | count | site |
|---|---|---|
| 58.2 | 181,982 | `btc_swing.py:114` — the `out.append({...})` swing dict |
| 15.3 | 90,792 | `firstswing.py:225` — `Lvl` snapshot copies per bar |
| 13.3 | 205,987 | `btc_swing.py:131` — `breaks` mark dicts |
| 12.3 | 440,072 | `btc_swing.py:75` — the `for pos in range(...)` walk |

There is no unbounded accumulator. `bar_highs`/`bar_lows` are cleared at
`bars_seen == 1` (`firstswing.py:210-211`) and each `SwingEngine` is rebuilt
per swing, so per-engine state is bounded by one swing (~21 bars), not by the
window. **Nothing in the algorithm is O(window²)** — the engine is re-seeded
per swing precisely so it is not.

## Verdict: the blocker is NOT real

Phase 0 needed no chunking, no pre-filtering, and no timing remap. The call
that was reported to die runs in 18.5s and costs 177 MB.

**The most likely explanation is the harness, not the algorithm.** Two
candidates, both worth knowing before Phase 1:

1. **Loading both halves.** `exp_s3_forensic._candles` builds *both* the
   candle-dict list and the `FlowCandle` list. Only `FlowCandle` is needed to
   swing. The dict half is several hundred MB more on 1.95M rows, and
   `_read_tf` holds a full pandas frame plus a `sort_values` copy on top. A
   harness that loaded the dicts and then also ran the engine's 15m/1h data
   would be the memory-bound thing — not `_compute_swings`.
2. **A different `min_bars`.** The handover recorded `min_bars=N` with N
   unstated. The run above is `min_bars=10` (`sw10`, the champion's setting).
   Larger `min_bars` produces *fewer* swings and is cheaper, so that does not
   explain a failure either — but the number should be pinned down before
   anyone repeats this.

**I could not reproduce the reported death on this machine, and I am not
claiming the original report was wrong** — only that the blocker as written
does not block. Anyone who saw the original failure should say what harness
it was; that is the only open thread in Phase 0.

## Discipline notes

- **Control gate.** `swings_continuous()` is a hand-rolled thin wrapper
  around `compute_btc_swings`, so before any number is trusted the script
  asserts it equals the real `btc_routes._compute_swings`. It does
  (`wrapper_matches_routes: true`) — the wrapper is not a second
  implementation that happens to agree.
- **A broken instrument was caught and fixed, not reported.** The first run
  printed `ws_MB 0` for every prefix. That was a real bug in my
  `working_set_mb()`: `ctypes.windll.psapi.GetProcessMemoryInfo` was called
  without `argtypes`, so the 64-bit `HANDLE` was truncated to `c_int` and the
  call silently returned 0. Fixed with explicit `restype`/`argtypes` before
  the memory column was believed. Had I not fixed it, I would have "confirmed"
  a 0 MB memory profile and concluded the opposite.
- **Prefixes before the full run.** The scaling curve is the diagnosis; the
  full run is only run once the curve says it is affordable. This is what
  made the 18.5s result trustworthy rather than lucky.

## Where this leaves the 1m layer

Phase 0 is done and the way is clear. Phases 1–3 in §7 were written under the
assumption that 1m swings were unaffordable, so they should be re-read with
that constraint removed:

- **Phase 1** (a `exp_entry_tf="1m"` kwarg substituting `swings_ltf`) is
  unblocked and remains the right next step — it is wiring, not new concept.
- **Phase 2** (4-cell sweep, 1m setup on/off × `exp_mltf` on/off) is unblocked.
- **Phase 3** (`exp_mltf_green_r`, the R-threshold add-on) is *independent* of
  all of this and was never blocked in the first place.

**Still nothing adopted.** Production untouched, all flags default-off.
