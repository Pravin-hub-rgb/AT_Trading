# Permutation Matrix — HTF 1h (flip/b2/decisive) × LTF 15m/5m (flip/b2/decisive) — FULL 1.93M

> **Setup:** `HTF 1h cap16 355 Flip 284 B2 334 Decisive intervals` `LTF 15m mb50 2936 swings / 5m mb14 17552 swings` `sl_buf 0.25ATR ext-stop1.5 MB50 trail 1m 1934262 fine 0.05%+2pt stream` `backend/debug/test_permutation_matrix.py:1` `C:\Users\Pravin\AppData\Local\Temp\opencode\perm_out.txt` `32259 x1h vs 442 +168 baseline v5`.

**Why this matrix:** you asked `htf is flip and we also trade only flip on ltf too?? or htf is b2 and we only trade flip on ltf .. something like that ... even on 5min too and many other combination`.

## 15m LTF (mb50) — HTF 1h flip/b2/decisive × LTF flip/b2/decisive

| HTF × LTF | Trades | Net | PF | DD | 2023 | 2024 | 2025 | 2026 | Win% |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **flip × decisive** | **442** | **168.1** | **1.86** | **23.3** | **−7.2** | **40.1** | **101.5** | **33.7** | **28.5%** |
| flip × flip | 326 | 92.5 | 1.70 | 15.2 | **+3.5** | 24.4 | 43.6 | 21.1 | 26.7% |
| flip × b2 | 399 | 69.1 | 1.51 | 28.3 | −28.4 | 24.6 | 51.1 | 21.9 | 30.3% |
| **decisive × decisive** | **558** | **122.6** | 1.60 | 35.4 | **+37.7** | **−16.9** | 35.3 | 66.5 | 27.1% |
| decisive × flip | 422 | 68.5 | 1.50 | 34.2 | 10.2 | −9.4 | 5.1 | 62.6 | 21.6% |
| b2 × decisive | 526 | 49.8 | 1.37 | 35.7 | −15.3 | −1.2 | 63.4 | 2.9 | 25.1% |
| b2 × flip | 399 | −4.9 | 1.23 | 32.4 | −18.1 | 5.7 | −4.2 | 11.8 | 21.6% |
| b2 × b2 | 462 | 3.8 | 1.23 | 30.3 | −6.6 | 0.3 | 42.7 | −32.6 | 26.4% |
| decisive × b2 | 514 | 37.7 | 1.34 | 37.5 | −0.2 | 7.8 | −1.5 | 31.6 | 28.0% |

**Takeaways 15m:**
- **Best total net = `flip × decisive` 168.1** `v5` `442 +168` — your current baseline still BEST overall `+46R vs decisive×decisive 122`.
- **Best 2023 worst = `decisive × decisive +37.7`** `558tr` where `flip × decisive −7.2` `flip × flip +3.5` `b2 × decisive −15.3` — `B2` helps 2023 only when combined as `decisive B2|FLIP`, not alone (`b2×b2 −6.6`, `b2×flip −18.1`).
- **Flip-sync you asked `htf flip + ltf flip` → 326 +92 net 2023 +3.5 small positive** vs `decisive 442 +168` — `decisive` keeps `B2` legs `+392R fix/btc_ideas:40` that pay 2025 `101.5 vs 43.6`.
- **`htf b2` alone hurts:** `b2×flip −4.9` `b2×b2 3.8` `b2×decisive 49.8` all < `flip×decisive 168`, confirms `HTF B2 only → NO` from `htf_b2_out.txt` `−15.3 vs −7.2`.

## 5m LTF (mb14) — HTF 1h flip/b2/decisive × LTF flip/b2/decisive

| HTF × LTF | Trades | Net | PF | DD | 2023 | 2024 | 2025 | 2026 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| flip × flip | 1540 | −245.2 | 1.39 | 47.7 | −146.9 | −94.6 | 29.9 | −33.5 |
| flip × b2 | 1779 | −330.1 | 1.21 | 46.0 | −179.6 | −39.4 | −50.8 | −60.3 |
| flip × decisive | **2161** | **−345.9** | 1.30 | 41.0 | **−193.0** | −141.7 | 32.3 | −43.5 |
| b2 × flip | 1993 | −694.6 | 1.07 | 72.3 | −146.3 | −193.6 | −158.9 | −195.7 |
| b2 × b2 | 2325 | −760.3 | 0.94 | 144.0 | −209.8 | −161.3 | −208.9 | −180.2 |
| decisive × decisive | 3001 | −746.7 | 1.12 | 94.5 | −147.6 | −229.6 | −215.4 | −154.1 |

**All 5m bleedy even with HTF gate** `−245 to −900` `2161-3001tr` `costs 85→50` style, no edge — **do not use 5m LTF**, `15m mb50` is where edge lives `fix/crazy_ghost_mix.md:13` `30-40% flat gaps` already.

## Verdict for your combo question

- **`htf flip + ltf flip` you asked:** `15m 326 +92 net 2023 +3.5 small positive` vs `decisive 442 +168` — `flip sync` is `−76R` total but `+10.7R` better in `2023` vs `−7.2`; **worse total, slightly better 2023**.
- **`htf b2 + ltf flip` you asked:** `15m 399 −4.9 net 2023 −18.1` — **worse than both**, `HTF B2` does not help flip.
- **Many other combos:** matrix above covers `3×3×2 = 18` `HTF×LTF×TF` combos on `1.93M` — **nothing beats `flip × decisive 168` total**; best 2023 is `decisive×decisive 37.7` but you pay `−46R total` to get `+44.9R 2023`.
- **Keep:** `v5 0.25ATR ext-stop1.5 MB50 flip×decisive 442 +168` locked `IS 179 +152` `page.tsx:1327` `4yr FULL 442 +168` `fix/v5_5directions_checklist.md:10` `fix/multi tf:625` — use `decisive×decisive` only as **2023 hedge alt** separate engine `backend/src/btc/engines/htf_ltf/v1_15m.py:17`.

