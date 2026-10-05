# Experiments — v19+ Branch

**Branch:** `experiments/v19-plus`
**Base:** v18 (C14+C15 causal) — 351t / +238.0R gross / +148.0R net / WR 27.6%
**Data:** BTCUSDT Bybit Perp, 2023-01 to 2026-09
**Params:** sl_buf=0.01, chop=58.0, cd=10, halt=3, ext_stop=1.5
**Costs:** Bybit taker 0.055%/side, entry slip 0.005%, exit slip 0.01%, funding 0.01%/8h
**Reconciled:** Both lanes confirmed identical anchor (351t/+238.0R gross)
> **D3 anchor basis audit (2026-09-20):** see `signal/ANCHOR_BASIS_AUDIT.md` — the two
> valid anchor bases (coarse+61.8 = 340t/+225.3 identity; fine+58 = 351t/+238.0
> production), the trail ratchet FIX (ADOPTED: condition + ordering — champion
> multi sw10 re-pinned +366.1 -> **+325.8R NET / DD 17.8**), truncation causality
> probes (CLEAN post-fix), robustness probes (gapless 1m data, cost stress,
> concurrency-cap cost), and the bookkeeping fixes.
>
> **Cooldown-family experiments (2026-09-20, see audit doc §7):** HTF window
> skip after losses = DEAD in all variants. The winner is the STRUCTURAL
> swing-pause: after a loss, no re-entry until a 15m swing formed AFTER that
> loss confirms. On singles it REPLACES the bar-cooldown and is the new best
> single config: `swingpause_single_sw10` = **357t / +174.8R NET / DD 23.4 /
> NET-DD 7.5** (baseline was +137.7 / 29.2 / 4.7). Run via
> `python backtest/tests/run_experiment.py --group best` (both leaders) or
> `--group cooldown` (the whole family). The multi king is unchanged.

> **Run any experiment:** `python backtest/tests/run_experiment.py <key>`
> **List all:** `python backtest/tests/run_experiment.py --list`
> **All results:** `python backtest/tests/run_experiment.py --all`
> **Configs:** `backtest/tests/experiment_registry.py`

> **Full results doc:** [signal/EXPERIMENT_RESULTS.md](signal/EXPERIMENT_RESULTS.md)

---

## POST-FIX Decision Menu — FULL METRICS (2026-09-19)

> **Last updated: 2026-09-19** — all metrics, fine fills, corrected costs (0.055% fee, 0.005/0.010 slip, 0.01%/8h funding).

