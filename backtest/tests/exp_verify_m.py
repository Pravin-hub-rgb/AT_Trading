"""VERIFY, DON'T QUOTE - recompute M and the trail_half numbers FROM THE ENGINE.

WHY THIS FILE EXISTS
    method/BASE_BOOK_NULL.md states M = 381.7R IS / 205.5R OOS against the +239.1R leg
    book, and quotes exp_trail_half as "IS +325.8 -> +429.6, OOS +70.2 -> +110.5,
    a +103.8R IS dNet and +40.3R OOS dNet, both inside the null." Those are
    DOCUMENT numbers. The engine has moved since they were written (the origin
    book was retired as lookahead; the shipping leg book measures +239.1R, not
    +325.8R), so quoting them as current would be exactly the error that
    produced the FS overlay's phantom +349.90R. So: recompute.

WHAT IS "M", stated plainly
    M is NOT a target to beat and NOT a property of the strategy. It is the 95th
    percentile of a MOVE-BLOCK BOOTSTRAP of the book against ITSELF: take its
    own consecutive trades in blocks of 20, resample the blocks with
    replacement until the trade count is restored, 10,000 times, and read off
    the net each time. M is the net you would need for a result to be better
    than 95% of pure reorderings of the same trades.

    Blocks of 20 (not a shuffle) because a shuffle destroys the win/loss streak
    structure; resampling blocks preserves within-block serial dependence, the
    win/loss run structure and the trade count.

    So "inside the null" means: "this result was not better than 95% of ways of
    re-ordering the trades it was computed from." It is a statement about what
    the bootstrap can RESOLVE at this trade count and R-tail, not proof of no
    edge. The book sits at the 41st percentile IS / 50th OOS, i.e. dead centre
    of its own null - the null is wide because the tail is wide.

HOW TO READ THE OUTPUT
    For each arm: observed net, the bootstrap null mean, M (p95), and the
    percentile of the observed value inside that arm's OWN null. An arm is
    "inside the null" when its percentile is below 95. Comparing an arm to
    another arm's M is the error method/BASE_BOOK_NULL.md warns about - each book
    generates its own null.

BLOCK=20, DRAWS=10000, SEED=20260928 are pre-registered to match
exp_base_null.py exactly, so the numbers are comparable to the published ones.
"""
import sys, json, random, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend", ""):
    sys.path.insert(0, str(ROOT / p) if p else str(ROOT))

import run_experiment as re_
import exp_equity_quality as EQ
from src.btc.btc_routes import _trade_costs
import experiment_registry as reg

BLOCK, DRAWS, SEED = 20, 10_000, 20260928
OUT = ROOT / "backtest" / "tests" / "_verify_m.json"

ARMS = [
    ("champion_multi_sw10_leg", {}, "the shipping leg book"),
    ("trail_half", {"exp_trail_half": 1}, "trail ratchets HALFWAY"),
    ("trail_delay1", {"exp_trail_delay_r": 1.0}, "trail waits for +1R"),
    ("trail_half_delay1", {"exp_trail_half": 1, "exp_trail_delay_r": 1.0}, "half + delay1"),
    ("trail_half_skipn6_dr3", {}, "top IS book in the registry"),
]


def block_bootstrap_nets(rs, costs):
    """Resample BLOCKS of consecutive trades; keep the count and cost pairing."""
    n = len(rs)
    if n == 0:
        return []
    nb = max(1, n // BLOCK)
    rng = random.Random(SEED)
    nets = []
    for _ in range(DRAWS):
        idx = []
        while len(idx) < n:
            start = rng.randrange(0, n - BLOCK + 1) if n > BLOCK else 0
            idx.extend(range(start, start + BLOCK))
        idx = idx[:n]
        s = 0.0
        for i in idx:
            s += rs[i] - costs[i]
        nets.append(s)
    return nets
def run(scope, key, extra):
    cfg = reg.EXPERIMENTS[key]
    d = EQ.load_scope(scope)
    sim = re_.build_module()
    o = dict(re_.BP)
    o.update(cfg["params"])
    o.update(extra)
    sw = d["sw10"] if cfg["swing"] == "sw10" else d["sw20"]
    fine = d["fine"] if cfg.get("basis", "fine") == "fine" else []
    tr = sim(d["c1h"], sw, d["c15"], d["sw15"], fine_ltf=fine, **o)["ltf_trades"]
    _trade_costs(tr, 0.055, 2, 0.005, 0.01, 0.01)
    tr = [t for t in tr if t.get("outcome") != "open"]
    return ([float(t.get("r_multiple", 0.0)) for t in tr],
            [float(t.get("cost_r", 0.0)) for t in tr])


def main():
    res = {}
    for scope in ("is", "oos"):
        print("\n" + "=" * 100)
        print("ERA %s   M = 95th pct of a 20-trade-block bootstrap of the arm's OWN trades" % scope.upper())
        print("=" * 100)
        print("%-26s | %-17s | %-12s | %-11s | %s"
              % ("arm", "observed n/net", "null mean", "M (p95)", "percentile / verdict"))
        print("-" * 100)
        for key, extra, note in ARMS:
            if key not in reg.EXPERIMENTS:
                print("%-26s | not in registry" % key)
                continue
            rs, cs = run(scope, key, extra)
            if not rs:
                print("%-26s | no closed trades" % key)
                continue
            obs = sum(a - b for a, b in zip(rs, cs))
            nets = sorted(block_bootstrap_nets(rs, cs))
            mean = sum(nets) / len(nets)
            p95 = nets[int(0.95 * (len(nets) - 1))]
            pct = 100.0 * sum(1 for v in nets if v <= obs) / len(nets)
            verdict = "INSIDE null" if pct < 95 else "CLEARS M"
            res["%s|%s" % (scope, key)] = {
                "n": len(rs), "observed": round(obs, 2), "null_mean": round(mean, 2),
                "M_p95": round(p95, 2), "percentile": round(pct, 2), "note": note}
            print("%-26s | %4d /%+9.2fR | %+9.2fR | %+9.2fR | %5.1fth %s"
                  % (key, len(rs), obs, mean, p95, pct, verdict))
    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("\nwrote %s" % OUT)


if __name__ == "__main__":
    main()