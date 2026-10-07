"""exp_persist_sweep - is exp_persist=7 still earning its place after C17?

WHY THIS EXISTS
===============
The knob-binds audit probes each knob with a value that CANNOT mean what the book
has - it measures whether a knob BINDS, not whether it is TUNED RIGHT. For
exp_persist that probe was 0, and it reported -66.1R IS / -5.0R OOS. Read
naively that says "keep 7". But -5R out of sample is a very different claim from
-66R in sample: post-C17 the knob's OOS value has almost vanished. A knob whose
cost is 5R in the era we did not tune on is not obviously load-bearing, and the
honest question is not "does it bind" but "is 7 the right number, or does a
smaller number do the same work".

A coarse single-endpoint probe cannot answer that. This sweeps the grid.

BASE, AND WHY IT IS STATED
==========================
Every row is measured against the SHIPPING config - max_consecutive_losses=3,
ext_stop_r=0.0, exp_persist=7 - with only exp_persist moving. That base matters:
the halt re-sequences which trades persist is even asked about, so the same probe
against a halt-off base gives a different number (66.1 vs 61.7 IS). Reading a
delta off the wrong row of a grid is how a correct table gets argued into a
wrong number. Both rows are true; only against the base named above.

WHAT WOULD COUNT AS A RESULT
===========================
A smaller value is only interesting if it is not WORSE in either era. A value
that trades IS for OOS is the era-split pattern this repo has seen six times,
and it is a reason to keep 7, not a reason to switch.

Run:  cd backtest/tests
      python -u exp_persist_sweep.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

BOOK = "fsent_champ_long"
GRID = (0, 2, 3, 4, 5, 6, 7)
OUT_MD = Path(__file__).parent / "_persist_sweep.md"
OUT_JSON = Path(__file__).parent / "_persist_sweep.json"


def main() -> int:
    from exp_tf_family import build_family_module
    from run_experiment import BP, net_r, get_swings
    from exp_multi_metrics import load_era
    from exp_full_metrics import compute
    from experiment_registry import EXPERIMENTS

    sim = build_family_module()
    cfg = EXPERIMENTS[BOOK]
    base = {**BP, **cfg["params"]}
    base.setdefault("exp_partial_r", 0.0)

    data, sw = {}, {}
    for era in ("is", "oos"):
        data[era] = load_era(era)
        sw[era] = get_swings(data[era], cfg.get("swing") or "sw10")

    def run(era, params):
        out = sim(data[era]["c1h"], sw[era], data[era]["c15"], data[era]["sw15"],
                  fine_ltf=data[era]["fine"], **params)
        tr = [t for t in out["ltf_trades"] if t.get("outcome") != "open"]
        m = compute([net_r([t]) for t in tr], [t.get("entry_date", "") for t in tr])
        return m

    print("=" * 96)
    print("exp_persist SWEEP - %s, post-C17 engine" % BOOK)
    print("=" * 96)
    print("base: %s" % json.dumps(
        {k: base.get(k) for k in ("max_consecutive_losses", "ext_stop_r",
                                  "exp_persist", "cooldown_bars", "mode")},
        sort_keys=True))
    print("grid: %s   (shipping value 7 marked *)" % ", ".join(
        "%d%s" % (v, "*" if v == base.get("exp_persist") else "") for v in GRID))
    print()

    rows = []
    for v in GRID:
        p = dict(base)
        p["exp_persist"] = v
        rec = {"exp_persist": v}
        for era in ("is", "oos"):
            m = run(era, p)
            rec[era] = {"n": m["n"], "net": round(m["net"], 2),
                        "dd": round(m.get("max_dd", 0.0), 2)}
        rows.append(rec)
        star = "*" if v == base.get("exp_persist") else " "
        print("  persist=%-3d%s IS %4d / %+8.2f / dd %5.2f    OOS %4d / %+8.2f / dd %5.2f"
              % (v, star, rec["is"]["n"], rec["is"]["net"], rec["is"]["dd"],
                 rec["oos"]["n"], rec["oos"]["net"], rec["oos"]["dd"]))

    ship = next(r for r in rows if r["exp_persist"] == base.get("exp_persist"))
    print()
    print("delta vs shipping (persist=%s):" % ship["exp_persist"])
    for r in rows:
        if r["exp_persist"] == ship["exp_persist"]:
            continue
        di = r["is"]["net"] - ship["is"]["net"]
        do = r["oos"]["net"] - ship["oos"]["net"]
        # the whole question in one word: does it lose in either era?
        flag = "LOSES OOS" if do < 0 else ("loses IS only" if di < 0 else "no worse")
        print("  persist=%-3d  %+8.2f IS  %+8.2f OOS   %s" % (r["exp_persist"], di, do, flag))

    better = [r for r in rows
              if r["exp_persist"] != ship["exp_persist"]
              and r["is"]["net"] >= ship["is"]["net"]
              and r["oos"]["net"] >= ship["oos"]["net"]]
    print()
    if better:
        print("VALUES NOT WORSE IN EITHER ERA:")
        for r in better:
            print("  persist=%d  IS %+.2f  OOS %+.2f" %
                  (r["exp_persist"], r["is"]["net"], r["oos"]["net"]))
    else:
        print("No value beats shipping in both eras. persist=7 stands.")

    OUT_JSON.write_text(json.dumps({"book": BOOK, "rows": rows}, indent=2) + "\n",
                        encoding="utf-8")
    lines = [
        "# exp_persist sweep - %s (post-C17)" % BOOK,
        "",
        "Grid against the shipping base (halt=3, ext_stop_r=0.0), both eras.",
        "",
        "| exp_persist | IS n | IS net | IS dd | OOS n | OOS net | OOS dd |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        star = " **" if r["exp_persist"] == ship["exp_persist"] else ""
        lines.append("| %d%s | %d | %.2f | %.2f | %d | %.2f | %.2f |" % (
            r["exp_persist"], star, r["is"]["n"], r["is"]["net"], r["is"]["dd"],
            r["oos"]["n"], r["oos"]["net"], r["oos"]["dd"]))
    lines += ["", "Shipping value marked ** is unchanged by this sweep."]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\nwrote %s and %s" % (OUT_MD.name, OUT_JSON.name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())