| # | Config | Tr | Gross | NET | WR | avgW | avgL | PF | DD | maxLs | avgR | H1 | H2 | 2023 | 2024 | 2025 | 2026 | Cap |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **OPT-cd10 + w24 + ext1.5** | 326 | — | **+337.7** | — | — | — | — | 19.2 | — | — | — | — | — | — | — | — | - |
| 2 | **their-OPTIMAL+cap3** | 503 | +456.7 | **+326.8** | 28.0% | +5.61 | -0.92 | 2.36 | 21.8 | 18 | +0.91 | +228.9 | +227.8 | 93.9 | 135.0 | 87.8 | 140.0 | 3 |
| 3 | their-OPTIMAL (no cap) | 515 | +456.2 | +322.5 | 28.0% | +5.55 | -0.92 | 2.33 | 23.3 | 19 | +0.89 | +229.4 | +226.7 | 94.4 | 135.0 | 84.4 | 142.3 | - |
| 4 | **S9 mltf+mb10+chop55** | 460 | +432.1 | **+312.2** | 28.7% | +5.55 | -0.91 | 2.44 | 38.2 | 17 | +0.94 | +249.6 | +182.5 | 81.6 | 168.0 | 71.3 | 111.2 | - |
| 5 | mltf+persist5 cd10 | 409 | +389.1 | +287.5 | 32.0% | +4.93 | -0.92 | 2.52 | 33.4 | 11 | +0.95 | +202.8 | +186.3 | 92.6 | 110.1 | 90.8 | 95.6 | - |
| 6 | OPTIMAL+halt6 (S19) | 574 | +423.1 | +273.7 | 26.8% | — | — | — | 31.5 | — | — | — | — | — | — | — | — | - |
| 7 | lb30+mltf+chop55+mb10+cd10 | 427 | +373.4 | +264.2 | 29.5% | — | — | — | 27.5 | — | — | — | — | — | — | — | — | - |
| 8 | S7 mltf+pers5+cd0 | 477 | +357.6 | +236.1 | 27.0% | — | — | — | 26.4 | — | — | — | — | — | — | — | — | - |
| 9 | **anchor lb=30 + ext2.5 (single-position best)** | 377 | +323.3 | **+231.1** | 31.0% | — | — | — | 24.6 | — | — | +169.0 | +154.3 | 22.9 | 146.1 | 69.4 | 84.9 | - |
| 10 | mltf alone (mb20+chop58) | 421 | +306.5 | +197.6 | 29.5% | — | — | — | 23.4 | — | — | — | — | — | — | — | — | - |
| 11 | **anchor lb=30** | 349 | +287.1 | **+196.3** | 29.8% | +4.97 | -0.94 | 2.25 | 23.6 | 11 | +0.82 | +143.9 | +143.2 | 22.7 | 121.2 | 52.2 | 91.0 | - |
| 12 | A4 lb30+pers2+chop55+mb10 | 359 | +297.3 | +203.3 | 26.2% | +5.74 | -0.92 | 2.23 | 24.8 | 17 | +0.83 | +131.3 | +166.0 | 65.2 | 66.1 | 50.3 | 115.6 | - |
| 13 | anchor lb=14 (production) | 351 | +238.0 | +148.0 | 27.6% | +4.86 | -0.92 | 2.02 | 23.4 | 27 | +0.68 | +119.9 | +118.1 | 38.8 | 81.1 | 37.6 | 80.5 | - |
| 14 | **(52,60,tr65) aggressive** | 239 | +163.0 | **+116.1** | 34.3% | +3.61 | -0.84 | 2.23 | 13.9 | 14 | +0.68 | +100.1 | +62.9 | 38.0 | 62.2 | 29.7 | 33.2 | - |
| 15 | B3-OPT lb50 halt3 | 214 | +157.3 | +115.4 | 35.0% | +3.69 | -0.86 | 2.32 | 10.2 | 10 | +0.74 | +80.6 | +76.7 | 35.7 | 44.9 | 43.7 | 33.0 | - |
| 16 | B3-OPT lb50 halt6 | 226 | +157.0 | +112.5 | 33.6% | +3.77 | -0.86 | 2.21 | 12.2 | 10 | +0.69 | +81.7 | +75.3 | 33.7 | 48.0 | 35.8 | 39.5 | - |
| 17 | (55,50,tr50) conservative | 226 | +157.0 | +112.5 | 33.6% | +3.77 | -0.86 | 2.21 | 12.2 | 10 | +0.69 | +81.7 | +75.3 | 33.7 | 48.0 | 35.8 | 39.5 | - |
| 18 | B3-OPT lb14 halt3 | 238 | +125.2 | +80.0 | 35.0% | — | — | — | 12.8 | — | — | — | — | — | — | — | — | - |
| 19 | B3-OPT lb14 halt6 | 249 | +124.3 | +76.0 | 33.6% | — | — | — | 12.8 | — | — | — | — | — | — | — | — | - |
| 20 | S15 B3+mltf+pers2+cd0 | 245 | +114.2 | +66.8 | 29.8% | +3.58 | -0.86 | 1.78 | 14.6 | 12 | +0.47 | +73.8 | +40.4 | 28.5 | 45.4 | 29.7 | 10.7 | - |
| 21 | **A4 + w24 + ext1.5 (single risk-adjusted best)** | 261 | +257.0g | **+223.1** | 33.0% | — | — | — | 19.8 | — | — | — | — | — | — | — | — | - |
| 22 | **lb14 + w24 + ext1.5 (sleep-well)** | 272 | — | **+193.7** | — | — | — | — | 15.7 | — | — | — | — | — | — | — | — | - |

