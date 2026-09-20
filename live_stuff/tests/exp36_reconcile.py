"""Exp 36 — reconcile the other lane's audit claims:
(a) anchor lb=30 fine NET (they claim +196.3; our estimate ~+171)
(b) mltf cd=10 overlap count (they claim ZERO overlapping positions)
(c) B3-OPT lb50 halt3 fine NET (they claim +115.4; ours +78.0)"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from test_experiments_craze import build_module, BASE, \
    load_candles, _compute_swings, SWING, MB15, INSTRUMENT
from engine.v18_params import get_v18_params as _gvp
from src.btc.btc_routes import _load_fine_1m, _trade_costs

BP = dict(BASE)
BP["chop_thresh"] = 58.0
_g = _gvp(INSTRUMENT)


def funding_of(tr):
    f = 0.0
    for t in tr:
        e, sl = float(t["entry_price"]), float(t["sl"])
        rk = abs(e - sl)
        if rk > 0 and e > 0:
            f += (int(t.get("bars_held") or 0) * 0.25 / 8.0) * 0.0001 * (e / rk)
    return f


def report(tag, tr):
    c2, _ = _trade_costs(tr, _g["fee_pct"], 0.0, _g["entry_slip_pct"], _g["exit_slip_pct"])
    fr = funding_of(tr)
    gross = sum(float(t["r_multiple"]) for t in tr)
    print("  %-28s %4dt gross %+8.1f fees %6.1f fund %5.1f NET %+8.1f"
          % (tag, len(tr), gross, c2, fr, gross - c2 - fr))


def main():
    (c15, f15), (c1h, f1h) = load_candles()
    sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
    sw1h20 = _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"])
    sw1h10 = _compute_swings(f1h, "continuous", min_bars=10)
    sim = build_module()
    fine = _load_fine_1m(min(c1h[0]["ts"], c15[0]["ts"]),
                         max(c1h[-1]["ts"], c15[-1]["ts"]), symbol=INSTRUMENT)

    r = sim(c1h, sw1h20, c15, sw15, fine_ltf=fine, **{**BP, "exp31_lb": 30})
    report("(a) anchor lb30 fine", r["ltf_trades"])

    r = sim(c1h, sw1h20, c15, sw15, fine_ltf=fine, **BP)
    report("(ref) anchor lb14 fine", r["ltf_trades"])

    # (b) mltf cd10 overlap count — max concurrent positions over time
    r = sim(c1h, sw1h20, c15, sw15, fine_ltf=fine, **{**BP, "exp_mltf": True})
    tr = r["ltf_trades"]
    report("(b) mltf cd10 (mb20)", tr)
    evs = []
    for t in tr:
        evs.append((int(t["entry_ts"]), 1))
        evs.append((int(t["exit_ts"]), -1))
    evs.sort()
    cur = mx = 0
    for _, d in evs:
        cur += d
        mx = max(mx, cur)
    print("     concurrent positions: max=%d ; trades=%d" % (mx, len(tr)))
    r = sim(c1h, sw1h10, c15, sw15, fine_ltf=fine,
            **{**BP, "exp_mltf": True, "chop_thresh": 55.0})
    tr = r["ltf_trades"]
    evs = []
    for t in tr:
        evs.append((int(t["entry_ts"]), 1))
        evs.append((int(t["exit_ts"]), -1))
    evs.sort()
    cur = mx = 0
    for _, d in evs:
        cur += d
        mx = max(mx, cur)
    print("     mltf cd10 (mb10+chop55 = S9): max concurrent=%d ; trades=%d" % (mx, len(tr)))
    report("      S9 fine", tr)

    # (c) B3-OPT lb50 halt3 fine
    r = sim(c1h, sw1h10, c15, sw15, fine_ltf=fine,
            **{**BP, "b3_k": 8, "b3_mode": "close", "exp_persist": 2,
               "max_consecutive_losses": 3, "exp31_lb": 50,
               "chop_thresh": 55.0})
    report("(c) B3-OPT lb50 halt3 fine", r["ltf_trades"])


if __name__ == "__main__":
    main()
