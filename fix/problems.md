# Deep Check — 1min Precise `intraday_1m_standalone.py` Audit

> Config filters `Min SL 13 / Traverse B7` already parked/fixed and working.
> Tracks: **entry pivot / SL pivot wrong-place** issues + **swing engine white-line parity** (closed 2026-09-04).

**Status snapshot (2026-09-04)**

| Section | State |
|---|---|
| Entry/SL items 1-6 | ✅ ALL resolved (2026-09-04) |
| Swing engine white-line parity | ✅ closed — B1 = extreme break + same-bar arm guard with V-reversal exception; FLIP finding retracted; B2/chop verified 100% white-pivot |

## Fixed — Verified Correct

- **Conservative 2nd break** `intraday_1m_standalone.py:589` `required_breaks=2` if conservative + `522 p.idx > fs2_end` — `27 Aug 09:55 skip → 09:58 entry` per `docs/entry theory.md:64,72` ✓
- **SL prev_pivot +1.0** `intraday_1m_standalone.py:359` `pivot ±1.0` — aligns with `intraday.py` `5min` buffer ✓
- **Breakeven RR≥1:3 + breakeven_r filter** `intraday_1m_standalone.py:479` `is_breakeven_enabled()` `1R/1.5R/2R` selectable + **FT-fail 1min on/off** `460` `49` ft_fail ✓

---

## Open — Entry/SL Pivot Wrong Place (that kinda stuff)

### 1. ✅ RESOLVED — Conservative entry broke FS2's own confirmation pivot (mirrored for all swings)

- **Location:** `intraday_1m_standalone.py:598-620` (`_is_fs2_internal`), `firstswing.py:185 snap + 431 _check_chop` (`break-before-kill`)
- **Rule:** `docs/entry theory.md:72` — `FS ke baad ke pivots` (FS end ke baad, FS ka apna nahi). Conservative = `1st post-FS break SKIP, 2nd ENTRY`. Applies to **both** `selling→short` (`hi> tgt`) and `buying→long` (`lo< tgt`) and any candle colour (`high/low` print, not close).
- **Bug was:** `p.idx > fs2_end` included FS2's own chop target `latest_sealed_low/high` (e.g. `09:48 L24215.8` for `FS2 09:37→09:49 FS@09:50` or `09:38 H24668.7` for `2025-09-30 FS 09:21→09:45 FS@10:00`). At `09:51`/`09:44` the only sealed pivot `>fs2_end` was the confirm pivot itself, so `low<24215.8` / `low<24668.7` counted as `count=1`, early entry.
- **Fix:** `firstswing.py:185` snapshot `prev_latest_high/low` before `186 walker kill`, `431 _check_chop` uses `snap` for `hi>tgt / lo<tgt` so same-bar `kill` (`09:44 H24669.05` kills `09:38 H24668.7`) does not hide `09:38→09:44` break. `intraday_1m_standalone.py:598` also now `p.idx > fs2_confirmed_at && p.idx != fs2_confirm_idx && p.idx < i`. `09:48` (`48 ≤50`) / `09:38` (`23 ≤29`) excluded, first candidate `09:51 L24206.5` / `09:44 low 24649.25→FS@09:44` correct.
- **Verified:** `2026-08-27` `09:55 skip→09:58 short 24200.85`, `2025-08-06` `11:00 target 12:18`, `2025-09-30` `09:38→09:44 FS@09:44` (was `10:00`, now white `Walker` `flowline.ts:342` = yellow `FS`), mirrored `buying` `09:44 low` and `selling` `09:44 high` both `snap` covered, `red high→low 09:44` and `green low→high` both tested (`hi/low print` `firstswing.py:232` `hi>tgt/lo<tgt`).
- **Every swing:** `any new H kills old H / any new L kills old L` `firstswing.py:193` still holds, but `break` now sees `prev_latest` before kill — so next `H/L` after `FS` is first post-FS pivot, regardless of colour.

