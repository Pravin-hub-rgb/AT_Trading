"""P56 - DOES THE 1h LAYER EARN ITS KEEPING? The 15m book with the 1h
window's EXPIRY removed, leaving the 1h layer to supply direction only.

THE ARCHITECTURAL QUESTION
    P55 closed the whole family of 1h-structure gates on evidence: the
    layer's information is real, era-dependent, and not separable at
    decision time. But that was about gating on the layer's STRUCTURE.
    It leaves the prior question untouched, and the prior question is the
    bigger one:

        if the 1h layer's only measured job is supplying direction
        (P3: FLIP +1.9R IS, -23.6R OOS, PF never above 1.20), what does the
        EXPIRY of that window actually buy?

    A window ends at -1R, +3R or 16 days. All three are TRADE outcomes or a
    duration cap. This file removes the expiry entirely: once the 1h layer
    declares a direction, that direction stays allowed to the end of the
    data. The gate becomes direction-only and purely structural.

    If the 15m book is close to unchanged, the expiry - the whole v7 trade
    machinery underneath the cascade - is decoration, and the honest
    architecture is one timeframe. If it collapses, the expiry is doing
    real work and P3's "the 1h layer supplies direction" needs qualifying
    with "and it knows when to stop supplying it".

PATCH MECHANISM
    One line in `to_intervals`:
        wend = _r_touch_end(...) if window_end=="r_touch" else int(t["exit_ts"])
    is replaced with `wend = last_htf_ts + 3600`, so no window ever closes.
    The source is read, patched and exec'd as a fresh module - the repo file
    is never written, so there is nothing to revert. cap_days=16 is left
    alone so the control path is byte-identical.

ALSO MEASURED, AND THE POINT OF COMPARING ON TRADE QUALITY
    A bigger book that is worse per trade is not a free lunch, so both the
    net and the R/trade, PF, win rate and drawdown are reported. An arm that
    only adds trades and dilutes the book is the expected failure mode and
    has to be visible as such.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backtest/sweeps", "backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate, net_r
import test_experiments_craze as tc
from test_4_new_concepts import load_unseen, load_fine_1m
from test_experiments_craze import _compute_swings
from engine.v18_params import SWING

M_NULL = 193.4
ORIG = 'wend = _r_touch_end(t, fine_ltf, fine_ts, ext_stop_r) if ' \
       'window_end=="r_touch" else int(t["exit_ts"])'
PATCH = 'wend = last_htf_ts + 3600'
LANES = (
    ("champion_multi_sw10", "sw10", (500, 325.8), (279, 70.1)),
    ("utcsat_multi_sw10", "sw10", (453, 279.5), (254, 66.9)),
)


def pf(rs):
    return sum(x for x in rs if x > 0) / max(1e-9, -sum(x for x in rs if x < 0))


def dd(rs):
    e = p = d = 0.0
    for x in rs:
        e += x
        p = max(p, e)
        d = max(d, p - e)
    return d


def get(scope, swtag):
    if scope == "oos":
        (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
        return (c1h, _compute_swings(f1h, "continuous", min_bars=10),
                c15, _compute_swings(f15, "continuous",
                                     min_bars=SWING["min_bars_15m"]),
                load_fine_1m(c15[0]["ts"], c15[-1]["ts"]))
    d = get_data()
    identity_gate(d, tc.build_module())
    return d["c1h"], d[swtag], d["c15"], d["sw15"], d["fine"]


def run_no_expiry(a, params):
    """Same result as patching wend, but by wrapping v7 instead of the
    source: every closed HTF trade's exit_ts is pushed to the end of the
    1h series, so to_intervals builds a window that never expires.

    v18 imports simulate_btc_trades_v7 INSIDE the function body, so the
    attribute on the v7 module must stay wrapped across BOTH the engine
    build and the engine call.
    """
    from src.btc.engines import v7_timecap as v7
    orig = v7.simulate_btc_trades_v7

    def wrapped(candles, *ar, **kw):
        trs = orig(candles, *ar, **kw)
        last = int(candles[-1]["ts"]) + 3600
        for t in trs:
            if t.get("outcome") != "open":
                t["exit_ts"] = last
        return trs

    v7.simulate_btc_trades_v7 = wrapped
    try:
        return tc.build_module()(*a, **params)
    finally:
        v7.simulate_btc_trades_v7 = orig


def main():
    print("=" * 100)
    print("  P56  THE 15m BOOK WITH THE 1h WINDOW'S EXPIRY REMOVED")
    print("=" * 100)
    print("  Once the 1h layer declares a direction it stays allowed to the")
    print("  end of data. The gate becomes direction-only and purely")
    print("  structural. M = %.1fR\n" % M_NULL)
    src = tc.SRC
    n = src.count(ORIG)
    print("  patch site occurrences in the shipped source: %d" % n)
    if n != 1:
        print("  PATCH SITE NOT UNIQUE - STOP, nothing run")
        return
    patched = src.replace(ORIG, PATCH)
    for key, swtag, ispin, oospin in LANES:
        params = {**BP, **EXPERIMENTS[key]["params"]}
        print("  --- %s" % key)
        for scope, pin in (("is", ispin), ("oos", oospin)):
            a = get(scope, swtag)
            ctrl = tc.build_module()(*a, **params)
            tc_ = [t for t in ctrl["ltf_trades"]
                   if t.get("outcome") != "open"]
            nc, kc = net_r(tc_), len(tc_)
            if abs(kc - pin[0]) > 2 or abs(nc - pin[1]) > 1.5:
                print("    [%s] CONTROL FAILED %dt %+.1fR -- STOP"
                      % (scope, kc, nc))
                return
            rr = run_no_expiry(a, params)
            tn = [t for t in rr["ltf_trades"] if t.get("outcome") != "open"]
            nn, kn = net_r(tn), len(tn)
            rc = [float(t["r_multiple"]) for t in tc_]
            rn = [float(t["r_multiple"]) for t in tn]
            print("    [%s] control %dt %+.1fR (PIN ok)"
                  % (scope.upper(), kc, nc))
            print("      %-26s %5s %9s %7s %6s %6s %7s"
                  % ("arm", "n", "net", "R/t", "PF", "DD", "WR"))
            for lbl, rs, n_, net_ in (("control (window expires)", rc, kc, nc),
                                      ("NO EXPIRY (direction only)",
                                       rn, kn, nn)):
                print("      %-26s %5d %+9.1fR %+7.3f %6.2f %6.1f %6.1f%%"
                      % (lbl, n_, net_, net_ / max(1, n_), pf(rs), dd(rs),
                         100.0 * sum(1 for x in rs if x > 0) / len(rs)))
            d = nn - nc
            flag = " *" if abs(d) > M_NULL else ""
            print("      %-26s %5d trades, dNet %+8.1fR%s"
                  % ("delta", kn - kc, d, flag))
            print()
    print("  Nothing adopted.")


if __name__ == "__main__":
    main()