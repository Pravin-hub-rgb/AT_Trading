"""Full-path causal autopsy from OTHER BOT — F1 / F6 / F7, one gate at a time.

RESULT 2026-09-23: ALL THREE DEAD path-true (see EXPERIMENT_LOG + §3f tombstone).
  F6 er_min — dIS -180..-202, dOOS -35..-50 (our ER<0.10 bucket is +107R GOOD)
  F1 runmag — raw +18 is _gen_start leak; causal -108 dIS / -32 dOOS
  F7 risk2  — -24.7 dIS / -48.4 dOOS (extends §3e)
exp_er_min/exp_er_max REVERTED from the patcher (dead kwargs = clutter).
exp_dir_causal KEPT (D3 audit tool). This harness kept as tombstone record.

Their pre-registered rule (net-neg bucket + small bigWin):
  F1 running mag >= 2%   — WE already path-tested: DEAD under exp_dir_causal
  F6 15m ER20 < 0.1      — NEW (ER24-on-1h was rejected in 3f; this is 15m/20)
  F7 stop width >= 2%    — WE already path-tested risk_max=2.0: DEAD (-24.7 dR)

Protocol:
  1. identity gate (sw20 coarse BASE 340/+225.3)
  2. trade-list ER bucket parity vs their claim
  3. path-true ONE gate at a time on champion_multi + swingpause single
     IS + true OOS 2021-22
  4. if F6 survives: ER band (er_min=0.1 AND er_max=0.5) + yearly

NOTE: exp_er_* kwargs were present only while this harness first ran;
re-running now raises TypeError (intentional — gate is dead).

Run: python live_stuff/tests/exp_causal_autopsy_path.py
"""
import sys
import time
from collections import defaultdict
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


def er20(candles, i, n=20):
    if i < n:
        return None
    c0 = float(candles[i - n]["close"])
    c1 = float(candles[i]["close"])
    path = 0.0
    for k in range(i - n + 1, i + 1):
        path += abs(float(candles[k]["close"]) - float(candles[k - 1]["close"]))
    return abs(c1 - c0) / path if path > 0 else 0.0


def bucket_er(rows):
    bins = [
        ("a:<0.10", lambda e: e < 0.10),
        ("b:0.10-0.20", lambda e: 0.10 <= e < 0.20),
        ("c:0.20-0.30", lambda e: 0.20 <= e < 0.30),
        ("d:0.30-0.50", lambda e: 0.30 <= e < 0.50),
        ("e:>=0.50", lambda e: e >= 0.50),
    ]
    print("\n--- ER20 buckets (trade-list) ---")
    for tag, fn in bins:
        lst = [r for r in rows if r["er"] is not None and fn(r["er"])]
        if not lst:
            print(f"  {tag:<14} n=0")
            continue
        rs = [r["r"] for r in lst]
        big = sum(x for x in rs if x >= 2.0)
        wr = 100.0 * sum(1 for x in rs if x > 0) / len(rs)
        print(f"  {tag:<14} n={len(lst):4d}  R={sum(rs):+8.1f}  "
              f"avg={sum(rs)/len(rs):+6.3f}  WR={wr:5.1f}%  bigWinR={big:+.1f}")


def show(tag, trades, base_r=None):
    n = len(trades)
    r = sum(float(t["r_multiple"]) for t in trades)
    wr = 100.0 * sum(1 for t in trades if float(t["r_multiple"]) > 0) / max(n, 1)
    nd = net_r(trades)
    d = f"  dR={r - base_r:+.1f}" if base_r is not None else ""
    print(f"  {tag:<44} n={n:4d}  R={r:+8.1f}  WR={wr:5.1f}%  NET={nd:+8.1f}{d}")
    return r, nd


def run(sim, data, params, c15, sw15, c1h, sw, fine, **flags):
    kw = {**BP, **params, **flags}
    kw.setdefault("exp_partial_r", 0.0)
    out = sim(c1h, sw, c15, sw15, fine_ltf=fine, **kw)
    return out["ltf_trades"] if isinstance(out, dict) else out


