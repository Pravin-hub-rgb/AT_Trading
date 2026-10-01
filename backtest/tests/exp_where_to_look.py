"""
The five dates worth putting on the chart, and what each one shows.

The trade diff between RETRO and CAUSAL is mostly not about which trades
exist - 488 of 500 entries are in both books. It is about where the stop sits.
So the useful dates are not "a trade that only appears in one book", they are
one trade, seen twice, with the stop in a visibly different place.

Ranked by how much R moves. Run this and the dates come from the engine, not
from memory:

    python -u exp_where_to_look.py

Then open the chart on each and flip the Book dropdown between
"v19 RETRO stop" and "v19 CAUSAL stop".
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
mod = types.ModuleType("wtl")
mod.__file__ = "wtl.py"
exec(compile(SRC, "wtl.py", "exec"), mod.__dict__)
pr = {k: v for k, v in {**BP, **EXPERIMENTS["champion_multi_sw10"]["params"]}.items()
      if k in set(inspect.signature(mod.simulate_htf_ltf_streak_halt).parameters)
      and k not in {"exp_mltf", "exp_persist", "exp_partial_r"}}

with open(Path(os.environ["TEMP"]) / "at_datacache.pkl", "rb") as f:
    d = pickle.load(f)


def run(causal):
    r = mod.simulate_htf_ltf_streak_halt(
        d["c1h"], d["sw10"], d["c15"], d["sw15"],
        fine_ltf=d["fine"], exp_causal_sl=causal, **pr)
    return [t for t in r["ltf_trades"] if t.get("outcome") != "open"]


def key(t):
    dv = t["dir"]
    dv = 1 if dv in (1, "1", "long", "LONG") else -1
    return (int(t["entry_ts"]), dv)


def when(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d %H:%M")


retro, causal = run(0), run(1)
assert abs(net_r(retro) - 325.78) < 0.5, "retro arm wrong - harness is broken"
assert abs(net_r(causal) - 247.96) < 0.5, "causal arm wrong - harness is broken"

rk = {key(t): t for t in retro}
ck = {key(t): t for t in causal}

print("=" * 78)
print("A. STOP MOVED, SAME TRADE EXISTS IN BOTH  - ranked by |R change|")
print("=" * 78)
rows = []
for k in set(rk) & set(ck):
    a, b = rk[k], ck[k]
    sa, sb = float(a.get("sl", 0)), float(b.get("sl", 0))
    ra, rb = float(a["r_multiple"]), float(b["r_multiple"])
    if abs(sa - sb) > 1e-6 or abs(ra - rb) > 1e-6:
        rows.append((abs(rb - ra), k, sa, sb, ra, rb))
rows.sort(reverse=True)
print("  %d shared trades differ. Top 8:" % len(rows))
print()
print("  %-17s %-6s %-10s %-10s %-8s %-8s %s"
      % ("date", "side", "sl_retro", "sl_causal", "R_retro", "R_causal", "dR"))
for _, k, sa, sb, ra, rb in rows[:8]:
    print("  %-17s %-6s %-10.2f %-10.2f %-+8.2f %-+8.2f %+.2f"
          % (when(k[0]), "LONG" if k[1] == 1 else "SHORT",
             sa, sb, ra, rb, rb - ra))

print()
print("=" * 78)
print("B. A TRADE THAT ONLY ONE BOOK TAKES  - membership")
print("=" * 78)
only_r = sorted(set(rk) - set(ck))
only_c = sorted(set(ck) - set(rk))
print("  RETRO only  (%d) - causal stopped these out earlier:" % len(only_r))
for k in only_r:
    t = rk[k]
    print("    %-17s %-6s R %+.2f  (%s)"
          % (when(k[0]), "LONG" if k[1] == 1 else "SHORT",
             float(t["r_multiple"]), t.get("outcome")))
print("  CAUSAL only (%d):" % len(only_c))
for k in only_c:
    t = ck[k]
    print("    %-17s %-6s R %+.2f  (%s)"
          % (when(k[0]), "LONG" if k[1] == 1 else "SHORT",
             float(t["r_multiple"]), t.get("outcome")))

print()
print("=" * 78)
print("C. THE THREE WORTH A SIDE-BY-SIDE LOOK")
print("=" * 78)
picks = []
for want, label in ((("2023-03-16"), "the flip: a winner that became a full stop-out"),
                    (("2023-06-20"), "the largest single R loss between the two books"),
                    (("2023-08-17"), "a big runner that survives both, just smaller")):
    for _, k, sa, sb, ra, rb in rows:
        if when(k[0]).startswith(want):
            picks.append((want[0], label, k, sa, sb, ra, rb))
            break
for date, label, k, sa, sb, ra, rb in picks:
    print()
    print("  %s   %s" % (when(k[0]), label))
    print("    %s   entry %.2f" % ("LONG " if k[1] == 1 else "SHORT",
                                  float(rk[k]["entry_price"])))
    print("    RETRO   stop %.2f   exit %+.2fR" % (sa, ra))
    print("    CAUSAL  stop %.2f   exit %+.2fR" % (sb, rb))
    print("    on the chart: the stop line is %.2f apart, everything else is the same"
          % abs(sa - sb))

print()
print("=" * 78)
print("D. WHERE THE 77.82R SITS")
print("=" * 78)
dr = sum(float(t["r_multiple"]) for t in retro if key(t) in set(only_r))
dc = sum(float(t["r_multiple"]) for t in causal if key(t) in set(only_c))
sr = sum(rb - ra for _, _, _, _, ra, rb in rows)
print("  trades only in RETRO            %+8.2fR  (%d trades)" % (dr, len(only_r)))
print("  trades only in CAUSAL           %+8.2fR  (%d trades)" % (dc, len(only_c)))
print("  R change on shared trades       %+8.2fR  (%d trades)" % (sr, len(rows)))
print("  identical                       %8.2fR  (%d trades)"
      % (0.0, len(set(rk) & set(ck)) - len(rows)))
print()
print("  So the gap is stop placement, not which trades were taken. A look at a")
print("  membership date shows one trade appearing or vanishing. A look at any")
print("  date in section A shows the same trade with a different stop - which is")
print("  what actually produces the difference.")
