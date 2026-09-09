# Crazy Ghost Mix — HTF Mean Reversion × LTF Swing Breaks — Brainstorm LIVE 1.93M

> **Why mix:** `AT_Trading v5` trend `442 +168 net 2023 −7.2` `MB50` gives back 46% `mfe7.9→real4.2` `Exp1` `C:\Users\Pravin\AppData\Local\Temp\opencode\exp1_out.txt` is plateau — `V5.1 ATR −49  V5.3 delay 159 V5.4 partial 140` all <168 `fix/v5_5directions_checklist.md:250` `v1_15m.py:17` `1.93M` `32259 x1h`. Ghost `BTC_GhostStreak\files\doc official.md:57 4 same-color → reversal` `RCHB 437` `State1 shift doc:167` `HTF Open pause doc:356` `reality leverage 20-50x` `streakseeker 2025-12-30 fee-aware` net bleedy but **mean-reversion HTF bias** is orthogonal to `AT swing` `HH/HL` `first swing 9:15 7-bar sustain` `overview.py:44` `bias 1h Flip cap16 355 +25 fragile`.

**Shared: flip only when opposite break, jump right** — `Ghost RCHB: lower RED high shifts down then break above → LONG` same as `AT FLIP: opposite swing break` `btc_engine:33 tradeable B2|FLIP` `one swing one trade 93` `touchable SL 128` — both wait for opposite break, not any touching.

## Crazy combos to test (one hypothesis at a time, same data `32259 x1h 1.93M` `0.05%+2pt` `stream` `1m 1934262` `fine` `btc_routes:377` `v1_15m:1` `v5_sl_buffer 0.25ATR ext-stop1.5` baseline `442 +168` `2023 −7.2` `2024 40 2025 101 2026 33`):

### Crazy 1 — HTF Ghost bias + LTF B2/FLIP same dir (MAIN per your ask)

- **HTF GHOST (1h):** streak `3 same-color → subscribe (track 1m ref highs/lows)` `4th same-color CLOSE → activate` `GREEN→SHORT RED→LONG` mean rev `doc official:57` `Window +15m(5m) / +45m(15m)` scaled to `1h: +240m (4h)`? For 1h test: `3→4 streak` `Window = 4th close + 240m` `State1 shift on continuation` `State4 cancel only if close beyond frozen protection` `doc:167` `reality 40-50pts min`.
- **HTF Open filter `doc:356`:** `SHORT pause if tick ABOVE 1h OPEN` `LONG pause if tick BELOW` — live tick.
- **LTF SWING (15m):** `_collect_signals swings 15m mb50 decisive stream` `btc_engine:33` `B2|FLIP` `one swing one trade` only when `htf_ghost_dir == ltf_sig dir` `v1_15m:87` same as current `HTF window` gate `s_ts < bar_ts <= e_ts`.
- **Why crazy:** `v5` HTF is `trend Flip cap16 +25 net +0.07/tr fragile` `fix/multi tf:238` `1h bleed −35R 2023` — ghost HTF is **fade** (`2023 chop` where `v5` bleeds −7.2 vs −41 `Exp4 LOW vol 309 +133` still trend) — orthogonal regime.
- **Expect:** fewer trades `30-40% flat gaps fix:13` already, ghost window `15-45m` even shorter → `~100-150 LTF trades` vs `442`, win% maybe up `LOW chop` not `HIGH chop 24 +9.9`.

### Crazy 2 — Normal v5 entry (HTF Flip + LTF B2/FLIP) but EXIT via mean-reversion (RCHB/opposite break)

- **Entry:** keep `1h Flip cap16 355tr +25` window `v1_15m:59 intervals` `ext-stop1.5` `sl_buf0.25` `442 +168`.
- **Exit:** instead of `MB50 trail v1_15m:199` `best 7.9→4.2` `giveback 3.66R Exp1`, use **Ghost RCHB trailing**: track color-specific 1m highs/lows `doc:437` `RED high lower → shift down` `GREEN low higher → shift up`, exit when `close breaks opposite RCHB` or `opposite-color streak 2-3` forms. `v4_chop HTF Open pause` as trail pause.
- **Why:** `v5` `50 runners avg 3.6d max12.1d` `Exp5 0-2d −244 355tr  3-5d +284 78tr 92%` `8/67 MFE buckets` — winners give back `36.7→29.1` `38.3→28.8` `39.4→26.7` `Exp1 top10` — RCHB exhaustion may lock more `MFE capture 54% → 65%`.

### Crazy 3 — Flip-sync: HTF Ghost FLIP + LTF FLIP same dir only

