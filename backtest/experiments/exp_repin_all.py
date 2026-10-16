"""Re-derive every registry pin from the current engine, on both eras.

WHY THIS EXISTS
---------------
The registry pins were found to be internally inconsistent in three separate
ways, and each one can silently make a reader quote the wrong number:

1. `n` and `net` are the IS-dataset figures, not the across-both-eras total.
   load_era("is") is run_experiment.get_data() - the 2023-01..2026-08 span -
   while the OOS era is a separate file loaded by load_unseen. The field names
   read like totals. 535 + 302 = 837, and the lens reports 837.

2. `win` is a GROSS win rate. net_r() subtracts fees, slippage and funding, so a
   trade that is +0.01R gross and -0.02R net counts as a win in `win` and as a
   loss in the lens. On fsent_champ_long_mcloff_htf15 that is 24 trades and 4.5
   percentage points.

3. There is no both-era total anywhere in the registry, while exp_results_export
   ranks books by "net across both eras" in its docstring and actually ranks by
   the IS-only pin.

This script re-measures all three correctly from the engine and writes both the
measurements and a drift report against whatever the pins currently say. Nothing
here edits the registry. That is a separate, deliberate step - a measurement tool
that also writes its own conclusions is how numbers get laundered.

SPANS
-----
  IS   2023-01 .. 2026-08   run_experiment.get_data()   (the larger one)
  OOS  2021-22              test_4_new_concepts.load_unseen()
  Both eras are reported separately and merged in calendar order.

Output: backtest/experiments/repin_all.json (incremental, resumable)
        backtest/experiments/repin_all.md
"""
from __future__ import annotations

import io
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tests"))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[1] / "backend"))

from experiment_registry import EXPERIMENTS, BP, ENGINE_DEFAULTS  # noqa: E402
from run_experiment import net_r, get_swings, get_data, build_module  # noqa: E402
from exp_tf_family import build_family_module  # noqa: E402

OUT = HERE / "repin_all.json"
MD = HERE / "repin_all.md"


def _dd(rs):
    """Peak-to-trough on the given R series.

    Peak-to-trough, not loss-from-inception. An earlier version of this harness
    tracked the minimum cumulative sum below zero and reported -0.00 for books
    whose equity never went underwater from inception, which made all 54 books
    look like they had drifted. The lens (equity_quality) uses peak-to-trough,
    so this must too or the two columns describe different books.
    """
    peak = cum = dd = 0.0
    for r in rs:
        cum += r
        if cum > peak:
            peak = cum
        if peak - cum > dd:
            dd = peak - cum
    return round(dd, 2)


def _era_stats(trades):
    """(n, net, dd_net, wr_net, wr_gross) for one era, dropping open trades.

    Open trades have no exit, so they have no realised R and are not counted by
    the lens either. Dropping them here keeps the pin and the lens on one set.
    """
    tr = [t for t in trades if t.get("outcome") != "open"]
    if not tr:
        return dict(n=0, net=0.0, dd_net=0.0, wr_net=None, wr_gross=None)
    net = [net_r([t]) for t in tr]
    gross = [float(t["r_multiple"]) for t in tr]
    nw = sum(1 for r in net if r > 0)
    gw = sum(1 for r in gross if r > 0)
    return dict(
        n=len(tr),
        net=round(sum(net), 2),
        dd_net=_dd(net),
        wr_net=round(nw / len(tr), 3),
        wr_gross=round(gw / len(tr), 3),
    )


def _run_one_era(sim, data, cfg):
    base = BP if cfg.get("use_bp", True) else ENGINE_DEFAULTS
    params = {**base, **(cfg.get("params") or {})}
    swing = cfg.get("swing") or "sw10"
    o = sim(data["c1h"], get_swings(data, swing), data["c15"], data["sw15"],
            fine_ltf=data["fine"], **params)
    return o["ltf_trades"] if isinstance(o, dict) else o