### 2. ✅ RESOLVED — Aggressive FS pivot dedup picks wrong pivot (FS pivot not counted)

- **Location:** `intraday_1m_standalone.py:652` `fs_break_pivot_idx`, `intraday.py:1021` `fs_break_pivot_idx`, `firstswing.py:429 last_confirm_hit` (`>dir_est 452 + gap 447`)
- **Rule:** Aggressive = `1st pivot break after FS` — must be **strictly newer** than the pivot FS itself broke. `FS ka apna pivot` dead → `FS pivot count no` (as you decided, `FS pivot` not counted, `FS ke baad ke pivots` `docs/entry theory.md:72`).
- **Bug was:** `652 for _p in reversed(pool) if _p.idx <= fs_confirmed_idx: fs_break = _p.idx; break` picked last `≤ conf` regardless of `dir_est/gap`. `2025-10-30 FS sustain @09:29 dir_est7 correct -1` vs **buggy `09:27 H25993.2 idx12`**, `2025-12-29 09:21 H26060.05 idx6` vs `12`, `2026-03-12 10:39 L84 23707.45` vs `86 23697.9` `20/270` mismatches `scan_real_aggressive.py`.
- **Fix:** `intraday_1m_standalone.py:652` now re-runs `FirstSwingEngine` up to `fs_confirmed_idx` to get `last_confirm_hit idx` (`firstswing.py:429` already `>dir_est+gap`) → `fs_break = hit idx if chop else -1` (sustain `-1` no dead pivot). `intraday.py:1021` same for `fs1_1min`. `FS pivot` (`09:48 L24215.8` for `27 Aug`) now dead, `09:51 L24206.5` is `1st post-FS`.
- **Verified:** `2025-10-30` `buggy 12 → correct -1` entry still `09:49` but now `> -1` live `1st` correct, `2026-03-12` `84→ -1?` actually `84` correct `86` buggy diff `20` days `>dir_est` now, `13 Aug 09:39` no longer fires on `24330.95` same pivot, `09:43` `24345.85` is `1st`.

### 3. ✅ RESOLVED — SL prev_pivot fallback wrong side

- **Location:** `intraday_1m_standalone.py:341-368`
- **Bug was:** `above = [p for p in eligible if p.px > ref_level]; pivot_ref = above[-1] if above else eligible[-2]` — `above` empty → `eligible[-2]` taken **without** `> ref` check. For `SHORT` (`dirn==-1`, SL must be *above* entry), this could pick a **low** pivot (`px < ref`) → `sl = pivot_ref.px +1` still **below entry** → `risk ≤0` inverted or `risk` tiny → `min_sl` widened but on wrong side, `pivot_ref` logged wrong, trade could be `risk <=0` `return False` silently dropped.
- **Fix:** Side-blind `eligible[-2]` deleted. `pivot_ref` stays `None` if no pivot on correct side (`> ref` for short, `< ref` for long). Then `elif min_sl_pts>0: sl = entry ± min_sl_pts` (13 default from `cfg min_sl_pts` `408`) → sane `entry ±13` stop, trade fires instead of dropping. `else: sl = entry_high/low + buffer 1.0`. `pivot_ref None` logged honest `null` (no pivot used). Both `eligible` exists but wrong side and `eligible` empty cases now use `min_sl`.
- **Verified:** `py_compile` + `run_backtest_1min` `270 days` `before/after` diff traceable to `prev_pivot` wrong-side fallback; recovered `risk<=0` dropped trades now `entry±13`.

### 4. ✅ RESOLVED — Reference rearm does not reset break count / broken levels

