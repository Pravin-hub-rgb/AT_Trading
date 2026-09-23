# D3 ALIGNMENT — HOSTILE LOOKAHEAD AUDIT (2026-09-23)

## Verdict

**REFUTED as a live-causal gate.** The `dirmatch` / `age10` numbers come from
reading **final** swing `dir` / `start_idx` off the **full-history** batch chain
at entry bar `i`, without requiring `confirmed_at_idx <= i`. A live trader at
bar `i` does not have that label.

| claim (other bot) | audit result |
|---|---|
| "prefix-identical chain => no lookahead" | **Wrong test.** Chain-diff used one fixed date cut + `min_bars=35`, compared swing *lists*, not the **selector** output. Per-entry truncation + production `min_bars=50`: **194/500 dir mismatch, 353/500 age mismatch.** |
| "direction is knowable from the pivot" | True for the **live forming engine**. The gate does **not** use that — it walks `swings_ltf` final dicts. **353/500 picks have `confirmed_at_idx > entry`.** |
| "125/125 opposed = 0% WR, 4/4 years" | True **only under full-history final labels.** Under labels available at entry (`data[:i+1]`): opposed = **271t, +250.7R, WR 30.3%.** |
| "age and dir are independent, both real" | Age table **inverts** under causal labels: age 0-10 **empty** (confirmation needs minBars), age 51+ is fine (+0.7..+1.4 avg). |
| "dirmatch +479.9 is legitimate" | Path-true with `confirmed_at_idx <= i`: **NET +75.0 (−404.9).** age10 configs → **0 trades.** |

## Path-true retest (`exp_dir_causal=1`, identity gate still green)

### IS 2023–2026 (sw10)

| config | old NET | causal NET | Δ |
|---|---:|---:|---:|
| dirmatch_multi_sw10 | +479.9 | **+75.0** | −404.9 |
| age25_dirmatch_multi | +386.7 | **−4.7** | −391.3 |
| age10_dirmatch_multi | +455.5 | **0 trades** | −455.5 |
| dirmatch_swingpause_single | +288.1 | **+102.0** | −186.1 |
| age10_dirmatch_swingpause_single | +435.7 | **0 trades** | −435.7 |

### True OOS 2021–2022 (sw10)

| config | old NET | causal NET | Δ |
|---|---:|---:|---:|
| dirmatch_multi_sw10 | +162.6 | **+53.4** | −109.3 |
| age25_dirmatch_multi | +156.4 | **+8.0** | −148.4 |
| age10_dirmatch_multi | +51.9 | **0 trades** | −51.9 |
| dirmatch_swingpause_single | +57.7 | **−12.8** | −70.4 |

`age10_*` is **structurally empty** under confirmation gating: with
`min_bars_15m=50`, a swing cannot be both confirmed and age ≤ 10 at entry.

## Label audit (same 500 champion trades)

| labeling | opposed n | opposed R | opposed WR | all exactly −1R? |
|---|---:|---:|---:|---|
| **FULL final** (the claim) | 125 | −125.0 | **0.0%** | yes |
| **TRUNCATED at entry** (live-knowable) | 271 | **+250.7** | **30.3%** | no |
| **LIVE forming engine state** | 64 | **+147.7** | **31.2%** | no |

- Full picks with `confirmed_at > entry`: **353/500 (70.6%)**
- Signal’s own `swing_no` unconfirmed at entry: **500/500 (100%)** — marks fire
  during formation, before chop declaration; the gate then reads that swing’s
  **final** dir (post-FLIP).
- Of the 125 full-opposed: under **live** labels → **96 become MATCH, 29 remain opposed**.
- Of the 125 full-opposed: under **truncated** labels → **24 flip dir**, 101 keep dir.

## Why the other bot’s proofs fail

1. **Chain-diff (`exp_chain_diff_cline.py`)** cuts at one date, uses
   `min_bars=35` (not 50), and compares swing *lists* elementwise. The gate is
   not “swing #k exists” — it is “**last** swing with `start_idx <= i`”.
   Full history can contain a swing that **starts before `i` and confirms after
   `i`**; truncated-at-`i` does not have it. That is exactly the leak.
