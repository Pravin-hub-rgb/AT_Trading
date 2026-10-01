"""Path-true volume gates — IS champion/king/swingpause + OOS 2021-22.

Autopsy findings (exp_volume_autopsy.py, baseline 351t/+211.7):
  - B2 x rvol15: low-rvol B2 = -11.9R (131t WR21%) vs hi-rvol B2 = +44.7R
  - pct15 Q1 (trailing 96 bar percentile <15) = -13.8R PF0.72
  - FLIP low-rvol is the MONEY (+169.7) — do NOT gate FLIP on rvol
  - rvol>=2 / short+pct / abs-Q5: noise or tiny — skipped

Gates (craze kwargs, default off):
  exp_vol_b2_rvol  skip B2-kind entries when 15m rvol < thresh
  exp_vol_pct_min  skip ANY entry when 15m volume percentile < thresh

Run: python backtest/tests/exp_volume_path.py
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from run_experiment import get_data, BP, identity_gate, net_r
import test_experiments_craze as craze
from experiment_registry import EXPERIMENTS
from test_4_new_concepts import load_unseen, load_fine_1m as load_fine_unseen
from src.btc.btc_routes import _compute_swings
from engine.v18_params import SWING


def run(sim, params, c15, sw15, c1h, sw, fine, **flags):
    kw = {**BP, **params, **flags}
    kw.setdefault("exp_partial_r", 0.0)
    out = sim(c1h, sw, c15, sw15, fine_ltf=fine, **kw)
    return out["ltf_trades"] if isinstance(out, dict) else out


def full(trades):
    rs = [float(t["r_multiple"]) for t in trades]
    n = len(rs)
    if n == 0:
        return "n=0"
    net = sum(rs)
    wins = [x for x in rs if x > 0]
    losses = [x for x in rs if x <= 0]
    wr = 100.0 * len(wins) / n
    peak = cum = dd = 0.0
    for x in rs:
        cum += x
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
    pw = sum(wins)
    pl = abs(sum(losses))
    pf = (pw / pl) if pl > 0 else float("inf")
    avgw = (pw / len(wins)) if wins else 0.0
    avgl = (pl / len(losses)) if losses else 0.0
    pf_s = f"{pf:.2f}" if pf != float("inf") else "inf"
    return (f"n={n:4d} NET={net:+8.1f} WR={wr:5.1f}% R/t={net/n:+.3f} "
            f"PF={pf_s:>5} avgW={avgw:+.2f} avgL={avgl:.2f} DD={dd:.1f}")


def main():
    t0 = time.time()
    print("=" * 100)
    print("  PATH-TRUE VOLUME GATES — exp_vol_b2_rvol / exp_vol_pct_min")
    print("=" * 100)

    data = get_data()
    identity_gate(data)
    sim = craze.build_module()
    c15, sw15, c1h, sw10 = data["c15"], data["sw15"], data["c1h"], data["sw10"]
    fine_is = data["fine"]

    # Confirm volume is on IS candles
    vmiss = sum(1 for c in c15 if not (c.get("volume") or 0))
    print(f"  IS 15m candles missing volume: {vmiss}/{len(c15)}", flush=True)

    print("loading OOS...", flush=True)
    (c15o, f15o), (c1ho, f1ho) = load_unseen("15m"), load_unseen("1h")
    sw15o = _compute_swings(f15o, "continuous", min_bars=SWING["min_bars_15m"])
    sw10o = _compute_swings(f1ho, "continuous", min_bars=10)
    fineo = load_fine_unseen(c15o[0]["ts"], c15o[-1]["ts"])
    vmiss_o = sum(1 for c in c15o if not (c.get("volume") or 0))
    print(f"  OOS 15m candles missing volume: {vmiss_o}/{len(c15o)}  ({time.time()-t0:.0f}s)", flush=True)
    if vmiss > len(c15) * 0.05 or vmiss_o > len(c15o) * 0.05:
        raise SystemExit("volume coverage too sparse — fix loaders/CSVs")

    configs = [
        ("champion_multi_sw10", {**EXPERIMENTS["champion_multi_sw10"]["params"]}, sw10, sw10o),
        ("utcsat_multi_sw10 (king)", {**EXPERIMENTS["utcsat_multi_sw10"]["params"]}, sw10, sw10o),
        ("swingpause single", {
            **{k: v for k, v in EXPERIMENTS["dirmatch_swingpause_single_sw10"]["params"].items()
               if k not in ("exp_require_dir_match", "exp_max_swing_age", "exp_dir_causal")}
        }, sw10, sw10o),
    ]

    variants = [
        ("baseline", {}),
        ("B2 skip rvol<0.50", dict(exp_vol_b2_rvol=0.50)),
        ("B2 skip rvol<0.75", dict(exp_vol_b2_rvol=0.75)),
        ("B2 skip rvol<1.00", dict(exp_vol_b2_rvol=1.00)),
        ("skip pct15<10", dict(exp_vol_pct_min=10.0)),
        ("skip pct15<15", dict(exp_vol_pct_min=15.0)),
        ("skip pct15<20", dict(exp_vol_pct_min=20.0)),
        ("B2 rvol0.75 + pct15<15", dict(exp_vol_b2_rvol=0.75, exp_vol_pct_min=15.0)),
        ("B2 rvol0.75 + pct15<10", dict(exp_vol_b2_rvol=0.75, exp_vol_pct_min=10.0)),
    ]

    results = []
    for name, params, sw_is, sw_oos in configs:
        print("\n" + "=" * 100, flush=True)
        print(f"  {name}", flush=True)
        print("=" * 100, flush=True)
        base_is = base_oos = None
        for label, flags in variants:
            tr_i = run(sim, params, c15, sw15, c1h, sw_is, fine_is, **flags)
            tr_o = run(sim, params, c15o, sw15o, c1ho, sw_oos, fineo, **flags)
            n_is = len(tr_i)
            n_o = len(tr_o)
            g_is = sum(float(t["r_multiple"]) for t in tr_i)
            g_o = sum(float(t["r_multiple"]) for t in tr_o)
            net_is = net_r(tr_i)
            net_o = net_r(tr_o)
            if base_is is None:
                base_is = (n_is, g_is, net_is)
                base_oos = (n_o, g_o, net_o)
            d_is = g_is - base_is[1]
            d_o = g_o - base_oos[1]
            print(f"  {label:<28} IS  {full(tr_i)}", flush=True)
            print(f"  {'':28} OOS {full(tr_o)}", flush=True)
            print(f"  {'':28} dIS={d_is:+.1f} dOOS={d_o:+.1f} "
                  f"NET I/O={net_is:+.1f}/{net_o:+.1f}", flush=True)
            results.append((name, label, n_is, g_is, net_is, n_o, g_o, net_o, d_is, d_o))

    print("\n" + "=" * 100, flush=True)
    print("  SUMMARY (research comparison: both-sides deltas; no fixed ship threshold)", flush=True)
    print("=" * 100, flush=True)
    print(f"  {'config':<28} {'variant':<24} {'dIS':>7} {'dOOS':>7} {'NET I/O':>16}", flush=True)
    for name, label, n_is, g_is, net_is, n_o, g_o, net_o, d_is, d_o in results:
        if label == "baseline":
            continue
        print(f"  {name:<28} {label:<24} {d_is:>+7.1f} {d_o:>+7.1f} "
              f"{net_is:>+7.1f}/{net_o:>+7.1f}", flush=True)

    # Also print baseline full rows for reference
    print("\n  baselines:", flush=True)
    for name, label, n_is, g_is, net_is, n_o, g_o, net_o, d_is, d_o in results:
        if label == "baseline":
            print(f"  {name:<28} IS n={n_is} {g_is:+.1f}R net={net_is:+.1f} | "
                  f"OOS n={n_o} {g_o:+.1f}R net={net_o:+.1f}", flush=True)

    print(f"\n(done in {time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
