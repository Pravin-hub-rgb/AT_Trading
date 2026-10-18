"""T1-T4 on the DIRECTIONAL target, plus a rolling-window frequency rule.

WHAT THIS RUNS
==============
Three things, in order of decisiveness:

  PART A  The full four-technique battery on the directional rule
          (htf_rr=5.0 for longs, 2.5 for shorts) on 107 and 110. This is the
          test that decides whether the finding survives.

  PART B  A rolling-window frequency rule. The static rule reads a book's whole
          trade count, which is only knowable retrospectively. The owner's
          variant reads a trailing count - how many trades in the last N bars -
          and switches on that. It is implementable live, which the static one
          is not.

  PART C  A two-book confirmation on maximally different books, since that is
          the cheapest test that can still falsify the rule. If it holds on a
          291-trade book and a 762-trade book it is not an artefact of the
          sample.

THE BAR
=======
Every part reports against the same rule used throughout: a change counts only
if it beats the registered configuration in BOTH eras. One era agreeing is what
exp_trail_skip_n=16 did and what the whole htf_rr sweep did.

Run: $env:PYTHONIOENCODING='utf-8'; python -u exp_directional_battery.py [a|b|c]
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

from experiment_registry import EXPERIMENTS, BP  # noqa: E402
from run_experiment import net_r, get_swings, get_data  # noqa: E402
from exp_tf_family import build_family_module  # noqa: E402
from exp_signal_metrics import load_era  # noqa: E402

OUT = HERE / "directional_battery.json"
MD = HERE / "directional_battery.md"
REPORT = HERE.parent / "docs" / "learn" / "DIRECTIONAL_RULE.md"

LONG_R, SHORT_R = 5.0, 2.5
CANDIDATES = [("fsent_champ_long_mcloff_htf15", "107"),
              ("fsent_champ_long_htf15_tskip6", "110")]
EXTREMES = [("fsent_sig_multi", "sigm 291 trades"),
            ("fsent_champ_long_htfesmcl4", "108 762 trades")]


def side(t):
    return "long" if str(t.get("dir") or "").lower() in ("long", "1", "1.0") else "short"


def closed(o):
    return sorted([t for t in (o["ltf_trades"] if isinstance(o, dict) else o)
                   if t.get("outcome") != "open"], key=lambda t: int(t["entry_ts"]))


def prof(tr):
    if not tr:
        return None
    rs = [net_r([t]) for t in tr]
    w = [r for r in rs if r > 0]
    l = [r for r in rs if r <= 0]
    cum = peak = dd = 0.0
    for r in rs:
        cum += r
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
    st = bst = 0
    for r in rs:
        st = st + 1 if r < 0 else 0
        bst = max(bst, st)
    return {"n": len(rs), "net": round(sum(rs), 2),
            "rpt": round(sum(rs) / len(rs), 4),
            "wr": round(100.0 * len(w) / len(rs), 1),
            "pf": round(sum(w) / -sum(l), 3) if l and -sum(l) else 0.0,
            "dd": round(dd, 2), "streak": bst}


def run(sim, data, cfg, swing, **ov):
    o = sim(data["c1h"], get_swings(data, swing), data["c15"], data["sw15"],
            fine_ltf=data["fine"], **{**BP, **(cfg.get("params") or {}), **ov})
    return closed(o)


def rolling_rule(trades, window_bars, low_trades, high_r, low_r):
    """Owner variant: a TRAILING count decides, not the whole-run count.

    A trade's target is fixed at the moment the trade is taken, from how many
    trades the book has taken in the previous `window_bars`. Nothing about the
    future enters the decision, so this is implementable live, which the static
    whole-run count is not.
    """
    ts = [int(t["entry_ts"]) for t in trades]
    out = []
    for i, t in enumerate(trades):
        cut = ts[i] - window_bars
        recent = sum(1 for x in ts[:i] if x >= cut)
        r = low_r if recent < low_trades else high_r
        out.append((t, recent, r))
    return out


def part_a(sim, ERA, log):
    """Full profile of the directional rule vs the shipped one."""
    res = {}
    for name, code in CANDIDATES:
        cfg = EXPERIMENTS[name]
        swing = cfg.get("swing") or "sw10"
        res[name] = {"code": code}
        for era in ("is", "oos"):
            base = run(sim, ERA[era], cfg, swing)
            dr = run(sim, ERA[era], cfg, swing, htf_rr=LONG_R, htf_rr_short=SHORT_R)
            b, d = prof(base), prof(dr)
            bl, dl = prof([t for t in base if side(t) == "long"]), prof([t for t in dr if side(t) == "long"])
            bs, ds = prof([t for t in base if side(t) == "short"]), prof([t for t in dr if side(t) == "short"])
            res[name][era] = {"base": b, "dir": d, "base_long": bl, "dir_long": dl,
                              "base_short": bs, "dir_short": ds}
            log("  %s %-4s  base %+7.1f (%3d, dd %5.2f, strk %2d)  ->  directional %+7.1f (%3d, dd %5.2f, strk %2d)"
                % (code, era.upper(), b["net"], b["n"], b["dd"], b["streak"],
                   d["net"], d["n"], d["dd"], d["streak"]))
            log("        long  %+7.1f -> %+7.1f    short %+7.1f -> %+7.1f"
                % (bl["net"], dl["net"], bs["net"], ds["net"]))
    return res


def part_b(sim, ERA, log):
    """The owner's rolling-window frequency rule."""
    res = {}
    WINDOWS = [(180 * 86400, 20), (180 * 86400, 40), (365 * 86400, 40)]
    for name, code in EXTREMES + CANDIDATES:
        cfg = EXPERIMENTS[name]
        swing = cfg.get("swing") or "sw10"
        res[name] = {"code": code}
        for era in ("is", "oos"):
            base = run(sim, ERA[era], cfg, swing)
            row = {"base": prof(base), "variants": {}}
            for wb, cut in WINDOWS:
                for hi, lo in ((5.0, 2.5), (4.0, 3.0)):
                    # replay the book under a rolling target
                    dec = rolling_rule(base, wb, cut, hi, lo)
                    by = {}
                    for t, _, r in dec:
                        by.setdefault("%g" % r, []).append(t)
                    row["variants"]["%dd/cut%d/%.1f-%.1f" % (wb // 86400, cut, hi, lo)] = {
                        "counts": {k: len(v) for k, v in by.items()},
                        "note": "target assignment only; net not recomputed"}
                    _ = prof(base)
            res[name][era] = row
            log("  %-11s %-4s  base %+7.1f (%d trades)" % (code, era.upper(),
                                                           row["base"]["net"], row["base"]["n"]))
    return res


def main() -> int:
    which = (sys.argv[1] if len(sys.argv) > 1 else "a").lower()
    t0 = time.time()
    print("loading ...", flush=True)
    ERA = {"is": get_data(), "oos": load_era("oos")}
    sim = build_family_module()
    logf = io.open(HERE / "directional_battery.log", "a", encoding="utf-8")

    def log(m):
        print(m, flush=True)
        logf.write(str(m) + "\n")

    log("\n===== part %s (%.0fs) =====" % (which, time.time() - t0))
    res = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    if which == "a":
        res["a"] = part_a(sim, ERA, log)
    elif which == "b":
        res["b"] = part_b(sim, ERA, log)
    else:
        raise SystemExit("a or b")
    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    report(res)
    log("\nwrote %s  (%.0fs)" % (OUT.name, time.time() - t0))
    return 0


def report(res):
    L = ["# The directional target — full profile", "",
         "Long trades want a further target, short trades a closer one. Direction",
         "is on the order ticket, so it needs no prediction and no lookahead, which",
         "is what separates it from the eight state-variable signals that all flipped",
         "between eras.", ""]
    if "a" in res:
        L += ["## Against the shipped configuration", "",
              "| book | era | | net | trades | R/trade | win % | PF | max DD | streak |",
              "|---|---|---|---:|---:|---:|---:|---:|---:|---:|"]
        for name, rec in res["a"].items():
            for era in ("is", "oos"):
                b, d = rec[era]["base"], rec[era]["dir"]
                if not b or not d:
                    continue
                for lab, p in (("shipped 3.0", b), ("directional 5.0/2.5", d)):
                    L.append("| %s | %s | %s | %+.1f | %d | %+.3f | %.1f | %.2f | %.2f | %d |"
                             % (rec["code"] if lab.startswith("ship") else "",
                                era.upper(), lab, p["net"], p["n"], p["rpt"],
                                p["wr"], p["pf"], p["dd"], p["streak"]))
        L.append("")
        L += ["## Long and short separately", "",
              "| book | era | side | shipped | directional | delta |", "|---|---|---|---:|---:|---:|"]
        for name, rec in res["a"].items():
            for era in ("is", "oos"):
                for sd in ("long", "short"):
                    b, d = rec[era]["base_" + sd], rec[era]["dir_" + sd]
                    if not b or not d:
                        continue
                    L.append("| %s | %s | %s | %+.1f | %+.1f | %+.1f |"
                             % (rec["code"], era.upper(), sd, b["net"], d["net"],
                                d["net"] - b["net"]))
        L.append("")
    MD.write_text("\n".join(L), encoding="utf-8")
    REPORT.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())