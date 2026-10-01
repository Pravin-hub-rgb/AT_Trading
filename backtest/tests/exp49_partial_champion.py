"""Exp 49 — partial exits (exp_partial_r) + other bot's champion reproduction.

Tests:
  1. Identity gate: flags-off == shipped (n=340)
  2. User coarse matrix: lb30 w24 ext1.5, lb30 w24 ext3.0, A4 w24 ext1.5, A4 w24 ext3.0
  3. Champion single: mode=atr_high, ext_stop_r=3.0, exp_partial_r=7.5
  4. Champion multi:  +exp_mltf, exp_persist=7
  5. Both on sw10 and sw20
  6. Canary: for every trade with partial_exit_price>0, verify R formula
  7. 6-segment WF per cell, JSON dump
"""
import sys, time, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from exp40c_wage_gate import BP, fund, run_coarse
from test_experiments_craze import build_module, load_candles, _compute_swings, SWING, MB15, INSTRUMENT, stats
from engine.v18_params import get_v18_params as _gvp
from src.btc.btc_routes import _load_fine_1m, _trade_costs
import src.btc.engines.htf_ltf.v18_streak_halt as shipped_mod

A4 = dict(exp31_lb=30, chop_thresh=55.0, exp_persist=2)
LB30 = dict(exp31_lb=30)

# Champion knobs (from other bot's audit-verified config)
CHAMPION = dict(
    mode="atr_high",
    atr_high_thresh=0.65,
    atr_low_thresh=0.35,
    sl_buf_atr=0.01,
    chop_thresh=58.0,
    cooldown_bars=8,
    max_consecutive_losses=3,
    ext_stop_r=3.0,
    exp_partial_r=7.5,
    window_end="exit",
)

PINS = {
    ("lb30", "w24", "ext1.5"): (265, 231.6),
    ("lb30", "w24", "ext3.0"): (307, 222.4),
    ("A4", "w24", "ext1.5"): (250, 207.1),
    ("A4", "w24", "ext3.0"): (285, 218.8),
}



def yearly_net(tr):
    """NET by calendar year of EXIT (not WF segments)."""
    py = {}
    for t in tr:
        yr = (t.get("exit_date") or t.get("entry_date") or "")[:4]
        py[yr] = py.get(yr, 0.0) + float(t["r_multiple"])
    return {k: round(v, 1) for k, v in sorted(py.items())}


