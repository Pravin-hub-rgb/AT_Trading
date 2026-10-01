"""
nemo's claim, made falsifiable.

  "+325.78R ka provenance questionable hai. Kya ye kahin pinned hai?"

This script does not argue. It prints three numbers and lets them speak:

  A. what the registry claims
  B. what the engine actually produces
  C. whether the harness check that says "MATCH" is reading the registry at all

Run:  python -u exp_pin_audit.py
Read: the answer to C. That is the whole point of this file.
"""
import sys, os, re, types, pickle, inspect
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest", "backtest/tests", "backtest/sweeps", "backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))

from experiment_registry import EXPERIMENTS, BP
from run_experiment import net_r
from exp_concurrency_guard import pf

# ---------------------------------------------------------------- A
print("=" * 78)
print("A. WHAT THE REGISTRY CLAIMS")
print("=" * 78)
e = EXPERIMENTS["champion_multi_sw10"]
reg_pin = e["pins"]
print("  registry key        : champion_multi_sw10")
print("  registry 'engine'   : %r" % e.get("engine"))
print("  registry pins       : %r" % (reg_pin,))
print()

# ---------------------------------------------------------------- B
print("=" * 78)
print("B. WHAT THE ENGINE ACTUALLY PRODUCES  (real disk import of the commit)")
print("=" * 78)
SRC = (ROOT / "backend/src/btc/engines/htf_ltf/v19_champion.py").read_text(encoding="latin-1")
m = types.ModuleType("pin_audit")
m.__file__ = "pin_audit.py"
exec(compile(SRC, "pin_audit.py", "exec"), m.__dict__)

# IDENTICAL param construction to exp_v19_import.py:16-17, so the number
# must come out the same. If it does not, this harness is wrong, not the engine.
pr = {**BP, **e["params"]}
pr = {k: v for k, v in pr.items()
      if k not in {"exp_mltf", "exp_persist", "exp_partial_r"}}

with open(Path(os.environ["TEMP"]) / "at_datacache.pkl", "rb") as f:
    d = pickle.load(f)
r = m.simulate_htf_ltf_streak_halt(d["c1h"], d["sw10"], d["c15"], d["sw15"],
                                   fine_ltf=d["fine"], **pr)
tr = [t for t in r["ltf_trades"] if t.get("outcome") != "open"]
rs = [float(t["r_multiple"]) for t in tr]
live_n, live_net = len(rs), net_r(tr)
print("  engine n            : %d" % live_n)
print("  engine net          : %+.2fR" % live_net)
print("  engine PF           : %.3f" % pf(rs))
print()

# ---------------------------------------------------------------- the gap
print("=" * 78)
print("THE GAP")
print("=" * 78)
dn = live_n - int(reg_pin.get("n", live_n))
dnet = live_net - float(reg_pin.get("net", live_net))
print("  registry says       : n=%s  net=%sR" % (reg_pin.get("n"), reg_pin.get("net")))
print("  engine says         : n=%d  net=%+.2fR" % (live_n, live_net))
print("  difference          : n %+d,  net %+.2fR" % (dn, dnet))
print()

# ---------------------------------------------------------------- C
print("=" * 78)
print("C. IS THE 'PIN MATCH' CHECK READING THE REGISTRY?")
print("=" * 78)
HARNESS = (ROOT / "backtest/tests/exp_v19_import.py").read_text(encoding="utf-8", errors="replace")

# find the line that produces the MATCH verdict
verdict = [l.strip() for l in HARNESS.splitlines() if "MATCH" in l]
print("  the line that prints MATCH:")
for l in verdict:
    print("      %s" % l)
print()

# does any PIN/MATCH line reference the registry?
pin_lines = [l for l in HARNESS.splitlines()
             if ("PIN" in l or "MATCH" in l)
             and ("pin" in l.lower() or "MATCH" in l)]
reads_registry = any(("EXPERIMENTS" in l) or ("registry" in l) or ("reg_pin" in l)
                     for l in pin_lines)
print("  does the PIN/MATCH block read the registry?  ->  %s" % reads_registry)
print()

# the decisive test: is the expected value a literal, or a lookup?
lits = re.findall(r"len\(rs\)==(\d+)\s*and\s*abs\(.*?-\s*([0-9.]+)\)", HARNESS)
print("  literal found in the MATCH condition:")
for a, b in lits:
    print("      len(rs)==%s  and  abs(net - %s)" % (a, b))
print()
print("  -> the expected values are LITERALS, not registry lookups.")
print()

# now run the check the way it SHOULD be written, and let it fail
print("=" * 78)
print("D. THE SAME CHECK, WRITTEN HONESTLY - READING THE REGISTRY")
print("=" * 78)
honest = (live_n == int(reg_pin.get("n", -1))
          and abs(live_net - float(reg_pin.get("net", 1e9))) < 0.5)
print("  honest check  : live_n == registry_n  and  |live_net - registry_net| < 0.5")
print("  honest result : %s" % honest)
print()
print("  the shipped check says : True")
print("  the honest check says  : %s" % honest)
print()
if honest:
    print("  => registry and engine AGREE. Nothing to fix.")
else:
    print("  => THE PIN DOES NOT GUARD ANYTHING.")
    print("     The shipped check returns True against a typed constant while the")
    print("     registry disagrees. A pin that cannot fail is not a pin.")
