import sys, pickle, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest","backtest/tests","backtest/sweeps","backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))
import src.btc.btc_engine as _be
from src.btc.engines.htf_ltf.v19_champion import simulate_htf_ltf_streak_halt as V19
FEE, ES, XS, FUND = 0.055, 0.005, 0.01, 0.01
with open(Path(__import__("os").environ["TEMP"]) / "at_datacache.pkl", "rb") as f:
    d = pickle.load(f)
pr = dict(sl_buf_atr=0.01, ext_stop_r=3.0, mode="atr_high", chop_thresh=58.0,
          cooldown_bars=8, max_consecutive_losses=3, htf_rr=3.0, window_end="exit")
def cost(t):
    rk = abs(float(t["entry_price"]) - float(t["sl"]))
    if rk <= 0: return 0.0, 0.0
    e = abs(float(t["entry_price"])); x = abs(float(t.get("exit_price", t["entry_price"])))
    fee = (e + x) * (FEE / 100.0) / rk
    slp = (e * (ES / 100.0) + x * (XS / 100.0)) / rk
    fnd = e * (FUND / 100.0) / 32.0 * int(t.get("bars_held", 0)) / rk
    return fee + slp + fnd, fnd
def run(rule):
    o = _be._collect_signals
    if rule == "origin":
        def w(*a, **k):
            k["pivot_rule"] = "origin"; return o(*a, **k)
        _be._collect_signals = w
    try:
        return V19(d["c1h"], d["sw10"], d["c15"], d["sw15"], fine_ltf=d["fine"], exp_causal_sl=0, **pr)["ltf_trades"]
    finally:
        _be._collect_signals = o
def rep(nm, tr):
    cl = [x for x in tr if x.get("outcome") != "open"]
    g = sum(float(x["r_multiple"]) for x in cl)
    cs = sum(cost(x)[0] for x in cl); fd = sum(cost(x)[1] for x in cl)
    rk = [abs(float(x["entry_price"]) - float(x["sl"])) for x in cl]
    print("%-22s %4d trades | gross %8.2fR | cost %7.2fR (fund %6.2f) | NET %8.2fR | avg risk %8.1f"
          % (nm, len(cl), g, cs, fd, g - cs, sum(rk) / len(rk)))
    return {(x.get("entry_ts"), x.get("dir")): x for x in cl}
print("=" * 118)
L = rep("leg (POST-C16, live)", run("leg"))
O = rep("origin (PRE-C16, lookahd)", run("origin"))
print("=" * 118)
print("registry pin  : 500 trades / net 325.78R   <-- NET basis, older code")
print()
print("membership : only-leg %d   only-origin %d   shared %d" % (len(set(L) - set(O)), len(set(O) - set(L)), len(set(L) & set(O))))
ch = [k for k in set(L) & set(O) if abs(float(L[k]["r_multiple"]) - float(O[k]["r_multiple"])) > 1e-9
      or abs(float(L[k]["sl"]) - float(O[k]["sl"])) > 1e-9]
print("stop or R changed on %d trades:" % len(ch))
for k in sorted(ch):
    a, b = L[k], O[k]
    print("  %s %-5s | sl %9.1f -> %9.1f | risk %7.1f -> %7.1f | R %+6.2f -> %+6.2f | cost %.2f -> %.2f"
          % (k[0], str(k[1]).upper(), float(b["sl"]), float(a["sl"]),
             abs(float(b["entry_price"]) - float(b["sl"])), abs(float(a["entry_price"]) - float(a["sl"])),
             float(b["r_multiple"]), float(a["r_multiple"]), cost(b)[0], cost(a)[0]))
tot = sum(float(O[k]["r_multiple"]) - float(L[k]["r_multiple"]) for k in ch)
tc = sum(cost(L[k])[0] - cost(O[k])[0] for k in ch)
print()
print("  gross R delta on changed trades : %+.2fR" % tot)
print("  cost  R delta on changed trades : %+.2fR" % tc)
print("  net  R delta on changed trades : %+.2fR" % (tot + tc))