def main():
    t0 = time.time()
    (c15, f15), (c1h, f1h) = load_candles()
    sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
    sw20 = _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"])
    sw10 = _compute_swings(f1h, "continuous", min_bars=10)
    sim = build_module()
    _g = _gvp(INSTRUMENT)

    def _net(tr):
        rs = [float(t["r_multiple"]) for t in tr]
        c2, _ = _trade_costs(tr, _g["fee_pct"], 0.0, _g["entry_slip_pct"], _g["exit_slip_pct"])
        return sum(rs) - c2 - fund(tr)

    # ---------- PHASE 0: identity gate ----------
    print("=== IDENTITY GATE ===")
    r_ship = shipped_mod.simulate_htf_ltf_streak_halt(c1h, sw20, c15, sw15, fine_ltf=[], **BP)
    s_ship = stats(r_ship["ltf_trades"])
    r0 = sim(c1h, sw20, c15, sw15, fine_ltf=[], **BP)
    s0 = stats(r0["ltf_trades"])
    assert s0["n"] == s_ship["n"] and s0["rs"] == s_ship["rs"], "IDENTITY GATE FAILED"
    print("  flags=off  n=%d  IDENTICAL=True" % s0["n"], flush=True)

    # ---------- PHASE 1: user coarse matrix ----------
    print("\n=== USER COARSE MATRIX (w24) ===")
    for tag, kw in [("lb30", LB30), ("A4", A4)]:
        for ext in (1.5, 3.0):
            tr, g = run_coarse(sim, c1h, sw20, c15, sw15, sw20, kw, 24, ext)
            pin_key = (tag, "w24", "ext%.1f" % ext)
            mark = ""
            if pin_key in PINS:
                en, eg = PINS[pin_key]
                m = (len(tr) == en and abs(g - eg) <= 0.15)
                mark = "  %s (pin %dt %+.1f)" % ("OK" if m else "MISMATCH", en, eg)
            print("  %-5s w24 ext%.1f  %3dt NET %+8.1f%s" % (tag, ext, len(tr), g, mark), flush=True)

    # ---------- 6-segment walk-forward helper (exp41 convention) ----------
    K6 = 6
    _ts0 = min(c1h[0]["ts"], c15[0]["ts"]); _ts1 = max(c1h[-1]["ts"], c15[-1]["ts"])
    _step = (_ts1 - _ts0) / float(K6)
    def seg6(tr):
        segs = [[] for _ in range(K6)]
        for t in tr:
            i = min(int((int(t["entry_ts"]) - _ts0) / _step), K6 - 1)
            if i < 0: i = 0
            segs[i].append(t)
        nets = [_net(sg) if sg else 0.0 for sg in segs]
        return nets, min(nets)
    # ---------- PHASE 2: champion single (sw10 + sw20) ----------
    print("\n=== CHAMPION SINGLE (partial 7.5R) ===")
    fine = _load_fine_1m(min(c1h[0]["ts"], c15[0]["ts"]), max(c1h[-1]["ts"], c15[-1]["ts"]), symbol=INSTRUMENT)
    for sw_tag, sw in [("sw20", sw20), ("sw10", sw10)]:
        r = sim(c1h, sw, c15, sw15, fine_ltf=fine, **{**BP, **CHAMPION})
        tr = r["ltf_trades"]
        net = _net(tr)
        s = stats(tr)
        # canary: verify R formula for partial trades
        partial_count = 0
        canary_fail = 0
        for t in tr:
            pep = t.get("partial_exit_price", 0.0)
            if pep > 0:
                partial_count += 1
                entry = float(t["entry_price"])
                exit_px = float(t["exit_price"])
                risk = abs(entry - float(t["sl"]))
                d = 1 if t["dir"] == "long" else -1
                expected_r = 7.5 + ((exit_px - entry) * d / risk) * 0.5
                actual_r = float(t["r_multiple"])
                if abs(actual_r - expected_r) > 0.05:
                    canary_fail += 1
                    print("    CANARY FAIL: trade %s expected %.4f got %.4f" % (t.get("entry_date", "?"), expected_r, actual_r))
        nets6, worst6 = seg6(tr)
        print("  champion single %s: %3dt NET %+8.1f  WR %.1f%%  DD %.1f  partials=%d canary_fails=%d  worst6=%+.1f  years=%s" %
              (sw_tag, len(tr), net, s["wr"], s["dd"], partial_count, canary_fail, worst6, yearly_net(tr)), flush=True)

    # ---------- PHASE 3: champion multi (sw10 + sw20) ----------
    print("\n=== CHAMPION MULTI (partial 7.5R + mltf + persist7) ===")
    champion_multi = {**CHAMPION, "exp_mltf": True, "exp_persist": 7}
    for sw_tag, sw in [("sw20", sw20), ("sw10", sw10)]:
        r = sim(c1h, sw, c15, sw15, fine_ltf=fine, **{**BP, **champion_multi})
        tr = r["ltf_trades"]
        net = _net(tr)
        s = stats(tr)
        partial_count = sum(1 for t in tr if t.get("partial_exit_price", 0.0) > 0)
        partial_count = 0; canary_fail = 0
        for t in tr:
            pep = t.get("partial_exit_price", 0.0)
            if pep > 0:
                partial_count += 1
                entry = float(t["entry_price"]); exit_px = float(t["exit_price"])
                risk = abs(entry - float(t["sl"])); d = 1 if t["dir"] == "long" else -1
                expected_r = 7.5 + ((exit_px - entry) * d / risk) * 0.5
                if abs(float(t["r_multiple"]) - expected_r) > 0.05: canary_fail += 1
        nets6, worst6 = seg6(tr)
        print("  champion multi  %s: %3dt NET %+8.1f  WR %.1f%%  DD %.1f  partials=%d canary_fails=%d  worst6=%+.1f  years=%s" %
              (sw_tag, len(tr), net, s["wr"], s["dd"], partial_count, canary_fail, worst6, yearly_net(tr)), flush=True)

    # ---------- PHASE 4: champion no-partial (baseline) ----------
    print("\n=== CHAMPION NO-PARTIAL (exp_partial_r=0, baseline) ===")
    champion_base = {**CHAMPION, "exp_partial_r": 0.0}
    for sw_tag, sw in [("sw20", sw20), ("sw10", sw10)]:
        r = sim(c1h, sw, c15, sw15, fine_ltf=fine, **{**BP, **champion_base})
        tr = r["ltf_trades"]
        net = _net(tr)
        s = stats(tr)
        print("  baseline      %s: %3dt NET %+8.1f  WR %.1f%%  DD %.1f  WF=%s" %
              (sw_tag, len(tr), net, s["wr"], s["dd"], yearly_net(tr)), flush=True)

    (ROOT / "backtest/tests/_exp49_results.json").write_text(json.dumps(
        {"note": "full metrics in _exp49_out.txt; CAVEAT: partial second-fill fee+slip not yet in _trade_costs (approx 0.02R/partial trade)"}, indent=1))
    elapsed = time.time() - t0
    print("\n=== DONE (%.0fs) ===" % elapsed)


if __name__ == "__main__":
    main()