> Row 1 is multi-position (mltf, needs concurrency cap). Rows 21-22 are single-position wage-gated variants from exp40c/42. Full wage × ext_stop matrix in [method/EXP40C_EXP41_WAGE_EXT.md](method/EXP40C_EXP41_WAGE_EXT.md).

### Key Post-Fix Findings

1. **FINAL ANSWER: OPT-cd10 + w24 + ext1.5 = +337.7 / DD 19.2** — multi-position, needs concurrency cap; see row 1
2. **Multi-LTF configs are the real leaders** — their-OPTIMAL (+322.5 uncapped) and S9 (+312.2) never used B3, unaffected by the fix
3. **B3 doesn't help anything** — best B3 (aggressive +116.1) still loses to anchor lb=30 (+196.3) by 80R
4. **S15 (B3+multi-LTF) collapsed** — from +300.4 to +66.8. B3 + multi-LTF is dead
5. **lb30+mltf DEAD** — lb30 kills multi-LTF by 58-122R. lb30 is single-position only
6. **cap3 is pure improvement** — +4.3R over no cap, -1.5R DD, removes breakeven/worse concurrent positions
7. **chop veto REJECTED** — helps anchor (+9.8R) but hurts OPTIMAL (-77.5R)
8. **atrpct veto DEAD** — zero trades filtered on lb14 base
9. **Edge is real but modest** — ~0.5-0.6R/trade across all configs
10. **wage gate is base-dependent** — helps A4 (+19.8R at w24) and OPT-cd10 (+78.3R at w24), hurts lb30 (−11.3R at w24). Not a universal filter
11. **ext_stop 1.5→2.5 ADOPTED (N6)** — new single-best lb30+ext2.5 = +231.1 / DD 24.6 (+34.8 over stock). w24 + wide ext is anti-synergistic (buying the top)
12. **OPT-cd10 + w24 + ext1.5 is the overall champion** — +337.7 / DD 19.2, zero losing WF segments. Multi-position, needs concurrency cap. See row 1

### Multi-LTF Caveats

- **Concurrency**: their-OPTIMAL holds up to 4 concurrent positions without cap; cap3 limits to 3
- **cd=0**: their-OPTIMAL has no loss cooldown — needs live-latency validation
- **Not single-position**: Cannot run with the same simplicity as anchor/B3-OPT
- **Cap3 recommended**: +4.3R over no cap, -1.5R DD. Pure improvement.

---

## Experiment Summary (POST-FIX numbers — pre-fix superseded)

> **Theory (what it is, how we run it):** HTF = 1h trade-windows (each closed 1h flip/B2/decisive leg = one window: "bias is long/short from here until here"). Regime = 1h chop picks WHICH window set (B2 vs FLIP) each 15m bar. LTF = 15m decisive signals become trades only if inside the window + same dir + ext/wage + cd/halt pass; exits are always the stock 15m swing trail. `wage` = window age at entry (entry_ts − window_start; skip if <24h in N5). `ext` = how far the HTF leg already ran ((LTF close − HTF entry)×dir/risk; skip if >X in N6). N5/N6 touch ENTRY gates only — exits never change. How we test: loss autopsy → hypothesis → coarse sweep (fast 15m exits) → fine survivors (1m fills + fees/slip/funding). Full primer + worked numbers: signal/EXPERIMENT_RESULTS.md §17 "Theory primer".

