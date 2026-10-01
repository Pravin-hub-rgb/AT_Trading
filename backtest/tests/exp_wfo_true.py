"""TRUE re-optimizing walk-forward (WFO) — current champion family (2026-09-23).

Closes the long-standing backlog: every prior WF was FIXED-config stability.
This re-PICKS knobs on each train window, freezes for the test window.

Design (exp30 pattern, fine fills, net_r costs):
  - Grid ~48 combos over mode × thresh × ext × cd × persist (champion base)
  - Each combo runs ONCE full IS 2023-2026 (fine); trades sliced by entry_ts
  - 3 expanding year steps: train→test
      S1 train 2023       → test 2024
      S2 train 2023-24    → test 2025
      S3 train 2023-25    → test 2026
  - Baselines on the same test slices:
      fixed_champion = registry champion_multi_sw10 params
      oracle_full    = single best combo on FULL IS (in-sample upper bound)
  - Report: WF test NET, retention vs fixed_champion, chosen knobs per step

Caveat: engine state (halt streaks) carries across boundaries in full-period
runs — identical for all combos (fair comparison), same as exp30.

Run: python backtest/tests/exp_wfo_true.py
"""
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from run_experiment import get_data, BP, identity_gate, net_r
import test_experiments_craze as craze
from experiment_registry import EXPERIMENTS


def ts_of(datestr):
    return int(datetime.strptime(datestr, "%Y-%m-%d")
               .replace(tzinfo=timezone.utc).timestamp())


STEPS = [
    ("2024-01-01", "2025-01-01"),
    ("2025-01-01", "2026-01-01"),
    ("2026-01-01", "2027-01-01"),
]


def net_in(ledger, a, b):
    """net_r-style NET for trades with entry_ts in [a, b)."""
    rs = [r for ts, r in ledger if a <= ts < b]
    if not rs:
        return 0.0, 0
    # approximate net the same way run_experiment.net_r does on trade dicts
    # ledger stores precomputed net per trade already if we pass net per trade
    return sum(rs), len(rs)


def full_stats(tr):
    if not tr:
        return dict(n=0, net=0.0, wr=0.0, rpt=0.0, aw=0.0, al=0.0, pf=0.0,
                    dd=0.0, streak=0)
    rs = [float(t["r_multiple"]) for t in tr]
    nets = [net_r([t]) for t in tr]
    wins = [r for r in nets if r > 0]
    loss = [r for r in nets if r <= 0]
    net = sum(nets)
    wr = 100.0 * len(wins) / len(nets)
    aw = sum(wins) / len(wins) if wins else 0.0
    al = sum(loss) / len(loss) if loss else 0.0
    gp = sum(wins) if wins else 0.0
    gl = -sum(loss) if loss else 0.0
    pf = gp / gl if gl > 0 else float("inf")
    eq = peak = dd = 0.0
    mx = cur = 0
    for v in nets:
        eq += v
        if eq > peak:
            peak = eq
        d = peak - eq
        if d > dd:
            dd = d
        if v > 0:
            cur += 1
            if cur > mx:
                mx = cur
        else:
            cur = 0
    return dict(n=len(nets), net=net, wr=wr, rpt=net / len(nets),
                aw=aw, al=al, pf=pf, dd=dd, streak=mx)


def fmt(s):
    pf = s["pf"]
    pfs = "inf" if pf == float("inf") else f"{pf:.2f}"
    return (f"n={s['n']:>4} NET={s['net']:+8.1f} WR={s['wr']:5.1f}% "
            f"R/t={s['rpt']:+.3f} avgW={s['aw']:+.2f} avgL={s['al']:+.2f} "
            f"PF={pfs:>5} DD={s['dd']:5.1f} streak={s['streak']:>2}")


def trades_in(ledger, a, b, trades):
    """Trades for a combo ledger with entry in [a,b)."""
    out = []
    for i, (ts, r) in enumerate(ledger):
        if a <= ts < b:
            out.append(trades[i])
    return out


