"""A test for the drawdown-recovery code with an answer known in advance.

exp_results_export.py reported books spending 1014 and 1160 days under water
while the equity curve on /results showed them climbing. The owner spotted it by
looking at the chart rather than the number. That means the metric had never
been checked against anything.

This is that check. Every expected value below is worked out by hand in the
comment above it, from the timestamps and R values in the case itself.

A note on how this went the first time round: this file originally failed five
of its own assertions. All five were errors in the HAND-COMPUTED expectations,
not in the calculation - a dip described as 2R that was written as three -1.0
trades, a recovery written as 65 when 9 trades of 0.6R closes a 5R gap, and a
peak whose timestamp sat 61 days before the trough. The two-pass calculation
returned the right answer on every case. Writing the expectations down is what
caught that, which is the argument for writing them down.

Run:  python exp_dd_recovery_test.py
"""
from __future__ import annotations

import sys

DAY = 86400


def dd_recovery(pairs):
    """The calculation under test, copied from exp_results_export.py verbatim.

    pairs is a list of (exit_ts, r). Returns
    (worst_dd, dd_days, recover_days, dd_peak_ts, dd_trough_ts).
    """
    cum = pk = 0.0
    pk_ts = None
    worst_dd = 0.0
    dd_peak_ts = dd_peak_val = dd_trough_ts = None
    dd_trough_val = 0.0
    for i, (ts, r) in enumerate(pairs):
        cum += r
        ts = int(ts)
        if cum > pk:
            pk = cum
            pk_ts = ts
        else:
            d = pk - cum
            if d > worst_dd:
                worst_dd = d
                dd_peak_ts = pk_ts
                dd_peak_val = pk
                dd_trough_ts = ts
                dd_trough_val = cum
                dd_trough_i = i

    dd_days = 0.0
    recover_days = None
    if worst_dd > 0 and dd_peak_ts is not None and dd_trough_ts is not None:
        dd_days = (dd_trough_ts - dd_peak_ts) / DAY
        cum = dd_trough_val
        for i in range(dd_trough_i + 1, len(pairs)):
            cum += pairs[i][1]
            if cum >= dd_peak_val - 1e-9:
                recover_days = (int(pairs[i][0]) - dd_trough_ts) // DAY
                break
    return worst_dd, dd_days, recover_days, dd_peak_ts, dd_trough_ts


FAILS = []


def check(name, got, want):
    ok = got == want
    if not ok:
        FAILS.append(name)
    print("  %-42s got %-12s want %-12s %s"
          % (name, repr(got), repr(want), "OK" if ok else "*** FAIL ***"))
    return ok


