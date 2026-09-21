"""Anchor audit: (1) coarse-vs-fine basis check, (2) truncation lookahead probe.

python live_stuff/tests/exp_anchor_audit_cline.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from run_experiment import get_data, BP, fund
from src.btc.btc_routes import _trade_costs, _compute_swings, _load_fine_1m
from replay_harness import load_candles, INSTRUMENT
from engine.v18_params import SWING
import src.btc.engines.htf_ltf.v18_streak_halt as shipped_mod
from src.walker import FlowCandle

DAY = 86400
MB15 = SWING["min_bars_15m"]   # 50 — production
MB1H = SWING["min_bars_1h"]    # 20


def run_sim(c1h, sw1h, c15, sw15, fine, params):
    r = shipped_mod.simulate_htf_ltf_streak_halt(c1h, sw1h, c15, sw15, fine_ltf=fine, **params)
    return r["ltf_trades"]


def summarize(tr, tag):
    rs = [float(t["r_multiple"]) for t in tr]
    peak = cum = dd = 0.0
    for x in rs:
        cum += x; peak = max(peak, cum); dd = max(dd, peak - cum)
    wr = 100.0 * len([x for x in rs if x > 0]) / max(len(tr), 1)
    print("  %-28s n=%d gross=%+.1f WR=%.1f%% DD=%.1f" % (tag, len(tr), sum(rs), wr, dd))
    return tr


def key_sig(t):
    return (int(t["entry_ts"]), t["dir"], float(t["entry_price"]), round(float(t["sl"]), 2))


def main():
    data = get_data()
    params = dict(BP)
    # basis check: mb50 (production) and mb35 (doc/brief claim) x coarse/fine
    (c15_all, f15_all), (c1h_all, f1h_all) = load_candles()
    for mb in (MB15, 35):
        sw15x = _compute_swings(f15_all, "continuous", min_bars=mb)
        for fine, tag in [(data["fine"], "fine"), ([], "coarse")]:
            tr = run_sim(data["c1h"], data["sw20"], data["c15"], sw15x, fine, params)
            summarize(tr, "mb%d %s" % (mb, tag))
    full_fine = run_sim(data["c1h"], data["sw20"], data["c15"], data["sw15"], data["fine"], params)
    summarize(full_fine, "ANCHOR fine (runner basis, mb50)")
    full_coarse = run_sim(data["c1h"], data["sw20"], data["c15"], data["sw15"], [], params)
    summarize(full_coarse, "ANCHOR coarse (mb50)")
    ff = {key_sig(t) for t in full_fine}
    fc = {key_sig(t) for t in full_coarse}
    print("  entry-signature diff fine vs coarse: only-in-fine=%d only-in-coarse=%d" %
          (len(ff - fc), len(fc - ff)))

    # ---- truncation probe ----
    (c15_all, f15_all), (c1h_all, f1h_all) = load_candles()
    ts0 = c1h_all[0]["ts"]
    for days_back, tag in [(460, "T1 ~2025-06"), (170, "T2 ~2026-03")]:
        T = c1h_all[-1]["ts"] - days_back * DAY
        T -= T % 900
        guard = 3 * DAY  # ignore trades whose exit lands within 3d of the cut
        c15t = [c for c in c15_all if c["ts"] <= T]
        c1ht = [c for c in c1h_all if c["ts"] <= T]
        f15t = [FlowCandle(date=c["date"], open=c["open"], high=c["high"], low=c["low"], close=c["close"])
                for c in c15t]
        f1ht = [FlowCandle(date=c["date"], open=c["open"], high=c["high"], low=c["low"], close=c["close"])
                for c in c1ht]
        sw15t = _compute_swings(f15t, "continuous", min_bars=MB15)
        sw1ht = _compute_swings(f1ht, "continuous", min_bars=MB1H)
        finet = _load_fine_1m(ts0, T, symbol=INSTRUMENT)
        tr_full = [t for t in full_fine if int(t["entry_ts"]) < T - guard]
        tr_trunc = run_sim(c1ht, sw1ht, c15t, sw15t, finet, params)
        kt = {key_sig(t): t for t in tr_trunc}
        mism = [t for t in tr_full if key_sig(t) not in kt]
        # R parity for fully-closed trades
        rbad = 0
        for t in tr_full:
            k = key_sig(t)
            if k in kt and int(t["exit_ts"]) < T - guard:
                if abs(float(t["r_multiple"]) - float(kt[k]["r_multiple"])) > 1e-6:
                    rbad += 1
        extra = [t for t in tr_trunc if key_sig(t) not in {key_sig(x) for x in tr_full}]
        print("\n[TRUNC %s @ %s] past-trades full=%d trunc=%d  MISSING-in-trunc=%d  EXTRA-in-trunc=%d  R-mismatch(closed)=%d" %
              (tag, c1ht[-1]["date"][:16], len(tr_full), len(tr_trunc), len(mism), len(extra), rbad))
        for t in mism[:5]:
            print("   LOST: %s %s e=%.1f R=%+.2f" % (t["entry_date"][:16], t["dir"], float(t["entry_price"]), float(t["r_multiple"])))
        for t in extra[:5]:
            print("   EXTRA: %s %s e=%.1f R=%+.2f" % (t["entry_date"][:16], t["dir"], float(t["entry_price"]), float(t["r_multiple"])))
        verdict = "CLEAN (no future-data dependence)" if (not mism and not rbad) else "LOOKAHEAD / INSTABILITY DETECTED"
        print("   verdict: %s" % verdict)


if __name__ == "__main__":
    main()
