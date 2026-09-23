"""Path-true retest of the 5 OLD-ENGINE candidates never run on v18 (2026-09-23).

RESULT 2026-09-23 — see EXPERIMENT_LOG DEAD rows + ANCHOR_BASIS_AUDIT §3f-2:
  ADX / session / 4h-confirm / v9-cap  DEAD (all fail both-sides)
  flip-break  MARGINAL on swingpause only (dIS +7.6 / dOOS +8.3); DEAD on multi
  ADX/session/htf4/v9 kwargs REVERTED from craze (dead = clutter).
  exp_flip_break KEPT (stack research). Re-running ADX etc. now raises TypeError
  (intentional tombstone).

Identity basis: sw20 + coarse fills + BASE (340t/+225.3) via identity_gate().
Both-sides rule: IS (champion/king/swingpause) + OOS 2021-22 required.

Run: python live_stuff/tests/exp_oldengines_path.py
  (baseline + flip-break still work; other variants TypeError by design)
"""
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
from src.walker import FlowCandle
from engine.v18_params import SWING


def run(sim, data, params, c15, sw15, c1h, sw, fine, **flags):
    kw = {**BP, **params, **flags}
    kw.setdefault("exp_partial_r", 0.0)
    out = sim(c1h, sw, c15, sw15, fine_ltf=fine, **kw)
    return out["ltf_trades"] if isinstance(out, dict) else out


def show(tag, trades, base_r=None, base_net=None):
    n = len(trades)
    r = sum(float(t["r_multiple"]) for t in trades)
    wr = 100.0 * sum(1 for t in trades if float(t["r_multiple"]) > 0) / max(n, 1)
    nd = net_r(trades)
    d = f"  dR={r - base_r:+.1f}" if base_r is not None else ""
    dn = f"  dNET={nd - base_net:+.1f}" if base_net is not None else ""
    print(f"  {tag:<48} n={n:4d}  R={r:+8.1f}  WR={wr:5.1f}%  NET={nd:+8.1f}{d}{dn}")
    return r, nd


def synth_4h(candles):
    """Aggregate 1h candles into 4h buckets (ts//14400, UTC-aligned)."""
    out = []
    cur = None
    cur_b = None
    for c in candles:
        b = int(c["ts"]) // 14400
        if cur is None or b != cur_b:
            if cur:
                out.append(cur)
            cur_b = b
            cur = {
                "date": c["date"], "ts": b * 14400,
                "open": float(c["open"]), "high": float(c["high"]),
                "low": float(c["low"]), "close": float(c["close"]),
            }
        else:
            cur["high"] = max(cur["high"], float(c["high"]))
            cur["low"] = min(cur["low"], float(c["low"]))
            cur["close"] = float(c["close"])
            cur["date"] = c["date"]
    if cur:
        out.append(cur)
    return out


def swings_4h_from_1h(c1h, min_bars=10):
    c4 = synth_4h(c1h)
    f4 = [FlowCandle(date=c["date"], open=c["open"], high=c["high"],
                     low=c["low"], close=c["close"]) for c in c4]
    return _compute_swings(f4, "continuous", min_bars=min_bars), len(c4)


