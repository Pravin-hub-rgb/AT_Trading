"""
Retro vs causal SL on v19, IS and OOS, same params, same engine.

This is the measurement 484fe2a claimed but never ran against a committed
engine. It runs both arms from the committed file and prints the gap.

The falsifier: if exp_causal_sl=0 does NOT reproduce +325.78R, this harness is
wrong, not the engine. That is the correct failure direction.

Run: python -u exp_v19_causal.py     (about 2.5 min, four engine passes)
"""
import sys, os, pickle, types, inspect
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("live_stuff", "live_stuff/tests", "backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))

from experiment_registry import EXPERIMENTS, BP
from run_experiment import net_r
from exp_concurrency_guard import pf
import test_experiments_craze as tc
from exp_concurrency_guard import load_unseen
from test_4_new_concepts import load_fine_1m as lfo

SRC = (ROOT / "backend/src/btc/engines/htf_ltf/v19_champion.py").read_text(encoding="latin-1")
assert "exp_causal_sl" in SRC, "causal flag missing from the engine"

m = types.ModuleType("causal_probe")
m.__file__ = "causal_probe.py"
exec(compile(SRC, "causal_probe.py", "exec"), m.__dict__)

BASE = {k: v for k, v in {**BP, **EXPERIMENTS["champion_multi_sw10"]["params"]}.items()
        if k not in {"exp_mltf", "exp_persist", "exp_partial_r"}}
sig = set(inspect.signature(m.simulate_htf_ltf_streak_halt).parameters)
pr = {k: v for k, v in BASE.items() if k in sig}
assert "exp_causal_sl" in sig, "engine did not accept the flag"

with open(Path(os.environ["TEMP"]) / "at_datacache.pkl", "rb") as f:
    d = pickle.load(f)

IS_END = int(d["c15"][int(len(d["c15"]) * 0.70)]["ts"])


def run(c15, sw15, c1h, sw1h, fine, causal):
    r = m.simulate_htf_ltf_streak_halt(
        c1h, sw1h, c15, sw15, fine_ltf=fine, exp_causal_sl=causal, **pr)
    tr = [t for t in r["ltf_trades"] if t.get("outcome") != "open"]
    rs = [float(t["r_multiple"]) for t in tr]
    return len(rs), net_r(tr), pf(rs)


# OOS is the UNSEEN slice, loaded the same way exp_v19_oos.py:13-14 does it.
oc15, of15 = load_unseen("15m")
oc1h, of1h = load_unseen("1h")
ofine = lfo(oc15[0]["ts"], oc15[-1]["ts"])
osw15 = tc._compute_swings(of15, "continuous", min_bars=50)
osw1h = tc._compute_swings(of1h, "continuous", min_bars=10)

print("=" * 74)
print("RETRO (exp_causal_sl=0) vs CAUSAL (exp_causal_sl=1)")
print("=" * 74)

n0, net0, pf0 = run(d["c15"], d["sw15"], d["c1h"], d["sw10"], d["fine"], 0)
n1, net1, pf1 = run(d["c15"], d["sw15"], d["c1h"], d["sw10"], d["fine"], 1)
print()
print("  IS")
print("    retro   n=%-5d net=%+8.2fR  PF=%.3f" % (n0, net0, pf0))
print("    causal  n=%-5d net=%+8.2fR  PF=%.3f" % (n1, net1, pf1))
print("    gap     n=%+-5d    net=%+8.2fR" % (n1 - n0, net1 - net0))
assert abs(net0 - 325.78) < 0.5, "retro arm did not reproduce the pin - harness is wrong"

o0, on0, opf0 = run(oc15, osw15, oc1h, osw1h, ofine, 0)
o1, on1, opf1 = run(oc15, osw15, oc1h, osw1h, ofine, 1)
print()
print("  OOS")
print("    retro   n=%-5d net=%+8.2fR  PF=%.3f" % (o0, on0, opf0))
print("    causal  n=%-5d net=%+8.2fR  PF=%.3f" % (o1, on1, opf1))
print("    gap     n=%+-5d    net=%+8.2fR" % (o1 - o0, on1 - on0))
assert abs(on0 - 70.15) < 0.5, "OOS retro arm did not reproduce the pin - harness is wrong"
print("  both retro arms reproduced their pins, so the gaps above are real")

print()
print("=" * 74)
print("COMPARISON TO THE 484fe2a CLAIM")
print("=" * 74)
print("  484fe2a said: IS -63R to -78R, OOS +5R to +13R")
print("  registry 494/+248.0 was the causal IS pin at the time")
print("  if the IS gap lands near -78R, the retro advantage is confirmed")
print("  and +325.78R is inflated. If it does not, 484fe2a was wrong.")
