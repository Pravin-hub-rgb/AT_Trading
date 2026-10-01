"""Diagnose WHY truncation changes 2023-era trades: chain diff + signal diff."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from run_experiment import get_data, BP
from src.btc.btc_routes import _compute_swings, _load_fine_1m
from replay_harness import load_candles, INSTRUMENT
from src.walker import FlowCandle
from src.btc.btc_engine import _collect_signals
import src.btc.engines.htf_ltf.v18_streak_halt as shipped_mod

DAY = 86400


def swing_key(s, i):
    seg = s.get("seg") or {}
    return (i, s.get("dir"), seg.get("start_time") or "", seg.get("end_time") or "",
            round(float(seg.get("start_px", 0)), 2), round(float(seg.get("end_px", 0)), 2))


def first_div(a, b, label):
    n = min(len(a), len(b))
    for i in range(n):
        if swing_key(a[i], i) != swing_key(b[i], i):
            print("  %s: FIRST DIVERGENCE at swing #%d of %d/%d" % (label, i, len(a), len(b)))
            print("    full: %s" % (swing_key(a[i], i),))
            print("    trunc:%s" % (swing_key(b[i], i),))
            if i > 0:
                print("    prev ok: %s" % (swing_key(a[i-1], i-1),))
            return i
    print("  %s: identical on common prefix (%d vs %d swings)" % (label, len(a), len(b)))
    return -1


def main():
    data = get_data()
    (c15_all, f15_all), (c1h_all, f1h_all) = load_candles()
    T = c1h_all[-1]["ts"] - 460 * DAY
    T -= T % 900
    c15t = [c for c in c15_all if c["ts"] <= T]
    c1ht = [c for c in c1h_all if c["ts"] <= T]
    f15t = [FlowCandle(date=c["date"], open=c["open"], high=c["high"], low=c["low"], close=c["close"]) for c in c15t]
    f1ht = [FlowCandle(date=c["date"], open=c["open"], high=c["high"], low=c["low"], close=c["close"]) for c in c1ht]

    print("=== 15m chain: full vs trunc ===")
    sw15_full = _compute_swings(f15_all, "continuous", min_bars=35)
    sw15_tr = _compute_swings(f15t, "continuous", min_bars=35)
    first_div(sw15_full, sw15_tr, "15m")
    print("=== 1h chain: full vs trunc ===")
    sw1h_full = _compute_swings(f1h_all, "continuous", min_bars=20)
    sw1h_tr = _compute_swings(f1ht, "continuous", min_bars=20)
    first_div(sw1h_full, sw1h_tr, "1h")

    print("=== signals (decisive stream): full vs trunc ===")
    sig_full = _collect_signals(sw15_full, "decisive", skip_first=True, selection="stream", candles=c15_all)
    sig_tr = _collect_signals(sw15_tr, "decisive", skip_first=True, selection="stream", candles=c15t)
    fk = lambda s: (s.get("bar", ""), s.get("kind"), s.get("dir"), round(float(s.get("swing_start_px", 0)), 2))
    sf = {fk(s) for s in sig_full}
    st = {fk(s) for s in sig_tr}
    only_full = sorted(x for x in sf - st)
    only_tr = sorted(x for x in st - sf)
    print("  signals full=%d trunc=%d only-full=%d only-trunc=%d" % (len(sig_full), len(sig_tr), len(only_full), len(only_tr)))
    for x in only_full[:5]: print("    only-full: %s" % (x,))
    for x in only_tr[:5]: print("    only-trunc: %s" % (x,))

    print("=== sim entry lists: full-fine vs trunc-coarse vs trunc-fine ===")
    def entries(tr):
        return {(int(t["entry_ts"]), t["dir"]) for t in tr}
    full_fine = shipped_mod.simulate_htf_ltf_streak_halt(
        data["c1h"], data["sw20"], data["c15"], data["sw15"], fine_ltf=data["fine"], **dict(BP))["ltf_trades"]
    sw20_tr = sw1h_tr
    finet = _load_fine_1m(c1h_all[0]["ts"], T, symbol=INSTRUMENT)
    trunc_fine = shipped_mod.simulate_htf_ltf_streak_halt(
        c1ht, sw20_tr, c15t, sw15_tr, fine_ltf=finet, **dict(BP))["ltf_trades"]
    trunc_coarse = shipped_mod.simulate_htf_ltf_streak_halt(
        c1ht, sw20_tr, c15t, sw15_tr, fine_ltf=[], **dict(BP))["ltf_trades"]
    ef, etf, etc = entries(full_fine), entries(trunc_fine), entries(trunc_coarse)
    print("  entries: full=%d trunc_fine=%d trunc_coarse=%d" % (len(ef), len(etf), len(etc)))
    print("  trunc_fine vs trunc_coarse: only-fine=%d only-coarse=%d" % (len(etf - etc), len(etc - etf)))
    cut = T - 3 * DAY
    pre_f = {x for x in ef if x[0] < cut}
    pre_t = {x for x in etf if x[0] < cut}
    print("  before cut: full=%d trunc=%d only-full=%d only-trunc=%d" % (len(pre_f), len(pre_t), len(pre_f - pre_t), len(pre_t - pre_f)))
    for x in sorted(pre_f - pre_t)[:3]:
        import time as _tm
        print("    only-full: %s %s" % (_tm.strftime("%Y-%m-%d %H:%M", _tm.gmtime(x[0])), x[1]))
    for x in sorted(pre_t - pre_f)[:3]:
        import time as _tm
        print("    only-trunc: %s %s" % (_tm.strftime("%Y-%m-%d %H:%M", _tm.gmtime(x[0])), x[1]))


if __name__ == "__main__":
    main()
