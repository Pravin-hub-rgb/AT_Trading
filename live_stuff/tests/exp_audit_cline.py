"""Independent pre-live audit (Cline) — verify NEW king champion_multi_sw10 (no partials).

Run:  python live_stuff/tests/exp_audit_cline.py [key]
"""
import sys, time
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from run_experiment import get_data, run_one, fund
from src.btc.btc_routes import _trade_costs
from engine.v18_params import get_v18_params as gvp
from src.btc.engines.htf_ltf.v18_streak_halt import _atr_pct_15m

G = gvp("BTCUSDT_BYBIT")


def full_stats(tr, net_dd=False, costs=None):
    rs = [float(t["r_multiple"]) for t in tr]
    if net_dd:
        adj = {id(t): rs[i] - (costs[i] if costs else 0.0) for i, t in enumerate(tr)}
        rs = [adj[id(t)] for t in tr]
    peak = cum = dd = 0.0
    for x in rs:
        cum += x; peak = max(peak, cum); dd = max(dd, peak - cum)
    return {"n": len(tr), "gross": sum(rs), "dd": dd,
            "wr": 100.0 * len([x for x in rs if x > 0]) / max(len(tr), 1)}


def audit(key, data, sim):
    tr, el = run_one(key, data, sim)
    print("\n===== INDEPENDENT AUDIT: %s (%.0fs) =====" % (key, el))
    n = len(tr)
    rs = [float(t["r_multiple"]) for t in tr]
    parts = [t for t in tr if float(t.get("partial_exit_price", 0.0)) > 0]
    print("[C1] n=%d partials=%d gross=%+.2f" % (n, len(parts), sum(rs)))
    losses = [x for x in rs if x < 0]; wins = [x for x in rs if x > 0]
    print("[C1] avgR=%+.3f avgW=%+.3f avgL=%+.3f maxR=%+.2f minR=%+.2f" %
          (sum(rs)/n, sum(wins)/len(wins), sum(losses)/len(losses), max(rs), min(rs)))
    print("[C1] n(r>20)=%d n(r<-2)=%d zero-bar=%d" %
          (len([x for x in rs if 20 < x]), len([x for x in rs if x < -2]),
           len([t for t in tr if int(t["bars_held"]) == 0])))
    print("[C1] trades with R above 20 (eyeball check):")
    for t in sorted(tr, key=lambda t: -float(t["r_multiple"]))[:8]:
        print("     t%-4d %s %-5s R=%+7.2f bh=%d %s -> %s out=%s e=%.1f x=%.1f" % (
            t["trade_no"], (t.get("entry_date") or "")[:16], t["dir"], float(t["r_multiple"]),
            int(t["bars_held"]), (t.get("entry_date") or "")[:10], (t.get("exit_date") or "")[:10],
            t["outcome"], float(t["entry_price"]), float(t["exit_price"])))

    # costs per trade
    costs = []
    for t in tr:
        c = [0.0]
        _trade_costs([t], G["fee_pct"], 0.0, G["entry_slip_pct"], G["exit_slip_pct"])
        costs.append(float(t.get("cost_r", 0.0)))
    f = fund(tr)
    net = sum(rs) - sum(costs) - f
    s_g = full_stats(tr)
    s_n = full_stats(tr, net_dd=True, costs=costs)
    print("[C1] ENGINE  : NET=%+.1f DD(gross)=%.1f WR=%.1f%%" % (net, s_g["dd"], s_g["wr"]))
    print("[C1] NET-based DD (fees+slip on curve) = %.1f | funding=%.1fR cost=%.1fR" %
          (s_n["dd"], f, sum(costs)))

    # walk-forward 6 segments
    seg = n // 6
    wfs = [sum(rs[i*seg:(i+1)*seg]) for i in range(6)]
    print("[C1] worst6=%+.1f  segs=%s" % (min(wfs), ["%+.1f" % w for w in wfs]))
    py = defaultdict(float)
    for t in tr:
        py[(t.get("exit_date") or t.get("entry_date") or "")[:4]] += float(t["r_multiple"])
    print("[C1] minYear=%+.1f  yearly=%s" % (min(py.values()), {k: round(v, 1) for k, v in sorted(py.items())}))

    # concurrency
    evs = sorted([(int(t["entry_ts"]), 1) for t in tr] + [(int(t["exit_ts"]), -1) for t in tr])
    cur = peak = 0
    for _, dv in evs:
        cur += dv; peak = max(peak, cur)
    dist = defaultdict(int); cur = 0
    for _, dv in evs:
        if dv == 1: dist[cur] += 1; cur += 1
        else: cur -= 1
    print("[C3] peak concurrent=%d  entries-by-busy-level=%s" % (peak, dict(sorted(dist.items()))))

    # regime / atr_high semantics
    reg = defaultdict(int)
    for t in tr: reg[t["htf_regime"]] += 1
    print("[C5] htf_regime mix=%s  (mode atr_high: flip rows = ATRpct at/below 0.65 at entry => interval switch, NOT a filter)" % dict(reg))

    oc = defaultdict(int)
    for t in tr: oc[t["outcome"]] += 1
    print("[C6] outcomes=%s" % dict(oc))
    opens = [t for t in tr if t["outcome"] == "open"]
    if opens:
        last_ts = max(int(c["ts"]) for c in data["f1h"])
        print("[C6] 'open' trades=%d  last entry=%s  (MTM at last fine close — check none are stale)" %
              (len(opens), (opens[0].get("entry_date") or "")[:16]))

    def row(t):
        return "t%-4d %-5s %s->%s e=%9.1f x=%9.1f sl=%9.1f pe=%8.1f R=%+7.2f %-6s bh=%d" % (
            t["trade_no"], t["dir"], (t.get("entry_date") or "")[5:16], (t.get("exit_date") or "")[5:16],
            float(t["entry_price"]), float(t["exit_price"]), float(t["sl"]),
            float(t.get("partial_exit_price", 0.0)), float(t["r_multiple"]), t["outcome"][:6], int(t["bars_held"]))
    print("--- first 20 ---")
    for t in tr[:20]: print(row(t))
    print("--- last 20 ---")
    for t in tr[-20:]: print(row(t))
    print("--- worst 5 ---")
    for t in sorted(tr, key=lambda t: float(t["r_multiple"]))[:5]: print(row(t))
    return tr


def main():
    key = sys.argv[1] if len(sys.argv) > 1 else None
    data = get_data()
    sim = __import__("test_experiments_craze").build_module()
    atr = _atr_pct_15m(data["c15"])
    print("ATR%% sanity: last-bar atr%%=%.3f" % atr[-1])
    if key:
        audit(key, data, sim)
        return
    audit("champion_multi_sw10", data, sim)
    audit("champion_multi_sw20", data, sim)
    tr, _ = run_one("baseline_no_partial_sw10", data, sim)
    rs = [float(t["r_multiple"]) for t in tr]
    print("\n[cross] baseline_no_partial_sw10: n=%d gross=%+.1f (pin 394/163.6)" % (len(tr), sum(rs)))


if __name__ == "__main__":
    main()
