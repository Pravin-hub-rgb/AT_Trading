"""
Owner invariants over the whole swing chain.

Two halves, and the second half is the one that matters.

HALF 1 - emitted marks. Every mark the engine produced is checked against the
settled rules. Cheap, and catches most regressions.

HALF 2 - SUPPRESSED breaks. A break that happened but produced no mark. These
are the dangerous ones: `breaks` only ever holds marks that WERE emitted, so a
suppressed break cannot appear in the payload. A harness that validates emitted
marks alone is structurally blind to the exact bug class found on 2026-10-13
(the volatile FLIP at 2023-09-03 13:30 produced no mark at all, so nothing
downstream could ever have noticed).

So this reads the candle that was SKIPPED. For every bar where the engine saw
a break and emitted nothing, it classifies the bar against the gate state the
engine itself was holding, and anything that does not land in a named bucket is
reported as UNEXPLAINED. The headline number is that count, and it must be 0.

Usage:
    python -u exp_swing_invariants.py

Exit 0 only when every invariant holds and UNEXPLAINED == 0.
"""

from __future__ import annotations

import collections
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for _p in (ROOT / "backtest/tests", ROOT / "backend"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from src.firstswing import SwingEngine  # noqa: E402

MIN_BARS = 50
SYMBOL = "BTCUSDT_BYBIT"
INTERVAL = "15m"
LIMIT = 200_000

# ── instrument the engine so we can see the decision it was about to make ──────
# Reading marks back off the payload is not enough: we need the flags as the
# engine computed them, and the extreme levels it was comparing against, on
# every bar where it was armed.
_STEPS: list[dict] = []
_orig_step = SwingEngine._step


def _step_probe(self, down_break: bool, up_break: bool):  # type: ignore[no-untyped-def]
    def _lvl(x):  # type: ignore[no-untyped-def]
        return None if x is None else (float(x.px), int(x.idx))

    _STEPS.append(
        {
            "g": int(self.g_idx),
            "t": self.t,
            "eid": id(self),
            "mcount": len(self.break_marks),
            "marks": tuple((int(m.idx), m.kind) for m in self.break_marks),
            "state": self.state,
            "dir": self.dir,
            "dn": bool(down_break),
            "up": bool(up_break),
            "pending": bool(getattr(self, "_pending_arm", False)),
            "b2done": bool(getattr(self, "_b2_done_in_dir", False)),
            "last": getattr(self, "_last_mark_kind", None),
            "conf": bool(getattr(self, "dir_confirmed", False)),
            "b1_side": getattr(self, "_b1_side", None),
            "b1_bar": int(getattr(self, "b1_bar_idx", -1)),
            "cl": float(self.cl),
            "op": float(self.op),
            "eh": _lvl(getattr(self, "e_hi_prev", None)),
            "el": _lvl(getattr(self, "e_lo_prev", None)),
        }
    )
    return _orig_step(self, down_break, up_break)


SwingEngine._step = _step_probe  # type: ignore[method-assign]


def main() -> int:
    from src.btc.btc_routes import _load_window
    from src.btc.btc_swing import compute_btc_swings

    candles, flow = _load_window(INTERVAL, LIMIT, SYMBOL)[0]
    candles = list(candles)
    flow = list(flow)
    ts = [c["date"][:16] for c in candles]
    highs = [float(c["high"]) for c in candles]
    lows = [float(c["low"]) for c in candles]

    swings = compute_btc_swings(
        flow, opts={"minBars": MIN_BARS}, max_swings=max(1, len(candles) // 2)
    )

    # ── collect marks ────────────────────────────────────────────────────────
    marks: list[dict] = []
    fs_marks: list[dict] = []
    for s in swings:
        for b in s["breaks"]:
            marks.append({"g": int(b["idx"]), "t": ts[b["idx"]], "kind": b["kind"], "dir": b["dir"]})
        if s.get("fs_at_idx") is not None:
            fs_marks.append({"g": int(s["fs_at_idx"]), "t": ts[s["fs_at_idx"]], "dir": s["dir"]})

    kinds = collections.Counter(m["kind"] for m in marks)
    step_by_g: dict[int, dict] = {}
    for st in _STEPS:
        step_by_g[st["g"]] = st
    print("=" * 78)
    print("SWING INVARIANTS - %s %s" % (SYMBOL, INTERVAL))
    print("=" * 78)
    print("  swings %d   marks %d  %s" % (len(swings), len(marks), dict(kinds)))
    print()

    failures: list[str] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        print("  [%s] %s%s" % ("ok" if ok else "FAIL", name, ("  - " + detail) if detail else ""))
        if not ok:
            failures.append(name)

    # ── HALF 1: invariants over emitted marks ────────────────────────────────
    print("HALF 1 - emitted marks")
    print("-" * 78)

    by_swing: list[list[dict]] = [[] for _ in swings]
    idx_of: dict[int, int] = {}
    for s in swings:
        for b in s["breaks"]:
            idx_of[int(b["idx"])] = int(s["swing_index"])

    # H1.1 every swing starts with a B1
    bad = [s["swing_index"] for s in swings if not s["breaks"] or s["breaks"][0]["kind"] != "B1"]
    check("every swing opens with a B1", not bad, "offenders %s" % bad[:5] if bad else "%d swings" % len(swings))

    # H1.2 B1/B2 share direction, FLIP opposes its neighbours
    bad = []
    flip_flip = 0
    for s in swings:
        bs = s["breaks"]
        for i, b in enumerate(bs):
            if b["kind"] in ("B1", "B2"):
                nb = bs[i + 1] if i + 1 < len(bs) else None
                if nb and nb["kind"] in ("B1", "B2") and nb["dir"] != b["dir"]:
                    bad.append((ts[b["idx"]], b["kind"], b["dir"], nb["kind"], nb["dir"]))
            if b["kind"] == "FLIP" and i + 1 < len(bs) and bs[i + 1]["kind"] == "FLIP":
                if bs[i + 1]["dir"] == b["dir"]:
                    flip_flip += 1
    check("B1/B2 same side, FLIP opposite", not bad, "%d violations %s" % (len(bad), bad[:3]) if bad else "")
    check("no FLIP opposes the prior FLIP", flip_flip == 0, "%d same-side FLIP-FLIP" % flip_flip if flip_flip else "")

    # H1.3 marks strictly increase inside a swing
    bad = [s["swing_index"] for s in swings if [b["idx"] for b in s["breaks"]] != sorted(b["idx"] for b in s["breaks"])]
    check("marks strictly increase within a swing", not bad, "offenders %s" % bad[:5] if bad else "")

    # H1.4 VOLATILE B1 direction follows the candle colour
    #      (owner 2026-10-13, 2026-05-18 21:30 -> B1 up on a green bar;
    #       2023-02-12 05:30 -> B1 down on a red bar)
    #      Only volatile bars are subject to this. A one-sided break takes its
    #      direction from which extreme broke, and its colour may legitimately
    #      oppose that - checking colour on every B1 produced 398 false alarms.
    by_g: dict[int, list[dict]] = collections.defaultdict(list)
    for m in marks:
        by_g[m["g"]].append(m)
    bad = []
    volatile_b1 = 0
    for s in swings:
        b1 = s["breaks"][0]
        i = int(b1["idx"])
        st = step_by_g.get(i)
        if st is None or not (st["up"] and st["dn"]):
            continue
        volatile_b1 += 1
        green = float(candles[i]["close"]) > float(candles[i]["open"])
        if (b1["dir"] == "up") != green:
            bad.append((ts[i], b1["dir"], "GRN" if green else "RED"))
    check(
        "volatile B1 direction agrees with its candle colour",
        not bad,
        "%d disagree %s" % (len(bad), bad[:3]) if bad else "%d volatile B1s" % volatile_b1,
    )

    # H1.5 FS never lands before its own minBars gate
    bad = []
    for s in swings:
        f = s.get("fs_at_idx")
        if f is None:
            continue
        if int(f) < int(s["min_bars_idx"]):
            bad.append((ts[int(f)], ts[int(s["min_bars_idx"])]))
    check("FS never before the minBars gate", not bad, "%d %s" % (len(bad), bad[:3]) if bad else "%d FS" % len(fs_marks))

    # H1.6 FS at or after the last mark of its leg
    bad = []
    for s in swings:
        f = s.get("fs_at_idx")
        if f is None or not s["breaks"]:
            continue
        if int(f) < int(s["breaks"][-1]["idx"]):
            bad.append((ts[int(f)], ts[int(s["breaks"][-1]["idx"])]))
    check("FS at or after the leg's last mark", not bad, "%d %s" % (len(bad), bad[:3]) if bad else "")

    print()

    # ── HALF 2: suppressed breaks - read the candle that was skipped ─────────
    print("HALF 2 - suppressed breaks (the blind spot)")
    print("-" * 78)
    print("  A break the engine saw but did not mark. `breaks` cannot contain")
    print("  these, so this half exists to make them visible.")
    print()

    def gap_clean(st: dict, up: bool) -> bool:
        """1-candle gap on the level the break was aimed at."""
        lvl = st["eh"] if up else st["el"]
        if lvl is None:
            return False
        px, idx = lvl
        gap_bars = 1
        if not (idx <= st["g"] - 1 - gap_bars):
            return False
        nxt = idx + 1
        if not (0 <= nxt < len(candles)):
            return False
        return (highs[nxt] <= px) if up else (lows[nxt] >= px)

    # An engine instance whose marks never reached the chain was abandoned: the
    # stitch restarted and its B1/B2/FLIP were discarded, so the owner would
    # never see them and a suppression inside it is not a defect.
    #
    # Detect it by CONTENT, not by a drop in break_marks - a drop happens on
    # ordinary leg transitions, and keying off it classified 19725 of 20460
    # suppressions as discarded (96%), which made this half vacuous and would
    # have hidden exactly the cases it exists to find. An instance counts as
    # abandoned only when NONE of the marks it ever emitted appears in the chain.
    seen_by_eid: dict[int, set] = collections.defaultdict(set)
    for st in _STEPS:
        seen_by_eid[st["eid"]].update(st["marks"])
    chain_marks = {(int(b["idx"]), b["kind"]) for s in swings for b in s["breaks"]}
    discarded: set[int] = {
        eid for eid, ms in seen_by_eid.items() if not (ms & chain_marks)
    }

    buckets: collections.Counter = collections.Counter()
    unexplained: list[dict] = []
    suppressed_total = 0

    for st in _STEPS:
        if not (st["up"] or st["dn"]):
            continue
        if st["g"] in by_g:
            continue  # a mark was emitted here
        suppressed_total += 1
        if st["eid"] in discarded:
            buckets["engine instance abandoned before reaching the chain"] += 1
            continue
        volatile = st["up"] and st["dn"]
        green = st["cl"] > st["op"]
        d = st["dir"]
        if volatile:
            sustained = "up" if green else "down"
            if d is not None and sustained == d:
                if st["last"] == "FLIP":
                    buckets["volatile/sustained after a FLIP"] += 1
                elif st["b2done"]:
                    buckets["volatile/B2 already done in this direction"] += 1
                elif not gap_clean(st, sustained == "up"):
                    buckets["volatile/gap-contaminated"] += 1
                else:
                    buckets["volatile/UNEXPLAINED"] += 1
                    unexplained.append(st)
            else:
                buckets["volatile/sustained against the leg (FLIP)"] += 1
            continue
        # one-sided
        direction_of_break = "up" if st["up"] else "down"
        lvl = st["eh"] if direction_of_break == "up" else st["el"]
        if st["state"] == "watch":
            buckets["watch/armed on a later bar"] += 1
        elif not st["conf"]:
            # B2 territory - the leg direction is not confirmed yet, so a
            # with-the-leg break can still fire a B2 here.
            if st["b2done"]:
                buckets["not-confirmed/B2 already done in this direction"] += 1
            elif not gap_clean(st, direction_of_break == "up"):
                buckets["not-confirmed/gap-contaminated"] += 1
            elif lvl is not None and lvl[1] < st["b1_bar"]:
                buckets["not-confirmed/target predates this leg's B1"] += 1
            else:
                buckets["not-confirmed/UNEXPLAINED"] += 1
                unexplained.append(st)
        elif d is not None and direction_of_break == d:
            # Once the direction is CONFIRMED the engine has no plain-B2 path at
            # all: the two one-sided branches there emit FLIP or as_b2 only. A
            # with-the-leg break therefore produces no mark by design, and only
            # the chop/FS machinery runs. This was 4504 bars that a naive
            # classifier called unexplained.
            buckets["confirmed/with the leg - no B2 by design (chop/FS only)"] += 1
        else:
            # against the leg: _flip always emits, so a miss here is real
            buckets["confirmed/against leg/UNEXPLAINED"] += 1
            unexplained.append(st)

    for k, v in sorted(buckets.items()):
        flag = ""
        if k.endswith("UNEXPLAINED"):
            flag = "   <-- "
        print("    %-52s %6d%s" % (k, v, flag))
    print()
    print("    suppressed breaks examined : %d" % suppressed_total)
    check("every suppressed break has a named cause", not unexplained,
          "%d unexplained" % len(unexplained))
    if unexplained:
        for st in unexplained[:10]:
            print("        %s state=%s dir=%s up=%s dn=%s cl=%.1f op=%.1f"
                  % (st["t"][:16], st["state"], st["dir"], st["up"], st["dn"], st["cl"], st["op"]))
    print()

    print("=" * 78)
    if failures:
        print("RESULT: %d FAILED  ->  %s" % (len(failures), "; ".join(failures)))
        return 1
    print("RESULT: all invariants hold, 0 unexplained suppressed breaks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
