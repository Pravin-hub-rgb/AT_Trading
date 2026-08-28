# The Story of First Swing Detection

## The Market Opens

Every day at 9:15, the market opens with energy. Prices spike, dip, and explore. Within minutes, a natural range forms — a ceiling and a floor. But inside that opening range, a story is beginning. The first swing of the day.

Our job is to find that swing. Not with magic, but by watching how price behaves from the first bell through the morning drift.

---

## What We're Looking At

**The range** is simply the highest high and lowest low printed so far. Think of it as the market's playground — the boundaries it's working within.

**Pivots** are the little bounces and dips along the way. They're markers, not the main event.

**The swing direction** is either up (buying) or down (selling). We figure this out by watching which way price breaks out of the opening range.

---

## How It Works

### The Opening Act (9:15 – 9:29)

The day starts with no opinion. We watch the first bars print highs and lows, learning where the market wants to trade. But here's the thing: the opening minutes are noisy. A spike at 9:16 doesn't mean the market is suddenly bullish.

So we have a rule: **no swing is declared before 9:29**. But that doesn't mean we're not paying attention. We ARE tracking every break, every extreme, every pivot. We're building the case. We just don't announce the verdict until the opening drama settles.

If the engine sees a swing forming before 9:29, it holds that thought. It waits. At 9:29 sharp, it makes the call based on everything it observed.

### Two Cases: Same Direction vs Reversal

This is the core of the system. There are only two possibilities from the open.

**Case 1: Same Direction**

The market opens and keeps going the same way. It doesn't reverse — it just continues.

For a **selling swing**: price drops from the opening high, breaks the low once, then breaks it again for a new low. Two breaks of the same extreme in the same direction. That's the signal: the market is serious about selling.

For a **buying swing**: price rallies from the opening low, breaks the high once, then breaks it again for a new high. Two breaks of the same extreme in the same direction. That's the signal: the market is serious about buying.

The rule: **same side needs two breaks**. One break could be a fakeout. Two breaks proves the move is real.

**Case 2: Reversal**

The market opens, moves one way, then turns around and goes the other way.

For a **reversal to buying**: price drops from the opening high, makes a low, then reverses upward and breaks the opening high. Just one break of the opposite extreme is enough. The market has clearly flipped.

For a **reversal to selling**: price rallies from the opening low, makes a high, then reverses downward and breaks the opening low. Just one break of the opposite extreme is enough. The market has clearly flipped.

The rule: **opposite side needs only one break**. The reversal itself is the proof.

### The Trigger

Once the direction is confirmed (by either case), the swing is triggered. The broken extreme level is frozen as the sustain reference. From that moment, the swing needs one more thing: confirmation.

### The Confirmation

At this point, we know the direction and we've triggered the swing. But we need proof that the move is real and will last. There are two ways to get that proof.

**Chop confirmation:** After direction is confirmed, if price breaks any previous pivot in the opposite direction, that's chop. For a selling swing, if price rallies back above a previous pivot high, that's chop. But the swing still counts — the market is just chopping around before the real move.

**Sustain confirmation:** Price holds beyond the frozen broken level for 7 consecutive bars. For selling, that means 7 closes above the low that was broken. Each time a new lower low prints, the count resets — because that bar belongs to the move down, not the hold up. But once the broken level is established and price stays above it for 7 bars, we have sustain. The market is respecting the level.

The final confirmation is the SUS or FS marker. That's the moment the swing is declared and frozen.

---

## The 9:29 Rule

The opening range is treacherous. A swing that looks confirmed at 9:22 might vanish by 9:28. So everything before 9:29 is treated as preliminary. We track it, we count it, we build the case — but we don't declare.

At 9:29, the engine reviews everything:
- Did the swing survive the morning chop?
- Did the market reverse hard enough to kill it?
- Is there a clear direction with confirmation?

If yes, the swing is declared. If no, it's discarded. No swing exists before 9:29. That's the rule.

---

## What Makes a Swing?

**There is no minimum size.** A swing of 0.5 points counts just as much as a swing of 50 points. The engine doesn't care about percentage moves or point thresholds. If the market shows direction, confirms it through chop or sustain, and respects the time guard — it's a swing. Big or small, the rules treat them the same.

The only built-in minimums are:
- The range must be at least 20 points before zone rules activate
- Sustain requires 7 bars of consistent behavior

But there's no "swing must be at least X%" rule. A tiny move that meets the confirmation criteria is still a valid first swing.

---

## The Ending

When the swing confirms, three things freeze:
- **Start**: the counter-extreme from the opening range
- **End**: the deepest extreme reached after confirmation
- **Type**: chop (purple SUS marker) or sustain (cyan FS marker)

The story ends there. The next swing will have its own tale, but the first swing is history — declared, frozen, and ready to trade.
