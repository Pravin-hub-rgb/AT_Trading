"""
Check the fix on the engine itself, not on a copy of the logic.

Reads the 30 Nov 2023 23:45 trade straight out of the committed engine and
prints the stop it actually used, plus the book's totals. A replica of the
running-low code inside a diagnostic can drift from the engine and then argue
with itself; this cannot.

Run: python -u exp_sl_verify.py
"""
import sys, os, pickle, types, inspect
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest", "backtest/tests", "backtest/sweeps", "backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))

from experiment_registry import EXPERIMENTS, BP
from run_experiment import net_r

with open(Path(os.environ["TEMP"]) / "at_datacache.pkl", "rb") as f:
    d = pickle.load(f)
c15 = d["c15"]


def i_of(mm):
    for k, c in enumerate(c15):
        if str(c["date"])[:16] == mm:
            return k
    return -1


SRC = (ROOT / "backend/src/btc/engines/htf_ltf/v19_champion.py").read_text(encoding="latin-1")
m = types.ModuleType("v")
m.__file__ = "v.py"
exec(compile(SRC, "v.py", "exec"), m.__dict__)
pr = {k: v for k, v in {**BP, **EXPERIMENTS["champion_multi_sw10"]["params"]}.items()
      if k in set(inspect.signature(m.simulate_htf_ltf_streak_halt).parameters)
      and k not in {"exp_mltf", "exp_persist", "exp_partial_r"}}

T = i_of("2023-11-30 23:45")
EXPECT_LOW = float(c15[i_of("2023-11-30 21:15")]["low"])

print("=" * 74)
print("THE FIX, CHECKED ON THE ENGINE")
print("=" * 74)
for causal, tag in ((1, "CAUSAL"), (0, "RETRO ")):
    r = m.simulate_htf_ltf_streak_halt(d["c1h"], d["sw10"], c15, d["sw15"],
                                      fine_ltf=d["fine"], exp_causal_sl=causal, **pr)
    tr = [t for t in r["ltf_trades"] if t.get("outcome") != "open"]
    hit = [t for t in tr if str(t["entry_date"])[:16] == "2023-11-30 23:45"]
    rs = [float(t["r_multiple"]) for t in tr]
    oc = Counter(t.get("outcome") for t in tr)
    print()
    print("  %s  n=%-5d net=%+8.2fR  %r" % (tag, len(rs), net_r(tr), dict(oc)))
    if hit:
        t = hit[0]
        print("     30 Nov 23:45 %s  entry %.2f  sl %.2f  R %+.3f  (%s)"
              % (t["dir"], float(t["entry_price"]), float(t["sl"]),
                 float(t["r_multiple"]), t.get("outcome")))
        if causal:
            got = float(t["sl"])
            print("     21:15 low (what the rule should give) = %.2f" % EXPECT_LOW)
            print("     sl_buf_atr = 0.01, so the stop is slightly below the pivot.")
            print("     pivot = sl + 0.01 * ATR  ->  the pivot used was %.2f" % got)
            if abs(got - EXPECT_LOW) < 60:
                print("     >>> within ATR buffer of the 21:15 low. Fix took effect.")
            else:
                print("     >>> still far from 21:15. Check the reset.")
    else:
        print("     30 Nov 23:45 : no trade in this book")
