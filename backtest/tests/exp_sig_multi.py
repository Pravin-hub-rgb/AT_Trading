"""exp_sig_multi - fsent_sig_full's knobs with the serial constraint removed.

WHY THIS IS A SEPARATE OBJECT AND NOT A VARIANT
===============================================
The owner asked for the fsent_champ_long autopsy and, from it, a research line:
"sig_full + max_positions = 0". That arm appeared in the FS-side autopsy as the
one thing worth an hour, so this file is that hour.

It is NOT a mode candidate and NOT a registry book. It differs from fsent_sig_full
in exactly one value, `max_positions` 1 -> 0, which flips the `busy_until` gate
off. So it is the sig book's whole filter set - bias_momentum 0.8, fs_small_swing
6.0, trail_skip_n 2, weekends skipped, FS entry on shorts - running unlimited
concurrency.

That distinction matters because the repo has a documented history of exactly this
mistake: a one-knob variant measured well, got written into the registry as a
candidate, and then died at period control having been inert in sample the whole
time (`method/FLIP_QUALITY_PERIOD_CONTROL.md`). So the gates below are not
ceremony - they are the reason this arm is either real or explicitly not.

WHAT IS MEASURED
================
  part 1  the comparison, both eras, against fsent_sig_full AND
          fsent_champ_long, so it is not being compared to a strawman
  part 2  the period control, on the disagreement set only. New entries minus
          removed ones, half-year fixed effect, cluster-robust SE by month, plus
          a month-cluster bootstrap. P87's construction, unchanged. The power
          gate prints before the verdict, always.
  part 3  the third gate: per-cell half-year comparison, both sides of it
  part 4  tail dependence and direction mix, because the FS-side autopsy found
          this arm's long and short columns are both alive (+136.7 / +83.1) which
          is unusual here and worth confirming rather than assuming
  part 5  concurrency shape - how many positions are actually open at once, since
          that is the thing the knob changes and nothing else measures it

THE ORDER MATTERS
=================
The period control runs BEFORE any "this looks better" reading is offered, and the
verdict section is written to be able to say no. If b does not survive, the honest
outcome is that this arm is another in-sample artifact and the doc says so.

PART 6 EXISTS BECAUSE PART 1 WAS BEING COMPARED ACROSS TWO ENGINES
===================================================================
The sibling sweep in part 6 came back with the multi books showing EXACTLY zero
delta when `max_positions` was flipped in both directions - +533.4 to +533.4,
byte-identical, on all three books and both eras. Flipping a concurrency gate
cannot be a no-op on a book that holds up to six positions at once, so the sweep
was measuring a knob that was not connected.

It is. The harness engine's position gate reads

    if max_positions > 0 and (not exp_mltf) and busy_until and bar_time <= busy_until:

and the harness patch wraps `exp_mltf` into that condition to INJECT the
multi behaviour. So `max_positions` only arms the gate when `exp_mltf` is False.

Which is exactly the shape of this repo's two families, and it explains the zero:

  * `fsent_sig_full` carries `max_positions=1` and NO `exp_mltf`. The gate is armed
    and never bypassed, so it is genuinely serial - and setting `max_positions=0`
    genuinely opens it. **The +mp0 result in parts 1-5 is real.**
  * the multi books carry `exp_mltf=True` and no `max_positions`. The gate is
    bypassed regardless of `max_positions`, so flipping it to 1 on them does
    nothing. That is the byte-identical result part 6 caught - not a broken knob,
    but a knob that is inert on books already running multi.

So the arm's honest description is: **the serial sig book with its single-slot gate
removed.** `max_positions` is the right knob for THIS book, and the sibling sweep
is null for a structural reason rather than because the knob does nothing.

Run:  cd backtest/tests
      python -u exp_sig_multi.py
"""
from __future__ import annotations

import json
import math
import random
import statistics as st
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

SIG = "fsent_sig_full"
MULTI = "fsent_champ_long"
DRAWS = 4000
SEED = 20261008
OUT_JSON = Path(__file__).parent / "_sig_multi.json"
OUT_MD = Path(__file__).parent / "_sig_multi.md"
DOC_MD = ROOT / "backtest/docs/method/SIG_MULTI_STUDY.md"


