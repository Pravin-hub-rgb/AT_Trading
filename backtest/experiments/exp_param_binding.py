"""Which parameters are actually load-bearing, and which are decoration.

WHY THIS EXISTS
===============
The heat map swept two parameters per book and found 107 flat and 110 cliffed.
That answered "are these two knobs safe" and nothing else. 107 carries fifteen
parameters and 110 sixteen, so the sweep covered an eighth of the surface, and
- on the same book - exp_persist came up in both grids.

Before asking "is the edge robust across parameter values", the prior question
is "which parameter values are even doing anything". A knob that can be changed
with no effect on the trade list is not a parameter, it is a comment. Testing
sensitivity across a knob that changes nothing produces a beautifully flat
heatmap and tells you nothing at all - which is exactly what 107's cooldown
heatmap looked like.

So: perturb every parameter of both books to two neighbouring values each and
count how many trades change. Three outcomes worth separating.

  inert        trade list byte-identical. The knob is not connected.
  cosmetic     trade list changes but net barely moves. Connected, not load-bearing.
  structural   the trade list changes materially. This is where a cliff can live.

Note this does NOT rank parameters by importance, and it is not a sensitivity
test - a parameter can be strongly structural and perfectly smooth. It answers
only the prior question, and it is the question that decides how much of the
remaining surface still needs sweeping.

Run: $env:PYTHONIOENCODING='utf-8'; python -u exp_param_binding.py
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

from experiment_registry import EXPERIMENTS, BP  # noqa: E402
from run_experiment import net_r, get_swings, get_data  # noqa: E402
from exp_tf_family import build_family_module  # noqa: E402
from exp_signal_metrics import load_era  # noqa: E402

OUT = HERE / "param_binding.json"
MD = HERE / "param_binding.md"

BOOKS = [("fsent_champ_long_mcloff_htf15", "107"),
         ("fsent_champ_long_htf15_tskip6", "110")]

# (knob, low, high). Chosen as plausible neighbours, not arbitrary nudges -
# for a categorical, low/high are the other legal values.
PROBES = [
    ("atr_high_thresh", 0.55, 0.75),
    ("atr_low_thresh", 0.25, 0.45),
    ("sl_buf_atr", 0.005, 0.02),
    ("chop_thresh", 50.0, 70.0),
    ("cooldown_bars", 4, 12),
    ("exp_persist", 5, 9),
    ("ext_stop_r", 2.0, 4.0),
    ("htf_rr", 2.0, 4.0),
    ("exp_partial_r", 0.5, 1.0),
    ("mode", "atr_low", "atr_extreme"),
    ("pivot_rule", "wick", "body"),
    ("exp_fs_entry_side", "short", "both"),
    ("max_positions", 3, 5),
    ("window_end", "24bars", "4days"),
]
# max_consecutive_losses is handled separately: the owner has an open decision
# on it, and sweeping it here would quietly reopen that.
MCL_PROBE = ("max_consecutive_losses", 1, 3)
# 110 only
SKIP_PROBE = ("exp_trail_skip_n", 3, 9)


def closed(trades):
    return sorted([t for t in trades if t.get("outcome") != "open"],
                  key=lambda t: int(t["entry_ts"]))


def key_of(t):
    """Trade identity: when it entered and what it made. Exit time too, so a
    book that holds the same entries but trails them differently is caught."""
    return (int(t["entry_ts"]), int(t.get("exit_ts") or 0), round(net_r([t]), 4))


def run(sim, data, cfg, swing, **over):
    p = {**BP, **(cfg.get("params") or {}), **over}
    o = sim(data["c1h"], get_swings(data, swing), data["c15"], data["sw15"],
            fine_ltf=data["fine"], **p)
    return closed(o["ltf_trades"] if isinstance(o, dict) else o)


def main() -> int:
    t0 = time.time()
    print("loading eras ...", flush=True)
    ERA = {"is": get_data(), "oos": load_era("oos")}
    sim = build_family_module()
    res = {}
    lines = ["# Which parameters are load-bearing", "",
             "Every parameter of 107 and 110, perturbed to two neighbouring values",
             "on each side, on both eras. A knob whose trade list does not move is",
             "not a parameter. Counting how many trades change separates three",
             "things worth separating: inert (no change at all), cosmetic (list",
             "moves, net does not), and structural (the list moves materially).",
             "",
             "This is the prior question to a sensitivity test, not a replacement",
             "for one - a parameter can be strongly structural and perfectly",
             "smooth. 107's cooldown heat map was beautifully flat, and this is",
             "why that flatness was partly meaningless.", ""]

    for name, code in BOOKS:
        cfg = EXPERIMENTS[name]
        swing = cfg.get("swing") or "sw10"
        book = dict(EXPERIMENTS[name].get("params") or {})
        probes = list(PROBES) + [MCL_PROBE]
        if "exp_trail_skip_n" in book:
            probes.append(SKIP_PROBE)
        rec = {}
        print("\n=== %s ===" % code, flush=True)
        for era in ("is", "oos"):
            base = run(sim, ERA[era], cfg, swing)
            bkeys = set(key_of(t) for t in base)
            bnet = sum(net_r([t]) for t in base)
            for knob, lo, hi in probes:
                if knob not in book and knob not in BP:
                    continue
                row = {"value": book.get(knob, "(unset -> default)")}
                for lbl, val in (("lo", lo), ("hi", hi)):
                    if isinstance(book.get(knob), str) and not isinstance(val, str):
                        continue
                    try:
                        alt = run(sim, ERA[era], cfg, swing, **{knob: val})
                    except Exception as exc:  # noqa: BLE001
                        row[lbl] = {"error": "%s: %s" % (type(exc).__name__, exc)}
                        continue
                    akeys = set(key_of(t) for t in alt)
                    anet = sum(net_r([t]) for t in alt)
                    shared = len(bkeys & akeys)
                    row[lbl] = {
                        "n": len(alt), "net": round(anet, 2),
                        "d_n": len(alt) - len(base),
                        "d_net": round(anet - bnet, 2),
                        "shared": shared,
                        "pct_same": round(100.0 * shared / max(len(bkeys), 1), 1),
                    }
                if "lo" in row or "hi" in row:
                    worst = max((abs(row[k].get("d_net", 0)) for k in ("lo", "hi")
                                 if k in row and "error" not in row[k]), default=0.0)
                    row["max_abs_d_net"] = round(worst, 2)
                rec.setdefault(knob, {})[era] = row
                bits = []
                for lbl in ("lo", "hi"):
                    if lbl in row and "error" not in row[lbl]:
                        bits.append("%s: %d trades %+.1fR, %s%% same"
                                    % (lbl, row[lbl]["n"], row[lbl]["d_net"],
                                       row[lbl]["pct_same"]))
                    elif lbl in row:
                        bits.append("%s: ERROR" % lbl)
                print("  %-22s %s" % (knob, " | ".join(bits)), flush=True)
        res[name] = rec

    # verdict table
    lines += ["## Verdict", "",
              "| book | parameter | value | worst net move | trades still shared | reading |",
              "|---|---|---|---:|---:|---|"]
    for name, code in BOOKS:
        for knob in sorted(res[name]):
            vals = [res[name][knob][e] for e in ("is", "oos") if e in res[name][knob]]
            worst = max((v.get("max_abs_d_net", 0.0) for v in vals), default=0.0)
            shares = [v[l]["pct_same"] for v in vals for l in ("lo", "hi")
                      if l in v and "error" not in v[l]]
            smin = min(shares) if shares else 0.0
            if smin >= 99.9:
                reading = "**INERT** - no test can find a cliff here"
            elif worst < 15.0:
                reading = "cosmetic"
            else:
                reading = "**structural**"
            lines.append("| %s | `%s` | %s | %.1fR | %.1f%% | %s |"
                         % (code, knob, res[name][knob].get("is", {}).get("value", "?"),
                            worst, smin, reading))
    lines.append("")
    lines.append("An INERT row is not a wasted parameter, it is a parameter that")
    lines.append("cannot be overfitted on. The risk being bought down here is")
    lines.append("specific: a flat heat map over a knob that changes nothing proves")
    lines.append("nothing about the strategy.")
    lines.append("")

    io.open(OUT, "w", encoding="utf-8").write(json.dumps(res, indent=1))
    io.open(MD, "w", encoding="utf-8").write("\n".join(lines))
    print("\nwrote %s and %s  (%.0fs)" % (OUT.name, MD.name, time.time() - t0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())