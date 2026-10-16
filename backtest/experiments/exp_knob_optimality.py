"""Would optimising the knobs have helped, or hurt? Ask the out-of-sample era.

THE QUESTION, RESTATED SO IT CAN BE ANSWERED
--------------------------------------------
The owner asked, fairly: "a book has knob x set to 4 - what does x=6 do? Is
there a better value?" That cannot be answered honestly by reporting the best
in-sample value, because the best in-sample value of a swept knob is the number
most likely to be a fitting artefact. Reporting it and acting on it is the move
this repo has already identified as the disease.

So the question is put where it can be answered:

    1. sweep each knob on IS, one at a time, holding everything else fixed
    2. find the IS-best value
    3. compare it against the REGISTERED value ON OOS, which the sweep never saw

Three outcomes, all informative:

    OOS BETTER   the registered value is genuinely leaving something on the
                 table. This is the only case where moving is defensible, and
                 even then it costs a trial.

    OOS WORSE    the knob's IS peak does not survive. The apparent improvement
                 was the fitting artefact. Keep the registered value. This is
                 the expected result if the knobs are noise, and it is a real
                 answer, not a failure.

    IS-BEST IS
    ALREADY THE
    REGISTERED   nothing to do. Most common outcome, and it means the value is
    VALUE        not sitting on a spike.

WHY THIS IS NOT MORE TRIAL COUNT
--------------------------------
Reading OOS once per knob is one extra observation per book, and it is used to
REJECT a change rather than to make one. The sweep runs on IS only, exactly
where the existing selection already ran, so it adds no OOS degrees of freedom.
OOS is read after the IS peak is fixed, never used to pick it.

SHAPE IS ALSO REPORTED
----------------------
Because a knob on a plateau does not need to be moved and a knob on a spike
should not be trusted. exp_dof_plateau.py already established that nine of nine
knobs on the base book are plateaus; this repeats it per book and adds the
out-of-sample answer.

Output: knob_optimality.json + knob_optimality.md
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

OUT = HERE / "knob_optimality.json"
MD = HERE / "knob_optimality.md"

BOOKS = [
    ("fsent_champ_long_mcloff_htf15", "107"),
    ("fsent_champ_long_htf15_tskip6", "110"),
    ("fsent_champ_long_htf15_htffs", "109"),
    ("fsent_champ_long_htfesmcl4", "108"),
    ("fsent_champ_long_htffs", "106"),
]

# Only knobs this book actually overrides. Sweeping a knob the book does not set
# is not this book's knob, and reporting on it would pad the table with numbers
# that have no bearing on the question.
GRIDS = {
    "max_consecutive_losses": [0, 1, 2, 3, 4, 5],
    "exp_trail_skip_n": [0, 1, 2, 3, 4, 6, 8],
    "cooldown_bars": [0, 2, 4, 8, 12, 16],
    "ext_stop_r": [0, 0.75, 1.5, 3.0, 4.0],
    "chop_thresh": [46, 50, 54, 58, 62, 66],
    "sl_buf_atr": [0.0, 0.005, 0.01, 0.05, 0.15],
}
GOOD_FRAC = 0.60


def stats(trades):
    tr = [t for t in trades if t.get("outcome") != "open"]
    rs = [net_r([t]) for t in tr]
    cum = peak = dd = 0.0
    for r in rs:
        cum += r
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
    return {"n": len(tr), "net": round(sum(rs), 2), "dd": round(dd, 2)}


def run(sim, data, cfg, swing):
    p = {**BP, **(cfg.get("params") or {})}
    o = sim(data["c1h"], get_swings(data, swing), data["c15"], data["sw15"],
            fine_ltf=data["fine"], **p)
    tr = o["ltf_trades"] if isinstance(o, dict) else o
    return stats(sorted(tr, key=lambda t: int(t["entry_ts"])))


def main() -> int:
    # --report-only regenerates the markdown from the stored JSON without
    # re-running the sweep. The sweep is 34 minutes; a formatting bug in the
    # report must not cost that again.
    if "--report-only" in sys.argv and OUT.exists():
        res = json.loads(io.open(OUT, encoding="utf-8").read())
        write_report(res)
        print("wrote %s from stored JSON (no sweep re-run)" % MD.name)
        return 0

    t0 = time.time()
    print("loading eras ...", flush=True)
    IS, OOS = get_data(), load_era("oos")
    sim = build_family_module()

    res = {}
    for name, code in BOOKS:
        base_cfg = EXPERIMENTS[name]
        swing = base_cfg.get("swing") or "sw10"
        own = {k: v for k, v in (base_cfg.get("params") or {}).items() if k in GRIDS}
        if not own:
            print("\n%s sets none of the swept knobs; skipping" % code, flush=True)
            continue
        print("\n=== %s %s ===" % (code, name), flush=True)
        print("    registered knobs: %s" % own, flush=True)
        oos_reg = run(sim, OOS, base_cfg, swing)
        print("    registered on OOS: %s" % oos_reg, flush=True)
        for knob, reg in own.items():
            grid = [v for v in GRIDS[knob] if v != reg]
            cells = []
            for v in grid:
                c = dict(base_cfg)
                c["params"] = dict(base_cfg.get("params") or {})
                c["params"][knob] = v
                cells.append((v, run(sim, IS, c, swing)))
            reg_is = run(sim, IS, base_cfg, swing)
            best_v, best_s = max(cells, key=lambda x: x[1]["net"])
            allc = [(reg, reg_is)] + cells
            top = max(c["net"] for _v, c in allc)
            good = [v for v, c in allc if c["net"] >= GOOD_FRAC * top]
            shape = "PLATEAU" if len(good) >= 3 else "SPIKE"

            alt_cfg = dict(base_cfg)
            alt_cfg["params"] = dict(base_cfg.get("params") or {})
            alt_cfg["params"][knob] = best_v
            alt_oos = run(sim, OOS, alt_cfg, swing)

            d = alt_oos["net"] - oos_reg["net"]
            verdict = ("OOS BETTER" if d > 0.01 else
                       "OOS WORSE" if d < -0.01 else "NO CHANGE")
            print("    %-24s reg=%s  IS best=%s (%+.1f)  OOS: reg %+.1f vs alt %+.1f  -> %s  [%s]"
                  % (knob, reg, best_v, best_s["net"], oos_reg["net"], alt_oos["net"],
                     verdict, shape), flush=True)
            res["%s|%s" % (code, knob)] = {
                "code": code, "book": name, "knob": knob, "registered": reg,
                "is_registered": reg_is, "is_best_value": best_v,
                "is_best": best_s, "shape": shape,
                "oos_registered": oos_reg, "oos_at_is_best": alt_oos,
                "oos_delta": round(d, 2), "verdict": verdict,
                "grid": [{"value": v, "is": s} for v, s in cells],
            }
        print("    (%.0fs elapsed)" % (time.time() - t0), flush=True)

    io.open(OUT, "w", encoding="utf-8").write(json.dumps(res, indent=1, sort_keys=True))
    write_report(res)
    print("\nwrote %s and %s  (%.0fs)" % (OUT.name, MD.name, time.time() - t0))
    return 0


def write_report(res):
    """Render the markdown. Separated so --report-only can regenerate it from
    the stored JSON; the sweep is 34 minutes and a formatting bug must not cost
    that again."""
    L = ["# Would optimising the knobs have helped?", "",
         "Sweep on IS only. The IS-best value is then read on OOS, which the",
         "sweep never saw. That is the only way to ask the question without",
         "picking the number most likely to be a fitting artefact.", ""]
    L.append("| book | knob | set | IS best | OOS if set | OOS if at best | delta | verdict | shape |")
    L.append("|---|---|---:|---:|---:|---:|---:|---|---|")
    for k, v in sorted(res.items()):
        L.append("| %s | `%s` | %s | %s | %+.2f | %+.2f | %+.2f | **%s** | %s |" % (
            v["code"], v["knob"], v["registered"], v["is_best_value"],
            v["oos_registered"]["net"], v["oos_at_is_best"]["net"],
            v["oos_delta"], v["verdict"], v["shape"]))
    L.append("")
    L.append("## The grids, so nothing here is a bare verdict")
    L.append("")
    for k, v in sorted(res.items()):
        L.append("### %s `%s` - registered %s" % (v["code"], v["knob"], v["registered"]))
        L.append("")
        L.append("| value | IS trades | IS net | IS dd |")
        L.append("|---:|---:|---:|---:|")
        # grid entries arrive as {"value": v, "is": {...}}; flatten them so they
        # match is_registered, which is already flat. Mismatched shapes here
        # cost a 34-minute sweep to rediscover.
        cells = [{"value": v["registered"], **v["is_registered"]}]
        cells += [{"value": g["value"], **g["is"]} for g in v["grid"]]
        for c in sorted(cells, key=lambda x: x["value"]):
            mark = " **<- registered**" if c["value"] == v["registered"] else ""
            L.append("| %s%s | %d | %+.2f | %.2f |" % (c["value"], mark, c["n"], c["net"], c["dd"]))
        L.append("")
    io.open(MD, "w", encoding="utf-8").write("\n".join(L))


if __name__ == "__main__":
    raise SystemExit(main())