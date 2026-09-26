"""Idea G — ETH/BTC ratio momentum skip (exp_eth_skip): cross-asset regime gate.

Skip entries when ETH/BTC ratio momentum over exp_eth_lb hours exceeds
exp_eth_skip (fraction, e.g. 0.05 = 5%). Structural/regime gate (exogenous
variable). Both-sides: IS champion/king/swingpause + OOS 2021-22.

Run: python live_stuff/tests/exp_eth_ratio.py
"""
import csv
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from run_experiment import get_data, BP, identity_gate, net_r
import test_experiments_craze as craze
from experiment_registry import EXPERIMENTS
from test_4_new_concepts import load_unseen, load_fine_1m as load_fine_unseen
from src.btc.btc_routes import _compute_swings
from engine.v18_params import SWING


def load_eth_1h(ts_lo, ts_hi):
    """ETH 1h closes aligned 1:1 to BTC c1h by index (same span after outer join)."""
    path = ROOT / "data" / "eth-fut" / "ETHUSDT_1h.csv"
    rows = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            # IST wall-clock -> naive epoch-ish key: reuse same convention as loaders
            rows.append(r)
    return rows


def eth_closes_aligned(btc_c1h):
    """Build list of ETH closes same length as btc_c1h, by nearest-lower 1h ts."""
    path = ROOT / "data" / "eth-fut" / "ETHUSDT_1h.csv"
    # parse IST wall clock -> epoch using same offset as replay harness if available
    from datetime import datetime, timedelta, timezone
    IST = timedelta(hours=5, minutes=30)
    eth = {}
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            dt = datetime.strptime(r["timestamp"], "%Y-%m-%d %H:%M:%S") - IST
            ts = int(dt.replace(tzinfo=timezone.utc).timestamp())
            eth[ts] = float(r["close"])
    eth_ts = sorted(eth)
    out = []
    import bisect
    for c in btc_c1h:
        t = int(c["ts"])
        j = bisect.bisect_right(eth_ts, t) - 1
        out.append(eth[eth_ts[j]] if j >= 0 else 0.0)
    return out


def run(sim, params, c15, sw15, c1h, sw, fine, eth_c, **flags):
    kw = {**BP, **params, **flags}
    kw.setdefault("exp_partial_r", 0.0)
    kw["exp_eth_closes"] = eth_c
    out = sim(c1h, sw, c15, sw15, fine_ltf=fine, **kw)
    return out["ltf_trades"] if isinstance(out, dict) else out


def main():
    t0 = time.time()
    print("=" * 100)
    print("  ETH/BTC RATIO MOMENTUM SKIP (Idea G) — exp_eth_skip")
    print("=" * 100)

    data = get_data()
    identity_gate(data)
    sim = craze.build_module()
    c15, sw15, c1h, sw10 = data["c15"], data["sw15"], data["c1h"], data["sw10"]
    fine_is = data["fine"]
    eth_is = eth_closes_aligned(c1h)
    print(f"  IS eth closes: {len(eth_is)} (zeros={eth_is.count(0.0)})", flush=True)

    print("loading OOS...", flush=True)
    (c15o, f15o), (c1ho, f1ho) = load_unseen("15m"), load_unseen("1h")
    sw15o = _compute_swings(f15o, "continuous", min_bars=SWING["min_bars_15m"])
    sw10o = _compute_swings(f1ho, "continuous", min_bars=10)
    fineo = load_fine_unseen(c15o[0]["ts"], c15o[-1]["ts"])
    eth_oos = eth_closes_aligned(c1ho)
    print(f"  OOS eth closes: {len(eth_oos)} (zeros={eth_oos.count(0.0)})  ({time.time()-t0:.0f}s)", flush=True)

    if eth_is.count(0.0) > len(eth_is) * 0.05 or eth_oos.count(0.0) > len(eth_oos) * 0.05:
        raise SystemExit("ETH coverage too sparse — fix fetch")

    configs = [
        ("champion_multi_sw10", {**EXPERIMENTS["champion_multi_sw10"]["params"]}, sw10, sw10o, eth_is, eth_oos),
        ("utcsat_multi_sw10 (king)", {**EXPERIMENTS["utcsat_multi_sw10"]["params"]}, sw10, sw10o, eth_is, eth_oos),
        ("swingpause single", {
            **{k: v for k, v in EXPERIMENTS["dirmatch_swingpause_single_sw10"]["params"].items()
               if k not in ("exp_require_dir_match", "exp_max_swing_age", "exp_dir_causal")}
        }, sw10, sw10o, eth_is, eth_oos),
    ]

    variants = [
        ("baseline", {}),
        ("skip |mom24|>5%", dict(exp_eth_skip=0.05, exp_eth_lb=24)),
        ("skip |mom24|>8%", dict(exp_eth_skip=0.08, exp_eth_lb=24)),
        ("skip |mom24|>12%", dict(exp_eth_skip=0.12, exp_eth_lb=24)),
        ("skip |mom48|>8%", dict(exp_eth_skip=0.08, exp_eth_lb=48)),
        ("skip |mom72|>10%", dict(exp_eth_skip=0.10, exp_eth_lb=72)),
        ("skip mom24>+8% (eth hot)", dict(exp_eth_skip=0.08, exp_eth_lb=24)),  # signed: only positive via abs still; note
    ]

    for name, params, sw_is, sw_oos, eth_i, eth_o in configs:
        print("\n" + "=" * 100, flush=True)
        print(f"  {name}", flush=True)
        print("=" * 100, flush=True)
        print(f"  {'variant':<40} {'IS n':>5} {'IS R':>9} {'dIS':>7} "
              f"{'OOS n':>6} {'OOS R':>9} {'dOOS':>7} {'NET I/O':>16} {'dNET':>14}", flush=True)
        base = None
        for label, flags in variants:
            # signed-only variant: use abs gate still (same as |mom|); for eth-hot
            # we'd need a sign flag — keep abs for this run
            tis = run(sim, params, c15, sw15, c1h, sw_is, fine_is, eth_i, **flags)
            tos = run(sim, params, c15o, sw15o, c1ho, sw_oos, fineo, eth_o, **flags)
            ri = sum(float(t["r_multiple"]) for t in tis)
            ro = sum(float(t["r_multiple"]) for t in tos)
            ni, no = net_r(tis), net_r(tos)
            if base is None:
                base = (ri, ro, ni, no)
            print(f"  {label:<40} {len(tis):>5} {ri:>+9.1f} {ri-base[0]:>+7.1f} "
                  f"{len(tos):>6} {ro:>+9.1f} {ro-base[1]:>+7.1f}   "
                  f"{ni:+.1f}/{no:+.1f}  {ni-base[2]:+.1f}/{no-base[3]:+.1f}",
                  flush=True)

    print(f"\n(done {time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
