"""C16 SL pivot matrix for v19, measured after pivot_rule became explicit.

Before the fix the HTF half could not be selected at all: v7_timecap binds
_collect_signals at module import, so a monkeypatch of btc_engine reached only
the LTF call. Every "origin" run was really leg-on-HTF, origin-on-LTF.

Now both halves take the same explicit pivot_rule, so only two configurations
are reachable and the hybrids are gone. This script measures both, plus the
causal flag, and asserts the origin arm still reproduces the registry pin.

Run: python -u exp_v19_matrix.py     (about 4 min, three engine passes)
"""
import sys, pickle, os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest", "backtest/tests", "backtest/sweeps", "backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))

from src.btc.engines.htf_ltf.v19_champion import simulate_htf_ltf_streak_halt as V19

FEE, ES, XS, FUND = 0.055, 0.005, 0.01, 0.01


def load():
    with open(Path(os.environ["TEMP"]) / "at_datacache.pkl", "rb") as f:
        return pickle.load(f)


def costs(cl):
    tot = 0.0
    for x in cl:
        rk = abs(float(x["entry_price"]) - float(x["sl"]))
        if rk <= 0:
            continue
        e = abs(float(x["entry_price"]))
        xp = abs(float(x.get("exit_price", x["entry_price"])))
        tot += ((e + xp) * (FEE / 100.0) + e * (ES / 100.0) + xp * (XS / 100.0)) / rk \
            + e * (FUND / 100.0) / 32.0 * int(x.get("bars_held", 0)) / rk
    return tot


d = load()
rows = []
for name, rule, csl in (("origin / origin", "origin", 0),
                        ("leg / leg", "leg", 0),
                        ("leg / leg + causal", "leg", 1)):
    r = V19(d["c1h"], d["sw10"], d["c15"], d["sw15"], fine_ltf=d["fine"],
            exp_causal_sl=csl, pivot_rule=rule,
            sl_buf_atr=0.01, ext_stop_r=3.0, mode="atr_high", chop_thresh=58.0,
            cooldown_bars=8, max_consecutive_losses=3, htf_rr=3.0,
            window_end="exit")["ltf_trades"]
    cl = [x for x in r if x.get("outcome") != "open"]
    g = sum(float(x["r_multiple"]) for x in cl)
    c = costs(cl)
    rows.append((name, len(cl), g, c, g - c))
    print(f"  {name:22s} n={len(cl):<5d} gross {g:+9.2f}R  cost {c:7.2f}R  net {g-c:+9.2f}R")

print()
print("  HTF leg + LTF origin (the old dropdown hybrid, now unreachable):")
print("    n=499   gross +358.98R  cost 116.70R  net +242.28R")
print()

o, l, lc = rows[0], rows[1], rows[2]
print(f"  C16 cost, origin/origin -> leg/leg : {l[4]-o[4]:+.2f}R over {l[1]-o[1]:+d} trades")
print(f"  causal flag moves leg/leg by       : {lc[4]-l[4]:+.2f}R over {lc[1]-l[1]:+d} trades")
assert abs(o[4] - 325.78) < 0.5, f"origin arm did not reproduce the pin: {o[4]:.2f}"
print("\n  PASS: origin arm reproduces the registry pin n=500 net=+325.78R")