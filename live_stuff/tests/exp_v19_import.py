import sys, os, pickle
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
for p in ("live_stuff","live_stuff/tests","backend"):
    sys.path.insert(0,str(ROOT/p))
sys.path.append(str(ROOT/"backend"/"src"))
# REAL IMPORT - not exec, not compile, not read_text
from src.btc.engines.htf_ltf.v19_champion import simulate_htf_ltf_streak_halt as V19
import inspect
print("imported OK from:",inspect.getfile(V19))
print("is it the committed file?", "v19_champion" in inspect.getfile(V19))
with open(Path(os.environ["TEMP"])/"at_datacache.pkl","rb") as f: d=pickle.load(f)
from run_experiment import net_r
from experiment_registry import BP,EXPERIMENTS
from exp_concurrency_guard import pf
pr={**BP,**EXPERIMENTS["champion_multi_sw10"]["params"]}
p={k:v for k,v in pr.items() if k not in {"exp_mltf","exp_persist","exp_partial_r"}}
r=V19(d["c1h"],d["sw10"],d["c15"],d["sw15"],fine_ltf=d["fine"],**p)
tr=[t for t in r["ltf_trades"] if t.get("outcome")!="open"]
rs=[float(t["r_multiple"]) for t in tr]

# Read pins from registry (not hardcoded literals)
pin = EXPERIMENTS["champion_multi_sw10"]["pins"]
pin_n = int(pin.get("n", -1))
pin_net = float(pin.get("net", 1e9))
pin_dd = float(pin.get("dd", 1e9))

# Calculate DD
cum = 0.0
peak = 0.0
max_dd = 0.0
for r_val in rs:
    cum += r_val
    if cum > peak:
        peak = cum
    dd = peak - cum
    if dd > max_dd:
        max_dd = dd

print()
print("REAL IMPORT, v19_champion.py from disk:")
print("  IS  n=%d  net=%+.2fR  PF=%.3f  DD=%.2f"%(len(rs),net_r(tr),pf(rs), max_dd))
print("  PIN  n=%d  net=%.2fR  DD=%.2f"%(pin_n, pin_net, pin_dd))
match_n = len(rs) == pin_n
match_net = abs(net_r(tr) - pin_net) < 0.5
match_dd = abs(max_dd - pin_dd) < 0.5
print("  MATCH n:  %s  (engine=%d vs pin=%d)"%(match_n, len(rs), pin_n))
print("  MATCH net: %s  (engine=%.2f vs pin=%.2f)"%(match_net, net_r(tr), pin_net))
print("  MATCH dd:  %s  (engine=%.2f vs pin=%.2f)"%(match_dd, max_dd, pin_dd))
print("  OVERALL MATCH: %s"%(match_n and match_net and match_dd))

# NEGATIVE CONTROL: if we corrupt the pin, check MUST fail
print()
print("NEGATIVE CONTROL: corrupting pin to force FAIL...")
corrupt_net = pin_net + 999.0
corrupt_match = abs(net_r(tr) - corrupt_net) < 0.5
print("  Corrupted pin net=%.2f -> match=%s (MUST be False)"%(corrupt_net, corrupt_match))
if corrupt_match:
    print("  FAIL: Negative control PASSED (pin check cannot detect corruption)")
else:
    print("  PASS: Negative control FAILED as expected (pin check works)")