def mon(t):
    return datetime.fromtimestamp(int(t), tz=timezone.utc).strftime("%Y-%m")


def half(t):
    d = datetime.fromtimestamp(int(t), tz=timezone.utc)
    return "%d-%s" % (d.year, "H1" if d.month <= 6 else "H2")


def mdd(rs):
    cum = peak = 0.0
    m = 0.0
    for x in rs:
        cum += x
        if cum > peak:
            peak = cum
        m = max(m, peak - cum)
    return round(m, 2)


def instrument(y, coh, groups, clusters, seed):
    """P87's construction: intercept + cohort + one dummy per group except the
    first, solved with pinv. pinv not inv because a full dummy set is
    rank-deficient and returns b=0 silently on real data."""
    import numpy as np
    y = np.asarray(y, float)
    coh = np.asarray(coh, float)
    uniq = sorted(set(groups))
    cols = [np.ones(len(y)), coh]
    for g in uniq[1:]:
        cols.append(np.array([1.0 if x == g else 0.0 for x in groups]))
    X = np.column_stack(cols)
    Xi = np.linalg.pinv(X.T @ X)
    beta = Xi @ (X.T @ y)
    resid = y - X @ beta
    b = float(beta[1])

    Xi2 = np.linalg.pinv(X.T @ X)
    meat = np.zeros((X.shape[1], X.shape[1]))
    for c in set(clusters):
        m = np.array([x == c for x in clusters])
        u = X[m].T @ resid[m]
        meat += np.outer(u, u)
    G = len(set(clusters))
    V = Xi2 @ meat @ Xi2 * (G / max(1, G - 1))
    se = math.sqrt(max(float(V[1, 1]), 1e-18))
    t = b / se if se > 0 else 0.0
    mde = 1.96 * se

    rnd = random.Random(seed)
    by = {}
    for i, g in enumerate(clusters):
        by.setdefault(g, []).append(i)
    keys = list(by)
    acc = []
    for _ in range(DRAWS):
        idx = [i for k in [rnd.choice(keys) for _ in range(len(keys))] for i in by[k]]
        if len(set(idx)) < 4:
            continue
        acc.append(float((np.linalg.pinv(X[idx].T @ X[idx]) @ (X[idx].T @ y[idx]))[1]))
    return {"b": b, "t": t, "se": se, "mde": mde,
            "b_boot": (sum(acc) / len(acc)) if acc else 0.0, "n_groups": len(uniq)}


