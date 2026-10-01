"""
Which individual trades differ between retro SL and causal SL.

The frontend lets you flip between the two books and see them on the chart.
This prints the same thing as text so the two can be checked against each
other by eye: every entry that is in one book and not the other, plus every
entry present in both whose stop or R moved.

Both arms come from the committed engine. Both retro pins are asserted, so if
the harness is wrong it says so instead of quietly reporting a diff.

Run: python -u exp_v19_tradediff.py     (about 2.5 min)
"""
import sys, os, pickle, types, inspect
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest", "backtest/tests", "backtest/sweeps", "backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))

from experiment_registry import EXPERIMENTS, BP
from run_experiment import net_r

SRC = (ROOT / "backend/src/btc/engines/htf_ltf/v19_champion.py").read_text(encoding="latin-1")
m = types.ModuleType("diff_probe")
m.__file__ = "diff_probe.py"
exec(compile(SRC, "diff_probe.py", "exec"), m.__dict__)

pr = {k: v for k, v in {**BP, **EXPERIMENTS["champion_multi_sw10"]["params"]}.items()
      if k in set(inspect.signature(m.simulate_htf_ltf_streak_halt).parameters)
      and k not in {"exp_mltf", "exp_persist", "exp_partial_r"}}

with open(Path(os.environ["TEMP"]) / "at_datacache.pkl", "rb") as f:
    d = pickle.load(f)


def run(causal):
    r = m.simulate_htf_ltf_streak_halt(
        d["c1h"], d["sw10"], d["c15"], d["sw15"],
        fine_ltf=d["fine"], exp_causal_sl=causal, **pr)
    return [t for t in r["ltf_trades"] if t.get("outcome") != "open"]


def key(t):
    dv = t["dir"]
    dv = 1 if dv in (1, "1", "long", "LONG") else -1
    return (int(t["entry_ts"]), dv)


def when(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d %H:%M")


retro = run(0)
causal = run(1)
assert abs(net_r(retro) - 325.78) < 0.5, "retro arm wrong - harness is broken"
assert abs(net_r(causal) - 255.20) < 0.5, "causal arm wrong - harness is broken"

rk = {}
for t in retro:
    rk.setdefault(key(t), []).append(t)
ck = {}
for t in causal:
    ck.setdefault(key(t), []).append(t)

only_retro = sorted(set(rk) - set(ck))
only_causal = sorted(set(ck) - set(rk))
both = sorted(set(rk) & set(ck))

print("=" * 78)
print("BOOK SIZES")
print("=" * 78)
print("  retro   n=%d  net=%+.2fR" % (len(retro), net_r(retro)))
print("  causal  n=%d  net=%+.2fR" % (len(causal), net_r(causal)))
print()

print("=" * 78)
print("A. IN RETRO ONLY - %d entries. Causal SL stopped these out earlier." % len(only_retro))
print("=" * 78)
for k in only_retro:
    t = rk[k][0]
    print("  %s  %s  entry %.2f  sl %.2f  exit %.2f  R %+.3f  (%s)"
          % (when(k[0]), "LONG " if k[1] == 1 else "SHORT",
             float(t["entry_price"]), float(t.get("sl", 0)),
             float(t.get("exit_price", 0)), float(t["r_multiple"]),
             t.get("outcome")))
print()

print("=" * 78)
print("B. IN CAUSAL ONLY - %d entries. Causal SL let these live." % len(only_causal))
print("=" * 78)
for k in only_causal:
    t = ck[k][0]
    print("  %s  %s  entry %.2f  sl %.2f  exit %.2f  R %+.3f  (%s)"
          % (when(k[0]), "LONG " if k[1] == 1 else "SHORT",
             float(t["entry_price"]), float(t.get("sl", 0)),
             float(t.get("exit_price", 0)), float(t["r_multiple"]),
             t.get("outcome")))
print()

print("=" * 78)
print("C. IN BOTH - stop or R changed on these")
print("=" * 78)
moved = []
for k in both:
    a, b = rk[k][0], ck[k][0]
    sa, sb = float(a.get("sl", 0)), float(b.get("sl", 0))
    ra, rb = float(a["r_multiple"]), float(b["r_multiple"])
    if abs(sa - sb) > 1e-6 or abs(ra - rb) > 1e-6:
        moved.append((k, sa, sb, ra, rb))
moved.sort()
print("  %d of %d shared entries differ in stop or R" % (len(moved), len(both)))
for k, sa, sb, ra, rb in moved:
    print("  %s  %s  sl %.2f -> %.2f  (R %+.3f -> %+.3f,  d=%+.3f)"
          % (when(k[0]), "LONG " if k[1] == 1 else "SHORT",
             sa, sb, ra, rb, rb - ra))
print()

dr = sum(float(t["r_multiple"]) for t in retro if key(t) in set(only_retro))
dc = sum(float(t["r_multiple"]) for t in causal if key(t) in set(only_causal))
sr = sum(rb - ra for _, _, _, ra, rb in moved)
sc = sum(rb - ra for _, _, _, _, rb in
         [(k, rk[k][0], ck[k][0], float(rk[k][0]["r_multiple"]), float(ck[k][0]["r_multiple"]))
          for k in both] if False)
print("=" * 78)
print("R ACCOUNTING OF THE DIFFERENCE")
print("=" * 78)
print("  retro-only entries contributed   %+.2fR" % dr)
print("  causal-only entries contributed  %+.2fR" % dc)
print("  R change on shared entries      %+.2fR" % sr)
print("  identical entries               %d" % (len(both) - len(moved)))
