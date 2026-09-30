# P101 - HTF GATE LOOKAHEAD AUDIT. All three findings, verified in v19.

Branch: agents/champion-reality-audit
Date: 2026-09-30.

`reality of champion.md` flagged three unaudited findings in the HTF gate
path. They are not unaudited. They were found on 2026-09-17, fixed, and
re-verified in source on 2026-09-26. This note confirms the fixes are
present in the v19 champion and measures the one residual.

## THE THREE FINDINGS - ALL FIXED, ALL PRESENT IN v19

| id | lookahead | fix | in v19 |
|---|---|---|---|
| C14 chop regime gate | up to 45 min | `candle_ts_htf_close=[t+3600]`, `bisect_right(candle_ts_htf_close, ts+900)-1` | L287, L292 + 5 more sites |
| C15 HTF window gate | up to 60 min | `if not (s + 2700 < bar_ts <= e + 2700): continue` | L569, union branch L543 |
| C12 streak counter | outcome lookahead | `halt_skip_next`, counter updated after `r_multiple` | L570-583, L710-723 |

`new bugs.md` line 29 records the prior ruling: "no backtest lookahead
bug remains". Source inspection confirms it for v19.

## THE ONE RESIDUAL, MEASURED

C14-narrow (`new bugs.md`:573) is a separate, accepted finding:
`ext_stop_r` normalises the extension distance against `pe`, the HTF
window's stored entry price, which is the 1h bar's close. For 15m bars
inside that same 1h window the 1h close has not happened yet.

The doc accepted this as a filter, not a trigger, and claimed no
measurable effect on outcomes. Measured on the champion, IS:

    A as-is (residual present)      n=500  net=+325.78R  PF=2.384
    B ext_stop filter disabled      n=503  net=+327.15R  PF=2.387

Three trades and +1.4R. The doc's claim holds. The residual is worth
+1.4R of optimism and nothing more.

Note the champion runs `ext_stop_r=3.0` where the v18 default is 1.5.
A more permissive threshold admits more signals, so the residual gets
slightly more room to act. The measurement above already uses the
champion's own 3.0, so it is accounted for.

## RULING

The champion is not lookahead-dependent. Nothing here reduces +325.8R.
The three gate fixes are in the shipped code path, and the fourth item
is a measured 1.4R.

What remains open in `new bugs.md` (C1-C5, C7, C11, H3-H11, L1-L8, M1-M11,
P1, P2) is live-execution and operational. The doc states these carry
capital risk but zero effect on backtest numbers. That is the right
place to look next, and it is a live-trading question, not a
backtest-validity question.