# Experiment Log — All Tests (Pass & Fail)

> Every experiment ever tested. If you think of something, check here FIRST.
> Date tested, result, and why it died. No repeats.

---

## DEAD — Do Not Repeat

| Date | Idea | What we tried | Result | Why it died |
|---|---|---|---|---|
| 2026-09-14 | Entry quality filters | Doji filter, entry candle min, swing age max | DEAD | All 5 filters destroyed trades. First-swing entries are the edge. |
| 2026-09-14 | B2-only on multi | Force multi to only use B2 intervals | DEAD | Multi needs FLIP overlaps for coverage. B2-only = single. |
| 2026-09-14 | Hour-of-day filter | Block entries during specific hours | DEAD | No hour is consistently bad. Edge is structural, not temporal. |
| 2026-09-14 | Skip-first-swing (v1) | Skip first same-direction swing, enter on next | DEAD (−189R) | Exp 19: mechanism confirmed (97% of SLs = next opposite swing) but remedy enters too late — 41/75 moved winners die. |
| 2026-09-15 | Skip-windows after loss | Skip first N HTF windows opened after loss | DEAD | skipwin1: −1.1R, skipwin2: −26.1R. Recovery trades live in the next window. |
| 2026-09-15 | Skip-windows after halt | Same but only after 3 consecutive losses | DEAD | skipwinhalt: +102.6R (hurts multi −223R). Same problem — blocks recovery. |
| 2026-09-16 | Partial exits on multi | Re-enter at 0.5R on partial SL hit | DEAD | Partials convert 82 losses→wins via halt cascade but 55 extra trades = noise. No-partial wins. |
| 2026-09-17 | Partial_r sweep (1.0-5.0) | Test different partial R levels | ALL DEAD | partial_r=0 (no partials) = +325.8R best. Partials are dead on multi. |
| 2026-09-17 | Curfew on kings | Block entries during specific hour ranges | DEAD | No hour is consistently bad on kings. Tested 6-24h curfews, all dead. |
| 2026-09-18 | Second-swing conviction trail | Tighten trail at 2nd same-swing B2 | DEAD (−63.6R) | Exp 22: mb50 confirmation lag is PROTECTIVE — filters shake-outs. Slowness is a feature. |
| 2026-09-18 | Close-confirmed initial SL | Wait for close beyond SL level before entering | DEAD (−6.3R) | Exp 20: wick gain eaten by worse close-through fills + killed winners. |
| 2026-09-18 | Mark-history entry autopsy | Use mark features as quality filter | DEAD | FLIP entries 3.7× per-trade vs B2. No actionable bucket found. |
| 2026-09-18 | Sweep-and-reclaim qualifier | Require sweep below prior low before entry | DEAD | Volume destroyed (41-186 trades). Zero loss-predictive power. |
| 2026-09-18 | 1h momentum agreement | Only enter when 1h agrees with direction | DEAD (−55.2R) | DD better but gross down. Too restrictive. |
| 2026-09-19 | B3 structure confirmation | 3rd pivot break as entry confirmation | POTENTIAL but deferred | 206t +278.6R fine. Low trade count. User deferred decision. |
| 2026-09-20 | Wage-24 on lb30 | 24h wage gate on production base | DEAD on lb30 (−11.3R) | Helps A4 (+19.8R) but hurts lb30. Base-dependent, not universal. |
| 2026-09-20 | Wage × ext anti-synergy | Mix wage with tight ext | DEAD | w24 wins only at ext=1.5. Once ext opens to 2.5, w0 beats w24 by 52R. |
| 2026-09-21 | Skip-first-swing (v2) | Skip first LTF signal in each HTF window | DEAD (−8.3R on king) | First swing is where the edge lives. Wage gate handles fresh windows better. |
| 2026-09-21 | Funding rate filter | Skip entries when |funding| > 0.03-0.10% | DEAD (0 trades filtered) | Funding data too sparse (3/day), never hit thresholds during entry times. Max 0.11% only 2× in 3.7yr. |
| 2026-09-21 | LTF regime filter (fullstack) | chop15 band (55-61) + ATR ratio (≥1.4) + wage10 + swingpause + cd=0 | **ALIVE — NEW KING SINGLE** | +310.7R / DD 11.2 / NET/DD 27.7. Beats old king by +28.6R and −3.5DD. |
| 2026-09-21 | Trail tighten (exp_la4) | Tighten trail after MFE (1.5-5R) to 40-60% of peak | DEAD (delta −0.2R best) | All 15 configs flat. Swing trail already optimal. |
| 2026-09-21 | ATR trail (exp_la9) | Replace swing trail with ATR×k trail (k=1.0-3.0) | DEAD (−43R to −271R) | ALL configs catastrophically negative. Swing trail kills ATR trail. |
| 2026-09-21 | Volatility SL buffer | sl_buf_atr is already ATR-scaled; ext_stop_r swept in kingsweep | DEAD (already optimal) | sl_buf_atr=0.01×ATR14 IS volatility-adjusted. ext_stop_r=3.0 confirmed optimal. |
| 2026-09-23 | ADX>25 on 15m LTF | exp_adx_min 20/25/30 on champion/king/swingpause, IS+OOS | DEAD (champion dIS −137..−240 / dOOS −48..−113; swingpause OOS +20 but IS −60..−120 fails both-sides) | Old-lane +90.5 was a different trade list. Path-true kills it on every base. |
| 2026-09-23 | Session blocks 16-20 UTC | exp_only/skip_hour on champion/king/swingpause, IS+OOS | DEAD (only 16-20: dIS −145..−346; skip 16-20: dIS −74..−157; no both-sides pass) | Extends dead hour-of-day/curfew family. Period-level windows destroy coverage. |
| 2026-09-23 | 4h swing confirmation | exp_htf4_confirm with 4h swings synthesized from 1h (IS 392 / OOS 240 swings) | DEAD (dIS −66..−194 all bases; swingpause OOS +28.5 but IS −65.5) | 4h dir gate too coarse — cuts winners with the chop. 1h-momentum cousin already DEAD (−55R). |
| 2026-09-23 | v9 conditional HTF cap | exp_htf_extend_r=2.0 → v9 extend 16d→30d when HTF ≥2R at cut | DEAD (noise: champion dIS −6.2/dOOS −3.1; king −21.3/+7.7; swingpause −13.9/+5.3 — mixed signs) | Confirms old +0.5R noise. Never meaningful on v18 windows. |
| 2026-09-23 | htf_ltf v2 flip-break | exp_flip_break: LTF close must break HTF entry pe in direction | MARGINAL on single only (swingpause dIS +7.6 / dOOS +8.3, NET +29.6/+16.2 both-sides); DEAD on multi (champion dIS −189, king dIS −218) | Only both-sides pass of the 5, but ~8R/yr — below +30R/yr ship bar. Multi needs FLIP overlaps; continuation-only entries starve it. Keep flag for stack research; does not ship alone. |