def main():
    t0 = time.time()
    print("=" * 110)
    print("  TRUE RE-OPTIMIZING WALK-FORWARD — champion family, expanding year steps")
    print("=" * 110)

    data = get_data()
    identity_gate(data)
    sim = craze.build_module()
    c15, sw15, c1h, sw10 = data["c15"], data["sw15"], data["c1h"], data["sw10"]
    fine = data["fine"]

    ch0 = {**EXPERIMENTS["champion_multi_sw10"]["params"]}
    T0 = int(c15[0]["ts"])
    T1 = int(c15[-1]["ts"]) + 900

    # ---- grid (champion base; override knobs) ----
    modes = [
        ("atr_high", "atr_high_thresh", (0.60, 0.65, 0.70)),
        ("b2_vs_flip_chop", "chop_thresh", (55.0, 58.0, 61.8)),
    ]
    exts = (1.5, 3.0)
    cds = (0, 8)
    persists = (0, 7)
    halts = (3,)  # fixed production

    combos = []
    for mode, tk, tv in modes:
        for th in tv:
            for ext in exts:
                for cd in cds:
                    for pers in persists:
                        for halt in halts:
                            combos.append({
                                "mode": mode, tk: th,
                                "ext_stop_r": ext, "cooldown_bars": cd,
                                "exp_persist": pers, "max_consecutive_losses": halt,
                            })

    print(f"grid: {len(combos)} combos × full IS fine run", flush=True)

    def run_combo(ov):
        kw = {**BP, **ch0, **ov}
        kw.setdefault("exp_partial_r", 0.0)
        out = sim(c1h, sw10, c15, sw15, fine_ltf=fine, **kw)
        tr = out["ltf_trades"] if isinstance(out, dict) else out
        ledger = [(int(t["entry_ts"]), net_r([t])) for t in tr]
        return ledger, tr

    book = {}
    trades_by = {}
    for i, ov in enumerate(combos):
        book[i], trades_by[i] = run_combo(ov)
        if (i + 1) % 6 == 0:
            print(f"  {i+1}/{len(combos)} ({time.time()-t0:.0f}s)", flush=True)

    champ_idx = None
    oracle_idx = None
    oracle_full = -1e9
    for i, ov in enumerate(combos):
        full = sum(r for _, r in book[i])
        if full > oracle_full:
            oracle_full = full
            oracle_idx = i
        thresh_ok = True
        if ov["mode"] == "atr_high":
            thresh_ok = abs(float(ov.get("atr_high_thresh", -1)) - float(ch0["atr_high_thresh"])) < 1e-9
        elif ov["mode"] == "b2_vs_flip_chop":
            thresh_ok = abs(float(ov.get("chop_thresh", -1)) - float(ch0["chop_thresh"])) < 1e-9
        if (thresh_ok
                and ov["mode"] == ch0["mode"]
                and abs(ov["ext_stop_r"] - float(ch0["ext_stop_r"])) < 1e-9
                and ov["cooldown_bars"] == ch0["cooldown_bars"]
                and ov["exp_persist"] == ch0["exp_persist"]
                and ov["max_consecutive_losses"] == ch0["max_consecutive_losses"]):
            champ_idx = i

    if champ_idx is None:
        raise SystemExit(f"champion combo not found in grid — ch0={ch0}")

    print(f"\nchampion combo idx={champ_idx} {combos[champ_idx]}")
    print(f"oracle full-IS combo idx={oracle_idx} NET={oracle_full:+.1f} {combos[oracle_idx]}")

    print("\n" + "=" * 110)
    print("  EXPANDING WFO — pick best train NET, freeze for test (full metrics per path)")
    print("=" * 110)
    print(f"  {'step':<4} {'window':<22} {'chosen knobs':<44} {'trainNET':>9} {'testNET':>9} {'champ':>9} {'oracle':>9}")

    wf_test = wf_ch = wf_or = 0.0
    chosen_count = {}
    wf_path_trades = []
    champ_path_trades = []
    or_path_trades = []
    step_rows = []
    for si, (a_s, b_s) in enumerate(STEPS, 1):
        a, b = ts_of(a_s), ts_of(b_s)
        best, best_net = None, -1e18
        for i in range(len(combos)):
            tn = sum(r for ts, r in book[i] if T0 <= ts < a)
            if tn > best_net:
                best, best_net = i, tn
        tn_test = sum(r for ts, r in book[best] if a <= ts < b)
        tn_ch = sum(r for ts, r in book[champ_idx] if a <= ts < b)
        tn_or = sum(r for ts, r in book[oracle_idx] if a <= ts < b)
        wf_test += tn_test
        wf_ch += tn_ch
        wf_or += tn_or
        ov = combos[best]
        knob = (f"{ov['mode'][:8]} th={ov.get('atr_high_thresh') or ov.get('chop_thresh')} "
                f"ext={ov['ext_stop_r']} cd={ov['cooldown_bars']} p={ov['exp_persist']}")
        chosen_count[best] = chosen_count.get(best, 0) + 1
        step_tr = trades_in(book[best], a, b, trades_by[best])
        ch_tr = trades_in(book[champ_idx], a, b, trades_by[champ_idx])
        or_tr = trades_in(book[oracle_idx], a, b, trades_by[oracle_idx])
        wf_path_trades.extend(step_tr)
        champ_path_trades.extend(ch_tr)
        or_path_trades.extend(or_tr)
        print(f"  S{si:<3} {a_s}→{b_s[:4]:<8}     {knob:<44} "
              f"{best_net:>+9.1f} {tn_test:>+9.1f} {tn_ch:>+9.1f} {tn_or:>+9.1f}", flush=True)
        step_rows.append(dict(step=si, a=a_s, b=b_s, knobs=knob,
                              train_net=best_net, test_net=tn_test,
                              champ=tn_ch, oracle=tn_or,
                              n=len(step_tr),
                              stats=full_stats(step_tr),
                              champ_stats=full_stats(ch_tr),
                              oracle_stats=full_stats(or_tr)))

    print("-" * 110)
    print(f"  WF TOTAL test NET: {wf_test:+.1f}   "
          f"fixed champion on same windows: {wf_ch:+.1f}   "
          f"oracle (full-IS best, fixed): {wf_or:+.1f}")
    if wf_ch:
        print(f"  Retention vs fixed champion: {100.0 * wf_test / wf_ch:.0f}%")
    if wf_or:
        print(f"  WFO / oracle (selection efficiency): {100.0 * wf_test / wf_or:.0f}%")

    print("\n  FULL METRICS — concatenated test-window path (the WFO number):")
    print(f"    WFO path     {fmt(full_stats(wf_path_trades))}")
    print(f"    Fixed champ  {fmt(full_stats(champ_path_trades))}")
    print(f"    Oracle fixed {fmt(full_stats(or_path_trades))}")

    print("\n  chosen combos across steps:")
    for i, c in chosen_count.items():
        print(f"    n={c}  {combos[i]}  fullIS_NET={sum(r for _, r in book[i]):+.1f}  fullIS {fmt(full_stats(trades_by[i]))}")

    out = {
        "steps": STEPS,
        "wf_test": wf_test,
        "fixed_champion": wf_ch,
        "oracle_full": wf_or,
        "retention_pct": (100.0 * wf_test / wf_ch) if wf_ch else None,
        "oracle_eff_pct": (100.0 * wf_test / wf_or) if wf_or else None,
        "oracle_idx": oracle_idx,
        "champ_idx": champ_idx,
        "chosen": {str(i): c for i, c in chosen_count.items()},
        "combos": [combos[i] for i in chosen_count],
        "full_nets": {str(i): sum(r for _, r in book[i])
                      for i in list(chosen_count) + [champ_idx, oracle_idx]},
        "step_rows": step_rows,
        "path_stats": {
            "wfo": full_stats(wf_path_trades),
            "champion": full_stats(champ_path_trades),
            "oracle": full_stats(or_path_trades),
        },
    }
    path = ROOT / "backtest/tests/_exp_wfo_true.json"
    path.write_text(json.dumps(out, indent=2))
    print(f"\n  wrote {path}")
    print(f"(done {time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
