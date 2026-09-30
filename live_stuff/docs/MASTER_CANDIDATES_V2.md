# MASTER CANDIDATE TABLE — full metrics, computed not transcribed

**Written 2026-09-27. Supersedes the first draft of `MASTER_CANDIDATES.md`,
which was missing win rate and trade count on several rows.**

Every number in sections 0–4 is **computed from the engine** by
`live_stuff/tests/exp_full_metrics.py` → `_full_metrics.json`. Nothing typed by
hand. Candidates that cannot be re-run in that harness (CRAZE session modes, the
sizing queue, the M2 bridge study) are **not** fabricated from prose — they are
listed with a source pointer in §5, metric left blank rather than guessed.

Metric definitions: `ret%` = annualised OOS ÷ annualised IS. `top5%` = share of
net carried by the best 5% of trades. `ulcer` = RMS % drawdown. `calmar` =
avgR ÷ maxDD (per-trade, so read as a ratio, not a percentage).

---

## 0. champion_multi_sw10 — the shipped primary

| arm | n IS | n OOS | IS net | OOS net | IS WR | OOS WR | IS PF | OOS PF | IS DD | OOS DD | ret% |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline | 500 | 279 | +325.8 | +70.2 | 27.8% | 27.2% | 1.81 | 1.34 | 27.7 | 53.2 | 39.5% |
| half | 469 | 268 | +428.6 | +72.8 | 25.4% | 23.1% | 2.10 | 1.35 | 30.5 | 46.6 | 31.2% |
| half+delay1 | 466 | 271 | +429.6 | +89.8 | 26.0% | 24.0% | 2.10 | 1.42 | 27.0 | 46.3 | 38.4% |
| skip_decisive | 500 | 222 | +325.8 | +99.3 | 27.8% | 28.4% | 1.81 | 1.62 | 27.7 | 33.8 | **55.9%** |
| **STACK** | 466 | 217 | **+429.6** | **+110.5** | 26.0% | 25.3% | **2.10** | **1.65** | **27.0** | **30.6** | 47.2% |
| delay_r_1.5 | 487 | 262 | +351.4 | +81.0 | 29.2% | 27.9% | 1.87 | 1.40 | 29.1 | 50.4 | 42.3% |

## 1. utcsat_multi_sw10 — the shipped king

| arm | n IS | n OOS | IS net | OOS net | IS WR | OOS WR | IS PF | OOS PF | IS DD | OOS DD | ret% |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline | 454 | 253 | +358.9 | +60.2 | 29.1% | 28.9% | 2.01 | 1.33 | 21.2 | 29.4 | 30.8% |
| half | 431 | 242 | +401.0 | +66.3 | 26.0% | 25.2% | 2.14 | 1.36 | 26.8 | 28.9 | 30.3% |
| half+delay1 | 428 | 244 | +411.1 | +87.1 | 27.1% | 25.8% | **2.17** | 1.47 | 23.9 | 29.4 | 38.9% |
| skip_decisive | 454 | 200 | +358.9 | +76.8 | 29.1% | 28.5% | 2.01 | 1.52 | 21.2 | **24.6** | 39.3% |
| **STACK** | 428 | 194 | **+411.1** | **+94.6** | 27.1% | 26.3% | **2.17** | **1.63** | 23.9 | 29.2 | **42.2%** |
| delay_r_1.5 | 438 | 250 | +378.5 | +72.9 | 30.8% | 30.0% | 2.06 | 1.39 | 23.9 | 30.3 | 35.3% |

## 2. age10 — the single lane

| arm | n IS | n OOS | IS net | OOS net | IS WR | OOS WR | IS PF | OOS PF | IS DD | OOS DD | ret% |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **baseline** | 130 | 76 | **+435.7** | **+43.2** | **49.2%** | 39.5% | 7.57 | 1.91 | **8.7** | **8.6** | 18.2% |
| half | 118 | 71 | +418.2 | +28.0 | 39.8% | 31.0% | 7.03 | 1.57 | 9.9 | 9.4 | 12.3% |
| half+delay1 | 117 | 71 | +422.6 | +27.5 | 41.9% | 31.0% | 7.07 | 1.56 | 8.8 | 9.5 | 11.9% |
| skip_decisive | 119 | 47 | +425.3 | +16.0 | 49.6% | 34.0% | **7.93** | 1.47 | 8.7 | 10.2 | 6.9% |
| **STACK** | 109 | 46 | +422.3 | **−0.3** | 42.2% | **23.9%** | 7.53 | **0.99** | 8.8 | 12.5 | **−0.1%** |
| delay_r_1.5 | 128 | 75 | +431.3 | +41.2 | 49.2% | 38.7% | 6.88 | 1.84 | 8.7 | 8.6 | 17.5% |

