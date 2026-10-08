"""exp_live_gates - the two things that will stop a trade being taken live.

THE TWO QUESTIONS
=================
The owner raised both as LIVE blockers, not research curiosities:

  1. "bahut chota sl, toh humko min sl ka rule lagana pdega and how it changes
      the net R now... bucket dikhana min point sl kitna liya hai"
  2. "agar humne long trade liya hai toh jab tak yeh long end nahi hojata tab tak
      short nahi le skte hai - long toh le skte hai but short nahi"

Both are new engine knobs (`exp_min_sl_pct`, `exp_no_opposite`) and both default
to OFF, which is what makes the shipped pins reproduce. This measures them.

WHAT IS ACTUALLY BEING ASKED IN (1)
===================================
The engine ALREADY refuses a stop inside 0.05% of price
(`risk < 0.0005*entry -> continue`). On BTC at 40k that is $20. Round-trip fees
are larger than that, so the floor is not a floor - it is a formality, and any
trade whose pivot happens to sit near entry gets through with a stop the spread
eats. This sweeps the floor upward and reports what each level costs.

The first table is the DISTRIBUTION, which is the answer to "kitna chota SL hai
actually" - percentiles in both points and percent-of-price, long and short
separately, because a short's stop sits above entry and the two are not
symmetric in practice.

The second table is the SWEEP: every bucket, both eras, net / expectancy / DD /
trades kept / trades dropped, plus how much of the book's profit came from the
trades a given floor removes. That last column is the one that decides it: if
the 0.40% floor removes 90 trades and 20R of profit, it is not a risk filter, it
is the edge.

WHAT IS ACTUALLY BEING ASKED IN (2)
===================================
`max_positions=1` already serialises on `busy_until` and blocks EVERY entry while
a trade is open, in both directions. That is strictly stronger than what is asked.
`exp_max_concurrent` caps the count but ignores direction. Neither can express
"flat and long may coexist, long and short may not", which is the actual ask -
on one symbol a long and a short net to roughly zero exposure while paying two
lots of fees.

The measurement that matters is not the net alone. It is: how many
opposite-direction overlaps actually occur, and what a flat-and-long position is
worth per unit of drawdown against being forced flat when the direction flips.

Run:  cd backtest/tests
      python -u exp_live_gates.py
"""
from __future__ import annotations

import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

BOOKS = {
    "BASE": "fsent_champ_long",
    "atr_low": "fsent_champ_long_mode_atr_low",
}
SL_FLOORS = [0.0, 0.0010, 0.0020, 0.0025, 0.0030, 0.0040, 0.0050, 0.0060,
             0.0080, 0.0100, 0.0150]
OUT_JSON = Path(__file__).parent / "_live_gates.json"
OUT_MD = Path(__file__).parent / "_live_gates.md"


def mdd(rs):
    cum = peak = 0.0
    m = 0.0
    for x in rs:
        cum += x
        if cum > peak:
            peak = cum
        m = max(m, peak - cum)
    return round(m, 2)


def pct(vals, p):
    s = sorted(vals)
    return s[max(0, min(len(s) - 1, int(round(p * (len(s) - 1)))))]


