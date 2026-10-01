"""Exp 34 — LIVE-FEASIBILITY STRESS BATTERY on the two final candidates.

1. Late-entry repricing: every trade re-priced as if the market order was
   placed one 15m bar AFTER the trigger close (worst-case execution delay).
   Exit levels unchanged, risk re-based to the late entry, wins capped 3R.
2. Entry-slippage escalation: modeled slip x1 / x2 / x5 / x10.
3. Bootstrap CI (10k resamples) on NET/trade — is the edge statistically real?
Configs: king (B3-OPT lb50 halt6 cd10) and aggressive (52,60,trail65).
"""
import sys, time, json, random
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
KING = dict(b3_k=8, b3_mode="close", exp_persist=2, max_consecutive_losses=6,
            exp31_lb=50)
AGGR_PO = dict(chop_thresh=52.0, max_consecutive_losses=6)
AGGR_H = dict(b3_k=8, b3_mode="close", exp_persist=2, exp31_lb=60)
_g = _gvp(INSTRUMENT)
FEE, ESLIP, XSLIP = _g["fee_pct"], _g["entry_slip_pct"], _g["exit_slip_pct"]


def funding_of(tr):
    f = 0.0
    for t in tr:
        e, sl = float(t["entry_price"]), float(t["sl"])
        risk = abs(e - sl)
        if risk > 0 and e > 0:
            f += (int(t.get("bars_held") or 0) * 0.25 / 8.0) * 0.0001 * (e / risk)
    return f


def main():
    (c15, f15), (c1h, f1h) = load_candles()
    sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
    sw1h10 = _compute_swings(f1h, "continuous", min_bars=10)
    tch65 = _compute_swings(f15, "continuous", min_bars=65)
    sim = build_module()
    fine = _load_fine_1m(min(c1h[0]["ts"], c15[0]["ts"]),
                         max(c1h[-1]["ts"], c15[-1]["ts"]), symbol=INSTRUMENT)
    op15 = [float(c["open"]) for c in c15]
    n15 = len(c15)

    for tag, hflags, pover, extra in [
            ("KING lb50 halt6", KING, {}, {}),
            ("AGGR (52,60,tr65)", AGGR_H, AGGR_PO, {"swings_trail": tch65})]:
        r = sim(c1h, sw1h10, c15, sw15, fine_ltf=fine,
                **{**BP, **pover, **hflags, **extra})
        tr = r["ltf_trades"] if isinstance(r, dict) else r
        c2, _ = _trade_costs(tr, FEE, 0.0, ESLIP, XSLIP)
        fr = funding_of(tr)
        gross = sum(float(t["r_multiple"]) for t in tr)
        net = gross - c2 - fr
        print("=== %s: %dt gross %+.1f fees %.1f funding %.1f NET %+.1f ==="
              % (tag, len(tr), gross, c2, fr, net))

        # 1) late-entry repricing — TWO scenarios, NO winner cap, floor -1R:
        #    (a) same-instant: fill at NEXT bar's open (== trigger close instant,
        #        what a live bot acting within seconds actually gets)
        #    (b) one FULL bar late: fill at bar+2's open (15-minute delay)
        for label, off in [("same-instant (bot acts on close)", 1),
                           ("ONE BAR LATE (15min delay)", 2)]:
            late_rs = []
            skipped = missed_target = 0
            for t in tr:
                ei = int(t["entry_idx"])
                if ei + off >= n15:
                    skipped += 1
                    continue
                d = 1 if t["dir"] == "long" else -1
                ne = op15[ei + off]
                slp = float(t["sl"])
                risk2 = abs(ne - slp)
                if risk2 <= 0.0005 * ne:
                    skipped += 1
                    continue
                tgt = float(t["target"])
                if (d == 1 and ne >= tgt) or (d == -1 and ne <= tgt):
                    missed_target += 1
                rr = ((float(t["exit_price"]) - ne) / risk2) if d == 1 \
                    else ((ne - float(t["exit_price"])) / risk2)
                late_rs.append(max(-1.0, rr))
            late_cpt = (c2 + fr) / max(len(late_rs), 1)
            late_net = sum(x - late_cpt for x in late_rs)
            print("  LATE-ENTRY %-30s: %dt (skip %d, target-already-gone %d) NET %+8.1f  npt %+.3f  (base npt %+.3f)"
                  % (label, len(late_rs), skipped, missed_target, late_net,
                     late_net / max(len(late_rs), 1), net / len(tr)))
        # fill drift: |next open - trigger close| distribution
        diffs = []
        for t in tr:
            ei = int(t["entry_idx"])
            if ei + 1 < n15:
                cl = float(c15[ei]["close"])
                diffs.append(abs(op15[ei + 1] - cl) / cl * 100.0)
        diffs.sort()
        print("  fill drift (next open vs trigger close, %% of price): median %.3f%%  p90 %.3f%%  p99 %.3f%%"
              % (diffs[len(diffs) // 2], diffs[int(len(diffs) * 0.9)], diffs[int(len(diffs) * 0.99)]))

        # 2) slippage escalation (entry slip xk)
        for k in (1, 2, 5, 10):
            c2k, _ = _trade_costs(tr, FEE, 0.0, ESLIP * k, XSLIP)
            print("  slip x%-2d: NET %+8.1f  npt %+.3f" % (k, gross - c2k - fr, (gross - c2k - fr) / len(tr)))

        # 3) bootstrap CI on NET/trade (net per-trade series)
        npt_list = []
        cpt = (c2 + fr) / len(tr)
        for t in tr:
            npt_list.append(float(t["r_multiple"]) - cpt)
        rng = random.Random(42)
        means = []
        N = len(npt_list)
        for _ in range(10000):
            means.append(sum(rng.choice(npt_list) for _ in range(N)) / N)
        means.sort()
        lo, hi = means[250], means[9750]
        print("  BOOTSTRAP npt: mean %+.3f  95%% CI [%+.3f, %+.3f]  P(mean>0)=%.3f"
              % (sum(npt_list) / N, lo, hi,
                 sum(1 for m in means if m > 0) / 10000.0))
    print("\n(exp34 stress battery done)")


if __name__ == "__main__":
    main()
