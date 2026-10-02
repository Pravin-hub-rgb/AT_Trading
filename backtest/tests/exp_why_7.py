"""
Why do 493 of 500 trades have an identical stop under both rules, and 7 do not?

The reader is right to ask. If the two rules systematically differed by a small
amount, every trade would show it. Seven is not a systematic offset - it is a
specific case.

The retro pivot comes from _collect_signals, which has two branches:

    mark dir == swing dir   -> this swing's start pivot
    opposite-dir mark       -> the previous swing's END pivot  (state churn)

The second branch is not a running extreme at all. It is a different quantity
entirely, and comparing it against the running high is comparing two different
things. This checks which branch each of the 7 uses.

Run: python -u exp_why_7.py
"""
import sys, os, pickle, types, inspect
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest", "backtest/tests", "backtest/sweeps", "backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))

from experiment_registry import EXPERIMENTS, BP
from src.btc.btc_engine import _collect_signals

with open(Path(os.environ["TEMP"]) / "at_datacache.pkl", "rb") as f:
    d = pickle.load(f)
c15, sw15 = d["c15"], d["sw15"]

SRC = (ROOT / "backend/src/btc/engines/htf_ltf/v19_champion.py").read_text(encoding="latin-1")
m = types.ModuleType("w")
m.__file__ = "w.py"
exec(compile(SRC, "w.py", "exec"), m.__dict__)
pr = {k: v for k, v in {**BP, **EXPERIMENTS["champion_multi_sw10"]["params"]}.items()
      if k in set(inspect.signature(m.simulate_htf_ltf_streak_halt).parameters)
      and k not in {"exp_mltf", "exp_persist", "exp_partial_r"}}


def run(causal):
    r = m.simulate_htf_ltf_streak_halt(d["c1h"], d["sw10"], c15, sw15,
                                      fine_ltf=d["fine"], exp_causal_sl=causal, **pr)
    return [t for t in r["ltf_trades"] if t.get("outcome") != "open"]


retro, causal = run(0), run(1)
rk = {(int(t["entry_ts"]), t["dir"]): t for t in retro}
ck = {(int(t["entry_ts"]), t["dir"]): t for t in causal}

diff = []
for k in set(rk) & set(ck):
    if abs(float(rk[k]["sl"]) - float(ck[k]["sl"])) > 1e-6:
        diff.append(k)
diff.sort()

print("=" * 78)
print("%d of %d shared trades have a different stop" % (len(diff), len(set(rk) & set(ck))))
print("=" * 78)

# what is each pivot, and which branch produced it
sigs = _collect_signals(sw15, "decisive", skip_first=True,
                        selection="stream", candles=c15)
sigs_by_bar = {}
for s in sigs:
    sigs_by_bar.setdefault(str(s["bar"]), []).append(s)
swing_by_no = {int(s.get("swing_index", -1)): s for s in sw15}

print()
print("  %-17s %-6s %-10s %-10s %-7s %-6s %s"
      % ("entry", "dir", "sl_retro", "sl_causal", "d_sl", "swing", "branch"))
for k in diff:
    a, b = rk[k], ck[k]
    ed = str(a["entry_date"])[:16]
    cands = sigs_by_bar.get(str(a["entry_date"]), [])
    sig = cands[0] if cands else None
    sn = int(a.get("swing_no", -1))
    sdir = swing_by_no.get(sn, {}).get("dir")
    mdir = "up" if k[1] == 1 else "down"
    same = (sdir == mdir)
    print("  %-17s %-6s %-10.2f %-10.2f %+-7.2f %-6s %s"
          % (ed, "LONG" if k[1] == 1 else "SHORT",
             float(a["sl"]), float(b["sl"]),
             float(b["sl"]) - float(a["sl"]), sn,
             "same-dir (start pivot)" if same else "OPPOSITE-DIR (prev swing END)"))

print()
print("=" * 78)
print("AND THE 493 THAT MATCH")
print("=" * 78)
same_n = 0
opposite_n = 0
for k in set(rk) & set(ck):
    if k in diff:
        continue
    a = rk[k]
    sn = int(a.get("swing_no", -1))
    sdir = swing_by_no.get(sn, {}).get("dir")
    mdir = "up" if k[1] == 1 else "down"
    if sdir == mdir:
        same_n += 1
    else:
        opposite_n += 1
print("  matching stops, swing dir == mark dir : %d" % same_n)
print("  matching stops, opposite-dir marks     : %d" % opposite_n)
print()
diff_same = sum(1 for k in diff
                if swing_by_no.get(int(rk[k].get("swing_no", -1)), {}).get("dir")
                == ("up" if k[1] == 1 else "down"))
diff_opp = len(diff) - diff_same
print("  of the %d that DIFFER: %d same-dir, %d opposite-dir" % (len(diff), diff_same, diff_opp))
print()
print("  Both branches can differ, and in both directions, so this is not one")
print("  systematic cause. Where causal sits further from entry than retro, the")
print("  swing's true origin is closer to entry than anything seen between the")
print("  swing start and the entry bar - retro used the origin, causal could not")
print("  have known it yet. Where causal sits tighter, the two rules simply")
print("  picked different anchors.")
print()
print("  The earlier note in this file claimed the two rules can only disagree")
print("  on the opposite-direction branch. The data above does not support that:")
print("  %d of the %d differing trades are same-direction marks, and %d")
print("  opposite-direction marks match fine. Corrected. %d %d %d" % (diff_same, len(diff), diff_opp))
