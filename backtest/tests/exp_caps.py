"""P49 - BOTH OPEN CAPS, and the 1d-vs-2d decision the owner asked for.

  PART 1  the decay age cap, swept past the two points already on record
  PART 2  P4, the window `cap_days` parameter - literally 16 in three call
          sites of v18_streak_halt.py and never swept

TWO VOID RUNS, AND WHY THEY WERE VOID
    Run A of PART 2 reported cap_days inert - every value from 6 to 32
    gave byte-identical books. That was a harness bug, not a finding. The
    v18 module does `from src.btc.engines.v7_timecap import
    simulate_btc_trades_v7` INSIDE the function body, so the name is bound
    at CALL time, not at exec time. The patch was installed, build_module()
    was called, and the `finally` restored the original before the engine
    was ever invoked. The patch never applied. cap_days=16 matched the
    control only because the unpatched default is also 16. A separate probe
    with the patch held across the call gives 586t/+401.1R at cap_days=0 and
    233t/-16.5R at 1 - the parameter is emphatically not inert.

    Run A of PART 1 capped WINDOW age, not decay-LEG age. P38's cap is on
    the age of the legs the decay feature reads, which is a different
    quantity; the window-age numbers are W1's question and W1 is already
    closed. Corrected here to the age of the OLDEST of the last 4 confirmed
    buying legs, which is the leg P38 called stale.

THE REGISTRATION P3 ALREADY DEMANDED
    The queue records that P3 flipped this parameter's sign, so a cap is a
    PASS only if it beats 16 days in BOTH eras, and any arm that lowers the
    cap is expected to cost trades rather than gain them. Pre-registered
    before the run so a good IS number cannot be promoted on its own.

THE LEG-AGE RULE, WRITTEN OUT
    decay is the fraction of broken buying legs over the last 4. When the
    OLDEST of those 4 is older than the cap, the feature is reading stale
    structure - and stale legs were measured to be GOOD, so the correct
    action is to withhold judgement, not to apply it. Withheld means decay
    reads 0.5, which passes the < 0.75 gate. That is what "cap" means here.
"""
import bisect as bs
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate, net_r
import test_experiments_craze as tc
from test_4_new_concepts import load_unseen, load_fine_1m
from test_experiments_craze import _compute_swings
from engine.v18_params import SWING
from exp_decay_switch import legs_by_dir, decay_pair

M_NULL = 193.4
CAPD = (0, 1, 2, 3, 4, 6, 8, 12, 16, 20, 24, 32, 999)
AGED = (0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 7.0)
LANES = (
    ("champion_multi_sw10", "sw10", (500, 325.8), (279, 70.1)),
    ("utcsat_multi_sw10", "sw10", (454, 358.9), (253, 60.2)),
)


def pf(rs):
    return sum(x for x in rs if x > 0) / max(1e-9, -sum(x for x in rs if x < 0))


def get(scope, swtag):
    if scope == "oos":
        (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
        return (c1h, _compute_swings(f1h, "continuous", min_bars=10),
                c15, _compute_swings(f15, "continuous",
                                     min_bars=SWING["min_bars_15m"]),
                load_fine_1m(c15[0]["ts"], c15[-1]["ts"]))
    d = get_data()
    identity_gate(d, tc.build_module())
    return d["c1h"], d[swtag], d["c15"], d["sw15"], d["fine"]


def run_cap(cap, a, params):
    """Build AND call with the patch live across both. File never written."""
    from src.btc.engines import v7_timecap as v7
    orig = v7.simulate_btc_trades_v7

    def wrapped(*ar, **kw):
        kw["cap_days"] = cap
        return orig(*ar, **kw)

    v7.simulate_btc_trades_v7 = wrapped
    try:
        m = tc.build_module()
        return m(*a, **params)
    finally:
        v7.simulate_btc_trades_v7 = orig


def line(lbl, tr, nb):
    if len(tr) < 15:
        print("      %-30s %5d   (too few)" % (lbl, len(tr)))
        return None
    rs = [float(x["r_multiple"]) for x in tr]
    net = net_r(tr)
    d = net - nb
    wr = 100.0 * sum(1 for x in rs if x > 0) / len(rs)
    flag = " *" if abs(d) > M_NULL else ""
    print("      %-30s %5d %+9.1fR %+8.1fR PF %5.2f WR %5.1f%%%s"
          % (lbl, len(tr), net, d, pf(rs), wr, flag))
    return d


def main():
    print("=" * 100)
    print("  P49  BOTH OPEN CAPS      (M = %.1fR)" % M_NULL)
    print("  run 2 - part 1 now caps DECAY-LEG age, part 2 patch held live")
    print("=" * 100)
    print("  P4 pass rule PRE-REGISTERED: beat cap_days=16 in BOTH eras.\n")
    for key, swtag, ispin, oospin in LANES:
        params = {**BP, **EXPERIMENTS[key]["params"]}
        print("  --- %s" % key)
        for scope, pin in (("is", ispin), ("oos", oospin)):
            a = get(scope, swtag)
            r0 = run_cap(16, a, params)
            t0 = [t for t in r0["ltf_trades"] if t.get("outcome") != "open"]
            net0, n0 = net_r(t0), len(t0)
            if abs(n0 - pin[0]) > 2 or abs(net0 - pin[1]) > 1.5:
                print("    [%s] cap_days=16 CONTROL FAILED %dt %+.1fR "
                      "-- STOP" % (scope, n0, net0))
                return
            print("    [%s] control %dt %+.1fR (PIN ok, cap_days=16)"
                  % (scope.upper(), n0, net0))
            print("      PART 2  P4 window cap_days  (999 = uncapped)")
            for cd in CAPD:
                if cd == 16:
                    line("cap_days=16 (control)", t0, net0)
                    continue
                rr = run_cap(cd, a, params)
                tt = [t for t in rr["ltf_trades"]
                      if t.get("outcome") != "open"]
                line("cap_days=%s" % ("999 (none)" if cd == 999 else cd),
                     tt, net0)
            # ---- PART 1 : decay + LEG-age cap
            r = tc.build_module()(*a, **params)
            tr = [t for t in r["ltf_trades"] if t.get("outcome") != "open"]
            nb = net_r(tr)
            up, dn = legs_by_dir(a[3])
            upc = [L["cts"] for L in up]
            fts = [int(c["ts"]) for c in a[4]]
            flo = [float(c["low"]) for c in a[4]]
            fhi = [float(c["high"]) for c in a[4]]
            for t in tr:
                ts = int(t["entry_ts"])
                dv, _ = decay_pair(up, dn, ts, flo, fhi, fts, n=4)
                t["_u"] = 0.5 if dv is None else dv
                k = bs.bisect_right(upc, ts) - 1
                if k >= 3:
                    t["_la"] = (ts - upc[k - 3]) / 86400.0
                else:
                    t["_la"] = 0.0
            print("      PART 1  decay < 0.75 with a LEG-age cap")
            las = sorted(t["_la"] for t in tr)
            print("      %-30s %5.2f / %.2f / %.2f"
                  % ("oldest-of-4 leg age p50/90/max", las[len(las) // 2],
                     las[int(len(las) * 0.9)], max(las)))
            line("A no filter", tr, nb)
            line("decay<0.75, no leg cap",
                 [t for t in tr if t["_u"] < 0.75], nb)
            for g in AGED:
                line("decay<0.75, legs <=%.1fd old" % g,
                     [t for t in tr
                      if t["_la"] <= g and t["_u"] < 0.75], nb)
            print()
    print("  * = |dNet| exceeds M. Nothing adopted.")


if __name__ == "__main__":
    main()