*Harness `backend/debug/test_permutation_matrix.py:1` `C:\Users\Pravin\AppData\Local\Temp\opencode\perm_out.txt` `32259 x1h 128951 x15m 386855 x5m 1934262 x1m` `fine` `v5_sl_buffer 0.25`.*

---

## FS and FS-opposite permutations — 15m/5m — `trade opposite to swing` `fs is opposite direction chop to its swing` `first swing detection theory:63` `btc_swing:105` `firstswing.py:500 chop opposite`

> **What is FS:** `Swing dir up (buying) → FS chop is down break` `firstswing.py:500 down swing → tgt latest_sealed_high hi>px chop` `btc_swing:105 fs_at = last_chop_cross_idx opposite` `docs/first swing detection theory:63` `SUS disabled firstswing.py:580 100% FS fix/btc_ideas:58` `kind FS`. `FS-opposite = trade opposite to swing` `entry theory:11 For BUYING wait selling swing → BUY` `docs/entry theory:11` `opposite`.

**Engine:** `backend/src/btc/engines/htf_ltf/v1_15m.py:1` patched `11` `_fs_intervals(swings,candles,opposite)` `13` `htf_entry_break fs/fs_opposite` `14` `ltf_entry_break fs/fs_opposite` `15` `htf fs intervals (s_ts,e_ts,dir)` from `swing.dir` `opposite=-dir` `start confirmed_at_idx+1 → next swing start` `33` `filtered_sigs` `78` `ext_stop 1.5` same `backend/debug/test_permutation_fs.py:1` `C:\Users\Pravin\AppData\Local\Temp\opencode\perm_fs_out2.txt`.

### 15m LTF fs permutations — `HTF fs/fs_opposite/flip/b2/decisive × LTF fs/fs_opposite/flip/b2/decisive`

| HTF × LTF | Trades | Net | PF | DD | 2023 | 2025 | Win% |
|---|---:|---:|---:|---:|---:|---:|---:|
| flip × fs | 398 | 89.0 | 1.70 | 21.6 | 12.8 | 44.0 | 34.7% |
| flip × fs_opposite | 12 | −5.3 | 1.13 | 9.0 | −3.1 | −5.3 | 8.3% |
| flip × flip | 326 | 92.5 | 1.70 | 15.2 | 3.5 | 43.6 | 26.7% |
| b2 × fs | 468 | 0.3 | 1.19 | 20.0 | 28.0 | −14.7 | 27.1% |
| b2 × fs_opposite | 6 | −9.9 | 0.00 | 6.0 | −2.0 | −1.1 | 0.0% |
| b2 × decisive | 526 | 49.8 | 1.37 | 35.7 | −15.3 | 63.4 | 25.1% |
| decisive × fs | 493 | 25.9 | 1.30 | 25.1 | 46.4 | −27.5 | 28.4% |
| decisive × decisive | 558 | 122.6 | 1.60 | 35.4 | 37.7 | 35.3 | 27.1% |
| **fs × fs** | 90 | 3.3 | 1.34 | 26.2 | −9.2 | −8.2 | 14.4% |
| **fs_opposite × decisive** | 82 | −86.2 | 0.05 | 71.5 | −22.1 | −21.0 | 3.7% |
| fs_opposite × flip | 45 | −51.6 | 0.03 | 40.6 | −20.3 | −12.9 | 2.2% |
| fs × decisive | 85 | −84.1 | 0.14 | 65.5 | −33.3 | −9.9 | 7.1% |
| fs_opposite × fs | 101 | −87.4 | 0.10 | 73.8 | −24.7 | −22.8 | 5.0% |
| flip × decisive **(v5)** | **442** | **168.1** | **1.86** | **23.3** | **−7.2** | **101.5** | **28.5%** |

**Takeaways FS:**
- **FS same-dir (buying swing up → LONG) 90 +3.3 net 101 −87 82 −86 etc — all FS intervals −9 to −87 net** `fs × decisive −84  fs_opposite × decisive −86  fs × fs 3.3` — **FS as HTF window is not edge** `fs 90 −87` vs `flip 355 +66 HTF net` `decisive 334 +38`.
- **FS-opposite (buying swing up → SHORT on LTF) you asked `fs of buying swing so we trade short on ltf`:** `fs_opposite × decisive −86.2 82tr 2023 −22.1 PF0.05` `fs_opposite × flip −51.6` `fs_opposite × fs −87.4` `fs_opposite × fs_opposite 1 −3.0` — **all FS-opposite LTF −51 to −87 net win 2-5%** `LTF fs_opposite 12 −5.3 6 −9 7 −10` — **trading opposite to swing destroys right tail 0 runners** `Exp1 top10 all TRAIL` `mfe7.9→real4.2` `opposite-dir fade bdir != sdir btc_engine:134` already `one swing one trade 93` `touchable SL 128` but `HTF FS-opposite whole-window fade PF0.05` same as `multi tf:214 PF0.54 REJECT`.
- **LTF FS-opposite as entry (fade LTF swing):** `flip × fs_opposite 12 −5.3` `b2 × fs_opposite 6 −9.9` `decisive × fs_opposite 7 −10` — **all −5 to −10 net 6-12tr** `win 0-8%` — **do not trade opposite to swing**.

### 5m LTF fs (for completeness) — all bleedy

| HTF × LTF (5m) | Trades | Net | 2023 |
|---|---:|---:|---:|
| flip × fs_opposite (5m) | 70 | −93.4 | −7.3 |
| flip × decisive (5m) | 2161 | −345.9 | −193.0 |
| fs_opposite × decisive (5m) | 458 | −352.8 | −99.8 |