- **Location:** `intraday_1m_standalone.py:512-528` traversal, `289 pivot_break_count`, `292 broken_pivot_levels`
- **Rule:** `docs/entry theory.md:64` — each desired swing has its own `1st skip → 2nd entry` (conservative day) or `1st break → entry` (aggressive day; mode comes from the bias case, not a per-trade toggle). New swing = new count.
- **Bug was:** On `ref_breach → _find_swing → ref update` only `pivot_break_count=0` reset (`528`), `broken_pivot_levels` **not** cleared. The stale set could swallow the new swing's genuine 1st break when a fresh pivot's price matched a historically-broken level (`skipped_already_broken`) — shifting the whole skip/entry sequence one break late. (The count-leak half — `2025-08-12: count 1 from 10:55 leaked across the 11:03 traverse` — was already fixed; this was the remaining set-leak half.)
- **Fix:** `broken_pivot_levels.clear()` added atomically with `pivot_break_count = 0` on every `reference_swing_updated` (`intraday_1m_standalone.py:537`). Within-swing dedup untouched.
- **Verified:** full-CSV `run_backtest_1min` before/after — identical trades (262 trades, WR 14.1%, total R −14.53): the stale-set swallow needs an exact float price match between a post-rearm fresh pivot and a historically-broken level, which never changed a trade on this dataset. Dedup still active (7,703 `skipped_already_broken` events) and rearm semantics now correct: fresh swing = fresh sequence.

### 5. ✅ RESOLVED — Swing-end guard uses `close` vs `entry = pivot level`

- **Location:** `intraday_1m_standalone.py:315-328` `_open_trade` guard, `est_entry` vs `ref_swing_end_px`
- **Rule:** Entry must be `ABOVE selling low / BELOW buying high` (end-line guard), and the **end line must not be breached before entry** — if breached, don't enter: the traversal already handles it (re-arms to the next same-direction swing with fresh break counting; measured **93/262 days** had pre-entry traverses, e.g. `2025-08-08` 3 traverses at `09:42/09:59/10:47` before the `11:09` entry).
- **Bug was:** `est_entry = dbar["close"]` checked against `ref_swing_end_px`, but 1min direct entry fills at the **pivot level** (wick through the level = genuine fill). The level's side of the end line is a static structural fact; the close varies candle to candle → wick-break entries could be mis-classified (`skipped_end_line`) or a wrong-side level could sneak through on a friendly close.
- **Measured before fixing:** 262/262 entries had the level on the correct side, 0 `skipped_end_line` blocks ever fired → the bug never produced a wrong verdict on this dataset (latent only). (Earlier "guard never has data" claim was an instrumentation artifact — reading trade dicts instead of events.)
- **Fix:** `est_entry = float(ref_level)` — deterministic level-side check, wick-through fills stay valid, close noise removed. End-line breaches before entry remain the traversal's job (skip + traverse + fresh counting).
- **Verified:** in-memory before/after (close-based vs level-based guard) over the full CSV — **262 trades identical, 0 dropped, 0 SL/outcome changes**. `py_compile` ok.

### 6. ✅ RESOLVED — Broken level key is `float px` only

- **Location:** `intraday_1m_standalone.py:296,706-714` `broken_pivot_levels`
- **Rule:** `2nd break` must be on a **new pivot** — a double bottom at the same exact `px` formed at two different times is **two different pivots**. "Already broken" should mean *this pivot bar was broken*, not "this price was ever broken".
- **Bug was:** `broken_pivot_levels` was a `set of float px` — a fresh pivot at the same exact price (double bottom `24206.5` at `idx 91` and `109`) was blocked by `skipped_already_broken` though it was a new valid pivot → conservative entry delayed or never fired.
- **Fix:** key by `(px, pivot_idx)` — `if (brk["level"], piv.idx) in broken_pivot_levels` / `.add((brk["level"], piv.idx))` (`intraday_1m_standalone.py:710,714`). Same pivot retested → still deduped; fresh pivot at same price → counts. Works with item 4's clear-on-rearm (rearm wipes the sequence; this guards within a sequence).
- **Verified:** full-CSV before/after (`prev_pivot`, `min_sl_pts=13`) — 262 trades, stats identical except **1 recovered entry**: `2025-12-24` entry moved `11:34 @ 26216.0` → `11:21 @ 26212.2` (13 min earlier — fresh double-bottom pivot no longer blocked). 129 wrongly-swallowed break events eliminated (`skipped_already_broken` 6,484 → 6,355). Honest note: both the old and new 12-24 entries hit SL (`-1R`) — the fix is semantic correctness, not that trade's P&L.

