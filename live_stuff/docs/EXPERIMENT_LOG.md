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

---

## NOT YET TESTED — Ideas for Future

| Priority | Idea | Theory | Status |
|---|---|---|---|
| HIGH | LTF regime filter (chop-band) | Skip entries when 15m is choppy (ATR5/ATR20 ratio, chop band) | Other bot testing |
| HIGH | Rebuild backtester with PersistentSwingEngine | Fix swing engine mismatch (Issue #1 on audit checklist) | CRITICAL for live |
| MED | Trailing stop acceleration | After X bars in profit, tighten trail faster | Not tested |
| MED | Volatility-adjusted SL buffer | Wider SL in high-vol, tighter in low-vol | Not tested |
| MED | Session-based trading | Only trade during high-volume hours (not hour-of-day filter, but session blocks) | Not tested |
| LOW | Funding rate filter | Skip when funding is extreme (>0.1%) | Not tested |
| LOW | Open interest filter | Skip when OI is spiking (distribution phase) | Not tested |
| LOW | Correlation filter | Skip when BTC is highly correlated with equities | Not tested |
| LOW | 4h confirmation | Require 4h swing agreement before entry | Not tested |
| LOW | Chart visualization | Plot HTF windows on chart for visual inspection | Not tested |

---

## Rules

1. **Check this log before testing ANY idea.** If it's in DEAD, don't test it again.
2. **Every experiment gets logged** — pass or fail, with date and numbers.
3. **"Base-dependent" means dead for us** — if it only works on one base, it's curve-fit.
4. **The first swing is sacred** — don't skip it, don't delay it. Entry at first B2/flip is the edge.
