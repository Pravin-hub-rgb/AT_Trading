"""The ATR regime knobs, swept fine - the doc's technique 1, on the knobs that
actually decide which trades we get.

WHY THIS EXISTS AND WHY IT TOOK A SECOND PASS
=============================================
The first pass here answered a different question. exp_param_binding.py asked
which knobs are load-bearing at all, by moving each one to two neighbours and
counting surviving trades. That was the right prior question - a knob that
cannot be changed cannot be overfitted on, and a flat heat map over one proves
nothing - but it is NOT technique 1. Technique 1 asks how performance MOVES
across neighbouring values, and it was applied to cooldown_bars and exp_persist
while the ATR knobs - the ones the owner correctly identified as core - went
untested. The prior question is not a substitute for this one.

WHAT IS BEING SWEPT, AND WHY THESE
==================================
Unified engine, unified.py:1097-1098, the entire atr_high mode:

    elif mode=="atr_high":
        use="decisive" if atrp > atr_high_thresh else "flip"

One comparison. Under that mode atr_high_thresh IS the regime rule and
atr_low_thresh is never read at all - it belongs to the atr_low,
chop_or_atr_low and chop_and_atr_low branches. chop_thresh is likewise unread
in this branch. So of the three knobs that look like the volatility detector,
exactly one is connected.

That is a code reading, not an inference from the sweep, and the sweep is here
to confirm it at a resolution finer than two points.

  atr_high_thresh  0.55 .. 0.75, fine, including both neighbours of 0.65
  atr_low_thresh   0.20 .. 0.50, fine, including 0.33 / 0.34 / 0.36
  mode             the regime rules the engine implements, since the owner
                   flagged mode as the broader and more core decision

READING THE OUTPUT
==================
The doc's picture is a cluster of profitable values degrading slowly, and its
failure shape is a cliff. So the report carries, per value: trades, net, net per
trade, drawdown, losing streak, profit factor, and the fraction of trades shared
with the registered book. The shared fraction is what separates "the edge
degraded" from "you are now running a different strategy".

Run: $env:PYTHONIOENCODING='utf-8'; python -u exp_atr_sensitivity.py
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

OUT = HERE / "atr_sensitivity.json"
MD = HERE / "atr_sensitivity.md"
REPORT = HERE.parent / "docs" / "learn" / "ATR_SENSITIVITY.md"

BOOKS = [("fsent_champ_long_mcloff_htf15", "107"),
         ("fsent_champ_long_htf15_tskip6", "110")]

HIGH = [0.50, 0.55, 0.58, 0.60, 0.62, 0.63, 0.64, 0.65, 0.66, 0.67, 0.68,
        0.70, 0.72, 0.75, 0.80]
LOW = [0.15, 0.20, 0.25, 0.28, 0.30, 0.32, 0.33, 0.34, 0.35, 0.36, 0.38,
       0.40, 0.45, 0.50, 0.60]

# the regime rules the engine actually implements. Expired and ensemble variants
# are excluded on purpose: they are one-off research lanes, not alternatives a
# book could sensibly be re-pointed at.
MODES = ["atr_high", "atr", "atr_low", "chop", "atr_both", "chop_or_atr",
         "soft_chop", "soft_atr", "decisive_vs_flip_chop", "b2_vs_flip_chop",
         "htf_dir", "htf_mag", "htf_mag_inv", "flip_quality", "dynamic_chop",
         "session"]


def closed(trades):
    return sorted([t for t in trades if t.get("outcome") != "open"],
                  key=lambda t: int(t["entry_ts"]))


def key_of(t):
    return (int(t["entry_ts"]), int(t.get("exit_ts") or 0), round(net_r([t]), 4))


def stats(trades, base_keys=None):
    if not trades:
        return None
    rs = [net_r([t]) for t in trades]
    n = len(rs)
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
    gw, gl = sum(w), -sum(l)
    out = {"n": n, "net": round(sum(rs), 2), "rpt": round(sum(rs) / n, 4),
           "wr": round(100.0 * len(w) / n, 1),
           "pf": round(gw / gl, 3) if gl else 0.0,
           "dd": round(dd, 2), "streak": bst}
    if base_keys:
        mine = set(key_of(t) for t in trades)
        out["same_pct"] = round(100.0 * len(mine & base_keys) / max(len(base_keys), 1), 1)
    return out


def run(sim, data, cfg, swing, **over):
    p = {**BP, **(cfg.get("params") or {}), **over}
    o = sim(data["c1h"], get_swings(data, swing), data["c15"], data["sw15"],
            fine_ltf=data["fine"], **p)
    return closed(o["ltf_trades"] if isinstance(o, dict) else o)


def sweep(sim, ERA, log, book, knob, values):
    name, code = book
    cfg = EXPERIMENTS[name]
    swing = cfg.get("swing") or "sw10"
    out = {}
    for era in ("is", "oos"):
        base = run(sim, ERA[era], cfg, swing)
        bk = set(key_of(t) for t in base)
        rows = []
        for v in values:
            try:
                tr = run(sim, ERA[era], cfg, swing, **{knob: v})
            except Exception as exc:  # noqa: BLE001
                rows.append({"v": v, "error": "%s: %s" % (type(exc).__name__, exc)})
                continue
            rows.append(dict(v=v, **stats(tr, bk)))
        out[era] = rows
        ok = [r for r in rows if "error" not in r]
        print("  %s %-4s %-16s %2d/%2d ok   net %s"
              % (code, era.upper(), knob, len(ok), len(rows),
                 ("%+.1f .. %+.1f" % (min(r["net"] for r in ok),
                                      max(r["net"] for r in ok))) if ok else "n/a"),
              flush=True)
    return out


def table(rows, knob, code, era):
    L = ["### %s %s — `%s`" % (code, era.upper(), knob), "",
         "| %s | trades | net R | net/trade | win %% | PF | max DD | streak | same as book |"
         % knob, "|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in rows:
        # mode values are strings, everything else is numeric
        lbl = ("%.2f" % r["v"]) if isinstance(r["v"], (int, float)) else str(r["v"])
        if "error" in r:
            L.append("| %s | - | - | - | - | - | - | - | %s |" % (lbl, r["error"][:28]))
        else:
            L.append("| %s | %d | %+.1f | %+.3f | %.1f | %.2f | %.2f | %d | %.1f%% |"
                     % (lbl, r["n"], r["net"], r["rpt"], r["wr"], r["pf"],
                        r["dd"], r["streak"], r["same_pct"]))
    L.append("")
    return L


def main() -> int:
    t0 = time.time()
    if (sys.argv[1] if len(sys.argv) > 1 else "").lower() == "report":
        res = json.loads(OUT.read_text(encoding="utf-8"))
        print("rebuilding the report from %s" % OUT.name, flush=True)
        return report(res)
    print("loading eras ...", flush=True)
    ERA = {"is": get_data(), "oos": load_era("oos")}
    sim = build_family_module()
    res = {}
    for book in BOOKS:
        print("\n=== %s ===" % book[1], flush=True)
        res[book[0]] = {}
        for knob, vals in (("atr_high_thresh", HIGH), ("atr_low_thresh", LOW),
                           ("mode", MODES)):
            res[book[0]][knob] = sweep(sim, ERA, print, book, knob, vals)

    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("\nwrote %s  (%.0fs)" % (OUT.name, time.time() - t0))
    return report(res)


def report(res):
    R = ["# ATR regime sensitivity - the doc's technique 1, on the core knobs", "",
         "2026-10-16. Source: `4 backtesting techniques behind winning strategies.md`,",
         "technique 1, applied to the knobs that decide which trades we get.",
         "Harness: `backtest/experiments/exp_atr_sensitivity.py`. Raw:",
         "`atr_sensitivity.json`.", "",
         "## Why these knobs, and why this was a second pass", "",
         "The prior pass in this repo (`exp_param_binding.py`) asked which knobs",
         "are load-bearing at all, by moving each to two neighbours and counting",
         "surviving trades. That was the right prior question but it is not",
         "technique 1. It was applied to `cooldown_bars` and `exp_persist` while",
         "the ATR knobs went untested - and the ATR knobs decide whether a trade",
         "is taken in the `decisive` window or the `flip` window, which is the",
         "difference between the book existing and not.", "",
         "## What the engine actually does with them", "",
         "`unified.py:1097-1098` - the entire `atr_high` mode:", "",
         "```python",
         "elif mode == \"atr_high\":",
         "    use = \"decisive\" if atrp > atr_high_thresh else \"flip\"",
         "```", "",
         "One comparison. Under this mode:", "",
         "| knob | read by `atr_high`? | where it is actually used |",
         "|---|---|---|",
         "| `atr_high_thresh` | **yes - it is the whole rule** | line 1097 |",
         "| `atr_low_thresh` | **no** | `atr_low`, `chop_or_atr_low`, `chop_and_atr_low` (1095, 1099, 1101) |",
         "| `chop_thresh` | **no** | every `chop`-named branch (1093 onward) |",
         "",
         "So of the three knobs that look like the volatility detector, one is",
         "connected. That is read from the source; the sweeps below confirm it at",
         "finer resolution than two points, which is the point - a two-point probe",
         "cannot distinguish \"inert\" from \"coarse grid\".", "",
         "## Correction to the binding report", "",
         "The binding report listed `window_end` as INERT. That verdict was wrong,",
         "and it was wrong because of how it was tested, not because of the knob.",
         "`unified.py:730` reads:", "",
         "```python",
         "wend = _r_touch_end(...) if window_end == \"r_touch\" else int(t[\"exit_ts\"]) + _wend_settle",
         "```", "",
         "The knob is live; only the single value `\"r_touch\"` discriminates. The",
         "binding probe tested `24bars` and `4days`, neither of which is",
         "`r_touch`, so both fell into the else branch and produced identical",
         "books. `r_touch` moves 107 from 525/+538.40 to 522/+532.95. The knob was",
         "live the whole time and the probe never asked the value that mattered.",
         "", "Similarly `mode=\"atr_extreme\"` does not exist - the engine",
         "implements 27 modes and that is not one of them, which is why the",
         "binding probe reported ERROR rather than a number there.", ""]

    for book in BOOKS:
        code = book[1]
        R += ["---", "", "# %s `%s`" % (code, book[0]), ""]
        for knob in ("atr_high_thresh", "atr_low_thresh", "mode"):
            for era in ("is", "oos"):
                R += table(res[book[0]][knob][era], knob, code, era)

    R += ["---", "", "## How to read these tables", "",
          "`same as book` is the fraction of trades identical to the registered",
          "configuration. It separates three failures that a net number conflates:",
          "",
          "- **low `same`, flat net** - the knob reshuffles the book without",
          "  changing profit. The edge is broad rather than specific.",
          "- **low `same`, collapsed net** - you are running a different strategy",
          "  and it is worse. That is a cliff, and the doc's red flag.",
          "- **high `same`, collapsed net** - the worst case: the same trades,",
          "  materially less money. Profit was coming from a few large positions",
          "  rather than from the book.", "",
          "`atr_low_thresh` should read identically at every value. If it does not,",
          "the code reading above is wrong and that is the more serious finding.", ""]
    REPORT.write_text("\n".join(R), encoding="utf-8")
    print("wrote %s" % (REPORT.name,))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())