def main():
    t0 = time.time()
    print("=" * 100)
    print("  CAUSAL AUTOPSY FULL-PATH — F1 runmag / F6 ER20 / F7 risk2 (one at a time)")
    print("=" * 100)

    data = get_data()
    identity_gate(data)
    sim = craze.build_module()
    fine_is = data["fine"]
    c15, sw15, c1h = data["c15"], data["sw15"], data["c1h"]
    sw10 = data["sw10"]

    # ---- OOS ----
    (c15o, f15o), (c1ho, f1ho) = load_unseen("15m"), load_unseen("1h")
    sw15o = _compute_swings(f15o, "continuous", min_bars=SWING["min_bars_15m"])
    sw10o = _compute_swings(f1ho, "continuous", min_bars=10)
    fineo = load_fine_unseen(c15o[0]["ts"], c15o[-1]["ts"])
    print(f"OOS loaded: {len(c1ho)} x1h, {len(c15o)} x15m")

    # ---- trade-list ER parity on champion ----
    ch = {**EXPERIMENTS["champion_multi_sw10"]["params"]}
    tr_base = run(sim, data, ch, c15, sw15, c1h, sw10, fine_is)
    rows = []
    import bisect
    ts15 = [int(c["ts"]) for c in c15]
    for t in tr_base:
        i = bisect.bisect_left(ts15, int(t["entry_ts"]))
        rows.append({"r": float(t["r_multiple"]), "er": er20(c15, i)})
    print("\n=== TRADE-LIST ER20 parity (champion base) ===")
    show("champion base IS", tr_base)
    bucket_er(rows)
    cut = [r for r in rows if r["er"] is not None and r["er"] < 0.10]
    cut_r = sum(r["r"] for r in cut)
    big = sum(r["r"] for r in cut if r["r"] >= 2.0)
    print(f"  F6 cut bucket ER<0.10: n={len(cut)} R={cut_r:+.1f} bigWinR={big:+.1f}")
    print(f"  their claim: n=93 R=-17.7 bigWinR=+43.0 (⚠ bigWin large)")

    # ---- path-true gates ----
    print("\n" + "=" * 100)
    print("  PATH-TRUE — champion_multi_sw10")
    print("=" * 100)
    print(f"  {'variant':<40} {'IS n':>5} {'IS R':>9} {'dIS':>7} "
          f"{'OOS n':>6} {'OOS R':>9} {'dOOS':>7}")
    base_is_r = base_oos_r = None
    variants = [
        ("baseline", {}),
        ("F6 er_min=0.10", dict(exp_er_min=0.10)),
        ("F6 er_min=0.15", dict(exp_er_min=0.15)),
        ("F6 band 0.10-0.50", dict(exp_er_min=0.10, exp_er_max=0.50)),
        ("F6 band 0.15-0.50", dict(exp_er_min=0.15, exp_er_max=0.50)),
        ("F1 runmag=2.0 (ref DEAD)", dict(exp_max_running_mag=2.0)),
        ("F1 runmag=2.0+causal", dict(exp_max_running_mag=2.0, exp_dir_causal=1)),
        ("F7 risk_max=2.0 (ref DEAD)", dict(exp_risk_max_pct=2.0)),
    ]
    ch_is = ch_oos = None
    for name, flags in variants:
        if ch_is is None:
            ch_is = {**EXPERIMENTS["champion_multi_sw10"]["params"]}
            ch_oos = ch_is
        tis = run(sim, data, ch, c15, sw15, c1h, sw10, fine_is, **flags)
        tos = run(sim, data, ch, c15o, sw15o, c1ho, sw10o, fineo, **flags)
        ri = sum(float(t["r_multiple"]) for t in tis)
        ro = sum(float(t["r_multiple"]) for t in tos)
        if base_is_r is None:
            base_is_r, base_oos_r = ri, ro
        ndi, ndo = net_r(tis), net_r(tos)
        print(f"  {name:<40} {len(tis):>5} {ri:>+9.1f} {ri-base_is_r:>+7.1f} "
              f"{len(tos):>6} {ro:>+9.1f} {ro-base_oos_r:>+7.1f}   "
              f"NET {ndi:+.1f}/{ndo:+.1f}")

    # ---- single swingpause ----
    print("\n" + "=" * 100)
    print("  PATH-TRUE — swingpause single (strip dirmatch if present)")
    print("=" * 100)
    sp = {**EXPERIMENTS["dirmatch_swingpause_single_sw10"]["params"]}
    sp.pop("exp_require_dir_match", None)
    sp.pop("exp_max_swing_age", None)
    sp.pop("exp_dir_causal", None)
    base_is_r = base_oos_r = None
    for name, flags in [
        ("baseline", {}),
        ("F6 er_min=0.10", dict(exp_er_min=0.10)),
        ("F6 band 0.10-0.50", dict(exp_er_min=0.10, exp_er_max=0.50)),
        ("F1 runmag=2.0", dict(exp_max_running_mag=2.0)),
        ("F7 risk_max=2.0", dict(exp_risk_max_pct=2.0)),
    ]:
        tis = run(sim, data, sp, c15, sw15, c1h, sw10, fine_is, **flags)
        tos = run(sim, data, sp, c15o, sw15o, c1ho, sw10o, fineo, **flags)
        ri = sum(float(t["r_multiple"]) for t in tis)
        ro = sum(float(t["r_multiple"]) for t in tos)
        if base_is_r is None:
            base_is_r, base_oos_r = ri, ro
        ndi, ndo = net_r(tis), net_r(tos)
        print(f"  {name:<40} {len(tis):>5} {ri:>+9.1f} {ri-base_is_r:>+7.1f} "
              f"{len(tos):>6} {ro:>+9.1f} {ro-base_oos_r:>+7.1f}   "
              f"NET {ndi:+.1f}/{ndo:+.1f}")

    # ---- utcsat multi (king) ----
    if "utcsat_multi_sw10" in EXPERIMENTS:
        print("\n" + "=" * 100)
        print("  PATH-TRUE — utcsat_multi_sw10 (king)")
        print("=" * 100)
        ut = {**EXPERIMENTS["utcsat_multi_sw10"]["params"]}
        base_is_r = base_oos_r = None
        for name, flags in [
            ("baseline", {}),
            ("F6 er_min=0.10", dict(exp_er_min=0.10)),
            ("F6 band 0.10-0.50", dict(exp_er_min=0.10, exp_er_max=0.50)),
        ]:
            tis = run(sim, data, ut, c15, sw15, c1h, sw10, fine_is, **flags)
            tos = run(sim, data, ut, c15o, sw15o, c1ho, sw10o, fineo, **flags)
            ri = sum(float(t["r_multiple"]) for t in tis)
            ro = sum(float(t["r_multiple"]) for t in tos)
            if base_is_r is None:
                base_is_r, base_oos_r = ri, ro
            ndi, ndo = net_r(tis), net_r(tos)
            print(f"  {name:<40} {len(tis):>5} {ri:>+9.1f} {ri-base_is_r:>+7.1f} "
                  f"{len(tos):>6} {ro:>+9.1f} {ro-base_oos_r:>+7.1f}   "
                  f"NET {ndi:+.1f}/{ndo:+.1f}")

    # ---- yearly for best F6 candidate ----
    print("\n" + "=" * 100)
    print("  YEARLY — champion baseline vs er_min=0.10 vs band")
    print("=" * 100)
    for name, flags in [
        ("baseline", {}),
        ("er_min=0.10", dict(exp_er_min=0.10)),
        ("band 0.10-0.50", dict(exp_er_min=0.10, exp_er_max=0.50)),
    ]:
        tr = run(sim, data, ch, c15, sw15, c1h, sw10, fine_is, **flags)
        py = defaultdict(float)
        for t in tr:
            py[str(t.get("entry_date", ""))[:4]] += float(t["r_multiple"])
        yrs = "  ".join(f"{y}:{py[y]:+.1f}" for y in sorted(py))
        print(f"  {name:<24} {yrs}")

    print(f"\n(done {time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