def main():
    from exp_signal_metrics import load_era

    t0 = time.time()
    print("loading eras ...", flush=True)
    ERA = {"is": get_data(), "oos": load_era("oos")}
    sim = build_family_module()

    names = [k for k, v in EXPERIMENTS.items()
             if isinstance(v, dict) and isinstance(v.get("pins"), dict)
             and "n" in v["pins"]]
    done = json.loads(io.open(OUT, encoding="utf-8").read()) if OUT.exists() else {}
    print("%d pinned books, %d already measured" % (len(names), len(done)), flush=True)

    for i, name in enumerate(names, 1):
        if name in done:
            continue
        cfg = EXPERIMENTS[name]
        rec = {}
        try:
            per = {}
            for era in ("is", "oos"):
                tr = _run_one_era(sim, ERA[era], cfg)
                per[era] = sorted(tr, key=lambda t: int(t["entry_ts"]))
            stats = {era: _era_stats(tr) for era, tr in per.items()}
            merged = sorted(per["is"] + per["oos"], key=lambda t: int(t["entry_ts"]))
            stats["all"] = _era_stats(merged)
            rec["ok"] = True
            rec["stats"] = stats
            rec["span"] = dict(
                is_first=min((int(t["entry_ts"]) for t in per["is"]), default=None),
                is_last=max((int(t["entry_ts"]) for t in per["is"]), default=None),
                oos_first=min((int(t["entry_ts"]) for t in per["oos"]), default=None),
                oos_last=max((int(t["entry_ts"]) for t in per["oos"]), default=None),
            )
        except Exception as exc:  # noqa: BLE001
            rec["ok"] = False
            rec["error"] = "%s: %s" % (type(exc).__name__, exc)
        done[name] = rec
        io.open(OUT, "w", encoding="utf-8").write(json.dumps(done, indent=1, sort_keys=True))
        flag = "ok " if rec.get("ok") else "ERR"
        if rec.get("ok"):
            s = rec["stats"]
            print("[%2d/%d] %s %-36s IS %4d/%+8.2f  OOS %4d/%+8.2f  ALL %4d/%+8.2f  (%.0fs)"
                  % (i, len(names), flag, name, s["is"]["n"], s["is"]["net"],
                     s["oos"]["n"], s["oos"]["net"], s["all"]["n"], s["all"]["net"],
                     time.time() - t0), flush=True)
        else:
            print("[%2d/%d] %s %-36s %s" % (i, len(names), flag, name, rec["error"]), flush=True)

    # ---------------- report ----------------
    L = []
    L.append("# Every registry pin, re-derived from the current engine")
    L.append("")
    L.append("`n` and `net` in the registry are the **IS-dataset** figures")
    L.append("(2023-01..2026-08). The OOS era is a separate file. The **all** columns")
    L.append("below are the two eras merged in calendar order - the lens convention.")
    L.append("")
    L.append("`win` in the registry is **gross**; `wr_net` here is the same trade set")
    L.append("after fees, slippage and funding.")
    L.append("")
    L.append("| book | IS n | IS net | wr_net | wr_gross | OOS n | OOS net | wr_net | ALL n | ALL net | ALL dd |")
    L.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    drift = []
    mapping = {}
    nomatch = []
    drift_by_field = {}
    for name in sorted(done):
        rec = done[name]
        if not rec.get("ok"):
            L.append("| `%s` | ERROR: %s |||||||||" % (name, rec.get("error", "?")))
            continue
        s = rec["stats"]
        L.append("| `%s` | %d | %+.2f | %.3f | %.3f | %d | %+.2f | %.3f | %d | %+.2f | %.2f |" % (
            name, s["is"]["n"], s["is"]["net"], s["is"]["wr_net"], s["is"]["wr_gross"],
            s["oos"]["n"], s["oos"]["net"], s["oos"]["wr_net"],
            s["all"]["n"], s["all"]["net"], s["all"]["dd_net"]))
        p = EXPERIMENTS[name]["pins"]
        # Pin conventions have drifted historically: n/net are the IS dataset,
        # but dd_net has been written on the gross basis, the net basis and the
        # merged basis on different days. Each candidate column is tested so the
        # report says WHICH column a pin matches rather than just that it moved.
        matched = False
        for pk, cands in (("n", ("is", "oos", "all")), ("net", ("is", "oos", "all")),
                          ("dd_net", ("is", "oos", "all")), ("oos_n", ("is", "oos", "all")),
                          ("oos_net", ("is", "oos", "all")), ("oos_dd_net", ("is", "oos", "all"))):
            if pk not in p:
                continue
            field = "dd_net" if "dd" in pk else ("net" if "net" in pk else "n")
            hit = [c for c in cands if abs(float(p[pk]) - s[c][field]) <= 0.02]
            if not hit:
                drift.append((name, pk, p[pk], "no column matches"))
                drift_by_field.setdefault(pk, []).append(name)
            else:
                mapping.setdefault(pk, {}).setdefault(hit[0], []).append(name)
                matched = True
        if not matched:
            nomatch.append(name)
    L.append("")
    L.append("## Which column each existing pin actually matches")
    L.append("")
    L.append("Pin conventions were never uniform. This says, per field, which")
    L.append("column the existing value reproduces - so the new convention below is")
    L.append("a deliberate choice, not an accident inherited from one bad day.")
    L.append("")
    L.append("| pin field | matches `is` | matches `oos` | matches `all` | matches nothing |")
    L.append("|---|---:|---:|---:|---:|")
    for pk in ("n", "net", "dd_net", "oos_n", "oos_net", "oos_dd_net"):
        mm = mapping.get(pk, {})
        tot = sum(len(v) for v in mm.values())
        nn = len(drift_by_field.get(pk, []))
        L.append("| `%s` | %d | %d | %d | %d |" % (pk, len(mm.get("is", [])), len(mm.get("oos", [])), len(mm.get("all", [])), nn))
    L.append("")
    L.append("## The new convention these numbers will be written under")
    L.append("")
    L.append("| field | span | lens |")
    L.append("|---|---|---|")
    L.append("| `n`, `net`, `wr_net` | IS dataset, 2023-01..2026-08 | net |")
    L.append("| `oos_n`, `oos_net`, `oos_wr_net` | OOS dataset, 2021-22 | net |")
    L.append("| `dd_net` | both eras merged, calendar order | net |")
    L.append("| `n_all`, `net_all` | both eras merged | net |")
    L.append("| `gross_win`, `oos_gross_win` | as `wr_net` but gross | gross |")
    L.append("")
    L.append("Open trades are dropped everywhere, matching the lens. Some older pins")
    L.append("counted them, which is why a few `n` values are one higher than re-derived.")
    L.append("")
    L.append("## Why the win rates differ")
    L.append("")
    L.append("`gross_win` is the old `win`: the same trades counted before fees,")
    L.append("slippage and funding. `wr_net` is after them.")
    L.append("")
    L.append("| book | gross_win | wr_net | gap pp |")
    L.append("|---|---:|---:|---:|")
    gaps = []
    for name in sorted(done):
        rec = done[name]
        if not rec.get("ok"):
            continue
        s = rec["stats"]
        g = s["is"]["wr_gross"]
        nt = s["is"]["wr_net"]
        gaps.append((name, g, nt, 100 * (g - nt)))
    for nm, g, nt, d in sorted(gaps, key=lambda x: -x[3]):
        L.append("| `%s` | %.3f | %.3f | %.1f |" % (nm, g, nt, d))

    # ---------------- new pins payload ----------------
    newpins = {}
    for name in sorted(done):
        rec = done[name]
        if not rec.get("ok"):
            continue
        s = rec["stats"]
        newpins[name] = {
            "n": s["is"]["n"], "net": s["is"]["net"],
            "wr_net": s["is"]["wr_net"], "gross_win": s["is"]["wr_gross"],
            "oos_n": s["oos"]["n"], "oos_net": s["oos"]["net"],
            "oos_wr_net": s["oos"]["wr_net"], "oos_gross_win": s["oos"]["wr_gross"],
            "dd_net": s["all"]["dd_net"],
            "n_all": s["all"]["n"], "net_all": s["all"]["net"],
        }
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps({"measured": done, "new_pins": newpins}, indent=1, sort_keys=True))
    io.open(MD, "w", encoding="utf-8").write("\n".join(L))
    print("\nwrote %s and %s  (%.0fs)" % (OUT.name, MD.name, time.time() - t0))
    print("books measured: %d   pin fields with no matching column: %d"
          % (len(done), len(drift)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())