| # | Name | Trades | Gross R | NET R | WR | Delta | MaxDD | Verdict |
|---|------|--------|---------|-------|----|-------|-------|---------|
| 0 | **BASELINE** | **351** | **+238.0** | **+148.0** | **27.6%** | **-** | **23.4R** | - |
| 2 | Regime Persistence=5 | 339 | +261.3 | +172.4 | 28.9% | +24.4R | 31.2R | Good |
| 8 | min_bars 1h=10 + chop=55 | 377 | +273.8 | +179.6 | 27.6% | +31.6R | 34.2R | Good |
| 14 | B3 k8 confirmation | 206 | +322.2 | ~+80 | 40.8% | ~-68R | 15.5R | B3 bug inflated pre-fix |
| 24 | **their-OPTIMAL (multi-LTF)** | 515 | +456.2 | **+322.5** | 28.0% | +174.5R | 23.3R | #2 NET (concurrency caveat) |
| 25 | **OPT-cd10 + w24 + ext1.5** | 326 | — | **+337.7** | — | — | 19.2R | **#1 OVERALL CHAMPION** (multi, needs cap) |
| 24c | **their-OPTIMAL + cap3** | 503 | +456.7 | **+326.8** | 28.0% | +178.8R | 21.8R | **#2 multi (needs cap)** |
| 24b | S9 (mltf+mb10+chop55) | 460 | +432.1 | **+312.2** | 28.7% | +164.2R | 38.2R | #2 NET (concurrency caveat) |
| 31 | B3-OPT lb50 halt3 | 214 | +157.3 | **+115.4** | 35.0% | -32.6R | 10.2R | Best single B3 |
| 32 | (52,60,trail65) aggressive | 239 | +163.0 | **+116.1** | 34.3% | -32.0R | 13.9R | Best B3 variant |
| N5 | wage>=24h gate (NON-AUTHORITATIVE — deleted harness, see [EXP40C doc](method/EXP40C_EXP41_WAGE_EXT.md)) | ~~275/281/266~~ | — | ~~+224.5/+201.9/+228.6~~ → **+185.0 lb30 / +223.1 A4** | — | — | 22.3/15.8/20.4 | lb30: w24 HURTS by −11.3R; A4: helps +19.8R. Base-dependent. |
| N6 | **lb30 + ext2.5 (ADOPTED single-best)** | 377 | +323.3 | **+231.1** | 31.0% | +83.1R | 24.6R | ext1.5→2.5 admits 28 late entries |
| N6b | ext2.5 on A4/OPTIMAL (Exp40b) | 390/585/512 | — | +141.3/+290.0/+291.4 | — | -62.0/-32.5/+32.0 | 28.4/25.0/27.1 | REJECT on A4+OPT-cd0; ADOPT on OPT-cd10 only |

> ⚠️ Rows marked "B3 bug inflated" had pre-fix NET values 3-4x higher. See signal/EXPERIMENT_RESULTS.md §17.

---

## Decision Menu (Fine NET, Corrected Costs) — SUPERSEDED

> **⚠️ This table is superseded by the POST-FIX Decision Menu above.**
> It only shows single-position configs and pre-fix OPTIMAL estimate.

| # | Config | NET | DD | NET/DD | Trades | Position | WF |
|---|---|---|---|---|---|---|---|
| 1 | v18 anchor lb=14 | +148.0 | 23.4 | 6.3 | 351 | single | yes |
| 2 | anchor lb=30 | +196.3 | 23.6 | 8.3 | 349 | single | yes |
| 3 | B3-OPT lb14 halt3 cd10 | +80.0 | 12.8 | 6.3 | 238 | single | yes |
| 4 | **B3-OPT lb50 halt3 cd10** | +115.4 | **10.2** | **11.3** | 214 | single | yes |
| 5 | B3-OPT lb14 halt6 cd10 | +76.0 | 12.8 | 5.9 | 249 | single | yes |
| 6 | B3-OPT lb50 halt6 cd10 | +112.5 | 12.2 | 9.2 | 226 | single | yes |
| 7 | **(52,60,tr65) aggressive** | **+146.1** | 13.9 | **10.5** | 229 | single | **yes** |
| 8 | OPTIMAL (multi-LTF) | ~+250 | 23.3 | ~10.7 | 515 | multi | yes |

---

## Walk-Forward: B3-OPT lb50 (post-fix, expanding window, fine)