---

## ALIVE — Adopted into Production Configs

| Date | Idea | What we adopted | Impact | Config |
|---|---|---|---|---|
| 2026-09-15 | Swing pause | After loss, wait for new 15m swing to confirm | +37.1R / −5.8DD (single) | All single kings |
| 2026-09-16 | No partial exits | Remove partial exits entirely | +84.3R on multi (no-partial wins) | All configs |
| 2026-09-20 | Wage gate (10h) | Skip entries in windows < 10h old | +65.3R / −3.5DD on king single | wage10_swingpause_wskip_single_sw10 |
| 2026-09-20 | IST-weekend skip (single) | Skip Sat+Sun entries on single | +42.8R / −5.2DD | wage10_swingpause_wskip_single_sw10 |
| 2026-09-20 | UTC-Saturday skip (multi) | Skip UTC Saturday entries on multi | +33.2R | utcsat_multi_sw10 |
| 2026-09-21 | sw10 (min_bars_1h=10) | Twitchier 1h swings, more signals | +117.4R vs sw20 on multi | All kings |
| 2026-09-21 | cd=0 with swingpause | Drop cooldown_bars (redundant) | 0.1R difference, cleaner config | wage10_swingpause_wskip_single_sw10 |
| 2026-09-22 | Causal SL | Replace retroactive swing_start_px with running extreme | −69R IS avg, +9R OOS avg (more honest) | All configs via `exp_causal_sl=1` |
| 2026-09-23 | F6 ER20 gate (15m) | Cut entries with Kaufman ER20 < 0.10 (or band 0.10–0.50) | DEAD (−180..−202 dIS, −7..−50 dOOS) | On OUR trade-list ER<0.10 is the #2 bucket (+107R, bigWin +163) — opposite of other-bot claim. Path-true kills champion/king/swingpause. §3f ER24-1h + this 15m/20 = both ER roads tombstoned. |
| 2026-09-23 | F1 runmag ≥2% | Cap running magnitude at 2% of price | DEAD (causal −108 dIS / −32 dOOS) | Raw +18 dIS is the `_gen_start` leak; exp_dir_causal=1 collapses it. Single flat (+0.2/+6.1 = noise). |
| 2026-09-23 | F7 stop width ≥2% | exp_risk_max_pct=2.0 | DEAD (−24.7 dIS / −48.4 dOOS) | Extends §3e risk-width family (1.0/1.5 already dead). Wide stops are survivors; cutting re-tightens the halt cascade. |
| 2026-09-23 | Live-snapshot runmag gate | exp_max_live_runmag using replay_live_state start_idx (the last open salvage path) | DEAD (champion 2.0: −24.2 dIS / −36.4 dOOS; 3.0/4.0 = noise; king 3.0 OOS +21 but IS −7.5 fails both-sides rule) | Trade-list bucket was net-neg (2%+: −9.9R bigW=2) but path cascade loses more downstream than the cut saves. Batch+causal ref still −108 dIS. No salvage gate remains open. |

