"""Focused diagnostic: for a few batch trades, rebuild using ALL data up to
entry (not 30-day warmup) and check if the trade reproduces.

The hypothesis: the 0/490 is caused by the 30-day warmup window making the
chain shorter, NOT by a fundamental L5 blocker. If we use all data up to E,
the chain should be identical and the trade should reproduce."""
import sys, time
from pathlib import Path
import datetime as _dt

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from run_experiment import get_data, BP, EXPERIMENTS
from src.btc.btc_routes import _compute_swings
from replay_harness import load_candles, INSTRUMENT
from src.walker import FlowCandle
import test_experiments_craze as craze

G = __import__("engine.v18_params", fromlist=["get_v18_params"]).get_v18_params(INSTRUMENT)
BAR = 900

# L1 patch
L1_OLD = '        for t in trades:\n            if t["outcome"]=="open": continue\n'
L1_NEW = '        for t in trades:\n            if t["outcome"]=="open" and False: continue\n'
orig_loader = craze._load_module

def l1_loader(text, name):
    return orig_loader(text.replace(L1_OLD, L1_NEW), name)


def main():
    t0 = time.time()
    data = get_data()
    craze._load_module = l1_loader
    sim = craze.build_module()
    craze._load_module = orig_loader

    (c15_all, f15_all), (c1h_all, f1h_all) = load_candles()
    params = {**BP, **EXPERIMENTS["champion_multi_sw10"]["params"]}

    batch = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                fine_ltf=data["fine"], **params)["ltf_trades"]
    print("batch: %d trades" % len(batch))

    # Test trades at different points: early, mid, late
    test_indices = [10, 50, 100, 200, 300, 400, 480]
    E0 = int(c15_all[0]["ts"])

    results = {"warmup": 0, "full": 0, "total": 0}

    for ti in test_indices:
        if ti >= len(batch):
            continue
        t = batch[ti]
        E = int(t["entry_ts"])
        d = t["dir"]
        e_end = E + 2 * BAR

        print("\n" + "=" * 60)
        print("Trade #%d: %s %s R=%+.2f  entry=%s" %
              (ti+1, d, t.get("break_kind","?"), float(t["r_multiple"]),
               _dt.datetime.utcfromtimestamp(E/1000).strftime("%Y-%m-%d %H:%M")))

        results["total"] += 1

        # Method 1: 30-day warmup (what the one-pass harness does)
        warm15 = 30 * 86400
        warm1h = 20 * 86400
        sl15_w = [c for c in c15_all if E - warm15 <= c["ts"] <= e_end]
        sl1h_w = [c for c in c1h_all if E - warm1h <= c["ts"] <= e_end]
        f15_w = [FlowCandle(date=c["date"], open=c["open"], high=c["high"],
                            low=c["low"], close=c["close"]) for c in sl15_w]
        f1h_w = [FlowCandle(date=c["date"], open=c["open"], high=c["high"],
                            low=c["low"], close=c["close"]) for c in sl1h_w]
        sw15_w = _compute_swings(f15_w, "continuous", min_bars=50)
        sw10_w = _compute_swings(f1h_w, "continuous", min_bars=10)

        r_w = sim(sl1h_w, sw10_w, sl15_w, sw15_w, fine_ltf=[], **params)
        hit_w = any(x["dir"] == d and E <= int(x["entry_ts"]) <= e_end
                    for x in r_w["ltf_trades"])

        print("  warmup (30d): chain15=%d  chain1h=%d  %s" %
              (len(sw15_w), len(sw10_w), "HIT" if hit_w else "MISS"))

        # Method 2: ALL data up to E+2bars (what live actually sees)
        sl15_f = [c for c in c15_all if c["ts"] <= e_end]
        sl1h_f = [c for c in c1h_all if c["ts"] <= e_end]
        f15_f = [FlowCandle(date=c["date"], open=c["open"], high=c["high"],
                            low=c["low"], close=c["close"]) for c in sl15_f]
        f1h_f = [FlowCandle(date=c["date"], open=c["open"], high=c["high"],
                            low=c["low"], close=c["close"]) for c in sl1h_f]
        sw15_f = _compute_swings(f15_f, "continuous", min_bars=50)
        sw10_f = _compute_swings(f1h_f, "continuous", min_bars=10)

        r_f = sim(sl1h_f, sw10_f, sl15_f, sw15_f, fine_ltf=[], **params)
        hit_f = any(x["dir"] == d and E <= int(x["entry_ts"]) <= e_end
                    for x in r_f["ltf_trades"])

        print("  full (all):  chain15=%d  chain1h=%d  %s" %
              (len(sw15_f), len(sw10_f), "HIT" if hit_f else "MISS"))

        # Method 3: batch chains (should always match)
        r_b = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                  fine_ltf=[], **params)
        hit_b = any(x["dir"] == d and E <= int(x["entry_ts"]) <= e_end
                    for x in r_b["ltf_trades"])
        print("  batch:        chain15=%d  chain1h=%d  %s" %
              (len(data["sw15"]), len(data["sw10"]),
               "HIT (reference)" if hit_b else "MISS (unexpected)"))

        if hit_f:
            results["full"] += 1
        if hit_w:
            results["warmup"] += 1

    print("\n" + "=" * 60)
    print("SUMMARY:")
    print("  Tested: %d trades" % results["total"])
    print("  Warmup (30d window, what one-pass does): %d/%d reproduce" %
          (results["warmup"], results["total"]))
    print("  Full (all data, what live sees):          %d/%d reproduce" %
          (results["full"], results["total"]))
    print("  (%.0fs)" % (time.time() - t0))


if __name__ == "__main__":
    main()
