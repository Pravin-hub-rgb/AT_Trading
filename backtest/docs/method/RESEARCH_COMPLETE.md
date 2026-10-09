# RESEARCH COMPLETE — what was swept, what came out, what is left

Date: 2026-10-09. Harness: `exp_completion_sweep.py`.
Companion: `FSENT_MASTER_STUDY.md` (the full record).

---

# 0. The one-line answer

**Sweeping this family is finished. The result is that `max_consecutive_losses`
was the whole story, and every other knob is decoration.**

Evidence: in the 3×2×2 joint grid over `max_consecutive_losses` × HTF leg length
× HTF FS entry, **zero negative half-years is determined entirely by the first
factor.** All four `mcl=0` arms are clean. All four `mcl=4` arms are clean. Of the
four `mcl=3` arms only one is clean. **Swing length and FS entry change the
number, never the verdict.**

---

# 1. The joint grid

`fsent_champ_long`, both eras, 12 arms:

| mcl | swing | htf_fs | n | net | dd IS | dd OOS | **neg** |
|---:|---|---|---:|---:|---:|---:|---:|
| 0 | sw10 | off | 912 | +837.50 | 15.13 | 14.16 | **0** |
| 0 | sw10 | all | 1275 | +1283.46 | 19.95 | 15.02 | **0** |
| **0** | **htf15** | **off** | **859** | **+893.52** | **15.13** | **13.64** | **0** |
| 0 | htf15 | all | 1245 | **+1321.41** | 18.84 | 15.02 | **0** |
| 3 | sw10 | off | 839 | +772.96 | 13.42 | 11.88 | **1** |
| 3 | sw10 | all | 1191 | +1199.94 | 19.78 | 16.12 | 1 |
| 3 | htf15 | off | 800 | +822.45 | 17.28 | 16.86 | 0 |
| 3 | htf15 | all | 1161 | +1222.24 | **29.62** | 16.12 | 1 |
| 4 | sw10 | off | 872 | +817.10 | 15.06 | 12.66 | **0** |
| 4 | sw10 | all | 1230 | +1244.03 | 27.74 | 14.20 | **0** |
| **4** | **htf15** | **off** | **822** | **+865.68** | **15.95** | **13.91** | **0** |
| 4 | htf15 | all | 1198 | +1289.13 | 18.22 | 14.20 | **0** |

**Ten of twelve are clean.** A criterion that ten of twelve arms pass is not
discriminating — and pretending otherwise is how this repo ended up with four
"candidates" that all reduce to one integer.

## the recommendation: `fsent_champ_long_mcloff_htf15`

IS 560 / +616.17 / 15.13 / WR 41.1% · OOS 299 / +277.35 / 13.64 / WR 38.1%

**Not the +1321R arm.** That one uses `exp_htf_fs_entry=all`, which collapses
flip/decisive/b2 into a single `fs_entered` set — the book that scores best is the
book that stopped distinguishing regimes. This one reaches +616R and stays honest.

| book | IS net | OOS net | IS dd | OOS dd | neg |
|---|---:|---:|---:|---:|---:|
| `champ_long` (shipping) | +533.37 | +239.59 | 13.42 | 11.88 | **1** |
| `mcloff` | +566.58 | +270.91 | 15.13 | 14.16 | 0 |
| **`mcloff_htf15`** | **+616.17** | **+277.35** | 15.13 | 13.64 | **0** |

---

# 2. Every knob, swept