---


### ✅ RESOLVED — 3 Sept 2026 second-swing B1 at 9:28 instead of 9:27 (V-reversal same-bar arm)

- **Symptom (user):** FS1 ends 09:25, swing 2 seeds 09:26 (RED, flow high→low). 09:27 broke the 09:26 high — a V reversal — so B1 belongs at 09:27, but it was marked 09:28.
- **Root cause:** the same-bar arm guard (added for the 30 Sept phantom) deferred ALL same-bar arming. At 09:27 the walker sealed the 09:26 high pivot (`H@23970.15` sealed during 09:27) and 09:27's high broke that pivot — a genuine V reversal — but the guard blocked the B1 to 09:28.
- **Discriminator vs the 30 Sept phantom:** the break direction vs the leg the seal terminated. 3 Sept: pre-seal leg = DOWN (red seed flow), break = UP → **opposite = V reversal → arm same bar**. 30 Sept 09:44: pre-seal leg = UP, break = UP → **same direction = flow extension → stay deferred**.
- **Tie-break (seed-colour rule):** on the arming bar BOTH extremes can break (3 Sept: V up +1.25 AND marginal low-dip −0.30). The seed colour decides: red seed flow high→low → the up-break is the B1, the same-direction down-break is flow extension (suppressed). Green seed mirrored.
- **Fix:** `firstswing.py process_bar` — capture `_pending_leg_dir` (walker leg at bar start); after break computation, if `defer_same_bar_arm` + pending + watch: opposite-direction break → arm SAME bar and suppress the same-direction break; else pending carries to next bar (30 Sept unchanged).
- **Verified:** 2026-09-03 swing 1 = `B start 11(09:26)/23958.15`, `B1 up @ 23970.15 bar 12 (09:27)` ✓; 2025-09-30 byte-identical (B1 down @ 09:45) ✓; swing-0 identical 270/270 ✓. Full-CSV: 4070 → 4153 swings, 59 days re-chunked (same-bar V-reversals now fire a bar earlier per this rule).

### ✅ RESOLVED — 30 Sept second-swing B1 at 9:44 (and 08-01 09:37)

- **Root cause:** NOT the extreme-break rule — it was **same-bar arming**: the 09:44 bar sealed H 24669.05 and the up-break fired in that same bar → phantom B1 up "breaking" the 09:43 high (a stamp shift inside the white 09:42→09:44 leg).
- **Wrong fix (tried + reverted):** re-anchoring B1 on the "latest sealed pivot" — it made B1 fire on minor internal pullback pivots (2025-08-01 09:37 broke neither the 9:33 extreme nor the 9:32 low).
- **Final fix:** B1 keeps the approved **extreme-break semantics** (`e_lo_prev`/`e_hi_prev`) + `defer_same_bar_arm` in firstswing.py — a Walker seal arms the engine from the NEXT bar, never the same bar. Applied to every post-first-swing engine site (server.py /api/swings/first_second, intraday.py ×3, intraday_1m_standalone.py).
- **Verified (chart endpoint):** 2025-09-30 B1 down @ 09:45 @ 24647.15 (broke the 9:42 low); 2025-08-01 B1 down @ 09:58 @ 24690.3 (broke the 9:32 low extreme — matches old approved behavior).


## ✅ Swing Engine — White Line Parity (CLOSED 2026-09-04)

> Trigger: *"all cuse of this disparity between flowline in the frontend which is great btw and between the backend stuff"* — the swing marks kept not matching the frontend white line.

### Verification ledger — all clean