2. **Temporal stability of 0% WR** does not prove causality. Final dir is
   computed on the **same path that produced the loss** (price ran against the
   trade → swing’s completed leg is the opposite way). Uniform 4/4 years is
   consistent with **outcome-aligned labeling**, not with a live filter.
3. **“Direction from running extreme is causal.”** Yes — for the **live**
   `SwingEngine.dir` at bar `i`. The patch never reads that. It reads
   `swings_ltf[j]["dir"]` after the chain has finished (`btc_swing.py` only
   appends **declared** swings with final fields).
4. **Age confound table** uses the same full-history `start_idx`. Under
   truncation, age **353/500** change; causal age 0-10 is empty.

## What is still true

- The **shipped champion** identity gate is unaffected (`exp_dir_causal=0`).
- Raw full-history **association** is real as a *descriptive* autopsy: trades
  whose **completed** swing ended opposite the trade all hit −1R. That is a
  statement about the **future**, not a gate.
- `skip_decisive` (ATR% causal, `v18_streak_halt.py:266`) remains the clean
  path-true filter from the prior session.

## Recommendation

| config | action |
|---|---|
| `dirmatch_*`, `age10_*`, `age25_dirmatch_*` | **Do not ship.** Numbers do not survive `confirmed_at_idx <= i`. |
| age10 “BEST EVER” single | **Dead** — 0 causal trades. |
| Other bot’s 125/125 writeup | Mark **REFUTED (lookahead via final chain labels)** in docs. |
| Future structural gates | Must read **live engine state at bar i** or **only swings with `confirmed_at_idx <= i`**. Re-run this audit before any pin is trusted. |

## Salvage follow-up (2026-09-23) — all paths closed

Causal re-label + path-true retest of every candidate that survived the audit:

| candidate | trade-list (live labels) | path-true IS/OOS | verdict |
|---|---|---|---|
| live dir-match | OPPOSED **+147.7R** (good — inverted vs leaky 125/125) | n/a (no net-neg bucket to cut) | nothing to gate |
| live age 51+ | **+136.7R / avg +2.40** (best — inverted vs leaky “stale”) | n/a | nothing to cut |
| live runmag ≥2% | −9.9R / bigW 2 (passes rule) | **−24 / −36 dIS/dOOS** (champion 2.0); 3.0/4.0 noise | **DEAD** |
| early-exit on live dir flip | hybrid +266 vs base +445 | already dead on trade-list | **DEAD** |
| entry-candle / risk / body stacks | −14 … −306 dR | risk_max 2.0 = −24.7 / −48.4 | **DEAD** (§3e/§3h) |

**No gate ships.** The open path (live-snapshot runmag) failed full-path the
same way every scattered per-trade filter fails (§3e path cascade). What
remains from the D3 session is the **methodology** — `replay_live_state`,
`exp_dir_causal`, identity-gated path-true harnesses — not new pins.

Harnesses: `exp_alignment_salvage.py` (buckets),
`exp_alignment_live_gate_path.py` (path-true, kwargs since reverted),
`exp_causal_autopsy_path.py` (F1/F6/F7 tombstone).

## Reproduce

```
python live_stuff/tests/exp_alignment_causal_audit.py
python live_stuff/tests/exp_alignment_live_state_audit.py
python live_stuff/tests/exp_causal_dirmatch_path.py
python live_stuff/tests/exp_alignment_salvage.py
python live_stuff/tests/exp_alignment_salvage_path.py
python live_stuff/tests/exp_causal_autopsy_path.py
# live-snapshot path-true: exp_alignment_live_gate_path.py (needs exp_max_live_runmag — reverted; see EXPERIMENT_LOG 2026-09-23)
```

Flags: `exp_dir_causal` added to `test_experiments_craze.py` (default 0).
`exp_er_*` and `exp_max_live_runmag` were temporary; both reverted (dead = clutter).