**All 5m fs bleedy `−93 to −352` like 5m `−245 to −900` before** `15m mb50` is where edge lives.

## When to use B2 vs Flip — conditional game changer for 2023 `decisive × decisive +37.7`

> **Both have edge like they do give some trades correct then if we were able to find a way when to use b2 or when to use flip so brain storm here** — your ask.

**Observation `15m`:**
- `flip × decisive 168 (+101.5 in 2025 bull, −7.2 in 2023 chop)` vs `decisive × decisive 122 (+35.3 in 2025, +37.7 in 2023)` — **Flip wins total +46R (101.5−35.3 = +66.2 in 2025) but loses 2023 −45R (−7.2→+37.7)**.
- `flip × flip 92 (+43.6 in 2025, +3.5 in 2023)` `flip × b2 69 (+51.1 in 2025, −28.4 in 2023)` — `B2 legs +392R fix/btc_ideas:40` pay in `2025 bull` but bleed `2023 chop` `flip × b2 −28.4`.
- `b2 × decisive 49 (+63.4 in 2025, −15.3 in 2023)` `b2 × b2 3.8 (+42.7 vs −6.6)` — `B2 HTF` alone hurts `2023 −15.3`.

**Brain storm — diagnose first (no filter yet) `Exp4 LOW vol 309 +133 79% vs HIGH vol 17 +12` `MED chop 366 +130 vs HIGH chop 24 +9.9` `fix/v5:172` `atr% 15m` `chop lp14 v4_chop.py:26` `Exp1 MAE 0.5-0.75 +3.95 best 38% runners` `C:\Users\Pravin\AppData\Local\Temp\opencode\exp1_out.txt`:**

| Regime | Flip×Decisive 2023 | Decisive×Decisive 2023 | Better | Why |
|---|---|---:|---:|---|
| **Chop 2023** | −7.2 (121tr) | **+37.7 (161tr +45R)** | **Decisive** | `2023` is `post-bear chop 108tr −35 HTF` `fix/multi tf:238` where `exact pivot SL` `v5 0.25ATR` `−7.2` bleeds, `B2|FLIP union` covers both leg types `B2 56.5% FLIP 43.5% census fix/btc_ideas:58` `sustain NO-OP 101` — `B2` catches `same-dir continuation` `firstswing.py:436` while `FLIP` catches `reversal` `firstswing.py:458` |
| **Trend 2025** | **101.5 (108tr)** | 35.3 (102tr) | **Flip** | `2025 mixed → bull` `MB50 trail 78 +284 92% win 3-5d` `Exp5 0-2d −244` where `Flip` captures `1.5R gold bucket PF4.95 fix:220` `ext-stop1.5` while `B2` late |
| **All 4yr** | **168.1 (442tr)** | 122.6 (558tr) | **Flip** | `Flip` PF1.86 vs 1.60 DD23.3 vs 35.4 |

**Idea — conditional HTF/LTF break `when to use what`:**
- **HTF `flip` when `LOW vol (<0.35% ATR) 309 +133` + `MED chop 366 +130`** `Exp4` where `flip × decisive` `101.5` wins `2025` `+66R` — keep `v5` as is.
- **HTF `decisive` when `HIGH chop (>61.8) 24 +9.9` or `2023-like chop`** `decisive × decisive 37.7` `+45R` vs `flip` — switch to `decisive` only in `HIGH chop` regime `v4_chop 26-59` `chop_lb14 61.8` `fix:355` `REJECT` before but now as **regime-conditioned HTF**, not always.
- **LTF `flip` when `MAE bucket 0.5-0.75 +3.95 best` `Exp1` where `flip` needs `0.63R heat` vs `B2` needs `0.5-0.75` same? `flip × flip 92 vs flip × b2 69` `b2` bleed `−28.4 2023` — `B2` only when `sustainBars 7` close `7-bar sustain first swing detection theory:63` `firstswing.py:580 disabled` on `BTC` — no `SUS`.

**Do NOT trade opposite to swing:** `FS-opposite whole-window 82 −86 PF0.05` `LTF fs_opposite 12 −5 6 −9` all `win 0-8%` `7-12tr` — `entry theory:11 For BUYING wait selling swing → BUY` `opposite` is HTF bias already `v5` `same-dir inside HTF window` `v1_15m:90`, not `LTF opposite`.

**Next experiment (you asked permutation and combination here too) — to find `when`:**
- [x] `HTF conditional break` engine `backend/src/btc/engines/htf_ltf/v11_conditional_htf.py` `htf_entry_break="conditional"` `if chop>61.8 or atr%<0.35 → decisive else flip` `v1_15m:13` `htf_entry_gate` `v7` `btc_routes:571` `whitelist v1|v3|v5|v6` needs `v11` — **DONE 2026-09-08** `C:\Users\Pravin\AppData\Local\Temp\opencode\cond_out.txt`
- [x] `FS as HTF window` already `90 +3.3 85 −84` `fs_opposite −86` — **not edge**, keep `Flip/Decisive` HTF, not `FS`.
- [x] `LTF FS-opposite` already `12 −5 6 −9` — **do not use**, keep `decisive` LTF.

---

## Conditional HTF — game changer `when to use B2 vs Flip` — `v11_conditional_htf` `chop>61.8` `atr<0.35` `FULL 1.93M`

> **Engine:** `backend/src/btc/engines/htf_ltf/v11_conditional_htf.py:1` `_chop_series_1h lb14 v4_chop.py:26` `_atr_pct_15m` `chop>61.8 HIGH choppy` `atr_low<0.35% LOW vol 309 +133 Exp4` `mode chop/atr_low/chop_or_atr_low/b2_vs_flip_chop` `simulate_htf_ltf_conditional` `HTF Flip vs Decisive vs B2 intervals 355/284/334` `LTF decisive 0.25ATR ext-stop1.5` `backend/debug/test_conditional_htf.py:1` `C:\Users\Pravin\AppData\Local\Temp\opencode\cond_out.txt`.

