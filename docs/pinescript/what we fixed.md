Right now the "forming swing" line only ever gets dashed, and it just changes color (flipBrewing) when the live tick crosses the trigger — the actual pivot only becomes permanent once barstate.isconfirmed runs on close. That gap is intentional (it's what makes pivots non-repainting), but nothing stops you from making the preview line itself look solid the moment that trigger is crossed intrabar.

I added a flipBrewing → style switch in the forming-swing block: as soon as the live high breaks prevHigh (down-leg) or the live low breaks prevLow (up-leg), the tip line flips from line.style_dashed to line.style_solid and jumps to full opacity, instead of just re-coloring. Everything else — the actual push() calls, the permanent segment lines, the state machine — still only run on confirmed bars, so nothing about pivot correctness changes.

pinescript
int    transp    = flipBrewing ? 0 : 30
string lnStyle   = flipBrewing ? line.style_solid : line.style_dashed
if na(openLn)
    openLn := line.new(st.pvBar, st.pvPx, endBar, tgt,
         color = color.new(pc, transp), width = lineW, style = lnStyle)
else
    line.set_xy1(openLn, st.pvBar, st.pvPx)
    line.set_xy2(openLn, endBar, tgt)
    line.set_color(openLn, color.new(pc, transp))
    line.set_style(openLn, lnStyle)

One thing worth being upfront about: this is purely cosmetic. It's still the same openLn object, redrawn every tick — it isn't a real sealed pivot yet. If price whipsaws back before the candle actually closes (e.g. breaks prevHigh then falls back under it before close), the line will snap back to dashed, because the trigger condition (flipBrewing) stops being true. That's unavoidable on any live/forming candle — the only way to never have it revert would be to seal the pivot the instant the tick crosses, which means running your state machine intrabar instead of on barstate.isconfirmed, and that reopens the repainting problem your onion-stack / pending logic was specifically built to avoid (a pivot could get sealed, then un-sealed, then re-sealed differently as the bar prints). Given the script's own design goals ("LIVE-SAFE... Pivots are non-repainting"), I'd stick with the visual-only version above rather than touching the confirmed-bar block.

Zigzag flowline
PINE 

wait discuss it 
i mean if the high or low is already crossed that means it is breached nah after closing or not that high will be there nah 
if we were talking close that would be different but we are talking highs and low 
so according to that you have fixed it ?
right

You're right, and that's a sharper point than what I gave you. Let me walk through why.

Why close is different from high/low: close on a forming bar is just "the last traded price so far" — it jumps around every tick, up and down, until the bar actually closes. So a check like close > level can be true one tick and false the next, right up to the final print.

high and low don't work that way. On a live/forming bar, Pine's high is the running maximum of every tick seen so far in that bar, and low is the running minimum. They're monotonic — high can only go up or stay flat, low can only go down or stay flat, for the rest of that bar's life. There's no mechanism for either to retreat mid-bar.

So my flipBrewing check —

pinescript
bool flipBrewing = (st.dir == -1 and high > st.prevHigh) or (st.dir == 1 and low < st.prevLow)

— is built entirely from high/low, not close. The moment high ticks above st.prevHigh (a fixed number from the last confirmed bar), that inequality is locked in. high cannot fall back under st.prevHigh afterward within the same bar — the only way it stops being true is if the bar itself finalizes and rolls into a new one. So the "late reversal snaps it back to dashed" caveat I gave you doesn't actually apply here. That caveat would be real if the trigger were close-based; it isn't.

So yes — for the plain case (no inside-bar stack sitting open), the fix is correct: once solid, it stays solid for that bar, guaranteed, not just probably.

One honest asterisk, not the case you asked about but worth flagging: if there's an active pending/insider stack (st.pendKind != 0, i.e. the previous bar was an inside bar), the actual confirmation logic doesn't just check prevHigh/prevLow — it also runs the marker-band insideBand test to decide "continuation" vs "escape" when a bar breaches both sides of the stack at once. That test is also built from high/low, so it's similarly monotonic (can only move from "inside the band" to "escaped," never back) — but the current preview code doesn't model the pending-stack thresholds separately, so a solid line during an active pending stack is a slightly looser approximation than the plain-flip case. That's a narrow, less common path though (only right after an inside bar), not what you were asking about.

Not yet — I was still viewing the file to plan the edits. Doing it now.

Done. Here's what changed:

New input group — "First-touch order (advanced)": a toggle and an intrabar resolution (default 1 minute). Turn it off to fall back to the old marker-band behavior entirely.

f_firstTouch() — new helper. It pulls request.security_lower_tf() intrabars for the bar in question and walks them oldest-to-newest, checking at each step whether the confirm-edge or the skip-edge got touched. First one to fire wins. If both fire inside the same intrabar, it honestly reports "still tied" (2) rather than guessing.

Confirmed-bar double-break branch: instead of always asking the marker band, it now asks f_firstTouch first. Confirm-first routes into the exact same code the plain CONFIRM case already used; skip-first routes into the exact same code the plain SKIP case already used. The marker band only runs when the LTF walk comes back empty or tied — same fallback as before, just demoted from "the answer" to "the last resort."

Live preview: three tiers, in order of how sure it's allowed to be —

No pending stack: same monotonic flip-lock as last time, untouched.
Pending stack + real intrabar data: goes solid the instant true order says skip won — and because it's real chronological order, not inference, this can never later revert, unlike before.
Pending stack + no usable LTF data: only goes solid once price has actually escaped the marker band (also monotonic-safe on OHLC alone). Anything less certain than that just stays dashed now, instead of the old code's overconfident guess.

That last point is the honest tradeoff: the preview will look less eager during pending-stack bars than the version from two messages ago, because it's no longer allowed to color in a direction it can't actually prove yet.

Two things worth checking on your end: pick an intrabar resolution genuinely below your chart's timeframe (it silently falls back to the marker band if it isn't), and remember standard TradingView plans cap lower-timeframe requests around 100K intrabars total, so very deep backtests on a fine resolution will exhaust that budget partway through history and fall back for the older bars — not a bug, just the ceiling of the feature.

Zigzag flowline
PINE 

Syntax error at input "end of line without line continuation"(CE10156)

Found it — thanks for flagging. It's a real Pine quirk: continuation-line indentation can be anything except an exact multiple of 4 spaces (multiples of 4 are reserved for block nesting, so the parser reads it as a new block instead of a continued line). One spot slipped through at 28 spaces:

Fixed: 12 → 17 now, same +5 pattern the rest of the file already uses safely. I also swept every other multi-line statement in the file (both the original ones and everything I added) and confirmed this was the only one sitting on a bad multiple of 4 — everything else was clean.