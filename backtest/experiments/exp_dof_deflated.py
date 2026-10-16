"""The deflated test, re-run at the trial count the evidence actually supports.

WHY THIS EXISTS
---------------
exp_thesis_deflated_stats.py charged 464 trials, estimated as
`logged_experiments x 8 documented arms per experiment`, and found the
out-of-sample result unremarkable against the best of 464 lucky searches
(p_net = 1.0). That verdict was reasonable arithmetic on an unearned estimate.
The estimate was never audited.

exp_dof_inventory.py found the registry supports 4 varying structural switches:
mode (7), swing (3), exp_fs_entry_side (3), pivot_rule (2), plus max_positions
(2) - 252 genuinely different books. exp_dof_plateau.py then swept every
numeric knob that varies across 42 grid points on 9 book/knob pairs and found
9 of 9 to be PLATEAUS: the book survives its whole neighbourhood.

That matters more than it looks. A knob on a plateau does not produce
independent attempts at the same thing - it produces the SAME trade list again.
chop_thresh swept 42 to 62 returns byte-identical n, net, drawdown and avg_r on
the champion. Twenty sweep points, one result. Charging the deflation test for
twenty trials there is charging it for the same trade list twenty times.

So this recomputes the p-value across a range of trial counts rather than
defending one, and prints the table. The reader can see where the result stops
being exceptional, and argue with that number instead of with a methodology.

Output: dof_deflated.json
"""
from __future__ import annotations

import io
import json
import random
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tests"))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[1] / "backend"))

from exp_signal_metrics import load_era  # noqa: E402
from run_experiment import net_r, get_swings, BP, ENGINE_DEFAULTS  # noqa: E402
from exp_tf_family import build_family_module  # noqa: E402
from experiment_registry import EXPERIMENTS  # noqa: E402

OUT = HERE / "dof_deflated.json"

BOOK = "fsent_champ_long_htf15_tskip6"
SCOPE = "oos"
SEED = 20261016
SETS = 4000
TRIAL_COUNTS = (40, 100, 126, 252, 464, 1000)


def max_dd(rs):
    peak = cum = dd = 0.0
    for r in rs:
        cum += r
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
    return dd


def main() -> int:
    t0 = time.time()
    print("loading %s era ..." % SCOPE, flush=True)
    data = load_era(SCOPE)
    sim = build_family_module()
    cfg = EXPERIMENTS[BOOK]
    params = {**(BP if cfg.get("use_bp", True) else ENGINE_DEFAULTS), **(cfg.get("params") or {})}
    o = sim(data["c1h"], get_swings(data, cfg.get("swing") or "sw10"),
            data["c15"], data["sw15"], fine_ltf=data["fine"], **params)
    tr = [t for t in (o["ltf_trades"] if isinstance(o, dict) else o)
          if t.get("outcome") != "open"]
    tr.sort(key=lambda t: int(t["entry_ts"]))
    net = [net_r([t]) for t in tr]
    gross = [float(t.get("r_multiple") or 0.0) for t in tr]
    n = len(net)
    obs_net, obs_gross = sum(net), sum(gross)
    print("book %s  n=%d  net=%+.2f  gross=%+.2f  dd=%.2f"
          % (BOOK, n, obs_net, obs_gross, max_dd(net)), flush=True)

    # ZERO-EDGE null with the book's own variance and tail shape: centre the
    # trade distribution, keep the count fixed. Resampling raw R would carry the
    # real edge into the null and make every p 1.0, measuring nothing.
    mu_net = obs_net / n
    mu_gross = obs_gross / n
    centred_net = [r - mu_net for r in net]
    centred_gross = [r - mu_gross for r in gross]

    rng = random.Random(SEED)
    nmax = max(TRIAL_COUNTS)
    # best-of-N is a DIFFERENT statistic at every N. Keeping one maximum and
    # reporting it against every N is wrong: the max of 40 draws and the max of
    # 1000 draws are different numbers, and reusing the 1000-draw max at N=40
    # would overstate how lucky the result looks at small N. So the running
    # maximum is recorded at each N checkpoint and each N reads its own.
    traj_net = {N: [] for N in TRIAL_COUNTS}
    traj_gross = {N: [] for N in TRIAL_COUNTS}
    traj_dd = {N: [] for N in TRIAL_COUNTS}
    for _ in range(SETS):
        bn = bg = bd = None
        for k in range(1, nmax + 1):
            sn = sum(rng.choice(centred_net) for _ in range(n))
            sg = sum(rng.choice(centred_gross) for _ in range(n))
            dd = max_dd([rng.choice(centred_net) for _ in range(n)])
            if bn is None or sn > bn:
                bn = sn
            if bg is None or sg > bg:
                bg = sg
            if bd is None or dd > bd:
                bd = dd
            if k in traj_net:
                traj_net[k].append(bn)
                traj_gross[k].append(bg)
                traj_dd[k].append(bd)

    obs_dd = max_dd(net)
    rows = []
    print()
    print("=" * 74)
    print("BEST-OF-N UNDER A ZERO-EDGE NULL   (%s, %s, %d sets)" % (BOOK, SCOPE.upper(), SETS))
    print("=" * 74)
    print("%8s %14s %14s %14s" % ("trials N", "p net", "p gross", "p dd"))
    print("-" * 74)
    for N in TRIAL_COUNTS:
        pn = sum(1 for b in traj_net[N] if b >= obs_net) / SETS
        pg = sum(1 for b in traj_gross[N] if b >= obs_gross) / SETS
        pd = sum(1 for d in traj_dd[N] if d >= obs_dd) / SETS
        rows.append({"n_trials": N, "p_net": round(pn, 4),
                     "p_gross": round(pg, 4), "p_dd_worse": round(pd, 4)})
        print("%8d %14.4f %14.4f %14.4f" % (N, pn, pg, pd))
    print()
    print("A p above 0.05 means: best-of-N luck alone explains the result.")
    print("N=126 is the structural space the registry supports.")
    print("N=464 is the estimate exp_thesis_deflated_stats.py charged.")
    print()
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(
        {"book": BOOK, "scope": SCOPE, "n_trades": n, "observed": {
            "net": round(obs_net, 2), "gross": round(obs_gross, 2), "dd": round(obs_dd, 2)},
         "sets": SETS, "seed": SEED, "table": rows}, indent=1))
    print("wrote %s  (%.0fs)" % (OUT.name, time.time() - t0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())