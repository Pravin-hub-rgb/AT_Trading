"""DECOMPOSITION CENSUS - htf_rr is two knobs welded together. Separate them.

THE PROBLEM WITH EVERY htf_rr RESULT SO FAR
===========================================
Sweeping htf_rr from 3.0 to 4.0 moves two independent things at once:

    KNOB A  the HTF target sets WHEN THE WINDOW CLOSES.
            unified.py:730 closes the window at the HTF trade's exit, and
            v7_timecap.py:80 sets that exit to `entry + rr_target * risk`.
            A longer target means a longer window, which means MORE LTF entries
            get admitted inside it.

    KNOB B  the same target sets the R-multiple BOOKED on the HTF trade itself.

So every number produced by that sweep is the sum of two effects and neither can
be read. 4.0 might be better because it books more R on the HTF trade, or
because a longer window admits more LTF trades, or both, or because the extra
LTF trades are worse than average. The era split is unreadable for exactly this
reason, and so is the volatility bucketing - they were all reading a blended
number.

The registry default is 3.0 for every book. window_end is "exit".

WHAT THIS MEASURES
==================
Per HTF window, at htf_rr = 3.0 and again at 4.0, on the same book and era:

    open ts, close ts, duration in bars
    direction
    HTF R at 3.0 and at 4.0
    LTF entries admitted at 3.0 and at 4.0, and their net R

and then the delta, attributed:

    delta from ENTRY SET   = (LTF net at 4.0) - (LTF net at 3.0)
    delta from HTF BOOKING = (HTF R at 4.0)  - (HTF R at 3.0)
    delta total            = sum of the two

The answer to the whole research programme is in which term dominates:

  entry-set dominant   -> htf_rr is a WINDOW-DURATION knob in disguise. The
                          right move is an ATR-adaptive window length, and
                          window_end="r_touch" already decouples it.
  HTF-booking dominant -> it is a plain target knob. The right move is the
                          extension-rate framing: which 3R-reachers extend.

Window-level, not trade-level, deliberately. Windows are far fewer than trades,
so this is fewer decisions and less room to overfit - which is the property the
external review asked for. And the state variables that would drive a window-level
rule (_decay_legs, _decay_frac, leg size, ATR) are leg properties, available at
window open, not trade properties.

Run: $env:PYTHONIOENCODING='utf-8'; python -u exp_htfrr_decompose.py
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

OUT = HERE / "htfrr_decompose.json"
MD = HERE / "htfrr_decompose.md"

PAIRS = [(3.0, 4.0), (2.5, 4.0), (3.0, 5.0)]
BOOKS = [("fsent_champ_long_mcloff_htf15", "107"),
         ("fsent_champ_long_htf15_tskip6", "110"),
         ("fsent_champ_long_htffs", "106"),
         ("fsent_champ_long_htf15_htffs", "109"),
         ("fsent_champ_long_htfesmcl4", "108")]


def run(sim, data, cfg, swing, rr):
    p = {**BP, **(cfg.get("params") or {}), "htf_rr": rr}
    o = sim(data["c1h"], get_swings(data, swing), data["c15"], data["sw15"],
            fine_ltf=data["fine"], **p)
    return (o if isinstance(o, dict) else {"ltf_trades": o})


def htf_windows(o):
    """HTF trades, keyed by open timestamp. These ARE the windows: unified.py
    closes an LTF window at the HTF trade's exit, so one HTF trade is one window.
    """
    out = {}
    for t in (o.get("htf_trades") or []):
        if t.get("outcome") == "open":
            continue
        out[int(t["entry_ts"])] = {
            "dir": t.get("dir"),
            "open": int(t["entry_ts"]),
            "close": int(t.get("exit_ts") or t["entry_ts"]),
            "r": net_r([t]),
        }
    return out


def ltf_by_window(trades, wins):
    """Bucket every LTF entry under the window that was open when it fired."""
    acc = {}
    for t in trades:
        if t.get("outcome") == "open":
            continue
        ts = int(t["entry_ts"])
        hit = None
        for k, w in wins.items():
            if w["open"] <= ts <= w["close"]:
                hit = k
                break
        a = acc.setdefault(hit, {"n": 0, "net": 0.0})
        a["n"] += 1
        a["net"] += net_r([t])
    return acc


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
            rrs = sorted({v for p in PAIRS for v in p})
            runs = {}
            for rr in rrs:
                o = run(sim, ERA[era], cfg, swing, rr)
                wins = htf_windows(o)
                runs[rr] = {"windows": wins, "ltf": ltf_by_window(o.get("ltf_trades") or [], wins)}
            rec = {}
            for lo, hi in PAIRS:
                wl, wh = runs[lo], runs[hi]
                keys = set(wl["windows"]) | set(wh["windows"])
                dur_l = dur_h = 0
                ent_l = ent_h = 0
                nltf_l = nltf_h = 0
                net_l = net_h = 0.0
                htf_l = htf_h = 0.0
                matched = 0
                for k in keys:
                    a = wl["windows"].get(k)
                    b = wh["windows"].get(k)
                    if a and b:
                        matched += 1
                        dur_l += a["close"] - a["open"]
                        dur_h += b["close"] - b["open"]
                        htf_l += a["r"]
                        htf_h += b["r"]
                    ea = wl["ltf"].get(k) or {"n": 0, "net": 0.0}
                    eb = wh["ltf"].get(k) or {"n": 0, "net": 0.0}
                    nltf_l += ea["n"]; nltf_h += eb["n"]
                    net_l += ea["net"]; net_h += eb["net"]
                d_entry = net_h - net_l
                d_htf = htf_h - htf_l
                rec["%g->%g" % (lo, hi)] = {
                    "windows": len(keys), "windows_matched": matched,
                    "dur_bars_lo": dur_l, "dur_bars_hi": dur_h,
                    "dur_ratio": round(dur_h / dur_l, 3) if dur_l else 0,
                    "ltf_n_lo": nltf_l, "ltf_n_hi": nltf_h,
                    "ltf_net_lo": round(net_l, 2), "ltf_net_hi": round(net_h, 2),
                    "htf_r_lo": round(htf_l, 2), "htf_r_hi": round(htf_h, 2),
                    "delta_entry_set": round(d_entry, 2),
                    "delta_htf_booked": round(d_htf, 2),
                    "delta_total": round(d_entry + d_htf, 2),
                }
            res[name][era] = rec
        for era in ("is", "oos"):
            for k, v in res[name][era].items():
                tot = v["delta_total"]
                share = (v["delta_htf_booked"] / tot * 100.0) if abs(tot) > 1e-9 else 0.0
                print("  %-4s %-4s %-8s windows %4d  dur x%.2f  LTF %4d->%4d  "
                      "entry-delta %+8.1f  HTF-delta %+8.1f  total %+8.1f  HTF share %5.1f%%"
                      % (code, era.upper(), k, v["windows"], v["dur_ratio"],
                         v["ltf_n_lo"], v["ltf_n_hi"], v["delta_entry_set"],
                         v["delta_htf_booked"], tot, share), flush=True)
        print("      (%.0fs)" % (time.time() - t0), flush=True)

    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    report(res)
    print("\nwrote %s and %s  (%.0fs)" % (OUT.name, MD.name, time.time() - t0))
    return 0


def report(res):
    L = ["# htf_rr decomposition - is it a window knob or a target knob?", "",
         "Every previous htf_rr result is unreadable, and this is why.", "",
         "```",
         "KNOB A   v7_timecap.py:80  target = entry + rr_target * risk",
         "         unified.py:730     the LTF window closes at the HTF trade's exit",
         "         => a longer target means a LONGER WINDOW, which means MORE",
         "            LTF ENTRIES are admitted inside it",
         "",
         "KNOB B   the same target sets the R booked on the HTF trade itself",
         "```", "",
         "So 3.0 -> 4.0 moves two independent things at once, and every sweep,",
         "bucket and era comparison so far has been reading their sum. This",
         "separates them per window.", "",
         "| book | era | compare | windows | duration x | LTF entries | delta from ENTRY SET | delta from HTF BOOKING | total |",
         "|---|---|---|---:|---:|---|---:|---:|---:|"]
    for name, code in BOOKS:
        for era in ("is", "oos"):
            for k, v in res[name][era].items():
                L.append("| %s | %s | %s | %d | %.2f | %d → %d | %+.1f | %+.1f | %+.1f |"
                         % (code, era.upper(), k.replace("->", " → "), v["windows"],
                            v["dur_ratio"], v["ltf_n_lo"], v["ltf_n_hi"],
                            v["delta_entry_set"], v["delta_htf_booked"],
                            v["delta_total"]))
    L += ["", "---", "", "## How to read it", "",
          "Read the last three columns together.", "",
          "- **delta from ENTRY SET dominates** → htf_rr is a window-duration knob",
          "  wearing a target's clothes. Raising the target is really admitting",
          "  more LTF trades, and the question becomes *how long should a window",
          "  stay open* rather than *how far should a target sit*. That is an",
          "  ATR-adaptive window length, and `window_end=\"r_touch\"` already",
          "  decouples the two — at a cost previously measured at −130R.",
          "- **delta from HTF BOOKING dominates** → it really is a plain target",
          "  knob, and the extension-rate framing is right: which 3R-reachers",
          "  extend to 4R.",
          "- **the duration ratio** is the direct read. If the window barely",
          "  changes length while the numbers move, the effect is Knob B. If it",
          "  stretches, the effect is Knob A.", "",
          "This census changes nothing and adopts nothing. It is the measurement",
          "that decides which mechanism is worth building, and it was worth doing",
          "before any state variable, because a mechanism aimed at Knob A would",
          "be aimed at the wrong half of the effect.", ""]
    MD.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())