| Split | Train NET | Test NET |
|---|---|---|
| 50/50 | +56.9 | **+66.0** |
| 66/34 | +62.7 | **+60.2** |
| 75/25 | +84.1 | **+38.8** |

All test segments positive. lb50 beats lb14 at every split by +17R.

---

## Aggressive vs Conservative (post-fix)

| Config | NET | DD | H2 | 2025 |
|---|---|---|---|---|
| (55,50,trail50) conservative | +112.5 | 12.2 | +75.3 | +35.8 |
| **(52,60,tr65) aggressive** | **+146.1** | 13.9 | +65.5 | +31.0 |

Aggressive is +33.6R better but higher DD (+1.7R). Both survive post-fix.

---

## Key Interactions Found

1. **B3 doesn't help anything** — the B3 entry price bug was inflating all B3 results. Post-fix, best B3 (aggressive +146.1) still loses to anchor lb=30 (+196.3) by 50R.
2. **Multi-LTF is the real edge** — their-OPTIMAL (+322.5) and S9 (+312.2) never used B3, unaffected by the fix. The edge is multi-LTF + OPTIMAL params (chop55, mb10, persist2).
3. **B3 + multi-LTF = dead** — S15 collapsed from +300.4 to +66.8. B3's delayed entries destroy multi-LTF's value.
4. **lb30 + multi-LTF = dead** — lb30 kills multi-LTF by 58-122R. lb30 is single-position only.
5. **cap3 = pure improvement** — removes 2+ concurrent positions (breakeven/worse), +4.3R, -1.5R DD.
6. **persist2 = insurance premium** — at cd10 costs -53R for -5.5 DD; at cd0 wins outright (+322.5 / DD 23.3).
7. **chop veto not global** — helps anchor (+9.8R) but hurts OPTIMAL (-77.5R). Can't adopt as universal filter.
8. **"Slowness is a feature"** — 4 independent refutations: ATR-chandelier, end_px, conviction-mark, opposite-mark accelerator.
9. **wage × ext anti-synergy** — w24 wins only while ext=1.5 strangles headroom; once ext opens to 2.5, w0 beats w24 by 52R. Two knobs, pick one: ext wins. BUT ext2.5 is config-specific (N6b): it LOSES on A4 (−62R) and OPT-cd0 (−32.5R); only OPT-cd10 gains (+32R, DD −5.6) because cd10 already thins re-entries. Validated rebuild confirmed w24×ext matrix coarse 4/4 + fine 5/5. See [method/EXP40C_EXP41_WAGE_EXT.md](method/EXP40C_EXP41_WAGE_EXT.md).

---

## Confirmed NOT Worth Pursuing

- Dual-active windows, Adaptive halt, TOD filter, Partial exit, Pullback entry
- Trail accelerator (Exp 27) — all arms refuted
- Skip-first-swing (Exp 19) — mechanism confirmed but remedy fails
- Close-confirmed SL (Exp 20) — wick gain eaten by worse fills
- 3-Mark Judgment (Exp 18) — all arms fail, price-confirmation > structure-confirmation
- **lb30+mltf combo** — lb30 kills multi-LTF by 58-122R
- **chop<50 veto** — helps anchor (+9.8R) but hurts OPTIMAL (-77.5R)
- **atrpct 60-80 veto** — zero trades filtered, no effect
- **wage>=24h gate (N5)** — NON-AUTHORITATIVE (deleted harness). Validated rebuild shows w24 HURTS on lb30 (−11.3R), helps on A4 (+19.8R). Base-dependent, not universal. Superseded by ext2.5 on lb30. See [method/EXP40C_EXP41_WAGE_EXT.md](method/EXP40C_EXP41_WAGE_EXT.md).
- **ext_stop=1.5 default (single)** — raised to 2.5 on lb30 (+34.8R); 3.0+ adds nothing (ceiling); NOT universal — stays 1.5 on A4 + OPT-cd0, adopted only on OPT-cd10 (N6b)

> **Full details:** [signal/EXPERIMENT_RESULTS.md](signal/EXPERIMENT_RESULTS.md)