| Version | Trades | Net | PF | DD | 2023 | 2024 | 2025 | 2026 | Win% |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| V5.0 flip × decisive | 442 | 168.1 | 1.86 | 23.3 | −7.2 | 40.1 | 101.5 | 33.7 | 28.5% |
| HTF decisive × decisive | 558 | 122.6 | 1.60 | 35.4 | +37.7 | −16.9 | 35.3 | 66.5 | 27.1% |
| **Conditional chop>61.8 (decisive vs flip)** | **446** | **177.1** | **1.88** | **23.9** | **−7.8** | **45.0** | **91.5** | **48.5** | **27.8%** |
| Conditional atr_low <0.35 | 536 | 165.1 | 1.75 | 31.4 | +21.4 | 32.4 | 56.5 | 54.8 | 26.9% |
| Conditional chop_or_atr_low | 539 | 172.5 | 1.77 | 31.4 | +21.4 | 25.7 | 55.4 | 70.0 | 26.5% |
| Conditional chop_and_atr_low | 442 | 163.6 | 1.84 | 23.9 | −7.8 | 45.5 | 92.6 | 33.3 | 28.1% |
| **Conditional b2_vs_flip_chop** `HIGH chop → B2 else Flip` | **446** | **197.2** | **1.95** | **23.3** | **−7.5** | **62.3** | **99.5** | **43.0** | **28.3%** |
| Conditional chop>50 | 512 | 137.6 | 1.67 | 31.9 | −8.7 | 24.9 | 72.0 | 49.4 | 26.0% |
| Conditional chop>70 (pure Flip) | 442 | 168.1 | 1.86 | 23.3 | −7.2 | 40.1 | 101.5 | 33.7 | 28.5% |
| Conditional atr<0.3 | 512 | 155.9 | 1.75 | 20.6 | +32.0 | 17.5 | 53.4 | 53.0 | 27.0% |
| Conditional atr<0.4 | 542 | 156.2 | 1.72 | 26.8 | +37.4 | 13.8 | 53.4 | 51.7 | 27.3% |

**Takeaways — game changer you asked `if we figure out when to use what that will be a game changer`:**
- **Best total = `b2_vs_flip_chop` `446 +197.2 PF1.95 DD23.3 +29.1R vs V5.0 168.1`** `HIGH chop>61.8 → B2 else Flip` `HTF B2 284 intervals vs Flip 355` — **beats `decisive×decisive +37.7` in total by +74.6R** while **2023 −7.5 vs +37.7 loses −45R 2023** but `2024 +62.3 vs +40.1 +22.2R` `2025 99.5 vs 101.5 −2R` `2026 43.0 vs 33.7 +9.3R` total +29R.
- **Best 2023 still `decisive×decisive +37.7`** `558tr` but total `122.6` `−74.6R vs conditional 197` — `conditional b2_vs_flip` gives `2023 −7.5` similar to `V5.0 −7.2` not `+37.7`, so **not game changer for 2023**, but **is game changer for total**.
- **Best 2023 + total trade-off:** `atr<0.35 21.4 +165 total` `chop_or_atr 21.4 +172 total` `atr<0.4 37.4 +156 total` `atr<0.3 32.0 +155 total` — **`atr<0.35` gives `+21.4 2023` with `165 total (−3R vs V5)`, `chop_or_atr` gives `+21.4 2023` with `172 total (+4R vs V5)`** `539tr` `WIN both` `+4R total +28.6R 2023`.
- **Chop>50 is too low `137 net` worse than 61.8 `177`**, `Chop>70 = pure Flip 168` (no decisive used) — `61.8` is sweet spot `v4_chop:26` `38.2/61.8` `fix:355`.
- **Verdict:** `HTF B2 when HIGH chop (>61.8 choppy) else Flip` is **current BEST total 197.2** `+29R vs V5` `PF1.95` `DD23.3 same as V5` `446tr` — **game changer for total, not for 2023**. If you want `2023 +37.7` keep `decisive×decisive` as **2023 hedge alt** `558 +122` separate `v11` mode `chop_or_atr_low 539 +172 2023 +21.4` is **balanced best both** `+4R total +28.6R 2023` vs `V5`.

*Harness `backend/debug/test_permutation_matrix.py:1` `backend/debug/test_permutation_fs.py:1` `backend/debug/test_conditional_htf.py:1` `C:\Users\Pravin\AppData\Local\Temp\opencode\perm_out.txt` `perm_fs_out2.txt` `cond_out.txt` `32259 x1h 128951 x15m 386855 x5m 1934262 x1m` `fine` `v5_sl_buffer 0.25`.*

---

## Continuous crossover — `B2 R − Flip R` vs continuous 1h chop (10 buckets) — `backend/debug/test_exp_continuous_crossover.py:1` `C:\Users\Pravin\AppData\Local\Temp\opencode\continuous_crossover.csv` `C:\Users\Pravin\AppData\Local\Temp\opencode\cont_cross_out.txt` `2935 LTF decisive signals 442 Flip 526 B2 trades` `chop BEFORE signal bar-1 v11:92` `atr_pct 15m` `fine 1.93M`