- **Both FLIP only** `entry_break flip` `btc_engine:33 tradeable FLIP` `B2 excluded` — `HTF ghost 4th streak` is itself a FLIP (color shift) then `LTF FLIP` inside same direction (both wait for opposite break). `v5` is `decisive B2|FLIP` `446tr +5.4` `minBars50` vs `flip50 390 +8.8` `b2 +392R fix/btc_ideas:40` — `FLIP only` tighter.
- **State-based trail:** `initial 0.25ATR → first new swing in trade direction → activate MB50` `Exp7 V5.3 conditional` note `V5.3 159 vs 168 immediate` — test again with `FLIP sync`.

### Crazy 4 — HTF Ghost bias + LTF B2/FLIP but with v5 SL buffer + ext-stop kept

- Hybrid: `HTF Ghost streak bias` + `LTF MB50` + `0.25ATR buffer v5_sl_buffer:37` `sl_buf0.25` `11.2 DD` vs `hhll30 9.3` + `ext-stop1.5 v1_15m:93 pf4.95 1..1.5R gold vs 1.5..2R 0.02 fix:220`. Keep both edges.

### Crazy 5 — Reversed: HTF Swing bias (1h Flip) + LTF Ghost RCHB entry (inside HTF window)

- **HTF:** normal `1h Flip cap16 355 +25` `intervals`.
- **LTF:** Ghost RCHB inside window: for `1h LONG window`, take `15m GREEN→SHORT?` Not. Inside `LONG window` take `RED streak 4→LONG` with `RCHB break` instead of `B2/FLIP`. Tests if exhaustion entry inside trend window beats swing break.

### Crazy 6 — Window-less: Ghost streak on 15m itself (no HTF), but filter by AT Swing daily bias `overview.py:94` `pos 54% highs_extreme 85%` `HH/HL` `prev-day sustain` — `IF daily bullish allow only LONG ghosts`.

- Uses `streakseeker` `smart_position trail 1R after +1R` `calculate_smart_position_size 0.04% fee-aware` `MAX_POSITIONS 3` `ADX25` `EMA` `research make strategy result better:101 MIN_SL60` as filters.

## How to build (separate engine, never disturb v5 `v1_15m` `v5_sl_buffer` `btc_routes:671` `_net_stats 714`):

- **Engine isolation:** `backend/src/btc/engines/htf_ltf/v8_ghost_htf_bias.py` `v9_mean_rev_exit.py` `v10_flip_sync.py` each `simulate_htf_ltf_ghost_*` own file `fix/crazy_ghost_mix.md` `Rule: each version has its OWN engine` `multi tf:7`.
- **Ghost HTF logic:** copy `BTC_GhostStreak\files\doc official.md:63 Phase1 3rd → Phase2 4th → Window +15/45m → State1 shift → State4 cancel` `streak_bot_modules/ghost_streak_manager.py` simple `streak_count same-color` `ref_high/low` `protection` `htf open` `tick pause`.
- **Streak count on 1h:** map `5m 3→4` to `1h 3→4` (same thresholds) `Window 1h = 4th close + 240m (4*60)` `15m HTF: 3→4 with 3*15=45m` matches `doc:723 Window shift`.
- **HTF Open filter:** `HTF Open = last 1h open tick` `doc:356` `if dir LONG and tick < HTF_OPEN → pause` else resume — use `candle_ts` `close` approximation for backtest, live tick for later.
- **Costs:** same `0.05%+2pt` `slip` `risk <0.0005*entry skip` `target 3R` `busy_until` `trail swing` vs `RCHB`.

## Test plan (same metrics `V5.0 442 168.1 PF1.86 DD23.3 8.4avg runner 54% −7.2/40/101/33` `Exp7 table` `backend/debug/test_crazy_ghost.py:1` `C:\Users\Pravin\AppData\Local\Temp\opencode\crazy_out.txt` 2026-09-08):

| Version | Net | PF | DD | Runners | Avg runner | MFE cap | 2023 | 2024 | 2025 | 2026 | Trades | Intervals |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **V5.0 MB50** | **168.1** | 1.86 | 23.3 | 50 | 8.4 | 54% | −7.2 | 40.1 | 101.5 | 33.7 | 442 | 355 (Flip) |
| **Crazy1 ghostHTF wh4h B2/FLIP** | **85.5** | 1.88 | 28.8 | ~30* | ~6* | ~60% | **18.3** | **−4.4** | **77.4** | **−5.9** | **203** | **1667 ghost** |
| Crazy1b ghost wh4 FLIP only | 18.7 | 1.54 | — | — | — | — | 21.0 | −17.6 | 21.0 | −5.7 | 104 | 1667 |
| Crazy1 wh8h | 28.5 | 1.37 | 39.0 | | | | 3.3 | −24.4 | 63.7 | −14.2 | 343 | 1511 |
| Crazy1 wh12h | −24.1 | 1.17 | 38.0 | | | | −26.2 | −28.1 | 59.1 | −28.9 | 429 | 1373 |
| Crazy1 wh4 no ext-stop | 27.0 | 1.37 | 40.0 | | | | 15.1 | −12.2 | 34.4 | −10.4 | 340 | 1667 |
| Crazy2 v5 entry + RCHB exit | **−129.1** | 0.85 | 11.2 | 0* | — | — | −39.5 | −32.5 | −35.8 | −21.3 | **682** | 355 |
| Crazy2 v5 entry + RCHB exit | *queued* | | | | | | | | | | | |
| Crazy3 flip-sync | *queued* | | | | | | | | | | | |
| Crazy4 ghostHTF+buf+extStop | 85.5 same as Crazy1 (buf kept) | | | | | | | | | | | |
| Crazy5 1h Flip + Ghost LTF | *queued* | | | | | | | | | | | |