def main():
    from exp_tf_family import build_family_module
    from run_experiment import net_r, get_swings
    from exp_signal_metrics import load_era
    from experiment_registry import EXPERIMENTS

    sim = build_family_module()
    P = print
    P("=" * 122)
    P("  LIVE GATES - minimum stop distance, and the opposite-direction lock")
    P("  both knobs default OFF, which is why every shipped pin still reproduces")
    P("=" * 122)

    data = {}
    for era in ("is", "oos"):
        d = load_era(era)
        data[era] = (d, get_swings(d, "sw10"))

    def run(era, book, **kw):
        d, sw = data[era]
        o = sim(d["c1h"], sw, d["c15"], d["sw15"], fine_ltf=d["fine"],
                **{**EXPERIMENTS[book]["params"], **kw})
        return [t for t in o["ltf_trades"] if t.get("outcome") != "open"]

    payload = {}

    # ---------------- PART 1: how small is the stop, actually ----------------
    P()
    P("#" * 122)
    P("# PART 1 - STOP SIZE DISTRIBUTION as shipped (exp_min_sl_pct = 0, floor 0.05%)")
    P("#" * 122)
    for nm, bk in BOOKS.items():
        P()
        P("  %s" % nm)
        for era in ("is", "oos"):
            tr = run(era, bk)
            longs = [t for t in tr if str(t.get("dir")) == "long"]
            shorts = [t for t in tr if str(t.get("dir")) == "short"]
            P("    %s  n=%d  (longs %d / shorts %d)"
              % (era.upper(), len(tr), len(longs), len(shorts)))
            for side, sel in (("long ", longs), ("short", shorts)):
                if not sel:
                    continue
                dist = []
                for t in sel:
                    e = float(t["entry_price"])
                    s = float(t.get("sl") or e)
                    dist.append((abs(e - s), 100.0 * abs(e - s) / e))
                pts = [x[0] for x in dist]
                pctv = [x[1] for x in dist]
                P("      %s  points  p0=%9.1f p5=%8.1f p10=%8.1f p25=%8.1f p50=%8.1f p95=%9.1f max=%9.1f"
                  % (side, min(pts), pct(pts, .05), pct(pts, .10), pct(pts, .25),
                     pct(pts, .50), pct(pts, .95), max(pts)))
                P("      %s  %%price p0=%6.2f p5=%6.2f p10=%6.2f p25=%6.2f p50=%6.2f p95=%6.2f max=%6.2f"
                  % (side, min(pctv), pct(pctv, .05), pct(pctv, .10), pct(pctv, .25),
                     pct(pctv, .50), pct(pctv, .95), max(pctv)))
                # how many are below the floors we are about to sweep
                for f in (0.002, 0.004, 0.006, 0.010):
                    k = sum(1 for v in pctv if v < f * 100)
                    P("         under %4.1f%% floor: %4d trades (%.1f%% of %s)"
                      % (f * 100, k, 100.0 * k / len(pctv), side.strip()))
            payload.setdefault(nm, {}).setdefault(era, {})["n"] = len(tr)

    # ---------------- PART 2: the min-SL sweep ----------------
    P()
    P("#" * 122)
    P("# PART 2 - MINIMUM STOP SWEEP.  'kept R lost' is the profit carried by the")
    P("#   trades a given floor removes - the column that decides whether a floor")
    P("#   is a risk filter or just the edge wearing a hat.")
    P("#" * 122)
    for nm, bk in BOOKS.items():
        P()
        P("  %s" % nm)
        P("  %-7s %6s %10s %8s %8s %8s %10s %10s"
          % ("era", "floor", "kept", "dropped", "net", "exp", "DD", "keptR lost"))
        for era in ("is", "oos"):
            base = run(era, bk)
            base_rs = [net_r([t]) for t in base]
            base_net = sum(base_rs)
            for f in SL_FLOORS:
                tr = run(era, bk, exp_min_sl_pct=f)
                rs = [net_r([t]) for t in tr]
                net = sum(rs)
                dropped = len(base) - len(tr)
                # which base trades went away, and what they were worth
                bkey = {(int(t["entry_ts"]), str(t["dir"])): net_r([t]) for t in base}
                kept = {(int(t["entry_ts"]), str(t["dir"])): net_r([t]) for t in tr}
                lost_r = sum(v for k, v in bkey.items() if k not in kept)
                P("  %-7s %5.2f%% %6d %10d %8.1f %8s %8.1f %10s"
                  % (era.upper(), f * 100, len(tr), dropped, net,
                     ("%.3f" % (net / len(tr))) if tr else "-", mdd(rs),
                     ("%+.1f" % lost_r) if lost_r else "0.0"))
                payload.setdefault(nm, {}).setdefault(era, {}).setdefault(
                    "minsl", []).append({
                        "floor_pct": round(f * 100, 3), "kept": len(tr),
                        "dropped": dropped, "net": round(net, 2),
                        "expectancy": round(net / len(tr), 4) if tr else None,
                        "dd": mdd(rs), "keptR_lost": round(lost_r, 2),
                        "base_net": round(base_net, 2),
                        "net_delta": round(net - base_net, 2),
                    })

    # ---------------- PART 3: opposite-direction lock ----------------
    P()
    P("#" * 122)
    P("# PART 3 - OPPOSITE-DIRECTION LOCK.  How often does a long and a short")
    P("#   actually coexist on this book?  That count is the whole justification:")
    P("#   if it is zero the rule is free insurance, if it is large the book is")
    P("#   paying two lots of fees to hold zero exposure.")
    P("#" * 122)
    for nm, bk in BOOKS.items():
        P()
        P("  %s" % nm)
        P("  %-5s %6s %10s %10s %10s %10s %10s"
          % ("era", "n", "opposite", "same", "flat+both", "base net", "locked net"))
        for era in ("is", "oos"):
            base = run(era, bk)
            brs = [net_r([t]) for t in base]
            # count opposite-direction overlaps on the SHIPPED book
            opp = same = both = 0
            ivs = []
            for t in base:
                a = int(t["entry_ts"])
                b = int(t.get("exit_ts") or a)
                dd = 1 if str(t["dir"]) == "long" else -1
                ivs.append((a, b, dd))
            for i in range(len(ivs)):
                for j in range(i + 1, len(ivs)):
                    a1, b1, d1 = ivs[i]
                    a2, b2, d2 = ivs[j]
                    if d1 != d2 and a1 <= b2 and a2 <= b1:
                        opp += 1
                        both += 1
                    elif d1 == d2 and a1 <= b2 and a2 <= b1:
                        same += 1
            tr = run(era, bk, exp_no_opposite=1)
            rs = [net_r([t]) for t in tr]
            P("  %-5s %6d %10d %10d %10d %10.1f %10.1f"
              % (era.upper(), len(base), opp, same, both, sum(brs), sum(rs)))
            payload.setdefault(nm, {}).setdefault(era, {})["opposite"] = {
                "base_n": len(base), "opposite_overlaps": opp,
                "same_overlaps": same, "net_base": round(sum(brs), 2),
                "net_locked": round(sum(rs), 2), "dd_base": mdd(brs),
                "dd_locked": mdd(rs),
                "n_locked": len(tr),
            }

    OUT_JSON.write_text(json.dumps(payload, indent=2, default=str) + "\n",
                        encoding="utf-8")
    lines = ["# live gates - minimum stop distance and the opposite-direction lock", "",
             "Both knobs default OFF; every shipped pin reproduces with them off.", "",
             "## part 2 - minimum stop sweep", "",
             "| book | era | floor | kept | dropped | net | expectancy | DD | keptR lost | net delta |",
             "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for nm in payload:
        for era in ("is", "oos"):
            for r in payload[nm][era].get("minsl", []):
                lines.append("| %s | %s | %.2f%% | %d | %d | %+.1f | %s | %.1f | %+.1f | %+.1f |" % (
                    nm, era.upper(), r["floor_pct"], r["kept"], r["dropped"],
                    r["net"], ("%.3f" % r["expectancy"]) if r["expectancy"] is not None else "-",
                    r["dd"], r["keptR_lost"], r["net_delta"]))
    lines += ["", "## part 3 - opposite-direction lock", "",
              "| book | era | base n | opposite overlaps | same overlaps | net base | net locked | DD base | DD locked |",
              "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for nm in payload:
        for era in ("is", "oos"):
            o = payload[nm][era].get("opposite")
            if not o:
                continue
            lines.append("| %s | %s | %d | %d | %d | %+.1f | %+.1f | %.1f | %.1f |" % (
                nm, era.upper(), o["base_n"], o["opposite_overlaps"],
                o["same_overlaps"], o["net_base"], o["net_locked"],
                o["dd_base"], o["dd_locked"]))
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    P()
    P("wrote %s and %s" % (OUT_MD.name, OUT_JSON.name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())