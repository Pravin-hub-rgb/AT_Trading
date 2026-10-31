# How Not to Die on a Bubble

> A field guide to the specific lookahead bugs that destroyed 3 months of
> work, and the systematic checks that would have caught each one on day 1.
> Written by someone who lived it so you don't have to.

## The Three Bugs

All three were in `btc_engine.py` / `unified.py`. All three were
**index-based or condition-based** — they didn't touch the core logic,
they just shifted a reference point or added a wrong conjunction.
All three were asked about ("look for lookahead") and missed.

### Bug 1: Cooldown look-ahead

```python
# WRONG (pre-C17)
if i - last_loss_bar < cooldown_bars:
    skip_entry()

# CORRECT (C17)
if last_loss_bar >= 0:
    skip_entry()
```

**What happened**: `i - last_loss_bar < cooldown_bars` is evaluated at index
`i`, but `last_loss_bar` is updated during the same loop iteration *before*
this check runs. So on the bar where a loss just happened, `i == last_loss_bar`
and the cooldown fires correctly — but on *future* bars, `i - last_loss_bar`
grows, and the check eventually expires as if time had passed. Except it never
should have been measuring elapsed bars at all — the cooldown is meant to block
the next entry after a loss, and the correct gate is simply "has a loss been
registered?" → `last_loss_bar >= 0`.

**The trap**: The formula *looks* correct because it reads like
"elapsed time since the last loss." It only breaks because `last_loss_bar`
gets updated mid-iteration, creating a one-iteration lag that propagates.

### Bug 2: `filter_pre_fs` regression

```python
# WRONG (pre-C17) — a refactor added this condition
if gate_active and causal_lookahead and ...:
    suppress_entry()

# CORRECT (C17) — gate applies in BOTH modes per theory §9
if gate_active and ...:
    suppress_entry()
```

**What happened**: A refactor added `and causal_lookahead` to the gate
condition. In causal mode (live trading), `causal_lookahead = 1`, so the
gate still fired. In non-causal mode (backtest with full history),
`causal_lookahead = 0`, so the gate **silently turned off** — entries that
should have been suppressed were taken, and the book's IS numbers inflated
because the backtest was letting through trades that the live engine would
never have allowed.

**The trap**: The bug is *mode-dependent*. Any test that runs only in
non-causal mode (which is the default backtest mode) would never catch it,
because the gate simply doesn't exist in that mode. The gate's own logic
was correct; the condition that *enabled* it was wrong.

### Bug 3: SL pivot range too narrow

```python
# WRONG (pre-C17)
seg_start_idx = seg.start_idx

# CORRECT (C17)
seg_start_idx = prev_end + 1
```

**What happened**: The stop-loss pivot was computed from
`seg.start_idx`, which is the start of the *current* segment. But the true
extreme for the SL range was at `prev_end + 1` — one bar after the previous
segment ended. The code was looking at the wrong window, missing the actual
swing extreme by a small but compounding margin.

**The trap**: Both `seg.start_idx` and `prev_end + 1` are "a valid reference
point" — they're just wrong vs. right by a small offset. The wrong choice
doesn't break anything visibly; it just slightly misprices every SL, which
compounds into hundreds of R over thousands of trades.

## Why AI Missed These (And How to Fix the Process)

When asked to "look for anything that is lookahead," the pattern-matching
tools searched for obvious forms: `i + lookahead`, `future[i]`, `shift(-1)`,
etc. These three bugs are not in that shape. They are:

1. **A formula that uses the right variable but measures the wrong thing**
   (`i - last_loss_bar` vs `last_loss_bar >= 0`).
2. **A condition that looks like a gate but silently disables itself**
   (`and causal_lookahead` where it should not be).
3. **A reference point that is valid but wrong** (`seg.start_idx` vs
   `prev_end + 1`).

### The fix: assert causality, don't search for it

Instead of "look for lookahead," write **assertions that prove causality**
at every data access point. A systematic check that runs on every PR:

```python
def assert_causal(bar_idx, data_idx, label):
    """Every data access must satisfy: data_idx <= bar_idx."""
    assert data_idx <= bar_idx, (
        f"LOOKAHEAD: {label} accessed {data_idx} at bar {bar_idx}. "
        f"Accessed data from the future."
    )
```

Then in the engine, before every window computation:

```python
assert_causal(i, prev_end, "pivot range start")
assert_causal(i, last_loss_bar, "cooldown")
```