def main():
    from exp_tf_family import build_family_module
    from run_experiment import net_r, get_swings
    from exp_signal_metrics import load_era
    from experiment_registry import EXPERIMENTS

    sim = build_family_module()
    ARM_NAMES = ("sig_full (serial)", "sig+mp0  <-- THIS", "champ_long (multi)")
    data = {}
    for era in ("is", "oos"):
        d = load_era(era)
        data[era] = (d, get_swings(d, "sw10"))

    def run(era, book, **kw):
        d, sw = data[era]
        o = sim(d["c1h"], sw, d["c15"], d["sw15"], fine_ltf=d["fine"],
                **{**EXPERIMENTS[book]["params"], **kw})
        return [t for t in o["ltf_trades"] if t.get("outcome") != "open"]

    P = print
    P("=" * 118)
    P("  SIG_FULL + max_positions=0  -  the sig book's filters, unlimited concurrency")
    P("  ONE value differs from fsent_sig_full. This is an object, not a variant,")
    P("  and the period control below runs before anything is called an improvement.")
    P("=" * 118)

    report = {}

    # ---------- part 1: the comparison ----------
    P()
    P("#" * 118)
    P("# PART 1 - the comparison. Compared to fsent_sig_full AND fsent_champ_long,")
    P("#   so it is not being measured against a strawman.")
    P("#" * 118)
    P("  %-24s %5s %10s %8s %7s %9s %9s %16s"
      % ("arm", "n", "net", "DD", "WR", "expect", "net/DD", "long R / short R"))
    for era in ("is", "oos"):
        P("  -- %s --" % era.upper())
        for nm, book, kw in (("sig_full (serial)", SIG, {}),
                             ("sig+mp0  <-- THIS", SIG, {"max_positions": 0}),
                             ("champ_long (multi)", MULTI, {})):
            tr = run(era, book, **kw)
            rs = [net_r([t]) for t in tr]
            L = [net_r([t]) for t in tr if str(t["dir"]) == "long"]
            S = [net_r([t]) for t in tr if str(t["dir"]) == "short"]
            d = mdd(rs)
            P("  %-24s %5d %+10.1f %8.1f %6.0f%% %9.3f %9s %16s"
              % (nm, len(tr), sum(rs), d, 100 * sum(1 for x in rs if x > 0) / len(rs),
                 sum(rs) / len(rs), "%.2f" % (sum(rs) / d) if d else "-",
                 "%+.1f / %+.1f" % (sum(L), sum(S))))
            report.setdefault(era, {})[nm] = {
                "n": len(tr), "net": round(sum(rs), 2), "dd": d,
                "wr": round(100 * sum(1 for x in rs if x > 0) / len(rs), 1),
                "expectancy": round(sum(rs) / len(rs), 4),
                "net_per_dd": round(sum(rs) / d, 2) if d else None,
                "long_n": len(L), "long_r": round(sum(L), 2),
                "short_n": len(S), "short_r": round(sum(S), 2),
            }
    P()

    # ---------- part 2: period control ----------
    P("#" * 118)
    P("# PART 2 - PERIOD CONTROL. cohort 1 = a trade sig+mp0 has that the serial")
    P("#   book does not, cohort 0 = one the serial book has that it does not.")
    P("#   Survivors are in NEITHER cohort. b is the arm's information after the")
    P("#   calendar explains everything. MDE prints before any verdict.")
    P("#" * 118)
    for era in ("is", "oos"):
        base = run(era, SIG)
        arm = run(era, SIG, max_positions=0)
        bk = {(int(t["entry_ts"]), str(t["dir"])): t for t in base}
        ak = {(int(t["entry_ts"]), str(t["dir"])): t for t in arm}
        surv = set(bk) & set(ak)
        new = sorted(set(ak) - set(bk))
        drop = sorted(set(bk) - set(ak))
        surv_cost = sum(net_r([ak[k]]) - net_r([bk[k]]) for k in surv)
        new_sum = sum(net_r([ak[k]]) for k in new)
        drop_sum = sum(net_r([bk[k]]) for k in drop)
        bnet = sum(net_r([t]) for t in base)
        anet = sum(net_r([t]) for t in arm)
        print()
        print("  %s" % era.upper())
        print("    serial  %4dt / %+9.2fR        sig+mp0 %4dt / %+9.2fR        dNet %+.2fR"
              % (len(base), bnet, len(arm), anet, anet - bnet))
        print("    survivors %d (%+.2fR)   NEW %d (%+.2fR)   DROPPED %d (%+.2fR)"
              % (len(surv), surv_cost, len(new), new_sum, len(drop), drop_sum))
        recon = surv_cost + new_sum - drop_sum
        ok = abs((anet - bnet) - recon) < 1e-6
        print("    ASSERT exact decomposition: %s" % ("OK" if ok else "MISMATCH - b below meaningless"))
        if not ok:
            return 1
        if not new or not drop:
            print("    NO DISAGREEMENT in one direction - b is not estimable in this")
            print("    cell. Reported as not estimable rather than as a pass.")
            report[era]["period"] = {"estimable": False,
                                     "new": len(new), "drop": len(drop)}
            continue
        y, coh, grp, clus = [], [], [], []
        for k in new:
            coh.append(1); y.append(net_r([ak[k]]))
            grp.append(half(ak[k]["entry_ts"])); clus.append(mon(ak[k]["entry_ts"]))
        for k in drop:
            coh.append(0); y.append(net_r([bk[k]]))
            grp.append(half(bk[k]["entry_ts"])); clus.append(mon(bk[k]["entry_ts"]))
        res = instrument(y, coh, grp, clus, SEED)
        raw = (sum(y[i] for i in range(len(y)) if coh[i])
               - sum(y[i] for i in range(len(y)) if not coh[i]))
        per = raw / len(y)
        print("    disagreement: %d new vs %d dropped   raw gap %+.4fR/trade"
              % (len(new), len(drop), per))
        print("    b after period control   %+.4f   (%.0f%% of the raw gap survives)"
              % (res["b"], 100 * (1 - res["b"] / raw) if raw else 0))
        print("    cluster-robust t (month) %+.3f    SE %.4f" % (res["t"], res["se"]))
        print("    month-cluster bootstrap  %+.4f  (%d draws)" % (res["b_boot"], DRAWS))
        print("    MDE = 1.96*SE = %.4f   effect %.4f   -> %s"
              % (res["mde"], abs(res["b"]),
                 "UNDERPOWERED, effect inside the noise floor"
                 if res["mde"] > abs(res["b"]) else "powered, effect exceeds the minimum"))
        print("    POWER GATE PRINTED BEFORE ANY VERDICT, as required.")
        report[era]["period"] = {"estimable": True, "surv": len(surv),
                                 "new": len(new), "drop": len(drop),
                                 "raw_gap": round(per, 4),
                                 "b": round(res["b"], 4), "t": round(res["t"], 3),
                                 "se": round(res["se"], 4), "mde": round(res["mde"], 4),
                                 "b_boot": round(res["b_boot"], 4)}
    P()

    # ---------- part 3: half-year partition ----------
    P("#" * 118)
    P("# PART 3 - THIRD GATE: per-cell half-year, both sides, full per-cell net.")
    P("#" * 118)
    for era in ("is", "oos"):
        P()
        P("  %s" % era.upper())
        cells = {}
        for nm, book, kw in (("serial", SIG, {}), ("sig+mp0", SIG, {"max_positions": 0})):
            for t in run(era, book, **kw):
                h = half(t["entry_ts"])
                cells.setdefault(h, {}).setdefault(nm, [0.0, 0])
                c = cells[h][nm]
                c[0] += net_r([t]); c[1] += 1
        keys = sorted(cells)
        P("    %-9s %18s %18s %10s" % ("cell", "serial", "sig+mp0", "who"))
        wins = 0
        for k in keys:
            a = cells[k].get("serial", [0.0, 0])
            b = cells[k].get("sig+mp0", [0.0, 0])
            tag = "sig+mp0" if b[0] > a[0] else ("serial" if a[0] > b[0] else "tie")
            if b[0] > a[0]:
                wins += 1
            P("    %-9s %10.1f (%3dt) %10.1f (%3dt) %10s"
              % (k, a[0], a[1], b[0], b[1], tag))
        P("    sig+mp0 ahead in %d of %d half-years" % (wins, len(keys)))
        report[era]["partition_wins"] = wins
        report[era]["partition_cells"] = len(keys)

    # ---------- part 4: tail + direction ----------
    P()
    P("#" * 118)
    P("# PART 4 - tail dependence and direction mix.")
    P("#" * 118)
    P("  %-14s %-4s %9s %9s %9s %9s %9s %9s"
      % ("arm", "era", "drop t1", "drop t5", "drop t10", "drop1%", "drop5%", "top5%share"))
    for era in ("is", "oos"):
        for nm, book, kw in (("serial", SIG, {}), ("sig+mp0", SIG, {"max_positions": 0})):
            rs = [net_r([t]) for t in run(era, book, **kw)]
            s = sorted(rs)
            net = sum(rs)
            n = len(rs)

            def drop(k):
                return round(100.0 * (net - sum(s[-k:])) / net, 1)

            def contrib(pctv):
                k = max(1, int(round(n * pctv / 100.0)))
                return round(100.0 * sum(s[-k:]) / net, 1)

            P("  %-14s %-4s %9s %9s %9s %9s %9s %9s"
              % (nm, era.upper(), drop(1), drop(5), drop(10),
                 contrib(1), contrib(5), contrib(5)))
            report[era].setdefault(nm, {})["tail"] = {
                "drop_top1": drop(1), "drop_top5": drop(5), "drop_top10": drop(10),
                "contrib_top1pct": contrib(1), "contrib_top5pct": contrib(5),
            }

    # ---------- part 5: concurrency shape ----------
    P()
    P("#" * 118)
    P("# PART 5 - CONCURRENCY SHAPE. This is the thing the knob actually changes,")
    P("#   and nothing else in the repo measures it. How deep does the book actually")
    P("#   run, and does the serial book ever sit flat while a signal is available?")
    P("#" * 118)
    for era in ("is", "oos"):
        for nm, book, kw in (("serial", SIG, {}), ("sig+mp0", SIG, {"max_positions": 0})):
            tr = run(era, book, **kw)
            iv = sorted((int(t["entry_ts"]), int(t.get("exit_ts") or t["entry_ts"]))
                        for t in tr)
            depths = []
            for a, b in iv:
                depths.append(sum(1 for (x, y) in iv if x <= a <= y))
            mx = max(depths) if depths else 0
            hist = {}
            for dp in depths:
                hist[dp] = hist.get(dp, 0) + 1
            P("  %-14s %-4s entries=%d  max concurrent=%d  depth hist %s"
              % (nm, era.upper(), len(tr), mx,
                 " ".join("%d:%d" % (k, hist[k]) for k in sorted(hist))))
            report[era].setdefault(nm, {})["concurrency"] = {
                "max": mx, "hist": {str(k): v for k, v in sorted(hist.items())}}

    # ---------- part 6: which knob actually does this ----------
    P()
    P("#" * 118)
    P("# PART 6 - WHICH KNOB ACTUALLY MAKES THIS CHANGE. Flipping max_positions in")
    P("#   BOTH directions on the multi books returns byte-identical results, which")
    P("#   cannot be true of a working concurrency gate. So it is measured here.")
    P("#" * 118)
    P("  %-26s %-4s %6s %10s %10s" % ("arm", "era", "n", "net", "DD"))
    for era in ("is", "oos"):
        d, sw = data[era]
        for nm, kw in (("serial (as shipped)", {}),
                       ("max_positions=0", {"max_positions": 0}),
                       ("exp_mltf=False + mp=1", {"exp_mltf": False, "max_positions": 1}),
                       ("exp_mltf=False only", {"exp_mltf": False})):
            p = {**EXPERIMENTS[SIG]["params"], **kw}
            o = sim(d["c1h"], sw, d["c15"], d["sw15"], fine_ltf=d["fine"], **p)
            tr = [t for t in o["ltf_trades"] if t.get("outcome") != "open"]
            rs = [net_r([t]) for t in tr]
            P("  %-26s %-4s %6d %+10.1f %10.1f" % (nm, era.upper(), len(tr),
                                                   sum(rs), mdd(rs)))
        P("")

    P("  Reading: the harness gate is `max_positions > 0 and (not exp_mltf) and`")
    P("  `busy_until ...`, so max_positions only arms when exp_mltf is False.")
    P("  fsent_sig_full carries max_positions=1 and NO exp_mltf - the gate is armed")
    P("  and never bypassed, so it is genuinely serial and setting it to 0 genuinely")
    P("  opens it. Parts 1-5 measure a real change.")
    P("  The multi books carry exp_mltf=True and no max_positions, so the gate is")
    P("  bypassed whatever max_positions says. That is why flipping it on them is")
    P("  byte-identical - a structural reason, not a dead knob.")
    P()

    # ---------- verdict ----------
    P()
    P("=" * 118)
    P("VERDICT")
    P("=" * 118)
    est = [(e, report[e]["period"]) for e in ("is", "oos")
           if report[e].get("period", {}).get("estimable")]
    if len(est) == 2:
        all_pos = all(r["b"] > 0 for _, r in est)
        powered = [r["mde"] <= abs(r["b"]) for _, r in est]
        print("  b is positive in both eras: %s" % all_pos)
        print("  powered in both eras: %s" % all(powered))
        for e, r in est:
            print("    %-4s b=%+.4f t=%+.3f MDE=%.4f -> %s"
                  % (e.upper(), r["b"], r["t"], r["mde"],
                     "powered" if r["mde"] <= abs(r["b"]) else "UNDERPOWERED"))
        pw = all(report[e]["partition_wins"] > report[e]["partition_cells"] / 2
                 for e in ("is", "oos"))
        print("  ahead in a majority of half-years, both eras: %s" % pw)
        print()
        if all_pos and all(powered) and pw:
            print("  This is the first arm in this line of thinking that survives the")
            print("  period control, the power gate AND the partition together. It is")
            print("  still not a candidate: it has not been sibling-tested against the")
            print("  rest of the fsent family, and the registry is not the place to")
            print("  find that out after the fact.")
        elif all_pos:
            print("  Direction survives the period control but the magnitude is not")
            print("  established, or the partition does not agree. That is a candidate")
            print("  for more work, not an adoption.")
        else:
            print("  b does NOT survive in both eras. This is another in-sample")
            print("  artifact and the framework's discriminator says so. Drop it.")
    else:
        print("  Only %d of 2 eras were estimable. Nothing to conclude." % len(est))
    P()
    print("  Nothing promoted. No registry entry created.")

    OUT_JSON.write_text(json.dumps(report, indent=2, default=str) + "\n",
                        encoding="utf-8")
    lines = ["# sig_full + max_positions=0", "",
             "One value differs from `fsent_sig_full`. Period control, power gate and",
             "half-year partition all run before any verdict is offered.", "",
             "## part 1 - the comparison", "",
             "| era | arm | n | net | DD | WR% | expectancy | net/DD | long R | short R |",
             "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for era in ("is", "oos"):
        # only the three ARM rows - report[era] also holds "period", "partition_wins"
        # and per-arm sub-dicts, and iterating it blindly tried to format a string
        # with an int format spec.
        for nm in ARM_NAMES:
            r = report[era][nm]
            lines.append("| %s | %s | %d | %+.1f | %.1f | %.1f | %s | %s | %+.1f | %+.1f |" % (
                era.upper(), nm, r["n"], r["net"], r["dd"], r["wr"],
                r["expectancy"], r["net_per_dd"], r["long_r"], r["short_r"]))
    lines += ["", "## part 2 - period control", "",
              "| era | estimable | survivors | new | dropped | raw gap/trade | b | t | MDE | month boot |",
              "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for era in ("is", "oos"):
        r = report[era].get("period", {})
        if r.get("estimable"):
            lines.append("| %s | yes | %d | %d | %d | %+.4f | %+.4f | %+.3f | %.4f | %+.4f |" % (
                era.upper(), r["surv"], r["new"], r["drop"], r["raw_gap"],
                r["b"], r["t"], r["mde"], r["b_boot"]))
        else:
            lines.append("| %s | no (%d new / %d dropped) | - | - | - | - | - | - | - | - |" % (
                era.upper(), r.get("new", 0), r.get("drop", 0)))
    lines += ["", "## part 3 - half-year partition", "",
              "| era | sig+mp0 ahead | cells |", "|---|---:|---:|"]
    for era in ("is", "oos"):
        lines.append("| %s | %d | %d |" % (era.upper(), report[era]["partition_wins"],
                                           report[era]["partition_cells"]))
    lines += ["", "## part 5 - concurrency shape", "",
              "| era | arm | max concurrent | depth histogram |",
              "|---|---|---:|---|"]
    for era in ("is", "oos"):
        for nm in ("serial", "sig+mp0"):
            c = report[era][nm]["concurrency"]
            lines.append("| %s | %s | %d | %s |" % (
                era.upper(), nm, c["max"],
                " ".join("%s:%s" % (k, v) for k, v in c["hist"].items())))
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    P("wrote %s and %s" % (OUT_MD.name, OUT_JSON.name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())