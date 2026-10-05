# ENTRY-1 experiment - tried, measured, do not repeat

Date: 2026-10-02. Branch: agents/champion-reality-audit.

## The idea

The initial stop is placed on the leg extreme from the swing start up to the
entry bar. C16 made that the shipping rule and called the previous one
(a structural pivot, `pivot_rule="origin"`) a lookahead. Two follow-ups:

- **ENTRY-1 (HTF only)** - exclude the entry bar from the leg scan, so the
  entry's own high or low can never set its own stop. `pivot_rule="leg_no_entry"`.
- **ENTRY-1 (both legs)** - do the same on the 15m leg as well, which needed a
  separate knob `exp_ltf_no_entry` plus `exp_causal_sl=1` to reach the LTF stop
  source at all.

## Results - measured through the registry path, each book using its own params

| book | n | gross | net |
|---|---|---|---|
| RETRO (`origin`) | 500 | +445.22 | +325.78 |
| CAUSAL (`leg`) | 499 | +355.72 | +239.12 |
| ENTRY-1 HTF only | 500 | +445.19 | +325.75 |
| ENTRY-1 both legs | 495 | +322.18 | +215.14 |

## What it actually showed

**ENTRY-1 HTF-only is the origin book wearing a different name.** 0.03R apart
over 500 trades, with 497 of 500 stops identical. It is not a third answer to
the stop question; it is the first one again.

**ENTRY-1 both legs costs 110R of net.** -215.14 against -325.75. Rejected on
the numbers; not added to the dropdown.

**Both flags are no-ops unless `exp_causal_sl=1`.** With it at 0 the LTF leg
reads `sig["swing_start_px"]`, which `pivot_rule` already sets, so
`exp_ltf_no_entry` has nothing to act on. This is why the first attempt at
"apply it to both legs" measured zero difference and looked like an inert knob.

## The correction to the C16 audit

The origin pivot is **causal**. `backtest/tests/exp_origin_lookahead.py`
rebuilds the swing chain from candles truncated at each swing's own
confirmation and finds `seg.start_px` identical every time, 40 of 40. The
origin price was knowable at the entry bar.

What C16 changed was the risk denominator, not knowledge of the future. A
structural pivot sits closer than the leg extreme, so the denominator is
smaller and R inflates. That is worth fixing on its own terms, which is why
`pivot_rule="leg"` ships. But describing it as lookahead overstated it, and the
+445R-against-+355R gap is not a phantom profit - both books are real and place
the stop differently.

## Do not repeat these

- Do not try "exclude the entry candle" again. It is measured on both legs.
- Do not re-argue whether the origin stop is lookahead. It is tested.
- Do not compare gross against net and call it a disagreement. Gross is +445,
  net is +325; the difference is costs. Both were right.
- Do not measure by calling `unified.simulate_htf_ltf_streak_halt` directly and
  then publishing the number. `exp_partial_r` does not exist on that signature -
  the harness injects it - and the harness also rewrites the `exp_causal_sl`
  branch (t_c13), so raw and harness are different code paths for that branch.
  A direct-call number is not the shipped number. This cost one wrong pin here.
