"""Diagnose WHY the one-pass study gets 0/490.

For each batch trade, rebuild the causal slice and check:
1. Is the LTF signal present in the rebuilt chain?
2. Is the HTF interval present in the rebuilt chain?
3. Does the trade appear in the sim output?

Shows the FIRST 20 failed trades with exact root cause.
"""
import sys, time
from pathlib import Path
from collections import defaultdict
import datetime as _dt

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from run_experiment import get_data, BP, EXPERIMENTS
from src.btc.btc_routes import _trade_costs, _compute_swings
from engine.v18_params import get_v18_params as gvp
from replay_harness import load_candles, INSTRUMENT
from src.walker import FlowCandle
import test_experiments_craze as craze

G = gvp(INSTRUMENT)
DAY = 86400
BAR = 900

# L1 patch (same as one-pass harness)
SRC = craze.SRC
L1_OLD = '        for t in trades:\n            if t["outcome"]=="open": continue\n'
L1_NEW = '        for t in trades:\n            if t["outcome"]=="open" and False: continue\n'
orig_loader = craze._load_module

def l1_loader(text, name):
    t = text.replace(L1_OLD, L1_NEW)
    return orig_loader(t, name)


def main():
    t0 = time.time()
    data = get_data()
    craze._load_module = l1_loader
    sim = craze.build_module()
    craze._load_module = orig_loader

    (c15_all, f15_all), (c1h_all, f1h_all) = load_candles()
    params = {**BP, **EXPERIMENTS["champion_multi_sw10"]["params"]}

    # Get batch trades
    batch = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                fine_ltf=data["fine"], **params)["ltf_trades"]
    print("batch: %d trades" % len(batch))

    E0 = int(c15_all[0]["ts"])
    warm15 = 30 * DAY
    warm1h = 20 * DAY

    # Diagnose first 20 trades
    n_diag = min(20, len(batch))
    for ti in range(n_diag):
        t = batch[ti]
        E = int(t["entry_ts"])
        d = t["dir"]
        entry_px = float(t["entry_price"])
        sl_px = float(t["sl"])

        if E - E0 < warm15:
            print("\n--- Trade #%d: SKIP (warmup) ---" % (ti+1))
            continue

        print("\n" + "=" * 70)
        print("TRADE #%d: %s %s entry=%.1f sl=%.1f R=%+.2f  entry_ts=%s" %
              (ti+1, t["dir"], t.get("break_kind","?"), entry_px, sl_px,
               float(t["r_multiple"]),
               _dt.datetime.utcfromtimestamp(E/1000).strftime("%Y-%m-%d %H:%M")))
        print("=" * 70)

        # 1. Build causal slice
        e_end = E + 2 * BAR
        sl15 = [c for c in c15_all if E - warm15 <= c["ts"] <= e_end]
        sl1h = [c for c in c1h_all if E - warm1h <= c["ts"] <= e_end]
        f15 = [FlowCandle(date=c["date"], open=c["open"], high=c["high"],
                          low=c["low"], close=c["close"]) for c in sl15]
        f1h = [FlowCandle(date=c["date"], open=c["open"], high=c["high"],
                          low=c["low"], close=c["close"]) for c in sl1h]

        # 2. Rebuild chains
        sw15c = _compute_swings(f15, "continuous", min_bars=50)
        sw10c = _compute_swings(f1h, "continuous", min_bars=10)

        # 3. Compare chain lengths
        print("  15m chain: batch=%d  causal=%d  delta=%d" %
              (len(data["sw15"]), len(sw15c), len(data["sw15"]) - len(sw15c)))
        print("  1h chain:  batch=%d  causal=%d  delta=%d" %
              (len(data["sw10"]), len(sw10c), len(data["sw10"]) - len(sw10c)))

        # 4. Check the specific swing that produced this trade
        swing_no = int(t["swing_no"])
        print("  batch swing_no=%d  dir=%s  kind=%s" %
              (swing_no, t["dir"], t.get("break_kind","?")))

        if swing_no < len(data["sw15"]):
            bsw = data["sw15"][swing_no]
            print("  batch swing: dir=%s start_idx=%s end_idx=%s confirmed=%s" %
                  (bsw.get("dir"), bsw.get("seg", {}).get("start_idx"),
                   bsw.get("seg", {}).get("end_idx"),
                   bsw.get("confirmed_at_idx")))
            if bsw.get("breaks"):
                for bk in bsw["breaks"]:
                    print("    break: kind=%s dir=%s time=%s px=%s" %
                          (bk.get("kind"), bk.get("dir"),
                           bk.get("time", "")[:19], bk.get("px")))

        # 5. Check if the swing exists in causal chain
        found_in_causal = False
        if swing_no < len(sw15c):
            csw = sw15c[swing_no]
            print("  causal swing: dir=%s start_idx=%s end_idx=%s confirmed=%s" %
                  (csw.get("dir"), csw.get("seg", {}).get("start_idx"),
                   csw.get("seg", {}).get("end_idx"),
                   csw.get("confirmed_at_idx")))
            if csw.get("breaks"):
                for bk in csw["breaks"]:
                    print("    break: kind=%s dir=%s time=%s px=%s" %
                          (bk.get("kind"), bk.get("dir"),
                           bk.get("time", "")[:19], bk.get("px")))
            found_in_causal = True
        else:
            print("  causal: swing_no %d NOT IN CHAIN (chain has only %d swings)" %
                  (swing_no, len(sw15c)))

        # 6. Compare batch signal bar vs causal
        batch_bar = t.get("entry_date", "")[:19]
        print("  batch entry bar: %s" % batch_bar)

        # 7. Run sim on causal slice
        r = sim(sl1h, sw10c, sl15, sw15c, fine_ltf=[], **params)
        cand = r["ltf_trades"]
        hit = None
        for x in cand:
            if x["dir"] == d and E <= int(x["entry_ts"]) <= e_end:
                hit = x
                break

        if hit:
            print("  RESULT: REPRODUCES (R=%+.2f)" % float(hit["r_multiple"]))
        else:
            print("  RESULT: DOES NOT REPRODUCE")
            # Check: are there ANY signals from the same swing_no in the sim?
            for x in cand:
                if x.get("swing_no") == swing_no:
                    print("    -> same swing_no found but dir=%s (need %s) or entry_ts mismatch" %
                          (x["dir"], d))

            # 8. Check if signal collection finds the mark
            from src.btc.btc_engine import _collect_signals, CandleStore
            ltf_store_c = CandleStore(sl15)
            causal_sigs = _collect_signals(sw15c, "decisive", skip_first=True,
                                           selection="stream", candles=sl15)
            # Check if any signal matches the batch trade's bar and direction
            bar_found = False
            for sig in causal_sigs:
                if sig["bar"] == t.get("entry_date", "")[:19] and sig["dir"] == (1 if d == "long" else -1):
                    bar_found = True
                    print("    -> signal FOUND in causal chain at same bar")
                    break
            if not bar_found:
                # Check: was the signal present but at a different bar?
                for sig in causal_sigs:
                    if sig["dir"] == (1 if d == "long" else -1) and sig.get("kind") == t.get("break_kind"):
                        sig_ts = ltf_store_c.pos(sig["bar"])
                        print("    -> same-dir %s signal found at bar %s (batch bar: %s)" %
                              (sig["kind"], sig["bar"][:19], batch_bar))
                        break
                else:
                    print("    -> NO matching signal in causal chain at all")

            # 9. Check HTF intervals
            from src.btc.engines.v7_timecap import simulate_btc_trades_v7
            htf_flip_c = simulate_btc_trades_v7(sl1h, sw10c, entry_break="flip",
                                                  sl_mode="swing", rr_target=3.0,
                                                  trailing="off", breakeven_r=0.0,
                                                  skip_first=True, cap_days=16)
            htf_b2_c = simulate_btc_trades_v7(sl1h, sw10c, entry_break="b2",
                                                sl_mode="swing", rr_target=3.0,
                                                trailing="off", breakeven_r=0.0,
                                                skip_first=True, cap_days=16)

            # Check if the batch trade's HTF interval exists
            batch_kind = t.get("break_kind", "")
            if batch_kind == "FLIP":
                batch_htf = [x for x in data["htf_trades"] if int(x["entry_ts"]) <= E <= int(x["exit_ts"])
                             and x["dir"] == d]
            else:
                batch_htf = [x for x in data.get("htf_trades_b2", []) if int(x["entry_ts"]) <= E <= int(x["exit_ts"])]
            if batch_htf:
                htf_entry = batch_htf[0]
                htf_e = int(htf_entry["entry_ts"])
                htf_dir = htf_entry["dir"]
                print("  batch HTF window: entry=%s dir=%s exit=%s" %
                      (_dt.datetime.utcfromtimestamp(htf_e/1000).strftime("%Y-%m-%d %H:%M"),
                       htf_dir,
                       _dt.datetime.utcfromtimestamp(int(htf_entry["exit_ts"])/1000).strftime("%Y-%m-%d %H:%M")))

                # Does this window exist in causal HTF?
                if batch_kind == "FLIP":
                    causal_htf = [x for x in htf_flip_c if int(x["entry_ts"]) <= E <= int(x["exit_ts"])
                                  and x["dir"] == htf_dir]
                else:
                    causal_htf = [x for x in htf_b2_c if int(x["entry_ts"]) <= E <= int(x["exit_ts"])]
                if causal_htf:
                    print("  causal HTF window: EXISTS")
                else:
                    print("  causal HTF window: MISSING — this is the root cause")
            else:
                print("  batch HTF window: NOT FOUND (unexpected)")

    print("\n" + "=" * 70)
    print("DONE (%.0fs)" % (time.time() - t0))


if __name__ == "__main__":
    main()