**Keep:** `v5 0.25ATR` `Exp1 keep wide` `time 16d innocent Exp5 >10d 2%` `LOW vol 309 +133 bread` `Exp4` no filter. Look for plateau, not peak. Docs: `C:\Users\Pravin\AppData\Local\Temp\opencode\exp1_out.txt` `exp2_out2.txt` `exp7_out2.txt` `exp7_partial_out.txt`.

**Crazy1 Verdict 2026-09-08:** `wh4h` **best ghost window** `85.5 net PF1.88 203tr` `2023 +18.3 ✅ beats v5 −7.2 by +25.5R` but `2024 −4.4 vs +40.1 −44.5R` `2026 −5.9 vs +33.7` net **−82.6R vs V5.0** `1667 ghost intervals vs 355 Flip` — ghost fade is **negatively correlated** `2023` vs trend, `wh8h 28.5 wh12h −24` worse, `no ext-stop 27 vs 85` proves `ext-stop1.5` still needed for ghost. **Ghost HTF is regime hedge, not standalone profit** — keep as `v8` separate engine `backend/src/btc/engines/htf_ltf/v8_ghost_htf_bias.py:1`, do not merge into `v5`. Next: Crazy2 RCHB exit may capture `MFE 36.7→29.1` giveback `7.6R` `Exp1 top10`.

**Crazy1b — Flip-sync (HTF ghost 4h + LTF FLIP only):** `104tr +18.7 net PF1.54 2023 +21.0 2024 −17.6 2025 +21.0` `C:\Users\Pravin\AppData\Local\Temp\opencode\test_flip_sync.py` vs `decisive 203 +85.5` — decisive beats flip by +66.8R, `FLIP only` tighter but kills winners (104 vs 203).

**Crazy2 — Normal v5 entry (HTF Flip cap16 + LTF B2/FLIP) but EXIT via mean-reversion RCHB (1m RED highs/GREEN lows, doc:437):** `682tr −129.1 net PF0.85 DD11.2 2023 −39.5 2024 −32.5 2025 −35.8 2026 −21.3` `backend/src/btc/engines/htf_ltf/v9_mean_rev_exit.py:1` `C:\Users\Pravin\AppData\Local\Temp\opencode\crazy_v9_out.txt` vs `MB50 trail 442 +168` — **RCHB exit destroys right tail (−297R vs MB50)**, `MFE capture` not 54%→65% but 0 runners, proves `MB50 structure` is harvest.

*Created 2026-09-08 for crazy mix. Engines `v8_ghost_htf_bias.py` `v9_mean_rev_exit.py` built, separate, never disturb `v5`. Next: `v10_flip_sync` already tested as Crazy1b, `Crazy4/5/6` queued — do as much experiment we can man.*

## Logs

### 2026-09-08 — Crazy1 GHOST HTF + LTF B2/FLIP (1h streak 3→4 fade + 15m decisive, 0.25ATR ext-stop1.5) — 4h window BEST

- **Engine:** `backend/src/btc/engines/htf_ltf/v8_ghost_htf_bias.py:1` `_ghost_intervals_1h window_hours 4` `streak 3→4 GREEN→SHORT RED→LONG` `State1 shift doc:167` `1667 intervals` `203tr` vs `v5 355 intervals 442tr`.
- **Sweep:** `wh4h 85.5 net PF1.88 DD28.8 2023 +18.3` `wh8h 28.5 PF1.37 3.3` `wh12h −24.1 PF1.17 −26.2` `no ext-stop 27 PF1.37 15.1` `backend/debug/test_crazy_ghost.py:1` `C:\Users\Pravin\AppData\Local\Temp\opencode\crazy_out.txt`.
- **Brainstorm:** HTF ghost `2023 chop` `+18.3 ✅` where `v5` `−7.2` bleeds `+25.5` hedge, but `2024 bull −4.4 vs +40.1` `2026 −5.9 vs +33.7` net −44/−40 trend bleed — `30-40% flat gaps fix:13` ghost even more `1667 intervals` but shorter windows. **Crazy idea proven as hedge, not better standalone** — keep as separate `v8` for portfolio `Combined v5 LTF 168 + ghost 85?` not `combined 193` `btc_routes:714`.