def main():
    t0 = time.time()
    print("=" * 100)
    print("  OLD-ENGINE PORTS PATH-TRUE — ADX / session / 4h confirm / v9 cap / flip-break")
    print("=" * 100)

    data = get_data()
    identity_gate(data)
    sim = craze.build_module()
    c15, sw15, c1h, sw10, sw20 = (data["c15"], data["sw15"], data["c1h"],
                                  data["sw10"], data["sw20"])
    fine_is = data["fine"]

    print("building 4h swings IS...", flush=True)
    sw4_is, n4_is = swings_4h_from_1h(c1h, min_bars=10)
    print(f"  {n4_is} 4h bars, {len(sw4_is)} swings ({time.time()-t0:.0f}s)")

    # ---- OOS ----
    print("loading OOS...", flush=True)
    (c15o, f15o), (c1ho, f1ho) = load_unseen("15m"), load_unseen("1h")
    sw15o = _compute_swings(f15o, "continuous", min_bars=SWING["min_bars_15m"])
    sw10o = _compute_swings(f1ho, "continuous", min_bars=10)
    fineo = load_fine_unseen(c15o[0]["ts"], c15o[-1]["ts"])
    sw4_oos, n4_oos = swings_4h_from_1h(c1ho, min_bars=10)
    print(f"  OOS {len(c15o)}x15m, {len(c1ho)}x1h, {n4_oos}x4h, "
          f"{len(sw4_oos)} 4h swings ({time.time()-t0:.0f}s)", flush=True)

    # configs: champion multi, king (utcsat), swingpause single
    configs = [
        ("champion_multi_sw10", {**EXPERIMENTS["champion_multi_sw10"]["params"]},
         sw10, sw10o),
        ("swingpause single", {
            **{k: v for k, v in EXPERIMENTS["dirmatch_swingpause_single_sw10"]["params"].items()
               if k not in ("exp_require_dir_match", "exp_max_swing_age", "exp_dir_causal")}
        }, sw10, sw10o),
    ]
    if "utcsat_multi_sw10" in EXPERIMENTS:
        configs.insert(1, ("utcsat_multi_sw10 (king)",
                           {**EXPERIMENTS["utcsat_multi_sw10"]["params"]},
                           sw10, sw10o))

    # variants per candidate (flag dict, label) — trimmed for runtime
    variants = [
        ("baseline", {}),
        # 1) ADX on 15m
        ("ADX>=20", dict(exp_adx_min=20.0)),
        ("ADX>=25", dict(exp_adx_min=25.0)),
        ("ADX>=30", dict(exp_adx_min=30.0)),
        # 2) session hours UTC (E5 candidate = 16-20)
        ("only 16-20 UTC", dict(exp_only_hour_lo=16, exp_only_hour_hi=20)),
        ("skip 16-20 UTC", dict(exp_skip_hour_lo=16, exp_skip_hour_hi=20)),
        # 3) 4h confirmation (swings swapped per side)
        ("htf4 confirm", dict(exp_htf4_confirm=1)),
        # 4) v9 conditional cap (primary setting)
        ("v9 extend 2R->30d", dict(exp_htf_extend_r=2.0, exp_htf_extend_days=30)),
        # 5) flip-break
        ("flip-break", dict(exp_flip_break=1)),
    ]

    for name, params, sw_is, sw_oos in configs:
        print("\n" + "=" * 100, flush=True)
        print(f"  PATH-TRUE — {name}", flush=True)
        print("=" * 100, flush=True)
        print(f"  {'variant':<48} {'IS n':>5} {'IS R':>9} {'dIS':>7} "
              f"{'OOS n':>6} {'OOS R':>9} {'dOOS':>7}", flush=True)
        base_is_r = base_oos_r = None
        base_is_net = base_oos_net = None
        for label, flags in variants:
            fl_is = dict(flags)
            fl_oos = dict(flags)
            if fl_is.get("exp_htf4_confirm"):
                fl_is["swings_htf4"] = sw4_is
                fl_oos["swings_htf4"] = sw4_oos
            tis = run(sim, data, params, c15, sw15, c1h, sw_is, fine_is, **fl_is)
            tos = run(sim, data, params, c15o, sw15o, c1ho, sw_oos, fineo, **fl_oos)
            ri = sum(float(t["r_multiple"]) for t in tis)
            ro = sum(float(t["r_multiple"]) for t in tos)
            ni, no = net_r(tis), net_r(tos)
            if base_is_r is None:
                base_is_r, base_oos_r = ri, ro
                base_is_net, base_oos_net = ni, no
            print(f"  {label:<48} {len(tis):>5} {ri:>+9.1f} {ri-base_is_r:>+7.1f} "
                  f"{len(tos):>6} {ro:>+9.1f} {ro-base_oos_r:>+7.1f}   "
                  f"NET {ni:+.1f}/{no:+.1f}  dNET {ni-base_is_net:+.1f}/{no-base_oos_net:+.1f}",
                  flush=True)

    print(f"\n(done {time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