| # | Test | Scope | Result |
|---|---|---|---|
| 1 | Walker parity — flowline.ts vs walker.py, every sealed pivot | 54,068 pivots / 270 days | Byte-identical. The white line itself is perfect |
| 2 | No stale duplicate engines — swing_engine.py is a pure re-export shim; all production imports come from firstswing.py | all of server.py, intraday.py, intraday_1m_standalone.py | ✓ single implementation |
| 3 | Endpoint equivalence — /api/swings/first_second vs whole-day chain (seg, conf, B1 marks, offset-corrected) | 268 days | 0 mismatches |
| 4 | Trading chain sync — _find_swing replica vs chart chain | 265 days | 0 mismatches |
| 5 | Swing-0 exemption — first swing untouched by the fix | 270 days | ✓ 270/270 identical |

### Findings — final dispositions (re-measured on the final engine)
#### Finding 1 — FLIP "phantoms" — ✅ RETRACTED (wrong yardstick)
- Original claim: 1,594/2,726 FLIPs (58%) fired with no white-line flip/seal (e.g. 2025-08-01 FLIP up @ 10:10).
- **Truth:** measuring against white-line flip events was wrong — same mistake as B1. The correct rule is **structure-extreme break**. Evidence: 2025-08-01 10:39 FLIP down @ 24772.4 broke the 10:35 seed-candle low (bar low 24769.3 < 24772.4) — user-verified on chart — plus 9 more examples, all seed-extreme breaks. FLIP = first leg failed, structure reversed. Genuine mark.
- Original note (superseded): FLIP break detection uses per-bar running extremes (e_hi_prev/e_lo_prev) — that IS the approved extreme-break mechanism.

#### Finding 2 — B1 internal pivots — ✅ RESOLVED (reverted interim rule, restored extreme-break B1)
- The 30% figure measured the interim "latest sealed pivot" B1 rule — reverted because it fired B1 on minor internal pullback pivots (2025-08-01 09:37 broke neither the 9:33 extreme nor the 9:32 low). Example from the interim rule: B1 up @ 10:19 broke internal H@24746.4 — never a real break.
- **Final fix:** see the RESOLVED entry above (extreme-break B1 + same-bar arm guard).
- Original claim kept for record: "chart's most recent white H pivot there is 24752.05, which was never broken."

#### Finding 3 — B2 / seg starts / chop targets — ✅ RESOLVED (re-measured on final engine)
- B2: **2,845/2,845** broken levels ARE chart white pivots (0 internal-only).
- Chop targets: **4,070/4,070** confirmations broke a chart white pivot (0 exceptions).
- Seg starts: seed-candle extreme **by design** — seed = last swing end + 1 candle (user confirmed intentional; it fixed the second-swing marking issues). Not a bug.
- Original analysis below kept for record.

The single root cause behind Findings 2 & 3: every post-first-swing SwingEngine carries its own private WalkerEngine seeded at the swing start (fresh k=0, seed pivot from that bar's color). The chart's white line is the full-day walker seeded at 09:15. Two different books ⇒ two different "latest sealed pivot" levels. The engine can't see chart pivots formed before its swing started, and its opposite-side reference pivot is the seed bar's extreme instead of the chart's last pivot (30 Sept: chart L = 09:41 @ 24645.25 vs internal L = 09:42 low @ 24647.15). So "broke which zigzag?" has two different answers depending on which white line you ask — and you only see one of them.

Note: this also affects chop targets (chop = break of latest_sealed_high/low) — some confirmations happen on internal levels invisible on the chart.

### Superseded fix plan (NOT implemented — kept for record)
Kill FLIP phantoms — extend the white-pivot re-anchoring to the FLIP paths, but with chop-precedence (my earlier naive test showed FLIP preempts chop-confirm and collapses days — the flip check must yield to a same-bar chop confirmation). Fixes ~1,594 phantom marks.
One white line per day — seed each post-first-swing engine's pivot book (latest_sealed_high/low, e_hi_pivot/e_lo_pivot) from the full-day chart walker at the swing seed, so B1/B2/chop all reference levels that actually exist on your white line. Fixes Findings 2 & 3 at the root.
(Optional) Snap seg starts to white pivot vertices so the yellow line's origin is always a white-line point.