## 3. Equity-curve quality

| lane | era | arm | maxDD | ulcer | sortino | %mo+ | streak | top5% | n≥3R |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| champion | IS | baseline | 27.7 | 14.6 | 328.3 | 53.3% | 16 | 144.8% | 63 |
| champion | IS | **half+delay1 / STACK** | 27.0 | 12.4 | 424.1 | 51.1% | 19 | 128.2% | 62 |
| champion | OOS | baseline | 53.2 | 213.6 | 78.5 | 41.7% | 15 | 221.7% | 30 |
| champion | OOS | half+delay1 | 46.3 | 242.2 | 95.9 | 37.5% | 15 | 223.1% | — |
| champion | OOS | skip_decisive | 33.8 | 82.7 | 111.2 | 45.5% | 15 | 143.5% | — |
| champion | OOS | **STACK** | **30.6** | **54.0** | 112.7 | 40.9% | 15 | 159.9% | — |
| utcsat | IS | baseline | 21.2 | 11.6 | 364.9 | 55.6% | 13 | 127.7% | 62 |
| utcsat | IS | **half+delay1 / STACK** | 23.9 | **9.8** | 408.4 | 51.1% | 14 | 124.0% | 59 |
| utcsat | OOS | baseline | 29.4 | 110.3 | 67.3 | 41.7% | 9 | 225.4% | 28 |
| utcsat | OOS | **STACK** | 29.2 | **35.1** | 95.2 | 40.9% | 9 | 165.7% | — |

## 4. Four things this table says that the draft did not

1. **Win rate goes DOWN as the stack improves.** champion IS WR 27.8% → 26.0%,
   OOS 27.2% → 25.3%. Same on utcsat (29.1% → 27.1%). `half+delay1` survives
   pullbacks that used to exit as losses, so fewer trades finish positive — but
   each surviving trade is worth more (PF 1.81 → 2.10). **This is a
   profit-per-trade improvement, not a hit-rate improvement**, and it is worth
   knowing before anyone calls the stack "better".
2. **Trade count falls.** champion 500 → 466 IS, 279 → 217 OOS (a 22% OOS drop).
   age10 130 → 109 IS, 76 → 46 OOS. The stack is partly a volume story.
3. **`skip_decisive` has the highest retention of anything measured: 55.9%.** It
   is a perfect IS no-op (n 500 → 500, net +325.8 → +325.8) and acts only in OOS.
   That is a virtue *and* the reason its evidence is weak — its whole case rests
   on 57 OOS trades removed from a heavily-inspected era.
4. **age10 baseline has the best curve in the repo by a wide margin** — IS DD 8.7,
   ulcer 3.9, sortino 546.7, 65.1% positive months, streak 5, 49.2% WR — and
   **every arm degrades it**, the STACK catastrophically (OOS −0.3, PF 0.99,
   WR 23.9%). `delay_r_1.5` is the only arm that leaves it essentially intact.

Also worth stating plainly: **`calmar` here is per-trade**, so champion reads
0.02 and age10 reads 0.38. The ratio is the signal, not the magnitude.

## 5. Candidates not runnable in this harness

Left out of the computed tables rather than transcribed from prose. Sources are
given so the numbers can be looked up directly.

| candidate | source | summary | status |
|---|---|---|---|
| CRAZE session modes (union / entropy / dualunion / b2_vs_flip) | `MASTER_LEADERBOARD.md` §1 | OOS DD 4.0–6.0, PF 2.67–3.60, WR 36–48.5% | fail retention bar (18–26%) |
| chopband_multi | `MASTER_LEADERBOARD.md` §1 | 47% retention, best OOS R | **rejected** — fails sw20, 2024-only |
| N3 global_soft | `WIN_STREAK_STACKING_AUTOPSY.md` | champion IS +331.7 / OOS +90.0, PF 1.74, DD 43.2 | flat-book PASS, **stack FAIL** |
| wick gate (gray) | `WICK_1H_GATE_ADOPTION_RECORD.md` | +28.1/+25.7/+19.8/+23.8R, cascade 0.00, 6/6 seq-identical | forward 5/50 |
| M2 / sMZX / uMZX / ramp_mag / count_linear | `CAPITAL_STAGE_PLAN.md` §2 | sizing, dNet up to +346.5/+130.4 | **all blocked at bridge** |
| Z flags A / B / C | `REGIME_STRUCTURE_AUTOPSY.md` | 1.5× on one regime flag | sizing-only, correlated family |
| king_single / fullstack_single / wage12_single | `STRATEGY_SCORECARD.md` §2 | single lane | all fail retention (9–14%) |

