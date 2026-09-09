"""TRUNCATION INVARiance TEST — the strongest no-lookahead proof possible.

Run v18 on data TRUNCATED at 2023-07-01 and compare every trade decision
(entry bar, dir, swing_no, entry_price, SL) with the full 4-year run.
If the retroactive swing chain leaked future data into past decisions,
trades BEFORE the cutoff would differ. Boundary trades (within 2 days of
the cutoff) are excluded — their environment legitimately changes.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from test_pre_fs_marks import (c1h, f1h, c15, f15, sw1h, sw15, tr,  # full-run baseline
                               _load_fine_1m)
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt

CUT = "2023-07-01 00:00:00"


def trunc(candles, flow):
    c, f = [], []
    for cd, fl in zip(candles, flow):
        if cd["date"] >= CUT:
            break
        c.append(cd); f.append(fl)
    return c, f


c1h_t, f1h_t = trunc(c1h, f1h)
c15_t, f15_t = trunc(c15, f15)
sw1h_t = sw1h  # placeholder, recomputed below
from src.btc.btc_routes import _compute_swings
sw1h_t = _compute_swings(f1h_t, "continuous", min_bars=20)
sw15_t = _compute_swings(f15_t, "continuous", min_bars=50)
fine_t = _load_fine_1m(c1h_t[0]["ts"], c15_t[-1]["ts"])

res_t = simulate_htf_ltf_streak_halt(c1h_t, sw1h_t, c15_t, sw15_t, fine_ltf=fine_t,
    sl_buf_atr=0.25, ext_stop_r=1.5, mode="b2_vs_flip_chop",
    cooldown_bars=20, max_consecutive_losses=5)
tr_t = [t for t in res_t["ltf_trades"] if t["outcome"] != "open"]


def key(t):
    return (t["entry_idx"], t["dir"], t["swing_no"], round(t["entry_price"], 2),
            round(t["sl"], 2))


SAFE = "2023-06-29 00:00:00"  # exclude 2 boundary days
full_safe = [t for t in tr if str(t["entry_date"]) < SAFE]
trunc_safe = [t for t in tr_t if str(t["entry_date"]) < SAFE]

kf = {key(t) for t in full_safe}
kt = {key(t) for t in trunc_safe}
only_full = kf - kt
only_trunc = kt - kf

print(f"full run  (entries < {SAFE}): {len(full_safe)} trades")
print(f"truncated run (same period) : {len(trunc_safe)} trades")
print(f"identical decisions         : {len(kf & kt)}")
print(f"in full-run only            : {len(only_full)}")
print(f"in truncated-run only       : {len(only_trunc)}")
if only_full or only_trunc:
    print("\nMISMATCH DETAIL:")
    for k in sorted(only_full)[:10]:
        t = next(t for t in full_safe if key(t) == k)
        print(f"  full-only : {t['entry_date']} {t['dir']} sw{t['swing_no']} @ {t['entry_price']}")
    for k in sorted(only_trunc)[:10]:
        t = next(t for t in trunc_safe if key(t) == k)
        print(f"  trunc-only: {t['entry_date']} {t['dir']} sw{t['swing_no']} @ {t['entry_price']}")
else:
    print("\n>>> TRUNCATION INVARIANCE HOLDS: zero decision differences.")
    print(">>> The pipeline's past decisions are a pure function of past data.")
print(f"\n(boundary note: {len(tr)-len(full_safe)} full-run trades and "
      f"{len(tr_t)-len(trunc_safe)} truncated-run trades within 2d of cutoff excluded by design)")
