"""Full metrics at 3.0 vs 5.0, and does the right target depend on DIRECTION?

PART 1 - the frequency rule, in full
====================================
The rule found: books taking fewer trades want a further target, books taking
many trades want a closer one. Correlation between IS trade count and the index
of the best combined target is -0.928. The owner understood this correctly on
first hearing: few trades means a longer R window, many trades means a shorter
one. This file puts the whole metric matrix behind that so the rule is not being
believed on a net number.

PART 2 - the owner's own idea, which I initially misheard
=========================================================
They wrote "short window ke liye mR aur long window ke liye nR" and I read
"window" as the time window. They meant SHORT and LONG as directions - short is
a down trade, long is an up trade. So the actual proposal is:

    does the best target differ between long trades and short trades?

That is a different and better question than the frequency one, because direction
is knowable at decision time with zero lookahead, whereas trade count is only
known retrospectively for the whole run. If direction carries the signal and
trade count does not, the frequency rule is a proxy that will not survive live.

This tests it directly: split every book's trades by direction and sweep the
target within each half, separately for each era. A directional rule only
exists if one direction consistently wants a further target in BOTH eras.

Run: $env:PYTHONIOENCODING='utf-8'; python -u exp_frequency_matrix.py
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

OUT = HERE / "frequency_matrix.json"
MD = HERE / "frequency_matrix.md"
REPORT = HERE.parent / "docs" / "learn" / "FREQUENCY_AND_DIRECTION.md"

RR = [2.0, 2.5, 3.0, 4.0, 5.0]
BOOKS = [("fsent_champ_long_mcloff_htf15", "107"),
         ("fsent_champ_long_htf15_tskip6", "110"),
         ("fsent_champ_long_htf15_htffs", "109"),
         ("fsent_champ_long_htffs", "106"),
         ("fsent_champ_long_htfesmcl4", "108"),
         ("fsent_sig_multi_htffs", "sigm_htffs"),
         ("fsent_champ_long_htf15", "htf15"),
         ("fsent_sig_multi", "sigm")]


def side(t):
    d = str(t.get("dir") or "").lower()
    return "long" if d in ("long", "1", "1.0") else "short"


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
    med = sorted(rs)[len(rs) // 2]
    return {"n": len(rs), "net": round(sum(rs), 2),
            "rpt": round(sum(rs) / len(rs), 4),
            "wr": round(100.0 * len(w) / len(rs), 1),
            "pf": round(sum(w) / -sum(l), 3) if l and -sum(l) else 0.0,
            "avgw": round(sum(w) / len(w), 2) if w else 0.0,
            "avgl": round(-sum(l) / len(l), 2) if l else 0.0,
            "dd": round(dd, 2), "streak": bst, "med": round(med, 3)}


def run(sim, data, cfg, swing, **ov):
    o = sim(data["c1h"], get_swings(data, swing), data["c15"], data["sw15"],
            fine_ltf=data["fine"], **{**BP, **(cfg.get("params") or {}), **ov})
    tr = sorted([t for t in (o["ltf_trades"] if isinstance(o, dict) else o)
                 if t.get("outcome") != "open"], key=lambda t: int(t["entry_ts"]))
    return {"all": prof(tr),
            "long": prof([t for t in tr if side(t) == "long"]),
            "short": prof([t for t in tr if side(t) == "short"])}


def main() -> int:
    t0 = time.time()
    print("loading ...", flush=True)
    ERA = {"is": get_data(), "oos": load_era("oos")}
    sim = build_family_module()
    res = {}
    for name, code in BOOKS:
        cfg = EXPERIMENTS[name]
        swing = cfg.get("swing") or "sw10"
        res[name] = {"code": code}
        for era in ("is", "oos"):
            res[name][era] = {("rr%g" % r): run(sim, ERA[era], cfg, swing, htf_rr=r)
                              for r in RR}
        print("  %-11s done (%.0fs)" % (code, time.time() - t0), flush=True)

    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    report(res)
    print("\nwrote %s, %s and %s  (%.0fs)" % (OUT.name, MD.name, REPORT.name, time.time() - t0))
    return 0


def report(res):
    L = ["# Frequency rule, full metrics — and does direction decide instead?", "",
         "## The rule, stated once", "",
         "> Books taking **fewer** trades want a **further** target.",
         "> Books taking **many** trades want a **closer** one.", "",
         "Correlation between IS trade count and the index of the best combined",
         "target: **-0.928**.", "",
         "The owner understood this correctly the first time it was explained. The",
         "point of this file is the metric matrix behind it, so the rule is not being",
         "believed on a net number.", "",
         "---", "",
         "# Part 1 — full metrics at 3.0 and 5.0", ""]
    for era in ("is", "oos"):
        L += ["## %s" % era.upper(), "",
              "| book | trades | target | net | R/trade | median | win % | PF | avg win | avg loss | max DD | streak |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for name, code in BOOKS:
            for rr in (3.0, 5.0):
                p = res[name][era]["rr%g" % rr]["all"]
                if not p:
                    continue
                mark = " **<-**" if rr == 5.0 else ""
                L.append("| %s | %d | %g%s | %+.1f | %+.3f | %+.2f | %.1f | %.2f | %+.2f | %+.2f | %.2f | %d |"
                         % (code if rr == 3.0 else "", p["n"], rr, mark,
                            p["net"], p["rpt"], p["med"], p["wr"], p["pf"],
                            p["avgw"], p["avgl"], p["dd"], p["streak"]))
        L.append("")

    L += ["---", "", "## The deltas, 3.0 → 5.0", "",
          "| book | trades | d net IS | d net OOS | d R/trade | d win% | d DD | d streak | 5.0 better both |",
          "|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for name, code in BOOKS:
        a3, a5 = res[name]["is"]["rr3"]["all"], res[name]["is"]["rr5"]["all"]
        o3, o5 = res[name]["oos"]["rr3"]["all"], res[name]["oos"]["rr5"]["all"]
        if not all((a3, a5, o3, o5)):
            continue
        L.append("| %s | %d | %+.1f | %+.1f | %+.3f | %+.1f | %+.2f | %+d | %s |"
                 % (code, a3["n"], a5["net"] - a3["net"], o5["net"] - o3["net"],
                    a5["rpt"] - a3["rpt"], a5["wr"] - a3["wr"], a5["dd"] - a3["dd"],
                    a5["streak"] - a3["streak"],
                    "**yes**" if (a5["net"] > a3["net"] and o5["net"] > o3["net"]) else "no"))
    L.append("")

    L += ["---", "", "# Part 2 — direction: the owner's idea", "",
          "They wrote *\"short window ke liye mR aur long window ke liye nR\"*. I read",
          "\"window\" as time. They meant **short and long as directions** — short is a",
          "down trade, long is an up trade. So the real proposal is:",
          "",
          "> **does the best target differ between long trades and short trades?**", "",
          "This is a better question than the frequency one, because direction is known",
          "at decision time with zero lookahead, whereas trade count is only known",
          "retrospectively for the whole run. If direction carries the signal and",
          "frequency does not, the frequency rule is a proxy that will not survive",
          "live.", "",
          "## Net R by direction", ""]
    for era in ("is", "oos"):
        L += ["### %s" % era.upper(), "",
              "| book | side | trades | " + " | ".join("rr=%g" % r for r in RR) + " | best |",
              "|---|---|---:|" + "---:|" * (len(RR) + 1)]
        for name, code in BOOKS:
            for sd in ("long", "short"):
                p = res[name][era]["rr3"][sd]
                if not p:
                    continue
                cells = []
                for r in RR:
                    q = res[name][era]["rr%g" % r][sd]
                    cells.append("%+.0f" % q["net"] if q else "-")
                best = max(RR, key=lambda r: (res[name][era]["rr%g" % r][sd]["net"]
                                              if res[name][era]["rr%g" % r][sd] else -1e9))
                L.append("| %s | %s | %d | %s | **%g** |"
                         % (code if sd == "long" else "", sd, p["n"],
                            " | ".join(cells), best))
        L.append("")

    L += ["---", "", "## Verdict on direction", ""]
    li = []
    for name, code in BOOKS:
        for era in ("is", "oos"):
            bl = max(RR, key=lambda r: (res[name][era]["rr%g" % r]["long"]["net"]
                                        if res[name][era]["rr%g" % r]["long"] else -1e9))
            bs = max(RR, key=lambda r: (res[name][era]["rr%g" % r]["short"]["net"]
                                        if res[name][era]["rr%g" % r]["short"] else -1e9))
            li.append((code, era, bl, bs))
    L += ["| book | era | best for LONG | best for SHORT | different? |", "|---|---|---:|---:|---|"]
    diff = 0
    for code, era, bl, bs in li:
        d = "**yes**" if bl != bs else "no"
        if bl != bs:
            diff += 1
        L.append("| %s | %s | %g | %g | %s |" % (code, era.upper(), bl, bs, d))
    L += ["", "**%d of %d book-eras want a different target by direction.**" % (diff, len(li)), "",
          "For a directional rule to be real it has to be *consistent* — long",
          "wanting further in one era and closer in the other is the same flip that",
          "killed all eight signals. A table where the answer flips is not a rule.", ""]
    MD.write_text("\n".join(L), encoding="utf-8")
    REPORT.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())