def main() -> int:
    d = DAY

    # ---- CASE 1 ---------------------------------------------------------
    # Equity: 10 at day 0, then +1.0 on days 1..99  -> 109 at day 99.
    # Dip: three -1.0 trades on days 100,101,102     -> 106 at day 102.
    #   worst dd = 109 - 106 = 3.0,  peak day 99 -> trough day 102 = 3 days
    # Recovery: +0.4 per day from day 103. Need 109 - 106 = 3.0,
    #   3.0 / 0.4 = 7.5, so the 8th day wins -> day 110.  110 - 102 = 8 days.
    print("CASE 1  three-trade dip, recovers on the 8th day")
    s = [(0, 10.0)]
    for i in range(1, 100):
        s.append((i * d, 1.0))
    for i in range(3):
        s.append((100 * d + i * d, -1.0))
    for i in range(8):
        s.append((103 * d + i * d, 0.4))
    w, ddd, rec, _, _ = dd_recovery(s)
    check("worst drawdown", round(w, 3), 3.0)
    check("dd_days", round(ddd, 2), 3.0)
    check("recover_days", rec, 8)

    # ---- CASE 2 ---------------------------------------------------------
    # Equity: 20 at day 0, then +1.0 on days 1..49 -> 69 at day 49.
    # Dip: ten -0.5 trades on days 50..59           -> 64 at day 59.
    #   worst dd = 5.0,  day 49 -> day 59 = 10 days
    # Recovery: +0.6 per day from day 60. Need 69 - 64 = 5.0,
    #   5.0 / 0.6 = 8.33, so the 9th day wins -> day 68.  68 - 59 = 9 days.
    print("CASE 2  ten-trade dip of 5R, closes at 0.6R per trade")
    s = [(0, 20.0)]
    for i in range(1, 50):
        s.append((i * d, 1.0))
    for i in range(10):
        s.append((50 * d + i * d, -0.5))
    for i in range(9):
        s.append((60 * d + i * d, 0.6))
    w, ddd, rec, _, _ = dd_recovery(s)
    check("worst drawdown", round(w, 3), 5.0)
    check("dd_days", round(ddd, 2), 10.0)
    check("recover_days", rec, 9)

    # ---- CASE 3  THE REGRESSION THAT MATTERS ---------------------------
    # Equity peaks at 79 on day 29 (50 + 29 x 1.0), dips 2R, is back above the
    # peak by day 34, then climbs for 2000 days: 83 + 2000 x 0.5 = 1083, the
    # peak, on day 40 + 1999 = 2039. Then sixty -0.5 trades on days 2100..2159
    # take it to 1053, a 30R drawdown. The gap between that peak on day 2039 and
    # its trough on day 2159 is 120 days.
    #
    # The bug this replaces measured the EARLY recovery on day 34 against the
    # LATE trough on day 2159, which is 2125 days of nonsense. It must return
    # 30.0 / 120.0 and must report no recovery at all, because the curve never
    # climbs back to 1083.
    print("CASE 3  early recovery must not be charged against a later trough")
    s = [(0, 50.0)]
    for i in range(1, 30):
        s.append((i * d, 1.0))
    for i in range(2):
        s.append((30 * d + i * d, -1.0))
    for i in range(3):
        s.append((32 * d + i * d, 2.0))
    for i in range(2000):
        s.append((40 * d + i * d, 0.5))
    for i in range(60):
        s.append((2100 * d + i * d, -0.5))
    w, ddd, rec, _, _ = dd_recovery(s)
    check("worst drawdown is the LATE one", round(w, 3), 30.0)
    check("dd_days", round(ddd, 2), 120.0)
    check("recover_days (never recovered)", rec, None)

    # ---- CASE 4 ---------------------------------------------------------
    print("CASE 4  monotonically rising, no drawdown")
    s = [(i * d, 1.0) for i in range(50)]
    w, ddd, rec, _, _ = dd_recovery(s)
    check("worst drawdown", w, 0.0)
    check("dd_days", ddd, 0.0)
    check("recover_days", rec, None)

    # ---- CASE 5 ---------------------------------------------------------
    # 10 then +5 (peak 15, day 1) then -5 (trough 10, day 2) then +5 (back to
    # 15, day 3). dd 5.0 over 1 day, recovered on the very next trade.
    print("CASE 5  equity returns to exactly the peak value")
    s = [(0, 10.0), (1 * d, 5.0), (2 * d, -5.0), (3 * d, 5.0)]
    w, ddd, rec, _, _ = dd_recovery(s)
    check("worst drawdown", round(w, 3), 5.0)
    check("dd_days", round(ddd, 2), 1.0)
    check("recover_days", rec, 1)

    # ---- CASE 6  the one the real books tripped on ----------------------
    # A book that grinds up for years with only small dips, one of which is
    # 20R deep over 5 days and closes in 10 days. Every number here is small.
    # This is the shape a healthy book has, and it is the shape the bug turned
    # into four-figure answers.
    print("CASE 6  20R dip over 5 days, closes in 10")
    s = [(0, 100.0)]
    for i in range(1, 300):
        s.append((i * d, 1.0))
    for i in range(5):
        s.append((300 * d + i * d, -4.0))
    for i in range(10):
        s.append((305 * d + i * d, 2.2))
    w, ddd, rec, _, _ = dd_recovery(s)
    check("worst drawdown", round(w, 3), 20.0)
    check("dd_days", round(ddd, 2), 5.0)
    # 20.0 / 2.2 = 9.09, so the 10th day wins -> day 314.  314 - 304 = 10.
    check("recover_days", rec, 10)

    # ---- CASE 7  NON-MONOTONIC TIMESTAMPS - the real one ----------------
    # merged trades are sorted by ENTRY time, so their EXIT times are not in
    # order. The second version of this code walked the whole list asking "is
    # this trade's exit after the trough", and a trade sitting EARLIER in the
    # list but closing later satisfied it - at which point equity was still near
    # the peak and the condition matched at once. A book that recovered two rows
    # after its worst drawdown reported 1064 days because of this.
    #
    # Here: entry order is 0,1,2,... but exits are 0, 4000, 1, 2, ... so the
    # trade at row 1 sits early in the list and closes long after the trough.
    print("CASE 7  exit times out of order (sorted by entry, not exit)")
    s = [(0, 100.0)]
    for i in range(1, 200):                 # steady climb, equity ~300
        s.append((i * d, 1.0))
    s.append((200 * d, -20.0))              # the deepest dip
    for i in range(1, 6):                   # closed quickly, 5 days later
        s.append((200 * d + i * d, 5.0))
    # now scramble the exit times of the EARLY trades far into the future,
    # exactly as overlapping holds would
    scrambled = []
    for i, (ts, r) in enumerate(s):
        if 5 <= i < 50:
            scrambled.append(((ts // d + 5000) * d, r))
        else:
            scrambled.append((ts, r))
    w, ddd, rec, _, _ = dd_recovery(scrambled)
    check("worst drawdown", round(w, 3), 20.0)
    # the dip is 20R and closes at +5R per trade, so 4 trades -> 4 days
    check("recover_days", rec, 4)

    print()
    if FAILS:
        print("FAILED: %s" % ", ".join(FAILS))
        print("Do not trust these numbers until they pass.")
        return 1
    print("all checks passed")
    print()
    print("What this does NOT do: it proves the arithmetic on series whose answers")
    print("were worked out by hand. It says nothing about whether a real book's")
    print("drawdown genuinely lasts as long as reported. For that the equity curve")
    print("is the check - which is exactly how the original bug was found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())