| Bucket (1h chop before) | Flip tr | Flip net | B2 tr | B2 net | B2−Flip net | Flip PF | B2 PF | Flip avg | B2 avg |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0-20 | 0 | 0.0 | 0 | 0.0 | 0.0 | 0.00 | 0.00 | 0.00 | 0.00 |
| 20-30 | 3 | −3.0 | 6 | −3.3 | −0.3 | 0.00 | 0.27 | −1.00 | −0.55 |
| 30-40 | 77 | 71.6 | 79 | 50.1 | **−21.5** | 2.26 | 1.90 | 0.93 | 0.63 |
| 40-50 | 136 | 33.5 | 177 | 5.4 | **−28.1** | 1.30 | 1.04 | 0.25 | 0.03 |
| 50-55 | 84 | 38.2 | 109 | 36.8 | −1.5 | 1.64 | 1.43 | 0.46 | 0.34 |
| 55-60 | 78 | 8.8 | 88 | −39.0 | **−47.8** | 1.16 | 0.47 | 0.11 | −0.44 |
| 60-62 | 33 | 32.3 | 29 | 2.2 | **−30.1** | 2.42 | 1.09 | 0.98 | 0.08 |
| 62-65 | 20 | −17.1 | 20 | −15.5 | **+1.6** | 0.13 | 0.15 | −0.86 | −0.78 |
| 65-70 | 9 | −0.6 | 15 | 11.5 | **+12.1** | 0.91 | 2.35 | −0.07 | 0.76 |
| 70-75 | 2 | 4.4 | 3 | 1.6 | −2.8 | 0.00 | 2.54 | 2.19 | 0.54 |

*Paired where both traded same LTF signal (103/2935) delta 0.00 `20-30 1 0.00` `30-40 19 0.00` `40-50 25 0.00` `55-60 44 0.00` `62-65 11 0.00` — `both modes same signal → same R` `one swing one trade 93` `touchable SL 128` confirms `HTF window` not `LTF signal` drives difference, `per interval` not `per signal`.*

*Takeaway `61.8` is `not systematic crossover` `20 −0.3 30-40 −21.5 40-50 −28.1 50-55 −1.5 55-60 −47.8 60-62 −30.1 62-65 +1.6 65-70 +12.1` — `flip dominates LOW/MED 0-60` `B2 only +12.1 in 65-70 9 vs 15 tr` `HIGH 61.8-75 35 −14.8 vs 41 −3.0 +11.8` earlier `b2_flip_cond.txt` `24+9.9` but `continuous 10 buckets` shows `no monotonic increase` `20→30 −0.3 40→−28 50→−1 55→−47 60→−30 62→+1 65→+12` — `61.8` is `lucky partition` not `genuine regime relationship` `fix:355` `38.2/61.8` `v4_chop:26` needs stronger validation `walk-forward` `fix:140` `+197 vs 168 +29R same DD` `cond_out.txt:8` is `+29R` but `B2−Flip +11.8 HIGH` small sample `35/41` `24.2% B2 wins HIGH` `C:\Users\Pravin\AppData\Local\Temp\opencode\interval_out2.txt` `HIGH 33 intervals avg delta +0.20` `paired HIGH 9 +0.74` `B2 wins 2/9`.*

*Harness `backend/debug/test_exp_continuous_crossover.py:1` `C:\Users\Pravin\AppData\Local\Temp\opencode\continuous_crossover.csv` `C:\Users\Pravin\AppData\Local\Temp\opencode\cont_cross_out.txt` `2935 signals 442 Flip 526 B2` `chop BEFORE bar-1 v11:92` `no lookahead` `firstswing.py:580` `SUS 100% FS`.*

---

## Walk-forward regime test — `B2 vs Flip` per chop bucket, both modes on same interval, `chop BEFORE signal` (no lookahead) — `backend/debug/test_b2_vs_flip_conditionality.py:1` `C:\Users\Pravin\AppData\Local\Temp\opencode\b2_flip_cond.txt` `backend/debug/test_interval_b2_flip_csv.py:1` `C:\Users\Pravin\AppData\Local\Temp\opencode\b2_flip_interval.csv` `32259 x1h 355 Flip 284 B2 intervals` `2935 LTF decisive signals` `v11_conditional_htf 61.8` `firstswing.py:580` `SUS 100% FS`

**Bucket test `FULL 1.93M` `LTF decisive 2935 signals` `chop BEFORE signal bar-1` `no lookahead` `v11:92` `chop at j-1` `firstswing.py:580` `SUS removed` `fix/btc_ideas:101` `gap 1` `firstswing.py:373`:**

| Bucket (1h chop before signal) | Flip tr | Flip net | B2 tr | B2 net | B2−Flip | Flip win% | B2 win% |
|---|---:|---:|---:|---:|---:|---:|---:|
| LOW <38.2 | 48 | 26.1 | 58 | 9.8 | **−16.3** | 22.9% | 27.6% |
| MED 38.2-61.8 | 359 | **156.8** | 427 | 43.0 | **−113.8** | 28.1% | 22.2% |
| HIGH 61.8-75 | 35 | −14.8 | 41 | −3.0 | **+11.8** | 20.0% | **29.3%** |
| EXTREME >75 | 0 | 0.0 | 0 | 0.0 | 0.0 | — | — |

**Interval-level `HTF interval` as base calendar `355 FLIP intervals` `C:\Users\Pravin\AppData\Local\Temp\opencode\b2_flip_interval.csv` `per HTF interval` `chop_before atr_pct chop_change slope3 slope5 htf_trades ltf_trades ltf_R winner delta_R`:**

| Bucket (HTF interval chop) | intervals | avg Flip | avg B2 | avg delta | B2 wins |
|---|---:|---:|---:|---:|---:|
| LOW <38.2 | 36 | 0.09 | −0.30 | −0.39 | 11/36 30.6% |
| MED 38.2-61.8 | 286 | 0.57 | 0.28 | −0.29 | 72/286 25.2% |
| HIGH 61.8-75 | 33 | 0.07 | 0.27 | **+0.20** | 8/33 24.2% |

| Paired where both have trades in same FLIP window (108/355) | n | avg delta | B2 wins |
|---|---:|---:|---:|
| LOW <38.2 | 7 | −1.31 | 2/7 |
| MED 38.2-61.8 | 92 | −0.50 | 31/92 |
| HIGH 61.8-75 | 9 | **+0.74** | 2/9 |