**N3 and STACK are mutually exclusive** — `stack+global_soft_n3` is −29.7R on
champion IS and negative on all three stack lanes (CHECKLIST 24.84).

## 6. The binding constraint

**Forward n = 5/50**, pre-registered (`FORWARD_TEST_PLAN.md`, CHECKLIST 24.70).
First read: R1 PARITY PASS / NO VERDICT (n=5). Study 2 (deflated statistics)
splits by era: **IS passes, OOS fails.**

No backtest clears it. It accrues passively.

## 7. One open, already-diagnosed task

`CAPITAL_STAGE_PLAN.md` a11: the gray cooldown-suppression bug
(`if cooldown_bars > 0 and r_multiple < 0 and not _isgray`) is **still present**
in `exp_sl_width_gate.py` and `exp_sl_fine_cascade.py`. The doc says their
gray-mode conclusions are affected and must be **re-run before quoting** — that
covers the SL-width ladder (a9) and the 3%+ fine-SL gate (a10).

| age10 | IS | **baseline** | **8.7** | 3.9 | 546.7 | 65.1% | **5** | 55.2% | — |
| age10 | IS | half+delay1 | 8.8 | **2.1** | 491.7 | 62.8% | 7 | 49.8% | — |
| age10 | OOS | **baseline** | **8.6** | 31.6 | 51.4 | 70.8% | 8 | 64.7% | — |
| age10 | OOS | **STACK** | 12.5 | 59.3 | 17.5 | 31.8% | 7 | — | — |

---

## 8. CANDIDATE — tight-stop half of the book — **DOCUMENTED, NOT ADOPTED**

Added 2026-09-29 from `RISK_CONCURRENCY.md` (P2). Recorded here because the
concentration is real and worth keeping visible. **It is not a validated
candidate and the numbers below must not be read as one.**

| lane | era | arm | n | net | WR | PF | dNet vs book |
|---|---|---|---:|---:|---:|---:|---:|
| champion | IS | **tight half** | 251 | **+300.0** | 27.1% | **3.17** | — |
| champion | IS | wide half | 249 | +25.8 | 32.9% | 1.39 | — |
| champion | OOS | **tight half** | 140 | **+51.6** | 20.7% | 1.75 | — |
| champion | OOS | wide half | 139 | +18.6 | 35.3% | 1.38 | — |
| utcsat | IS | **tight half** | 227 | **+300.7** | 27.3% | **3.35** | — |
| utcsat | IS | wide half | 227 | +58.2 | 34.4% | 1.67 | — |
| utcsat | OOS | **tight half** | 127 | **+43.7** | 22.0% | 1.72 | — |
| utcsat | OOS | wide half | 126 | +16.5 | 37.3% | 1.38 | — |

Stop distance is `|entry − sl| / entry`, known at entry, so the *feature* is
causal. The ordering is consistent in all four cells: tight-stop trades run
PF 1.7–3.4 against 1.4–1.7.

### Three reasons this is not a strategy yet

**1. The net is not additive — it is a subset.** +300.0R out of +325.8R is
**92% of the book from half the trades**, not +300R on top. The correct
framing is *concentration*, which is a fragility finding, not an edge
finding.

**2. Trading only the tight half is 4/4 negative.** dNet is
−25.8R / −18.6R / −58.2R / −16.5R. The wide trades are worse **and still
profitable**, so the selection spends more than it earns.

**3. The split is post-hoc and untested against the null.** "Half" was chosen
after seeing the distribution. Per the register's own standard, a candidate
needs a pre-registered null test, and **M = 193.4R** is the bar the
`|dNet|` has to clear. The best arm of the whole sweep reached **+13.3R —
about 1/15 of M.**

### What would promote it

A pre-registered split on a threshold fixed in advance, carried through the
block bootstrap, with `|dNet| > M` in **both** eras. Not a retune of "half."


