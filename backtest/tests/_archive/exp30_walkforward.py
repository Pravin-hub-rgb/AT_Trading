"""Exp 30 — TRUE ANCHORED WALK-FORWARD on the B3-OPT family (audit Q4 debt).

Design: 72-combo grid (chop x mb1h x persist x halt x B3 on/off, cd=10 fixed).
Each combo runs ONCE over the full period (coarse); trades sliced by entry_ts.
6 anchored steps: train = all data before test window, pick combo with best
train NET (gross - 0.22R/trade est. cost), apply frozen to test window.
Baselines: fixed B3-OPT+halt6 cd10 and fixed anchor, sliced identically.
Caveat: engine state (halt streaks) carries across boundaries (full-period
runs); identical treatment for all combos, so comparison is fair.
"""
import sys, time, json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from test_experiments_craze import build_module, BASE, \
    load_candles, _compute_swings, SWING, MB15
import src.btc.engines.htf_ltf.v18_streak_halt as shipped_mod

BP = dict(BASE)
BP["chop_thresh"] = 58.0
CPT = 0.22  # est. cost per trade in R


def ts_of(datestr):
    return int(datetime.strptime(datestr, "%Y-%m-%d")
               .replace(tzinfo=timezone.utc).timestamp())  # candle ts are SECONDS


STEPS = [("2023-07-01", "2024-01-01"), ("2024-01-01", "2024-07-01"),
         ("2024-07-01", "2025-01-01"), ("2025-01-01", "2025-07-01"),
         ("2025-07-01", "2026-01-01"), ("2026-01-01", "2026-10-01")]


def main():
    t0 = time.time()
    (c15, f15), (c1h, f1h) = load_candles()
    sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
    chains = {20: _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"]),
              10: _compute_swings(f1h, "continuous", min_bars=10)}
    sim = build_module()
    T0, T1 = int(c15[0]["ts"]), int(c15[-1]["ts"]) + 900

    r_ship = shipped_mod.simulate_htf_ltf_streak_halt(c1h, chains[20], c15, sw15, fine_ltf=[], **BP)
    s_ship0 = [(t["entry_ts"], t["r_multiple"]) for t in r_ship["ltf_trades"]]
    assert len(s_ship0) == 351, "ANCHOR MISMATCH"
    r0 = sim(c1h, chains[20], c15, sw15, fine_ltf=[], **BP)
    t0_ = r0["ltf_trades"]
    assert len(t0_) == 351 and [t["r_multiple"] for t in t0_] == [r for _, r in s_ship0], "IDENTITY GATE FAILED"
    print("IDENTITY GATE OK (351t exact)\n")

    combos = []
    for chop in (52.0, 55.0, 58.0):
        for mb in (10, 20):
            for pers in (0, 2, 5):
                for halt in (3, 6):
                    for b3k in (0, 8):
                        combos.append((chop, mb, pers, halt, b3k))
    print("grid: %d combos x full-period coarse run" % len(combos))

    def run_combo(chop, mb, pers, halt, b3k):
        h = {"exp_persist": pers} if pers else {}
        if b3k:
            h.update(b3_k=b3k, b3_mode="close")
        po = {"chop_thresh": chop, "max_consecutive_losses": halt}
        r = sim(c1h, chains[mb], c15, sw15, fine_ltf=[], **{**BP, **po, **h})
        tr = r["ltf_trades"]
        return [(int(t["entry_ts"]), float(t["r_multiple"])) for t in tr]

    book = {}
    for i, cb in enumerate(combos):
        book[cb] = run_combo(*cb)
        if (i + 1) % 12 == 0:
            print("  %d/%d (%0.0fs)" % (i + 1, len(combos), time.time() - t0))

    def net(ets, a, b):
        return sum(rr for ts, rr in ets if a <= ts < b) - CPT * len([1 for ts, _ in ets if a <= ts < b])

    def cnt(ets, a, b):
        return len([1 for ts, _ in ets if a <= ts < b])

    fixed_best = (55.0, 10, 2, 6, 8)   # B3-OPT+halt6 cd10
    fixed_anchor = (58.0, 20, 0, 3, 0)

    print("\nstep | train-> test window        | chosen combo (chop/mb/pers/halt/b3) | trainNET | testNET | fixedBest | anchor")
    wf_test = wf_fb = wf_an = 0.0
    for a_s, b_s in STEPS:
        a, b = ts_of(a_s), ts_of(b_s)
        best, best_net = None, -1e9
        for cb in combos:
            tn = net(book[cb], T0, a)
            if tn > best_net:
                best, best_net = cb, tn
        tn_test = net(book[best], a, b)
        fb = net(book[fixed_best], a, b)
        an = net(book[fixed_anchor], a, b)
        wf_test += tn_test; wf_fb += fb; wf_an += an
        print("%s | %s-%s | %s | %+8.1f | %+8.1f | %+8.1f | %+8.1f"
              % (a_s[:7], a_s[:7], b_s[:7], best, best_net, tn_test, fb, an))
    print("\nWF total test NET: %+.1f | fixed B3-OPT+halt6: %+.1f | fixed anchor: %+.1f" % (wf_test, wf_fb, wf_an))
    print("WF retention vs fixed-best config: %.0f%%" % (100.0 * wf_test / wf_fb if wf_fb else 0))
    chosen = {}
    for a_s, b_s in STEPS:
        a, b = ts_of(a_s), ts_of(b_s)
        best, best_net = None, -1e9
        for cb in combos:
            tn = net(book[cb], T0, a)
            if tn > best_net:
                best, best_net = cb, tn
        chosen[best] = chosen.get(best, 0) + 1
    print("chosen combos across steps: %s" % chosen)

    (ROOT / "backtest/tests/_exp30_wf.json").write_text(json.dumps(
        {"steps": STEPS, "wf_test": wf_test, "fixed_best": wf_fb, "fixed_anchor": wf_an,
         "chosen": {"%s/%s/%s/%s/%s" % k: v for k, v in chosen.items()}}))
    print("\n(exp30 walk-forward done %.0fs)" % (time.time() - t0))


if __name__ == "__main__":
    main()
