"""Exp 33 — VERIFY the other bot's menu config 2: "B3-OPT halt3 cd10" at lb14 and lb50.
Their claim: 215t / +350.9 net / DD 9.6 / NET-DD 36.5, IDENTICAL for lb14 and lb50.
Runs coarse gate, then fine NET + DD + per-year for both. Identity gate enforced."""
import sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from test_experiments_craze import build_module, stats, BASE, \
    load_candles, _compute_swings, SWING, MB15, INSTRUMENT
from engine.v18_params import get_v18_params as _gvp
from src.btc.btc_routes import _load_fine_1m, _trade_costs

BP = dict(BASE)
BP["chop_thresh"] = 58.0
H3 = dict(b3_k=8, b3_mode="close", exp_persist=2, max_consecutive_losses=3)
_g = _gvp(INSTRUMENT)


def net_of(tr):
    c2, _ = _trade_costs(tr, _g["fee_pct"], 0.0,
                         _g["entry_slip_pct"], _g["exit_slip_pct"])
    return sum(float(t["r_multiple"]) for t in tr) - c2


def ddur(tr):
    tr = sorted(tr, key=lambda t: int(t.get("exit_ts") or 0))
    peak = best = 0.0
    pk_i = pk_ts = tr_i = tr_ts = 0
    b_pk_i = b_pk_ts = 0
    cum = 0.0
    for i, t in enumerate(tr):
        cum += float(t["r_multiple"])
        if cum > peak:
            peak, pk_i, pk_ts = cum, i, int(t["exit_ts"] or 0)
        d = peak - cum
        if d > best:
            best, tr_i, tr_ts = d, i, int(t["exit_ts"] or 0)
            b_pk_i, b_pk_ts = pk_i, pk_ts
    return best, tr_i - b_pk_i, (tr_ts - b_pk_ts) / 86400.0


def main():
    (c15, f15), (c1h, f1h) = load_candles()
    sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
    sw1h10 = _compute_swings(f1h, "continuous", min_bars=10)
    sim = build_module()
    fine = _load_fine_1m(min(c1h[0]["ts"], c15[0]["ts"]),
                         max(c1h[-1]["ts"], c15[-1]["ts"]), symbol=INSTRUMENT)
    res = {}
    for lb in (0, 50):   # 0 = shipped lb14
        kw = {} if lb == 0 else {"exp31_lb": lb}
        r = sim(c1h, sw1h10, c15, sw15, fine_ltf=fine, **{**BP, **H3, **kw})
        tr = r["ltf_trades"] if isinstance(r, dict) else r
        s = stats(tr)
        ddn, ddt, ddd = ddur(tr)
        tag = "lb14" if lb == 0 else "lb50"
        res[tag] = s["rs"]
        print("  B3-OPT halt3 cd10 %s: %4dt gross %+8.1f  NET %+8.1f  WR %4.1f%%  DD %5.1f  DDdur %dt/%.0fd  H1 %+7.1f H2 %+7.1f"
              % (tag, s["n"], s["gross"], net_of(tr), s["wr"], ddn, ddt, ddd, s["h1"], s["h2"]))
        print("      per-year: %s | both-halves: %s"
              % ({k: round(v, 1) for k, v in sorted(s["py"].items())},
                 "PASS" if s["h1"] > 0 and s["h2"] > 0 else "FAIL"))
    same = res["lb14"] == res["lb50"]
    print("\n  lb14 vs lb50 trade lists IDENTICAL: %s" % same)
    if not same:
        d14, d50 = res["lb14"], res["lb50"]
        diffs = sum(1 for a, b in zip(d14, d50) if a != b)
        print("  differing trades: %d of %d/%d" % (diffs, len(d14), len(d50)))


if __name__ == "__main__":
    main()