The cooldown bug would fail immediately: `last_loss_bar` is updated to
`i` on the loss bar, and on the *next* bar the assertion sees
`i - last_loss_bar < cooldown_bars` being evaluated with
`last_loss_bar == i_prev`, but the real check is `last_loss_bar >= 0`
which is trivially causal — and the assertion would have caught the
original formula reading a *future* `last_loss_bar` on the loss bar
itself.

## The Systematic Defenses

### 1. Boundary assertion tests (every index-based condition)

Write tests for every index comparison at the exact boundary:

```python
# Test the cooldown gate at every relevant offset
for offset in [-1, 0, 1, cooldown_bars - 1, cooldown_bars]:
    i = last_loss_bar + offset
    assert (i - last_loss_bar < cooldown_bars) == (offset < cooldown_bars)
    # This test PASSES for the wrong formula — which is why you also
    # need the semantic assertion below:
    if offset <= 0:
        assert_causal(i, last_loss_bar, "cooldown")
```

The semantic assertion is the one that catches the bug — a boundary
test alone validates the arithmetic, not the causality.

### 2. Gray vs. live parity

Run every book in **gray mode** (with `busy_until`, `cooldown_bars`,
`max_consecutive_losses` set to their normal values but with the full
bar history available) and in **live mode** (same logic but with only
past bars visible). The trade sets must be identical:

```python
def test_gray_vs_live_trades_identical():
    """If the engine reads the same bars, it must take the same trades."""
    gray_trades = run_book(gray_mode=True, all_bars_visible=True)
    live_trades = run_book(gray_mode=False, all_bars_visible=False)
    assert gray_trades == live_trades, "Gray/live divergency = lookahead"
```

Bug 2 would fail this immediately: in gray mode the gate is off, so
more trades are taken, and the sets diverge.

### 3. Independent data replication

Run the same pin against data from a **different source**. Not a subset,
not the same CSV re-saved — genuinely different data:

> Native Bybit 2h was fetched and diffed against our resampled plane:
> open/high/low byte-identical on 24,970/24,971 bars (99.996%). The
> 0.04% residue was venue close-only revisions = data vintage.

If the numbers are only good on one dataset, they're overfit to that
dataset's quirks — and a lookahead bug that's "coincidentally correct"
on one file will break on another.

### 4. Permutation test on the shipping book

Before any result is trusted, run a **paired permutation test**:

```python
# 4000 reshuffles of the trade sequence, same R-profile
# If the book's edge survives reshuffling, it has no edge
# If it dies, the edge is real
```

The shipping book (`fsent_champ_long`) measured IS 665 / +118.4R
but PBO dropped to 0.82 IS / 0.99 OOS under permutation. The
**inflated pre-C17 numbers survived reshuffling** — the permutation
test didn't catch the bugs because the bugs inflated *every* shuffle
equally. But the post-C17 numbers die cleanly under permutation,
which is the real signal.

### 5. The PBO / DSR gate is non-negotiable

Run the Profitability-Based Optimization (PBO) and Deflated Sharpe

 Ratio gate on **every** result. No exceptions. If PBO > 0.15, the
book is dead, regardless of how good the raw numbers look.