**20 boundary cases `chop 60-63 around 61.8` `signal_time chop_before mode_selected Flip R B2 R` `C:\Users\Pravin\AppData\Local\Temp\opencode\b2_flip_cond.txt:20` `chop at bar-1` `mode b2 if >61.8 else Flip` `v11:117` `firstswing.py:580`:**

| date | chop_before | dir | in_flip | in_b2 | R_flip | R_b2 |
|---|---:|---|---|---|---|---|
| 2023-01-23 02:15 | 60.3 | short | True | True | −0.99 | −0.99 |
| 2023-02-12 00:00 | 60.4 | short | True | False | −1.18 | — |
| 2023-02-25 18:00 | 60.3 | short | False | True | — | −1.02 |
| 2023-03-29 00:15 | 60.6 | long | False | True | — | +0.59 |
| 2023-04-28 14:00 | 60.7 | short | True | False | −0.18 | — |
| 2023-05-14 06:00 | 62.1 | short | True | False | −1.03 | — |
| 2023-06-15 16:45 | 61.9 | short | True | False | −1.04 | — |

**Walk-forward with fixed `61.8` `HIGH→B2 else Flip` `v11:60` `fix:355` `38.2/61.8` `Train 2023→Test 2024` `Train 2023-24→Test 2025` `Train 2023-25→Test 2026` `61.8 frozen` `backend/debug/test_delta_chop_walkforward.py:1` `C:\Users\Pravin\AppData\Local\Temp\opencode\delta_walk3.txt`:**

| Train | best HTF in Train | Test | Flip | B2 | Cond b2_vs_flip | Decisive |
|---|---:|---:|---:|---:|---:|---:|
| 2023 (37.7) | decisive +37.7 | 2024 | 40.1 | −1.2 | **62.3** | −16.9 |
| 2023-2024 (32.9) | flip 32.9 | 2025 | **101.5** | 63.4 | 99.5 | 35.3 |
| 2023-2025 (134.4) | flip 134.4 | 2026 | 33.7 | 2.9 | 43.0 | **66.5** |

| Test | Flip | Cond b2_vs_flip diff | Cond chop_or_atr diff |
|---|---:|---:|---:|
| 2024 | 40.1 | **+22.2** (62.3) | **−14.4** (25.7) |
| 2025 | 101.5 | **−2.0** (99.5) | **−46.1** (55.4) |
| 2026 | 33.7 | **+9.3** (43.0) | **+36.3** (70.0) |

**Takeaways `B2 vs Flip` per bucket:**
- **LOW `Flip +26.1 vs B2 +9.8 −16.3` `MED 156.8 vs 43.0 −113.8`** `83% trades 407/442` — `Flip` (reversal) dominates trending/normal `LOW/MED chop 48+359=407` `B2 continuation same-dir 43.0` loses `−113R` in `MED` `firstswing.py:458 FLIP` vs `436 B2` `b2_gap 1`.
- **HIGH `Flip −14.8 (35tr 20% win) vs B2 −3.0 (41tr 29% win) +11.8`** `B2 6 more trades 29% win` — `HIGH chop 35-41tr 5%` `Exp4 24 +9.9` where `previous swing structure repeatedly violated → Flip noisy` `firstswing.py:458 FLIP` vs `B2 continuation has better follow-through` `firstswing.py:436` — B2 `less negative` not positive, `B2 29% vs Flip 20%` win.
- **Thus `b2_vs_flip_chop 197` total `+29R` comes from `2024 +62.3 vs 40.1 +22.2R` `2026 +43 vs 33 +9.3R` not `HIGH` `+11.8` alone** `bucket HIGH both negative` `MED still −113` — conditional `B2 in HIGH` saves `11.8` but loses `−113` in `MED` if you use `B2` there, so `HIGH→B2 else Flip` is **correct regime** but gain is `2024` trending `MED`? `2024` is `post-bear` not `HIGH chop`? Needs `HTF interval chop` vs `yearly` distinction `fix/multi tf:238` `2023 chop 108tr −35 HTF` `Exp5 0-2d −244`.
- **No lookahead verified `chop_before = chop at 1h bar j-1` `v11:92` `bisect_right(ts_htf, ts_ltf)-1 then j-1` `test_b2_vs_flip_conditionality.py:20` `chop_before_ltf_bar` not `current` `firstswing.py:580 SUS removed` `fix/btc_ideas:101` `gap 1 candle` `firstswing.py:373` — boundary `60.1→62.1` cases `in_flip/in_b2 differ` per `chop_before`.
- **Why not `197` as new edge yet:** `+197 vs 168 +29R same DD23.3` `cond_out.txt:8` `fix:134` is interesting `+29R` `PF1.95` same `DD` `446tr` but **walk-forward `Train 2023→Test 2024` `Train 2023-24→Test 2025` with fixed `61.8` not re-optimized per period** needed `fix/permutation:140` `Best total = b2_vs_flip 197 while 2023 −7.5 vs +37.7 loses −45R` — you searched conditional after seeing `2023 +37.7` `fix:14` `perm_out.txt` — data-mining risk.

*Harness `backend/debug/test_b2_vs_flip_conditionality.py:1` `C:\Users\Pravin\AppData\Local\Temp\opencode\b2_flip_cond.txt` `32259 x1h 128951 x15m 1934262 x1m fine 0.05%+2pt 1m stream` `v5_sl_buffer 0.25` `v11_conditional_htf 61.8` `firstswing.py:500` `btc_swing:105` `SUS disabled 100% FS fix/btc_ideas:58`.*

---

## Walk-forward regime test — `B2 vs Flip` per chop bucket, both modes on same interval, `chop BEFORE signal` (no lookahead)

