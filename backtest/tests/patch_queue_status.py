import io
import re
import sys
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "docs" / "method" / "OPEN_RESEARCH_QUEUE.md"
t = p.read_text(encoding="utf-8")

# The dash in these headings is an EM dash, not a hyphen. Matching on "-" silently
# does nothing, which is what happened the first two times.
DASH = "\u2014"

P4 = (
    "### `[x]` P4 " + DASH + " sweep `cap_days` - **CLOSED 2026-10-10.** Swept "
    "3/7/10/14/21. 21 clears the negative half-year (+835.93R, 0 negative, against "
    "+680.52R at the default 10). The adjacent question - how long after a window "
    "OPENS you may enter - was a hardcoded literal and is now "
    "`method/WINDOW_FLOOR_AND_AGE.md`: raising it to 5400 adds +5 to +8R on every champ "
    "book, and only `champ_long` needs 7200 to clear its cell. **Neither is a new book; "
    "both refine a lever the loss-run cutoff already provides.**"
)
W1 = (
    "### `[~]` W1 " + DASH + " window duration as a feature - **ANSWERED 2026-10-10, not "
    "closed. `method/WINDOW_FLOOR_AND_AGE.md`.** Median window age at entry is 2.2-2.4 days "
    "on every book and flat; R per trade is NOT flat and moves 3x between age buckets, and "
    "the direction is OPPOSITE between families - the champ books earn most from young "
    "windows (1.46 and 1.82 R/trade in the first 36h) while `sig_multi` earns almost nothing "
    "there (0.53) and most from the oldest bucket (4.47 R/trade on 55 trades, 58% win). Age "
    "is a real feature with no single extractable rule. **NOT a candidate:** the strongest "
    "cell rests on n=55 and the buckets were chosen after the result existed, which is how "
    "`biasmom05` got killed. Closing it needs the treatment `mcloff` got - re-derive, then a "
    "period control - plus forward confirmation of the direction."
)

t, n1 = re.subn(r"### `\[ \]` P4 .*?(?=\n\n)", lambda m: P4, t, count=1, flags=re.S)
t, n2 = re.subn(r"### `\[ \]` W1 " + DASH + r" window duration.*?(?=\n\n)",
                lambda m: W1, t, count=1, flags=re.S)
io.open(p, "w", encoding="utf-8", newline="").write(t)
print("P4 replaced: %d    W1 replaced: %d" % (n1, n2))
sys.exit(0 if (n1 and n2) else 1)