---

## NOT YET TESTED — Ideas for Future

| Priority | Idea | Theory | Status |
|---|---|---|---|
| HIGH | Rebuild backtester with PersistentSwingEngine | Fix swing engine mismatch (Issue #1 on audit checklist) | CRITICAL for live |
| MED | Open interest filter | Skip when OI is spiking (distribution phase) | Not tested |
| MED | Correlation filter | Skip when BTC is highly correlated with equities | Not tested |
| LOW | Chart visualization | Plot HTF windows on chart for visual inspection | Not tested |

**Old-engine ports 2026-09-23** (5 candidates from v6/v7-v10/E5/v2 lineage): all path-true tested
IS+OOS on champion/king/swingpause — see DEAD rows above. flip-break MARGINAL on single only
(both-sides +7.6/+8.3, below ship bar); ADX, session, 4h-confirm, v9-cap all DEAD.
Harness: `live_stuff/tests/exp_oldengines_path.py`.

**Stale rows removed 2026-09-23** (already DEAD, contradicted rows above):
- LTF regime chop-band — REJECTED (ANCHOR_BASIS_AUDIT §3h; sw20 −33.7R)
- Trailing stop acceleration — DEAD (exp_la4 −0.2R best; trail-tighten family)
- Volatility-adjusted SL buffer — DEAD (sl_buf_atr already ATR-scaled)
- Funding rate filter — DEAD (0 trades filtered)

---

## Rules

1. **Check this log before testing ANY idea.** If it's in DEAD, don't test it again.
2. **Every experiment gets logged** — pass or fail, with date and numbers.
3. **"Base-dependent" means dead for us** — if it only works on one base, it's curve-fit.
4. **The first swing is sacred** — don't skip it, don't delay it. Entry at first B2/flip is the edge.
