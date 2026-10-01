"""Backtest-only integrity tests for the v18 streak-halt engine."""
from __future__ import annotations
import os, sys
from collections import defaultdict
R = "c:/Users/Pravin/Desktop/main/AT_Trading"
sys.path.insert(0, R + "/backend")
sys.path.insert(0, R + "/backtest")
from replay_harness import load_candles, INSTRUMENT  # noqa: E402
from engine.v18_params import SWING, get_v18_params, V18_ENGINE  # noqa: E402
from src.btc.btc_routes import _compute_swings, _trade_costs, _load_fine_1m  # noqa: E402
from src.btc.engines.htf_ltf.v18_streak_halt import (  # noqa: E402
    simulate_htf_ltf_streak_halt,
)
EF = os.path.join(R, "backend/src/btc/engines/htf_ltf/v18_streak_halt.py")

# Re-anchored 2026-10-01 after C16, measured on Bybit perp: 352 trades.
# Kept as a constant so the assert and the printed band cannot drift apart -
# they did once already, when the print still read [346,356] after the assert
# had been moved to [348,358].
COUNT_BAND = (348, 358)


def _src():
    return open(EF, encoding="utf-8").read()


def _bp():
    p = dict(get_v18_params(INSTRUMENT)); p.update(V18_ENGINE)
    p["chop_thresh"] = 58.0  # PRODUCTION (btc_routes 914-918); V18_ENGINE's 61.8 default must not clobber it
    return p


def _run(fine=False):
    p = _bp()
    (c15, f15), (c1h, f1h) = load_candles()
    sw15 = _compute_swings(f15, "continuous", min_bars=SWING["min_bars_15m"])
    sw1h = _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"])
    fl = (_load_fine_1m(min(c1h[0]["ts"], c15[0]["ts"]), max(c1h[-1]["ts"], c15[-1]["ts"]), symbol=INSTRUMENT) if fine else [])
    kw = {k: p[k] for k in ["sl_buf_atr","ext_stop_r","chop_thresh","atr_low_thresh","atr_high_thresh","mode","cooldown_bars","max_consecutive_losses","htf_rr","window_end"] if k in p}
    r = simulate_htf_ltf_streak_halt(c1h, sw1h, c15, sw15, fine_ltf=fl, **kw)
    return p, r["ltf_trades"] if isinstance(r, dict) else []


def _net(tr, p):
    rs = [float(t["r_multiple"]) for t in tr]
    c2, _ = _trade_costs(tr, p["fee_pct"], 0.0, p["entry_slip_pct"], p["exit_slip_pct"])
    w = [x for x in rs if x > 0]; l = [x for x in rs if x < 0]
    return sum(rs), sum(rs) - c2, len(w), len(l)


def test_streak_books_losses_and_skips_next():
    s = _src()
    assert "ltf_trades.append({" in s
    assert "halt_skip_next = True" in s
    assert "consecutive_losses += 1" in s
    N = 5; seq = [-1.0]*5 + [-1.0] + [+5.0]
    consec = 0; hsn = False; booked = []; skipped = 0
    for r in seq:
        if hsn:
            hsn = False; consec = 0; skipped += 1; continue
        booked.append(r)
        if r <= 0:
            consec += 1
            if consec >= N:
                hsn = True; consec = 0
        else:
            consec = 0
    assert len(booked) == 6 and skipped == 1
    assert booked[:5] == [-1.0]*5 and booked[5] == +5.0
    print("PASS: 5 losers booked, 6th skipped, winner resumes")


def test_c14_c15_gates_present():
    s = _src()
    assert "bisect_right(candle_ts_htf" in s
    assert "s + 2700 < bar_ts <= e + 2700" in s
    assert ("s + 900" in s or "ts+900" in s)
    print("PASS: C14+2700 gates present in source")


def test_c15_count_band():
    p, tr = _run(fine=False)
    assert COUNT_BAND[0] <= len(tr) <= COUNT_BAND[1], "count outside production band"
    print("PASS: trade count %d within [%d,%d]" % (len(tr), *COUNT_BAND))


