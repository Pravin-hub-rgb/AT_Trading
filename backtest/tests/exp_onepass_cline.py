"""SEQUENTIAL ONE-PASS CAUSAL STUDY (C10 spec) — the honest live-expected number.

For every batch trade of champion_multi_sw10 (chronological):
  1. build a live-style causal slice (data up to discovery instant ONLY),
     chains rebuilt fresh on the SAME lists passed to the sim (L3),
  2. run the EXACT sim call with the L1 patch (open window = active bias),
  3. accept the trade if it reproduces (same dir, entry within the +2-bar pad, L4),
  4. collect EXTRA entries the causal slices produce (live chain state differs),
then pour accepted matches + extras through a SEQUENTIAL state machine
(cooldown 8 bars, halt3, applied chronologically) and compute the
live-expected NET vs the batch number.

Known limitation (documented): L5 (forming-swing marks appended to the batch
chain) is NOT implemented — the batch chain's still-forming swing is absent in
each slice; its marks are missing, so this study UNDERCOUNTS live-available
signals (conservative direction).

Run:  python backtest/tests/exp_onepass_cline.py
"""
import sys, json, time
from pathlib import Path
from collections import defaultdict
import datetime as _dt

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from run_experiment import get_data, BP, EXPERIMENTS, fund
from src.btc.btc_routes import _trade_costs, _compute_swings
from engine.v18_params import get_v18_params as gvp
from replay_harness import load_candles, INSTRUMENT
from src.walker import FlowCandle
import test_experiments_craze as craze

G = gvp(INSTRUMENT)
DAY = 86400
BAR = 900
PAD_BARS = 2  # L4: discovery pad

# L1 patch: keep still-open HTF windows as active bias (window to slice end)
SRC = craze.SRC
L1_OLD = '        for t in trades:\n            if t["outcome"]=="open": continue\n'
assert SRC.count(L1_OLD) == 1, "L1 anchor"
L1_NEW = '        for t in trades:\n            if t["outcome"]=="open" and False: continue\n'
orig_loader = craze._load_module


def l1_loader(text, name):
    t = text.replace(L1_OLD, L1_NEW)
    return orig_loader(t, name)


def ep(s):
    return _dt.datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S").timestamp()


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
    c2, _ = _trade_costs(batch, G["fee_pct"], 0.0, G["entry_slip_pct"], G["exit_slip_pct"])
    batch_net = sum(float(t["r_multiple"]) for t in batch) - c2 - fund(batch)
    print("batch: %d trades NET=%+.1f" % (len(batch), batch_net))

    E0 = int(c15_all[0]["ts"])
    warm15 = 30 * DAY
    warm1h = 20 * DAY

    accepted = []       # discovered matches (entry at/near E)
    extras = []         # causal-only entries
    repro = 0
    misses = []
    seen_extra = set()

    n_eligible = 0
    for i, t in enumerate(batch):
        E = int(t["entry_ts"])
        d = t["dir"]
        if E - E0 < warm15:
            continue
        n_eligible += 1
        e_end = E + PAD_BARS * BAR
        sl15 = [c for c in c15_all if E - warm15 <= c["ts"] <= e_end]
        sl1h = [c for c in c1h_all if E - warm1h <= c["ts"] <= e_end]
        if not sl15 or not sl1h:
            misses.append((E, d, "no-data"))
            continue
        f15 = [FlowCandle(date=c["date"], open=c["open"], high=c["high"], low=c["low"], close=c["close"]) for c in sl15]
        f1h = [FlowCandle(date=c["date"], open=c["open"], high=c["high"], low=c["low"], close=c["close"]) for c in sl1h]
        sw15c = _compute_swings(f15, "continuous", min_bars=50)
        sw10c = _compute_swings(f1h, "continuous", min_bars=10)
        r = sim(sl1h, sw10c, sl15, sw15c, fine_ltf=[], **params)
        cand = r["ltf_trades"]
        hit = None
        for x in cand:
            if x["dir"] == d and E <= int(x["entry_ts"]) <= e_end:
                hit = x
                break
        if hit is not None:
            repro += 1
            accepted.append(hit)
            for x in cand:
                ets = int(x["entry_ts"])
                key = (ets, x["dir"], round(float(x["entry_price"]), 2))
                if key not in seen_extra and E <= ets <= e_end:
                    seen_extra.add(key)
                    extras.append(dict(x))
        else:
            misses.append((E, d, "no-repro"))
        if (i + 1) % 100 == 0:
            print("  ... %d/%d replayed (%d repro, %d extra) %.0fs" %
                  (i + 1, len(batch), repro, len(extras), time.time() - t0))

    print("reproduction: %d/%d (%.1f%%)  extras discovered: %d" %
          (repro, n_eligible, 100.0 * repro / max(1, n_eligible), len(extras)))
    if misses:
        why = defaultdict(int)
        for _, _, w in misses:
            why[w] += 1
        print("miss reasons:", dict(why))

    # ---- sequential one-pass state machine over accepted + extras ----
    cd_bars = params["cooldown_bars"]
    halt_n = params["max_consecutive_losses"]

    def sequential(cands):
        cands = sorted(cands, key=lambda x: (int(x["entry_ts"]), x["dir"]))
        kept = []
        last_loss_i = -10 ** 9
        consec = 0
        halt_skip = False
        for c in cands:
            ets = int(c["entry_ts"])
            i_bar = (ets - E0) // BAR
            if cd_bars > 0 and i_bar - last_loss_i < cd_bars:
                continue
            if halt_skip:
                halt_skip = False
                consec = 0
                continue
            kept.append(c)
            if float(c["r_multiple"]) < 0:
                last_loss_i = i_bar
                consec += 1
                if consec >= halt_n:
                    halt_skip = True
                    consec = 0
            else:
                consec = 0
        return kept

    live_matches = sequential(accepted)
    live_all = sequential(accepted + extras)

    def report(tag, tr):
        if not tr:
            print("  %s: empty" % tag)
            return
        rs = [float(t["r_multiple"]) for t in tr]
        c2x, _ = _trade_costs(tr, G["fee_pct"], 0.0, G["entry_slip_pct"], G["exit_slip_pct"])
        f = fund(tr)
        net = sum(rs) - c2x - f
        pk = cm = dd = 0.0
        for x in rs:
            cm += x; pk = max(pk, cm); dd = max(dd, pk - cm)
        print("  %-28s n=%d gross=%+.1f NET=%+.1f DD=%.1f" % (tag, len(tr), sum(rs), net, dd))

    print("")
    print("=== LIVE-EXPECTED (sequential one-pass, causal slices, L1+L3+L4; L5 not implemented = conservative) ===")
    report("batch (reference)", batch)
    report("live: causal matches only", live_matches)
    report("live: matches + extras", live_all)

    out = {"batch_n": len(batch), "batch_net": batch_net, "repro": repro,
           "extras": len(extras), "live_matches_n": len(live_matches),
           "live_all_n": len(live_all)}
    (ROOT / "backtest/tests/_onepass_summary.json").write_text(json.dumps(out, indent=2))
    print("summary -> _onepass_summary.json  (%.0fs)" % (time.time() - t0))


if __name__ == "__main__":
    main()

