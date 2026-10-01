"""Deep diagnostic: compare the first N swings of batch chain vs full-data chain
to find exactly where they diverge."""
import sys, time
from pathlib import Path
import datetime as _dt

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from run_experiment import get_data, BP, EXPERIMENTS
from src.btc.btc_routes import _compute_swings
from replay_harness import load_candles, INSTRUMENT
from src.walker import FlowCandle
import test_experiments_craze as craze

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

    # Pick trade #481 (last test): short B2, entry near end of data
    ti = 480
    t = batch[ti]
    E = int(t["entry_ts"])
    e_end = E + 2 * BAR

    print("Trade #%d: %s %s R=%+.2f  entry=%s" %
          (ti+1, t["dir"], t.get("break_kind","?"), float(t["r_multiple"]),
           _dt.datetime.utcfromtimestamp(E/1000).strftime("%Y-%m-%d %H:%M")))

    # Full data up to e_end
    sl15_f = [c for c in c15_all if c["ts"] <= e_end]
    sl1h_f = [c for c in c1h_all if c["ts"] <= e_end]
    f15_f = [FlowCandle(date=c["date"], open=c["open"], high=c["high"],
                        low=c["low"], close=c["close"]) for c in sl15_f]
    f1h_f = [FlowCandle(date=c["date"], open=c["open"], high=c["high"],
                        low=c["low"], close=c["close"]) for c in sl1h_f]
    sw15_f = _compute_swings(f15_f, "continuous", min_bars=50)
    sw10_f = _compute_swings(f1h_f, "continuous", min_bars=10)

    sw15_b = data["sw15"]
    sw10_b = data["sw10"]

    print("\nChain lengths: batch15=%d full15=%d | batch10=%d full10=%d" %
          (len(sw15_b), len(sw15_f), len(sw10_b), len(sw10_f)))

    # Compare first N swings
    print("\n--- 15m swing comparison (first 10) ---")
    print("%-4s  %-6s %-6s | %-6s %-6s | %s" %
          ("#", "b_dir", "b_seg", "f_dir", "f_seg", "match?"))
    n_compare = min(len(sw15_b), len(sw15_f), 10)
    for i in range(n_compare):
        b = sw15_b[i]
        f = sw15_f[i]
        b_dir = b.get("dir", "?")
        f_dir = f.get("dir", "?")
        b_seg = "%s->%s" % (b["seg"]["start_idx"], b["seg"]["end_idx"])
        f_seg = "%s->%s" % (f["seg"]["start_idx"], f["seg"]["end_idx"])
        match = "OK" if b_dir == f_dir and b_seg == f_seg else "DIFF"
        print("%-4d  %-6s %-6s | %-6s %-6s | %s" %
              (i, b_dir, b_seg, f_dir, f_seg, match))

    # Find first divergence
    print("\n--- Finding first divergence ---")
    first_diff = -1
    for i in range(min(len(sw15_b), len(sw15_f))):
        b = sw15_b[i]
        f = sw15_f[i]
        if b.get("dir") != f.get("dir") or \
           b["seg"]["start_idx"] != f["seg"]["start_idx"] or \
           b["seg"]["end_idx"] != f["seg"]["end_idx"]:
            first_diff = i
            break
    if first_diff >= 0:
        print("First divergence at swing #%d" % first_diff)
        b = sw15_b[first_diff]
        f = sw15_f[first_diff]
        print("  batch: dir=%s seg=%s->%s confirmed=%s breaks=%s" %
              (b.get("dir"), b["seg"]["start_idx"], b["seg"]["end_idx"],
               b.get("confirmed_at_idx"), len(b.get("breaks", []))))
        print("  full:  dir=%s seg=%s->%s confirmed=%s breaks=%s" %
              (f.get("dir"), f["seg"]["start_idx"], f["seg"]["end_idx"],
               f.get("confirmed_at_idx"), len(f.get("breaks", []))))
    else:
        if len(sw15_b) == len(sw15_f):
            print("Chains are IDENTICAL (all %d swings match)" % len(sw15_b))
        else:
            min_len = min(len(sw15_b), len(sw15_f))
            print("First %d swings match. Divergence at chain end (batch=%d full=%d)" %
                  (min_len, len(sw15_b), len(sw15_f)))

    # Now check: does the batch trade's signal bar appear in the FULL chain?
    batch_bar = t.get("entry_date", "")[:19]
    print("\n--- Looking for batch signal in full chain ---")
    print("  Batch entry bar: %s" % batch_bar)
    from src.btc.btc_engine import _collect_signals, CandleStore
    ltf_store_f = CandleStore(sl15_f)
    full_sigs = _collect_signals(sw15_f, "decisive", skip_first=True,
                                 selection="stream", candles=sl15_f)
    print("  Full chain signals: %d total" % len(full_sigs))
    for sig in full_sigs:
        if sig["bar"] == batch_bar:
            print("  FOUND: bar=%s dir=%s kind=%s sl=%.1f" %
                  (sig["bar"], sig["dir"], sig["kind"], sig["swing_start_px"]))
            break
    else:
        # Check if signal is there but at a different bar
        matching = [s for s in full_sigs
                    if s["dir"] == (1 if t["dir"] == "long" else -1)
                    and s["kind"] == t.get("break_kind", "")]
        print("  NOT FOUND at batch bar. Signals with same dir+kind: %d" %
              len(matching))
        for s in matching[:5]:
            print("    bar=%s kind=%s sl=%.1f" % (s["bar"], s["kind"], s["swing_start_px"]))

    # Check: does the BATCH chain produce a signal at this bar?
    batch_sigs = _collect_signals(sw15_b, "decisive", skip_first=True,
                                  selection="stream", candles=c15_all)
    for sig in batch_sigs:
        if sig["bar"] == batch_bar:
            print("\n  Batch chain signal at bar: dir=%s kind=%s sl=%.1f swing_no=%s" %
                  (sig["dir"], sig["kind"], sig["swing_start_px"], sig["swing_no"]))
            break

    print("\n(%.0fs)" % (time.time() - t0))


if __name__ == "__main__":
    main()
