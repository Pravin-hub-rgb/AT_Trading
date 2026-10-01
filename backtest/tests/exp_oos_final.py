"""
OOS for the shipped rule, and for the retired one, measured side by side.

exp_v19_oos.py printed +70.15R, which is also the retired rule's OOS number, so
it is ambiguous whether the default actually took effect there. This runs both
arms explicitly and asserts the retro arm reproduces its known figure, so there
is no doubt which number belongs to which rule.

Run: python -u exp_oos_final.py
"""
import sys, os, types, inspect
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest", "backtest/tests", "backtest/sweeps", "backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))

from experiment_registry import EXPERIMENTS, BP
from run_experiment import net_r
from exp_concurrency_guard import concurrency, pf
import test_experiments_craze as tc
from exp_concurrency_guard import load_unseen
from test_4_new_concepts import load_fine_1m as lfo

SRC = (ROOT / "backend/src/btc/engines/htf_ltf/v19_champion.py").read_text(encoding="latin-1")
m = types.ModuleType("o")
m.__file__ = "o.py"
exec(compile(SRC, "o.py", "exec"), m.__dict__)
pr = {k: v for k, v in {**BP, **EXPERIMENTS["champion_multi_sw10"]["params"]}.items()
      if k in set(inspect.signature(m.simulate_htf_ltf_streak_halt).parameters)
      and k not in {"exp_mltf", "exp_persist", "exp_partial_r"}}

(oc15, of15), (oc1h, of1h) = load_unseen("15m"), load_unseen("1h")
ofine = lfo(oc15[0]["ts"], oc15[-1]["ts"])
osw15 = tc._compute_swings(of15, "continuous", min_bars=50)
osw1h = tc._compute_swings(of1h, "continuous", min_bars=10)

print("OOS window: %s .. %s   (%d 15m bars, %d 1h bars)"
      % (oc15[0]["date"][:10], oc15[-1]["date"][:10], len(oc15), len(oc1h)))
print()


def run(causal):
    r = m.simulate_htf_ltf_streak_halt(oc1h, osw1h, oc15, osw15,
                                      fine_ltf=ofine, exp_causal_sl=causal, **pr)
    return [t for t in r["ltf_trades"] if t.get("outcome") != "open"]


retired = run(0)
shipped = run(1)
r1, s1 = retired, shipped

print("=" * 72)
print("OOS - the two rules")
print("=" * 72)
for name, tr in (("RETIRED rule (flag 0)", r1), ("SHIPPED rule (flag 1)", s1)):
    rs = [float(t["r_multiple"]) for t in tr]
    print("  %-24s n=%-5d net=%+8.2fR  PF=%.3f  maxconc=%d"
          % (name, len(rs), net_r(tr), pf(rs), concurrency(tr)))
print()
print("  gap  %+.2fR over %d trades" % (net_r(s1) - net_r(r1), len(s1)))
print()
assert abs(net_r(r1) - 70.15) < 0.5, "retired arm did not reproduce +70.15R - harness is wrong"
print("  the retired arm reproduced +70.15R, so both numbers above are real")
print("  and not a default-flag accident.")

rk = {(int(t["entry_ts"]), t["dir"]): t for t in r1}
sk = {(int(t["entry_ts"]), t["dir"]): t for t in s1}
only_r = set(rk) - set(sk)
only_s = set(sk) - set(rk)
moved = sum(1 for k in set(rk) & set(sk)
            if abs(float(rk[k]["sl"]) - float(sk[k]["sl"])) > 1e-6)
rdiff = sum(1 for k in set(rk) & set(sk)
            if abs(float(rk[k]["r_multiple"]) - float(sk[k]["r_multiple"])) > 1e-9)
print()
print("  trades only in retired : %d" % len(only_r))
print("  trades only in shipped : %d" % len(only_s))
print("  stop moved on          : %d of %d shared" % (moved, len(set(rk) & set(sk))))
print("  R changed on           : %d of %d shared" % (rdiff, len(set(rk) & set(sk))))
print()
if rdiff == 0:
    print("  NOT ONE trade differs out of sample. The two rules produce the same")
    print("  book on 2021-2022. The entire 11.26R in-sample difference is")
    print("  in-sample only, which is what in-sample fitting looks like.")
else:
    print("  %d trades differ, so the rules are not identical out of sample." % rdiff)
print()
print("  trades only in retired : %d" % len(only_r))
print("  trades only in shipped : %d" % len(only_s))
print("  stop moved on          : %d of %d shared" % (moved, len(set(rk) & set(sk))))
print("  R changed on           : %d of %d shared" % (rdiff, len(set(rk) & set(sk))))
print()
if rdiff == 0:
    print("  NOT ONE trade differs out of sample. The two rules produce the same")
    print("  book on 2021-2022. The entire 11.26R in-sample difference is")
    print("  in-sample only, which is what in-sample fitting looks like.")
else:
    print("  %d trades differ, so the rules are not identical out of sample." % rdiff)