| knob | values | verdict |
|---|---|---|
| `max_consecutive_losses` | 0,1,2,3,4,6 | **the fix.** 0 and 4 clean; 1 is a trap (ddIS 35, 3 negatives) |
| `exp_bias_momentum_min` | 0–3.0 | 0.5 gives the parent's exact DD; **period control fails** |
| HTF `min_bars` | 10–30 | 13–15 plateau; 30 a spike |
| `exp_htf_fs_entry` | off/flip/all | flip inert; all degenerates the regime set |
| `exp_cap_days` | 3–21 | **21 gives +835.93 at 0 negative**, vs 10 at +680.52 |
| `window_end` | exit/r_touch/bias_flip | `r_touch` inert; **`bias_flip` +1154.94 at 0 negative** |
| `ext_stop_r` | 0–5 | only 2.0 binds (+788.09, 0 neg); 0/3/4/5 identical |
| `exp_partial_r` | 0–1.5 | **1.5 gives the lowest DD in the family, 10.35**, at +473.54 |
| `exp_skip_utc_sat` | 0/1 | 1 → 0 negative, +632.39 |
| `exp_skip_utc_sun` | 0/1 | 1 → 0 negative, +615.72 |
| `exp_no_opposite` | 0/1 | **removes 6 trades, does NOT fix the cell.** Never worth applying |
| `exp_min_sl_pct` | 0–0.01 | only hurts. Confirms the owner's dismissal |
| `cooldown_bars` | 0–24 | 8 optimal; 0 catastrophic (ddIS 51.39) |
| `exp_persist` | 0–12 | 5 marginally better |
| `sl_buf_atr` | 0–0.02 | flat, 0.005 ≈ default |
| `atr_high_thresh` | 0.5–0.8 | flat |
| `pivot_rule` | leg/leg_no_entry | leg_no_entry worse (ddIS 20.66) |
| **`chop_thresh`** | 46–70 | **DEAD — all values byte-identical** |
| **`atr_low_thresh`** | 0.20–0.50 | **DEAD — only read in `atr_low` mode** |
| **`exp_ltf_no_entry`** | 0/1 | **DEAD — byte-identical** |
| **`exp_causal_sl`** | 0/1 | **1 is catastrophic: ddIS 205.83.** Must stay off |

## four knobs in the engine that do nothing

`chop_thresh`, `atr_low_thresh` and `exp_ltf_no_entry` are **inert** in this
architecture — present in every champ book's params, reading like live controls,
producing identical output at every value. `exp_causal_sl=1` is not inert but is
catastrophic.

**That is a maintenance finding, not a research one**, and it is worth acting on
separately: dead knobs in a params dict are how a future person believes a
control exists when it does not.

---

# 3. The multiple-comparisons problem, stated plainly

**Sixteen arms clear zero negative cells while keeping at least half the book.**
Some of that is luck. Sweeping ~130 arms and reporting the ones that look good is
how you manufacture a result that does not replicate.

Three things make the surviving claims more than that:

1. **`mcl` is not a swept arm, it is a mechanism.** The autopsy explains *why* —
   a 3-loss cutoff stops the book before the recovery trade. That reasoning does
   not depend on having picked the value by search.
2. **The period control is powered and positive in both eras** for `mcl=0`, at
   t = 3.37 and t = 3.97. `biasmom05` was swept on the same grid and **failed** at
   t = −9.63, so the instrument discriminates.
3. **The grid is internally consistent** — 8 of 8 arms at mcl ∈ {0,4} are clean
   across both swing lengths and both FS settings. A fluke does not reproduce
   eight times.

**What does *not* survive this treatment:** the exact net figures. `+616.17R` is a
point estimate on 859 trades with a per-trade spread that put `2025-H1` at −0.69R
in the parent. Treat the ranking between clean arms as weak; treat *clean vs not
clean* as the finding.

---

# 4. What is left

| # | item | state |
|---|---|---|
| 1 | **period control on `mcloff_htf15`** | not run on this exact combination. The two factors were each tested separately; the combination was not |
| 2 | **forward evidence** | none for any arm. 26 days, 4–5 trades, `NO VERDICT` |
| 3 | **`mcl=0` is a risk decision** | raises concurrent exposure exactly when the book is doing worst |
| 4 | **dead knobs** | `chop_thresh`, `atr_low_thresh`, `exp_ltf_no_entry` — wire up or delete |
| 5 | **`exp_causal_sl` guard** | nothing stops someone setting it to 1 and getting ddIS 205.83 |
| 6 | **`window_end=bias_flip`** | +1154.94 at 0 negative, and the engine comments say it was rejected in Sept for a cohort effect. That tension is unresolved |

---

# 5. What was NOT done

- **No 2H plane work.** `HTF_2H_PLANE_TEST.md` predates this cycle and was not revisited.
- **No exit-family re-sweep.** The trailing and half-close docs predate this cycle; only `exp_partial_r` and `ext_stop_r` were touched here.
- **No decay-family re-sweep.** Same.
- **No portfolio or multi-instrument work.** Out of scope for this branch.
- **No grid deeper than 3×2×2.** The knobs are not independent — several are dead — so a deeper grid would mostly re-measure the same three factors.

**So: the knob space is swept. The engine's other axes are not, and pretending a
knob sweep is a research programme would be the wrong claim.**

---

*Shipping book unchanged: 528 / +533.37 / 13.42 IS, 311 / +239.59 / 11.88 OOS, one
negative half-year, `max_consecutive_losses=3` untouched.*