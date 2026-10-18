"""exp_stop_pct: does a PERCENTILE gate beat the fixed 3.0R gate?

WHY THIS IS THE BIGGER HALF OF THE EFFECT
==========================================
The htf_rr decomposition attributed the change in book net to two terms:

    entry-set term   2-3x larger   (which LTF entries exist)
    HTF term         smaller       (how much R the HTF trade books)

Eight state-variable signals were tested against the HTF term and all eight
flipped between eras. The external reviewer's objection was that this closes
only the smaller half. It is right, and the larger half runs through the
admission gate at unified.py:1212-1216:

    ext = (close - window_open) * dir / htf_risk
    if ext > ext_stop_r: continue

`ext` is measured in units of the window's own risk, which is a function of
where the swing started. That makes the gate's effective strictness a function
of the regime rather than of the strategy: 2021-22 measured 3.5x more volatile
than 2023-26, so a fixed 3.0R admits a different fraction of entries in each.

The gate diagnostic already established the gate has a real job - trades nearest
it are the weakest on every book and both eras, at +0.12R to +0.60R per trade
against +0.85R to +3.32R for fresh entries. So the question is not whether to
keep it but whether its LEVEL is right.

WHAT exp_stop_pct DOES
======================
New engine knob, default 0.0 = shipped behaviour, pins reproduce exactly. Above
zero it replaces the fixed level with that percentile of the extensions seen so
far in the run, so the gate blocks the same FRACTION of entries in every
regime. It is causal - the percentile is built from extensions already computed
during the walk, and falls back to the fixed level until 30 samples exist rather
than extrapolating from a handful.

The bar is the same one used for the signals: a level only counts if it is
better than the registered gate in BOTH eras on aggregate. One era agreeing is
what skip_n=16 did and what the htf_rr sweep did.

Run: $env:PYTHONIOENCODING='utf-8'; python -u exp_stop_pct.py
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

OUT = HERE / "stop_pct.json"
MD = HERE / "stop_pct.md"
REPORT = HERE.parent / "docs" / "learn" / "STOP_GATE_PERCENTILE.md"

PCT = [0.0, 0.50, 0.70, 0.85, 0.92, 0.96, 0.99]
RC = [1.5, 2.5, 3.0, 4.0, 6.0, 99.0]      # 99 = gate effectively off

BOOKS = [("fsent_champ_long_mcloff_htf15", "107"),
         ("fsent_champ_long_htf15_tskip6", "110"),
         ("fsent_champ_long_htffs", "106"),
         ("fsent_champ_long_htf15_htffs", "109"),
         ("fsent_champ_long_htfesmcl4", "108"),
         ("fsent_sig_multi_htffs", "sigm_htffs"),
         ("fsent_sig_multi", "sigm"),
         ("fsent_champ_long_htf15", "htf15")]


def stats(tr):
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
    tr = sorted([t for t in (o["ltf_trades"] if isinstance(o, dict) else o)
                 if t.get("outcome") != "open"], key=lambda t: int(t["entry_ts"]))
    return stats(tr)


def main() -> int:
    t0 = time.time()
    print("loading ...", flush=True)
    ERA = {"is": get_data(), "oos": load_era("oos")}
    sim = build_family_module()
    res = {}
    for name, code in BOOKS:
        cfg = EXPERIMENTS[name]
        swing = cfg.get("swing") or "sw10"
        res[name] = {}
        for era in ("is", "oos"):
            base = run(sim, ERA[era], cfg, swing)
            rec = {"fixed_3.0": base, "pct": {}, "rc": {}}
            for p in PCT:
                if p == 0.0:
                    rec["pct"]["0 (fixed)"] = base
                else:
                    rec["pct"]["%g" % p] = run(sim, ERA[era], cfg, swing, ext_stop_pct=p)
            for v in RC:
                rec["rc"][("%g" % v) if v < 90 else "off"] = run(
                    sim, ERA[era], cfg, swing, ext_stop_r=v)
            res[name][era] = rec
        for era in ("is", "oos"):
            r = res[name][era]
            ps = "  ".join("%s %+7.1f(%3d)" % (k, v["net"], v["n"])
                           for k, v in r["pct"].items() if v)
            rs_ = "  ".join("%s %+7.1f(%3d)" % (k, v["net"], v["n"])
                            for k, v in r["rc"].items() if v)
            print("  %-11s %-4s  base %+7.1f(%3d)" % (code, era.upper(),
                                                    r["fixed_3.0"]["net"], r["fixed_3.0"]["n"]), flush=True)
            print("      pct : %s" % ps)
            print("      rc  : %s" % rs_, flush=True)
        print("      (%.0fs)" % (time.time() - t0), flush=True)

    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    report(res)
    print("\nwrote %s, %s and %s  (%.0fs)" % (OUT.name, MD.name, REPORT.name, time.time() - t0))
    return 0


def report(res):
    L = ["# The admission gate as a percentile rather than a fixed 3.0R", "",
         "## Why this knob and not `htf_rr`", "",
         "The `htf_rr` decomposition split the change in book net into an entry-set",
         "term worth 2-3x the HTF term, and eight state-variable signals were tested",
         "against the smaller one. All eight flipped between eras. The larger half",
         "runs through the admission gate:", "",
         "```python",
         "# unified.py:1212-1216",
         "ext = (close - window_open) * dir / htf_risk",
         "if ext > ext_stop_r: continue",
         "```", "",
         "`ext` is in units of the window's own risk, which depends on where the swing",
         "started. So a fixed 3.0R is a different effective strictness in each",
         "regime - and 2021-22 measured 3.5x more volatile than 2023-26.", "",
         "The gate itself is earning its place. The gate diagnostic found trades",
         "nearest it are the weakest on every book and both eras (+0.12R to +0.60R",
         "per trade against +0.85R to +3.32R for fresh entries). The open question is",
         "its level, not its existence.", "",
         "## Percentile sweep — net R", ""]
    for era in ("is", "oos"):
        L += ["### %s" % era.upper(), "",
              "| book | base 3.0R | " + " | ".join("pct=%s" % p for p in PCT) + " |",
              "|---|---:|" + "---:|" * len(PCT)]
        for name, code in BOOKS:
            r = res[name][era]
            cells = []
            for p in PCT:
                key = "0 (fixed)" if p == 0.0 else "%g" % p
                v = r["pct"].get(key)
                cells.append("%+.0f" % v["net"] if v else "-")
            L.append("| %s | %+.0f | %s |" % (code, r["fixed_3.0"]["net"], " | ".join(cells)))
        L.append("")
    L += ["### Fixed-level sweep — the same knob the other way, for reference", ""]
    for era in ("is", "oos"):
        L += ["**%s**" % era.upper(), "",
              "| book | " + " | ".join(RC_KEYS) + " |",
              "|---|" + "---:|" * len(RC_KEYS)]
        for name, code in BOOKS:
            r = res[name][era]
            L.append("| %s | %s |" % (code, " | ".join(
                "%+.0f" % r["rc"][k]["net"] if r["rc"].get(k) else "-" for k in RC_KEYS)))
        L.append("")

    agg = {}
    for era in ("is", "oos"):
        for p in PCT:
            key = "0 (fixed)" if p == 0.0 else "%g" % p
            agg.setdefault(era, {})[key] = sum(res[n][era]["pct"][key]["net"] for n, _ in BOOKS)
    L += ["---", "", "## The bar", "",
          "A setting counts only if it beats the registered gate in **both eras**",
          "on aggregate. One era agreeing is what `exp_trail_skip_n=16` did and what",
          "the whole `htf_rr` sweep did.", "",
          "| setting | sum IS | sum OOS | beats 3.0R in both? |", "|---|---:|---:|---|"]
    bi, bo = agg["is"]["0 (fixed)"], agg["oos"]["0 (fixed)"]
    for p in PCT:
        key = "0 (fixed)" if p == 0.0 else "%g" % p
        si, so = agg["is"][key], agg["oos"][key]
        L.append("| %s | %+.0f | %+.0f | %s |"
                 % ("registered 3.0R" if p == 0.0 else "pct=%g" % p, si, so,
                    "**yes**" if (si > bi and so > bo) else ("-" if p == 0.0 else "no")))
    L += ["", "Nothing here is adopted. A percentile level chosen from this table on",
          "IS alone would be the same mistake in a new place. What this tells us is",
          "whether a regime-invariant gate is even worth having, which is a question",
          "about the mechanism rather than about the best number.", ""]
    MD.write_text("\n".join(L), encoding="utf-8")
    REPORT.write_text("\n".join(L), encoding="utf-8")


RC_KEYS = ["1.5", "2.5", "3.0", "4.0", "6.0", "off"]

if __name__ == "__main__":
    raise SystemExit(main())