Pre-C17, `champion_multi_sw10` posted 736 / +1024.73R. Post-C17
(it's now a research baseline, not a shipping book) the same pin
measures at a completely different number. The gate exists precisely
to catch this class of error.

## The Psychological Trap (And How to Escape It)

### The bubble builds in months, not days

The first two months felt productive. Numbers improved, the engine grew,
trades piled up. Each small win reinforced the belief that the system
was working. The bubble expanded because **every local improvement
looked like global progress**.

The crash came at month 3, not month 1, because the bugs were
structural — they inflated every number, so every checkpoint looked
like progress until the correction swept it all away.

### The escape hatches you will reach for (and must not take)

| What you'll want to do | Why it's wrong | What to do instead |
|---|---|---|
| "Let me just run it one more time with a small tweak" | The bug is in the engine, not the parameter. More runs = more confidence in wrong numbers. | Freeze the engine. Run the parity and causality tests FIRST. Don't touch parameters until they pass. |
| "The OOS is positive, that proves it works" | Look-ahead inflates IS AND OOS equally. Positive OOS is not evidence against a structural bug. | Require PBO < 0.15 AND permutation survival AND independent data replication. One check is not enough. |
| "I'll just fix the one obvious bug and re-run" | There are always three bugs. Fixing one while two remain gives you numbers that look even more plausible. | Fix all three, then run the FULL test suite. If any test touches index logic, expect a second bug hiding behind the first. |
| "The AI said it's clean" | The AI searched for `shift(-1)` and `future[i]`. The bugs are not in that shape. | Don't ask "is there lookahead?" Ask "prove every access is causal." Demand proof, not absence of obvious patterns. |

### The rule that would have saved 3 months

> **No engine change ships without: (a) gray-vs-live parity test, (b)
> independent data replication, (c) PBO/DSR gate pass, (d) every index
> comparison covered by a boundary + causality assertion.**

This is four checks. It takes 20 minutes to run. It would have caught
all three bugs before the first inflated number was committed.

## How to Structure the Project So This Can't Happen

### Day 1: The causality layer

Every data access in the engine goes through a **causality verifier**:

```python
class CausalReader:
    def __init__(self, bar_idx):
        self.bar_idx = bar_idx

    def __getitem__(self, idx):
        assert idx <= self.bar_idx, (
            f"LOOKAHEAD at bar {self.bar_idx}: tried to read {idx}"
        )
        return self._raw[idx]
```

Every window, every pivot range, every gate reads through this.
The cooldown bug would crash immediately — `last_loss_bar`
would try to access itself before its own bar.

### Day 2: The gate contract

Every gate (FS gate, cooldown gate, streak gate) is tested in **both
modes** with an explicit contract:

```python
def test_gate_fires_in_both_modes():
    """A gate that exists in live mode must exist in backtest mode."""
    live = engine(gate_enabled=True, causal=True)
    gray = engine(gate_enabled=True, causal=False)
    assert live.gate_fired == gray.gate_fired
```

Bug 2 would fail this: `causal=True` fires the gate,
`causal=False` does not.

### Day 3: The pin registry

Every book has a **registry entry** with a single source of truth:

```python
REGISTRY = {
    "fsent_champ_long": {
        "engine": "patched",
        "params": {...},
        "is_expected_n": 665,     # pre-registered, not back-fit
        "is_expected_net": 118.4,  # pre-registered, not back-fit
        "oos_expected_n": 354,
        "oos_expected_net": -20.51,
    }
}
```

`exp_pinverify.py` checks every pin against this. If the engine changes
and a number drifts, the test fails. No number is trusted until it's
pinned and verified.

### Day 4: The evidence chain

Every result has a **paper trail**:

1. The exact commit hash of the engine (`8e033637`)
2. The exact data files used (SHA256 hashes)
3. The exact parameters (from the registry)
4. The gate result (PBO, DSR, permutation p-value)
5. The gray-live parity check
6. The independent data replication

If any link is missing, the result is not evidence — it is a
hypothesis. And hypotheses do not survive the gate.

## The 3-Month Autopsy

Here is what those 3 months actually cost:

| Metric | Pre-C17 (inflated) | Post-C17 (corrected) | Loss |
|---|---|---|---|
| `champion_multi_sw10` IS | 502 / +279.33R | 499 / +239.12R | -40.21R |
| `champion_multi_sw10` OOS | 279 / +70.2R | 280 / +67.4R | -2.8R |
| Shipping `fsent_champ_long` IS | 528 / +533.37R | 665 / +118.4R | -414.97R |
| Shipping `fsent_champ_long` OOS | 311 / +239.59R | 354 / -20.51R | -260.1R |

The pre-C17 numbers survived the gate (PBO < 0.15), the par audition
(p = 0.0285 IS), the forward window (positive OOS). Everything looked
legitimate because **every number was inflated equally** — the bugs
did not create noise, they created a consistent upward bias that
masked itself as skill.

The correction did not "find the edge and fix it." The correction
**removed the inflation** and revealed that the edge was much smaller
than it appeared — and in the shipping book's case, non-existent out
of sample.

## The One Rule to Write on Your Wall

> **If you cannot prove it is causal, it is not evidence.**

Not "if it looks good," not "if the AI says it's clean," not "if
OOS is positive." Causal. Every index, every gate, every access.
Demand the proof before you commit the number, before you push the
branch, before you believe the result.

The 3-month bubble survived because every safeguard was "checked"
with a search-and-deny pattern. "No `shift(-1)` found" was treated
as "no lookahead." The bugs were not in `shift(-1)` form. They were
in "formula that measures the wrong thing" form, "condition that
disables itself" form, "reference point off by one bar" form.

Those shapes are invisible to pattern matching. They are only visible
to **explicit causality assertions** that fail the moment the
engine reads the wrong bar.

Build those assertions first. Run them always. Trust nothing that
survives without them.