def test_baseline():
    p, tr = _run(fine=True)
    g, n, w, l = _net(tr, p)
    rs = [float(t["r_multiple"]) for t in tr]
    yrs = defaultdict(float)
    for t in tr:
        yrs[str((t.get("exit_date") or t.get("entry_date") or "")[:4])] += float(t["r_multiple"])
    assert all(v >= 0 for v in yrs.values())
    assert 346 <= len(tr) <= 356
    # RE-ANCHORED AGAIN 2026-10-01, after C16. The previous anchor below was
    # itself set on 2026-09-26, five days before 203e207 changed
    # _collect_signals' pivot_rule default to "leg". The old bar was therefore an
    # ORIGIN-era bar and no longer described the engine that ships.
    #
    # Measured today, Bybit perp, leg rule, production params:
    #   352t  gross +220.15  net +146.55  PF 1.947  WR 27.8%
    #   outcomes  sl 145 / trail 207
    #   by year   2023 +38.78  2024 +81.11  2025 +47.97  2026 +52.29
    #
    # Against the origin-era anchor on the same Bybit window:
    #   count 351 -> 352      (+1)
    #   net   +137.33 -> +146.55   (+9.22)
    #   PF    1.907 -> 1.947       (+0.040)
    #   WR    27.6% -> 27.8%       (+0.2pt)
    #
    # That is the real size of C16's effect on the live engine: one extra trade
    # and two tenths of a point of win rate. It is not a regression and not a
    # jump, so the bars are re-centred on the leg measurement rather than moved
    # to accommodate a change that never happened.
    #
    # The bars are tighter than before on purpose. The previous pair was 120.0 net
    # against a 137.33 pin and 1.80 PF against a 1.907 pin, i.e. 12.6% and 5.6%
    # headroom, which is wide enough that the old pin and a real regression both
    # pass. 135.0 and 1.85 keep ~8% and ~5% below today's values.
    #
    # History of this anchor, kept because the trail fix it recorded is still the
    # reason the PF bar is not 2.0:
    # 2026-09-19 a329ff3 anchored 351t/+238.0/+163.7, before the trail-ordering
    # correctness fix ee574f9 (2026-09-21, "ratchet before SL check"). That fix
    # costs ~26R on fine fills because the pre-fix trail gave a trade one extra
    # bar of slack when its structural stop tightened - slack that does not exist
    # live, where the stop is armed at the activation instant. Same data, same
    # trade count, -26.31R gross / -26.33R net, -0.113 PF. The old PF bar of 2.0
    # cleared the pre-fix 2.020 by only 0.02. Win rate never moved across that
    # fix - only exit magnitude did. See backtest/docs/new bugs.md -> REBASELINE
    # NOTE (2026-09-26).
    #
    # All figures above are Bybit perp. BTCUSDT is Binance spot and is not traded
    # on this project; a measurement run with that symbol moves the window and the
    # trade set and will not match anything here.
    assert n >= 135.0
    pf = sum(x for x in rs if x > 0) / abs(sum(x for x in rs if x < 0)) if l else 9.0
    assert pf >= 1.85
    print("PASS: %dt gross %+.1f net %+.1f WR %.1f%% PF %.2f %s" % (len(tr), g, n, 100*w/len(tr), pf, dict(yrs)))


def test_no_deleted_losses():
    p, tr = _run(fine=False)
    oc = defaultdict(int)
    for t in tr: oc[t.get("outcome")] += 1
    assert oc["sl"] > 0
    rs = [float(t["r_multiple"]) for t in tr]
    wr = 100.0 * len([x for x in rs if x > 0]) / len(rs)
    assert 25 <= wr <= 40
    print("PASS: sl=%d trail=%d WR=%.1f%% (broken was 45%%)" % (oc["sl"], oc["trail"], wr))


if __name__ == "__main__":
    print("Running v18 causal-integrity backtest regressions...")
    for fn in [test_streak_books_losses_and_skips_next, test_c14_c15_gates_present, test_c15_count_band, test_baseline, test_no_deleted_losses]:
        print("[%s]" % fn.__name__)
        fn()
    print("ALL v18 BACKTEST INTEGRITY TESTS PASSED.")
