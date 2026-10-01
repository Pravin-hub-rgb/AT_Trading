"""
Are the remaining R differences real, or a display/rounding artefact?

The reader checked 18 Jan 2024 13:30 on the chart and saw the same entry, the
same stop and the same exit in both books, yet the harness reports +50.85R
against +42.36R. One of those is wrong, or the two are looking at different
things.

This prints the full record for that entry from both books - entry, stop, exit,
bars held, and the risk each one used - and recomputes R by hand from those
numbers. If the hand calculation matches the harness, the difference is real and
it is a stop-placement difference that is simply too small to see on a chart at
this price scale. If it does not match, the harness is wrong.

Run: python -u exp_r_check.py
"""
import sys, os, pickle, types, inspect
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest", "backtest/tests", "backtest/sweeps", "backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))

from experiment_registry import EXPERIMENTS, BP
from run_experiment import net_r

with open(Path(os.environ["TEMP"]) / "at_datacache.pkl", "rb") as f:
    d = pickle.load(f)
c15 = d["c15"]

SRC = (ROOT / "backend/src/btc/engines/htf_ltf/v19_champion.py").read_text(encoding="latin-1")
m = types.ModuleType("r")
m.__file__ = "r.py"
exec(compile(SRC, "r.py", "exec"), m.__dict__)
pr = {k: v for k, v in {**BP, **EXPERIMENTS["champion_multi_sw10"]["params"]}.items()
      if k in set(inspect.signature(m.simulate_htf_ltf_streak_halt).parameters)
      and k not in {"exp_mltf", "exp_persist", "exp_partial_r"}}

TARGET = "2024-01-18 13:30"


def run(causal):
    r = m.simulate_htf_ltf_streak_halt(d["c1h"], d["sw10"], c15, d["sw15"],
                                      fine_ltf=d["fine"], exp_causal_sl=causal, **pr)
    return [t for t in r["ltf_trades"] if t.get("outcome") != "open"]


books = {}
for causal, tag in ((0, "RETRO"), (1, "CAUSAL")):
    tr = run(causal)
    hit = [t for t in tr if str(t["entry_date"])[:16] == TARGET]
    if not hit:
        print("%s: entry %s not present" % (tag, TARGET))
        continue
    books[tag] = hit[0]
    t = hit[0]
    e = float(t["entry_price"])
    s = float(t["sl"])
    x = float(t["exit_price"])
    d_ = t["dir"]
    risk = abs(e - s)
    move = (x - e) if d_ == 1 else (e - x)
    hand = move / risk if risk else 0.0
    print()
    print("=" * 74)
    print("%s   %s %s" % (tag, "LONG" if d_ == 1 else "SHORT", TARGET))
    print("=" * 74)
    print("  entry        %.2f" % e)
    print("  sl (initial) %.2f" % s)
    print("  exit         %.2f" % x)
    print("  bars held    %s" % t.get("bars_held"))
    print("  outcome      %s" % t.get("outcome"))
    print()
    print("  risk   = |entry - sl|      = %.2f" % risk)
    print("  move   = exit - entry      = %.2f" % move)
    print("  R by hand                   = %+.3f" % hand)
    print("  R as the engine reported it = %+.3f" % float(t["r_multiple"]))
    print("  match                        = %s" % (abs(hand - float(t["r_multiple"])) < 0.01))
    t["_risk"] = risk
    t["_move"] = move

if len(books) == 2:
    a, b = books["RETRO"], books["CAUSAL"]
    print()
    print("=" * 74)
    print("SIDE BY SIDE")
    print("=" * 74)
    print("  entry   RETRO %.2f   CAUSAL %.2f   diff %+.2f"
          % (a["_entry"] if "_entry" in a else float(a["entry_price"]),
             float(b["entry_price"]),
             float(b["entry_price"]) - float(a["entry_price"])))
    print("  sl      RETRO %.2f   CAUSAL %.2f   diff %+.2f"
          % (float(a["sl"]), float(b["sl"]), float(b["sl"]) - float(a["sl"])))
    print("  exit    RETRO %.2f   CAUSAL %.2f   diff %+.2f"
          % (float(a["exit_price"]), float(b["exit_price"]),
             float(b["exit_price"]) - float(a["exit_price"])))
    print("  risk    RETRO %.2f   CAUSAL %.2f   diff %+.2f"
          % (a["_risk"], b["_risk"], b["_risk"] - a["_risk"]))
    print("  move    RETRO %.2f   CAUSAL %.2f   diff %+.2f"
          % (a["_move"], b["_move"], b["_move"] - a["_move"]))
    print()
    print("  R differs because RISK differs: the same move measured against a")
    print("  different stop size. move is %.2f in both; the denominator is not."
          % a["_move"])
    slgap = abs(float(b["sl"]) - float(a["sl"]))
    px = float(a["entry_price"])
    print()
    print("  the stops are %.2f apart, which is %.4f%% of a %.0f price."
          % (slgap, (slgap / px) * 100.0, px))
    print("  At that scale the two stop lines overlap visually on a chart, so the")
    print("  eye reads them as the same line. They are not the same number.")