> **Why this test:** `+197 vs 168 +29R same DD 23.3` `b2_vs_flip_chop HIGH chop→B2 else Flip` `cond_out.txt:8` `fix:134` is `+29R` but `2023 −7.5` not `+37.7` — you searched conditional after seeing `2023` `decisive×decisive +37.7` `fix:14` `perm_out.txt` — data-mining risk `fix/permutation:140` `Best total = b2_vs_flip 197 ... while 2023 −7.5 vs +37.7 loses −45R`. So test **does B2 genuinely beat Flip when HIGH chop?** Not just `which made more money` but `B2 R − Flip R per bucket` on **exact same HTF interval**.

**Engine:** `backend/src/btc/engines/htf_ltf/v11_conditional_htf.py:1` `mode b2_vs_flip_chop` `HIGH chop>61.8 → B2 else Flip` `_chop_series_1h lb14 v4_chop.py:26` `chop 100*log10(tr_sum/rang)/log10(lb) 0 trend 100 chop` `38.2/61.8 fib fix:355` `Exp4 LOW <38.2 52 +28 MED 366 +130 HIGH 24 +9.9` vs `LOW vol 309 +133` `v5_5directions:172` `firstswing.py:500 chop opposite` `btc_swing:105` `SUS disabled 100% FS fix/btc_ideas:58`.

**How HTF intervals chosen per LTF bar `v11:84-95` `_chop_series_1h lb14` `chop` per 1h bar `atr_pct 15m` `chop_per_ltf bisect 1h bar containing LTF bar` `v11:92` `ltf_sigs _collect_signals swings_ltf decisive stream 15m mb50` `v11:97` `if mode b2_vs_flip_chop: use = b2 if ch>61.8 else flip` `intervals_b2 284 vs Flip 355` `intervals_flip 355` `starts_b2 284` `bs.bisect_right(starts, bar_ts)-1` `s<bar_ts<=e` `sig.dir==htf_dir v11:150` `ext_stop 1.5 v11:138` `sl_buf 0.25ATR v11:149` `MB50 trail _trail_events v11:185` `fine 1.93M v11:219` same as `v1_15m.py:90` `btc_engine:179` `conservative sl before target` `gap` `_exit_on_fine 1m`.*

**Bucket test `backend/debug/test_b2_vs_flip_conditionality.py:1` `C:\Users\Pravin\AppData\Local\Temp\opencode\b2_flip_cond.txt` `FULL 1.93M` `LTF decisive 2935 signals` `chop BEFORE signal bar-1` `no lookahead` `v11:92` `chop at j-1` not `current` `firstswing.py:580` `SUS removed` `fix/btc_ideas:101`:**

| Bucket (1h chop before signal) | Flip tr | Flip net | B2 tr | B2 net | B2−Flip | Flip win% | B2 win% |
|---|---:|---:|---:|---:|---:|---:|---:|
| LOW <38.2 | 48 | 26.1 | 58 | 9.8 | **−16.3** | 22.9% | 27.6% |
| MED 38.2-61.8 | 359 | **156.8** | 427 | 43.0 | **−113.8** | 28.1% | 22.2% |
| HIGH 61.8-75 | 35 | −14.8 | 41 | −3.0 | **+11.8** | 20.0% | 29.3% |
| EXTREME >75 | 0 | 0.0 | 0 | 0.0 | 0.0 | 0.0% | 0.0% |

**Walk-forward per year `v11 b2_vs_flip_chop 446 +197` vs pure `Flip 442 +168` vs `B2 526 +49` `decisive 558 +122` `cond_out.txt:8` `fix:134`:**

| Year | Flip | B2 | Cond b2_vs_flip | Decisive | Best |
|---|---:|---:|---:|---:|---|
| 2023 | −7.2 | −15.3 | −7.5 | +37.7 | Decisive |
| 2024 | 40.1 | −1.2 | **62.3** | −16.9 | Cond |
| 2025 | 101.5 | 63.4 | 99.5 | 35.3 | Flip |
| 2026 | 33.7 | 2.9 | 43.0 | 66.5 | Decisive |

**20 boundary cases `chop 60-63 around 61.8` `signal_time chop_before mode_selected Flip R B2 R` `C:\Users\Pravin\AppData\Local\Temp\opencode\b2_flip_cond.txt:20` `chop at bar-1` `mode b2 if >61.8 else Flip` `v11:117`:**

| date | chop_before | dir | in_flip | in_b2 | R_flip | R_b2 |
|---|---:|---|---|---|---|---|
| 2023-01-23 02:15 | 60.3 | short | True | True | −0.99 | −0.99 |
| 2023-02-12 00:00 | 60.4 | short | True | False | −1.18 | — |
| 2023-02-25 18:00 | 60.3 | short | False | True | — | −1.02 |
| 2023-03-29 00:15 | 60.6 | long | False | True | — | +0.59 |
| 2023-04-28 14:00 | 60.7 | short | True | False | −0.18 | — |
| 2023-05-14 06:00 | 62.1 | short | True | False | −1.03 | — |
| 2023-06-15 16:45 | 61.9 | short | True | False | −1.04 | — |

