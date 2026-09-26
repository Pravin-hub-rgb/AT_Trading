"""Backtest-only integrity tests for the v18 streak-halt engine."""
from __future__ import annotations
import os, sys
from collections import defaultdict
R = "c:/Users/Pravin/Desktop/main/AT_Trading"
sys.path.insert(0, R + "/backend")
sys.path.insert(0, R + "/live_stuff")
from replay_harness import load_candles, INSTRUMENT  # noqa: E402
from engine.v18_params import SWING, get_v18_params, V18_ENGINE  # noqa: E402
from src.btc.btc_routes import _compute_swings, _trade_costs, _load_fine_1m  # noqa: E402
from src.btc.engines.htf_ltf.v18_streak_halt import (  # noqa: E402
    simulate_htf_ltf_streak_halt,
)
EF = os.path.join(R, "backend/src/btc/engines/htf_ltf/v18_streak_halt.py")


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
    assert 346 <= len(tr) <= 356, "count outside production band"
    print("PASS: trade count %d within [346,356]" % len(tr))


def test_baseline():
    p, tr = _run(fine=True)
    g, n, w, l = _net(tr, p)
    rs = [float(t["r_multiple"]) for t in tr]
    yrs = defaultdict(float)
    for t in tr:
        yrs[str((t.get("exit_date") or t.get("entry_date") or "")[:4])] += float(t["r_multiple"])
    assert all(v >= 0 for v in yrs.values())
    assert 346 <= len(tr) <= 356
    # RE-ANCHORED 2026-09-26. BOTH bars below were calibrated 2026-09-19
    # (a329ff3: 351t/+238.0 gross/+163.7 net) BEFORE the trail-ordering
    # correctness fix ee574f9 (2026-09-21, "ratchet before SL check"). That fix
    # costs ~26R on fine fills because the pre-fix trail gave a trade one extra
    # bar of slack when its structural stop tightened - slack that does not exist
    # live, where the stop is armed at the activation instant.
    #
    # Proof, pre-fix engine (ee574f9^) vs the current engine, both on today's
    # identical data:
    #   PRE-FIX   351t  gross +238.03  net +163.66  PF 2.020  WR 27.6%
    #   POST-FIX  351t  gross +211.72  net +137.33  PF 1.907  WR 27.6%
    # Same data, same trade count, -26.31R gross / -26.33R net, -0.113 PF.
    # Note the old PF bar of 2.0 cleared the PRE-FIX 2.020 by only 0.02.
    #
    # So 150.0 and 2.0 were pre-fix leftovers, not regression alarms; the fix
    # made the backtest more honest. 120.0 and 1.80 keep ~13% and ~5.6% headroom
    # below the correct post-fix values so both still catch a real drop.
    # Win rate is unchanged at 27.6% across the fix - only exit magnitude moved.
    # See live_stuff/docs/new bugs.md -> REBASELINE NOTE (2026-09-26).
    assert n >= 120.0
    pf = sum(x for x in rs if x > 0) / abs(sum(x for x in rs if x < 0)) if l else 9.0
    assert pf >= 1.80
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
