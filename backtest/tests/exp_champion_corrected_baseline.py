"""
PHASE 1 - corrected-chain baseline for the SHIPPING book.

Why this is not covered by exp_signal_metrics.py / exp_multi_metrics.py:
those walk `experiment_registry.EXPERIMENTS` (162 books). `champion_causal` -
the DEFAULT book in books.ts, and the one whose number the owner saw drop - is
NOT in that registry. It lives only in books.ts + the btc_routes.py version
ladder on the `unified` engine. So the 120-book run never touches it.

Its pinned params (btc_routes.py:1504-1521) and its pin (btc_routes.py:1495):

    sl_buf_atr=0.01  ext_stop_r=3.0  mode="atr_high"  chop_thresh=58.0
    cooldown_bars=8  max_consecutive_losses=3  htf_rr=3.0  window_end="exit"
    max_positions=0  exp_persist=7   pivot_rule="leg"
    PINNED: IS 499 trades / +239.12R, OOS 280 / +72.8R

books.ts disagrees with that pin (IS 421 / +127.39, OOS 251 / -31.05). Two
different pins for the same book id is itself worth resolving, so both are
printed for comparison.

Runs on the CURRENT engine, so this is the corrected-mark number.

Usage:
    $env:PYTHONIOENCODING='utf-8'
    ..\..\backend\venv\Scripts\python.exe -u exp_champion_corrected_baseline.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

PINNED = {"is": (499, 239.12), "oos": (280, 72.80)}
BOOKS_TS_PIN = {"is": (421, 127.39), "oos": (251, -31.05)}

PARAMS = dict(
    sl_buf_atr=0.01, ext_stop_r=3.0, mode="atr_high", chop_thresh=58.0,
    cooldown_bars=8, max_consecutive_losses=3, htf_rr=3.0, window_end="exit",
    max_positions=0, exp_persist=7, pivot_rule="leg",
)


def load_era(era: str) -> dict:
    """Same loaders exp_signal_metrics.py uses, so the series match."""
    if era == "is":
        from run_experiment import get_data
        return get_data()
    from test_4_new_concepts import load_unseen, load_fine_1m as load_fine
    from engine.v18_params import SWING
    from src.btc.btc_routes import _compute_swings
    (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
    return {
        "c15": c15, "f15": f15, "c1h": c1h, "f1h": f1h,
        "sw15": _compute_swings(f15, "continuous", min_bars=SWING["min_bars_15m"]),
        "sw10": _compute_swings(f1h, "continuous", min_bars=10),
        "sw20": _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"]),
        "htf15": _compute_swings(f1h, "continuous", min_bars=15),
        "fine": load_fine(c15[0]["ts"], c15[-1]["ts"]),
    }


def stats(trades: list[dict]) -> dict:
    """Closed trades only: _net_stats/net_r in this repo exclude outcome=='open'.

    The engine's R field is `r_multiple` (verified against a known pin).
    """
    closed = [t for t in trades if str(t.get("outcome", "")).lower() != "open"]
    rs = []
    for t in closed:
        r = t.get("r_multiple")
        if r is None:
            r = t.get("r") if t.get("r") is not None else t.get("net_r")
        if r is not None:
            rs.append(float(r))
    n = len(rs)
    net = sum(rs)
    wins = [x for x in rs if x > 0]
    losses = [x for x in rs if x <= 0]
    pf = (sum(wins) / abs(sum(losses))) if losses and sum(losses) != 0 else None
    eq = peak = 0.0
    dd = 0.0
    for x in rs:
        eq += x
        peak = max(peak, eq)
        dd = max(dd, peak - eq)
    return {
        "n": n, "net": net, "avgR": (net / n) if n else 0.0,
        "win": (len(wins) / n * 100.0) if n else 0.0,
        "pf": pf, "dd": dd, "open": len(trades) - len(closed),
    }


def main() -> int:
    from exp_tf_family import build_family_module

    sim = build_family_module()

    print("=" * 78)
    print("CHAMPION_CAUSAL - corrected chain baseline")
    print("=" * 78)
    print("  params: %s" % PARAMS)
    print()

    for era in ("is", "oos"):
        data = load_era(era)
        out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                  fine_ltf=data["fine"], **PARAMS)
        tr = out["ltf_trades"] if isinstance(out, dict) else out
        s = stats(tr)
        pn, pv = PINNED[era]
        bn, bv = BOOKS_TS_PIN[era]
        print("  --- %s ---" % era.upper())
        print("    trades raw=%d  closed=%d" % (len(tr), len([t for t in tr if str(t.get("outcome","")).lower() != "open"])))
        s = stats(tr)
        print("    trades  n=%d   net=%+.2fR   avgR=%+.3f   WR=%.1f%%   PF=%s   DD=%.1f   open=%d"
              % (s["n"], s["net"], s["avgR"], s["win"],
                 ("%.2f" % s["pf"]) if s["pf"] is not None else "-", s["dd"], s["open"]))
        print("    pin btc_routes   n=%-4d net=%+.2fR    delta  n %+d   net %+.2fR"
              % (pn, pv, s["n"] - pn, s["net"] - pv))
        print("    pin books.ts     n=%-4d net=%+.2fR    delta  n %+d   net %+.2fR"
              % (bn, bv, s["n"] - bn, s["net"] - bv))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())