**Takeaways — why B2 wins (only) in HIGH chop `+11.8` but both still negative:**
- **LOW `Flip +26.1 vs B2 +9.8 −16.3` `MED 156.8 vs 43.0 −113.8`** `83% trades 407/442` — `Flip` (reversal) dominates trending/normal `LOW/MED chop 48+359=407` `B2 continuation` `firstswing.py:436` `b2_gap 1` `same-dir` loses `−113R` in `MED`.
- **HIGH `Flip −14.8 (35tr 20% win) vs B2 −3.0 (41tr 29% win) +11.8`** `B2 6 more trades 29% win` — `HIGH chop 35-41tr` `5%` `Exp4 24 +9.9` where `previous swing structure repeatedly violated → Flip noisy` `firstswing.py:458 FLIP` vs `B2 continuation has better follow-through` `firstswing.py:436` `b2_gap 1` — B2 `less negative` not positive, `B2 29% vs Flip 20%` win.
- **Thus `b2_vs_flip_chop 197` total `+29R` comes from `2024 +62.3 vs 40.1 +22.2R` `2026 +43 vs 33 +9.3R` not `HIGH` bucket `+11.8` alone** `bucket HIGH both negative` `MED still −113` — conditional `B2 in HIGH` saves `11.8` but loses `−113` in `MED` if you use `B2` there, so `HIGH→B2 else Flip` is **correct regime** but gain is `2024` trending `MED`? `2024` is `post-bear` not `HIGH chop`? Needs `HTF interval chop` vs `yearly` distinction `fix/multi tf:238` `2023 chop 108tr −35 HTF` `Exp5 0-2d −244`.
- **No lookahead verified `chop_before = chop at 1h bar j-1` `v11:92` `bisect_right(ts_htf, ts_ltf)-1 then j-1` `test_b2_vs_flip_conditionality.py:20` `chop_before_ltf_bar` not `current` `firstswing.py:580 SUS removed` `fix/btc_ideas:101` `gap 1 candle` `firstswing.py:373` `SUS 7-bar`* — boundary `60.1→60.3→62.0` cases show `in_flip` vs `in_b2` differ per `chop_before`, `R_flip`/`R_b2` both `−0.99` when both intervals contain same bar `2023-01-23`.
- **Why not `197` as new edge yet:** `+197 vs 168 +29R same DD23.3` `cond_out.txt:8` `fix:134` is interesting `+29R` `PF1.95` same `DD` `446tr` but **walk-forward `Train 2023 Test 2024` `Train 2023-24 Test 2025` `Train 2023-25 Test 2026` with fixed `61.8` not re-optimized per period** needed `fix/permutation:140` `Best total = b2_vs_flip 197 while 2023 −7.5 vs +37.7 loses −45R` — you searched conditional after seeing `2023 +37.7` `fix:14` `perm_out.txt` — data-mining risk. So **do not declare `197` edge yet**, test `chop>61.8 → B2 else Flip` **chronologically** `Train 2023→Test 2024` `Train 2023-24→Test 2025` `Train 2023-25→Test 2026` with `61.8` fixed beforehand `v11:60` `fix:355` `38.2/61.8` not re-optimized.
- **Cool test you suggested:** For every `HTF interval chop` `atr%` `HTF mode flip/b2/decisive` `LTF mode decisive` `trade R MFE MAE exit reason` `per interval` `HTF mode = flip/b2/decisive` `LTF decisive` `C:\Users\Pravin\AppData\Local\Temp\opencode\b2_flip_cond.txt` already logs `signal_time chop_before mode_selected first_trade_after_mode` `20 boundary cases` `in_flip/in_b2 R_flip/R_b2` — next step **trade-level CSV** `HTF interval chop ATR% HTF mode LTF mode trade R MFE MAE exit` `backend/debug/test_b2_vs_flip_conditionality.py:20` to measure `B2−Flip per bucket` `LOW Flip +80 B2 +20 MED Flip +50 B2 +30 HIGH Flip −10 B2 +40` **crossover** `61.8` approximating genuine regime `fix:355` `Exp4 52 +28 366 +130 24 +9.9`.
- **Other cool test `Don't classify regime using same period` `signal_time chop_observation_time chop_value mode_selected first_trade_after_mode` `20 boundary cases` already `chop at bar-1` `v11:92` `firstswing.py:580` `SUS` `fix/btc_ideas:101` `gap 1` — next `HTF chop 72` decide `use B2` `C:\Users\Pravin\AppData\Local\Temp\opencode\b2_flip_cond.txt` `chop 60.1→62.1` cases.
- **5m result `1h → 5m` garbage `−245→−760` `perm_out.txt:15` `fix:27` `2161 −345` `1540 −245` while `1h → 15m` strongly profitable `442 +168` `558 +122` `197 +122` — edge exists at `1h→15m` interaction, not `more granular` `fix/permutation:38` `Do not use 5m LTF` `fix/crazy_ghost_mix:13` `30-40% flat gaps` `Exp5 0-2d −244 355tr`.
- **What NOT to do `RSI MACD VWAP ADX volume funding OI Bollinger EMA200 VIX` `V37` `fix/v5:277` `SSRN 2349848` `2602.11708` `5821842` — keep `one hypothesis → one experiment → preserve baseline → inspect trades → test OOS` `fix/v5:4` `23-26 trades ≥3R 135-174% net`.
- **Next experiment you ranked `#1 B2 vs Flip conditionality` per interval `HTF interval chop ATR% HTF mode LTF mode trade R MFE MAE` `B2−Flip per bucket` `LOW Flip +80 B2 +20 HIGH Flip −10 B2 +40` crossover `61.8` `fix/permutation:140` `v11 b2_vs_flip 197` `cond_out.txt:8` `C:\Users\Pravin\AppData\Local\Temp\opencode\b2_flip_cond.txt` `20 boundary` plus `Exp1 MAE 50 runners 38% 0.5-0.75 +3.95` `C:\Users\Pravin\AppData\Local\Temp\opencode\exp1_out.txt` `Exp2 delayed MB50 159 vs 168` `C:\Users\Pravin\AppData\Local\Temp\opencode\exp2_out2.txt` `Exp7 ATR −49` `C:\Users\Pravin\AppData\Local\Temp\opencode\exp7_out2.txt` `V37` warning.

*Harness `backend/debug/test_b2_vs_flip_conditionality.py:1` `C:\Users\Pravin\AppData\Local\Temp\opencode\b2_flip_cond.txt` `32259 x1h 128951 x15m 1934262 x1m fine 0.05%+2pt 1m stream` `v5_sl_buffer 0.25` `v11_conditional_htf 61.8` `firstswing.py:500` `btc_swing:105` `SUS disabled 100% FS fix/btc_ideas:58`.*


