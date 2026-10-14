"""
GATE - pin the knob-liveness claims as executable assertions, not comments.

WHY A TEST AND NOT A COMMENT

The owner asked which settings are unused. The answer was:

    chop_thresh   inert while mode="atr_high"
    max_positions inert (absent behaves as 0)
    ext_stop_r    only ~1.x is live; 0.0 / 3.0 / 5.0 are the same behaviour

A comment saying "this is dead" rots. If someone flips the mode tomorrow, or the
engine starts reading the key, the comment is quietly wrong and nothing checks it.
The owner was explicit: the test is the proof, not the comment. So the keys stay in
the registry untouched and THESE assertions carry the claim.

THE THREE KEYS ARE NOT DELETED, AND MUST NOT BE

  chop_thresh    4 books carry it. BP default is 58.0, the same value, so removal
                 would be a no-op today - but production mode is b2_vs_flip_chop
                 where this key IS live. Delete it and a future mode flip changes
                 behaviour silently.
  ext_stop_r     ALL books carry it. BP default is 1.5, which is INSIDE the live
                 band. Deleting it does not no-op, it switches a trailing stop on.
  cooldown_bars  books pin 8, BP defaults to 10, and 10 was measured at -126.8R.

THE MODE-CONDITIONAL POINT IS ASSERTED, NOT ASSUMED

Assertions 1-3 all run under mode="atr_high". Assertion 4 exists because a
"dead knob" claim that is only true for one mode is a trap. It forces
mode="b2_vs_flip_chop" and requires chop_thresh to actually matter there. If that
assertion ever fails, "dead" is not mode-conditional and the reasoning above is
wrong in a way no reader would notice.

Usage:
    $env:PYTHONIOENCODING='utf-8'
    ..\\..\\backend\\venv\\Scripts\\python.exe -u exp_knob_liveness.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

HERE = Path(__file__).resolve().parent
# a book that actually carries chop_thresh, so the assertion is not vacuous
PROBE = "fsent_champ_short"


def main() -> int:
    from exp_tf_family import build_family_module
    from run_experiment import BP, get_data
    from engine.v18_params import SWING
    from experiment_registry import EXPERIMENTS
    from src.btc.btc_swing import compute_btc_swings

    sim = build_family_module()
    d = get_data()

    def chain(fl, mb, gap=1):
        return compute_btc_swings(
            fl, opts={"minBars": max(2, int(mb)), "b2GapBars": gap},
            max_swings=max(1, len(fl) // 2))

    sw15 = chain(d["f15"], SWING["min_bars_15m"])
    sw10 = chain(d["f1h"], 10)
    pick = {"sw10": sw10, "htf15": chain(d["f1h"], 15),
            "sw20": chain(d["f1h"], SWING["min_bars_1h"])}

    def sig(override=None, book=PROBE):
        cfg = EXPERIMENTS[book]
        p = {**BP, **cfg["params"]}
        p.setdefault("exp_partial_r", 0.0)
        if override:
            for k, v in override.items():
                if v is _DROP:
                    p.pop(k, None)
                else:
                    p[k] = v
        sw = pick.get(cfg.get("swing") or "sw10", sw10)
        res = sim(d["c1h"], sw, d["c15"], sw15, fine_ltf=d["fine"], **p)
        tr = res["ltf_trades"] if isinstance(res, dict) else res
        rows = []
        for x in tr:
            if str(x.get("outcome", "")).lower() == "open":
                continue
            rows.append("%s|%s|%.4f" % (x.get("entry_time") or x.get("entry")
                                        or x.get("entry_idx"),
                                        x.get("dir"), x.get("r_multiple") or 0.0))
        rows.sort()
        return len(rows), hashlib.sha256(chr(10).join(rows).encode()).hexdigest()[:12]

    class _Drop:
        pass

    _DROP = _Drop()
    globals()["_DROP"] = _DROP

    results = []
    print("=" * 78)
    print("KNOB LIVENESS GATE - is each claim still true?")
    print("=" * 78)
    print("  probe book: %s   mode=%s" % (PROBE, EXPERIMENTS[PROBE]["params"].get("mode")))
    print()

    def check(num, label, fn, expect_live):
        try:
            ok, detail = fn()
        except Exception as e:  # noqa: BLE001
            ok, detail = False, "raised %s: %s" % (type(e).__name__, e)
        expect = "live (differs)" if expect_live else "inert (identical)"
        status = "ok  " if ok else "FAIL"
        print("  [%s] %d. %s" % (status, num, label))
        print("        expect %-18s  %s" % (expect, detail))
        results.append({"n": num, "label": label, "expect": expect,
                        "pass": ok, "detail": detail})
        return ok

    # ---- 1. chop_thresh inert under atr_high ---------------------------------
    def a1():
        hs = {}
        for v in (40, 58, 74):
            n, h = sig({"chop_thresh": v})
            hs[v] = (n, h)
        uniq = len(set(hs.values()))
        return uniq == 1, "40/58/74 -> %s" % ", ".join("%s n=%d" % (h, n) for n, h in hs.values())

    check(1, "chop_thresh 40 vs 58 vs 74 identical under mode=atr_high", a1, False)

    # ---- 2. ext_stop_r: only ~1.x is live ------------------------------------
    def a2():
        hs = {}
        for v in (0.0, 3.0, 5.0):
            n, h = sig({"ext_stop_r": v})
            hs[v] = (n, h)
        n1, h1 = sig({"ext_stop_r": 1.0})
        inert = len(set(hs.values())) == 1
        live = h1 != hs[3.0][1]
        return inert and live, ("0.0/3.0/5.0 identical=%s ; 1.0 differs=%s (n=%d vs %d)"
                                % (inert, live, n1, hs[3.0][0]))

    check(2, "ext_stop_r 0.0/3.0/5.0 identical AND 1.0 genuinely differs", a2, False)

    # ---- 3. max_positions absent == 0 -----------------------------------------
    def a3():
        n0, h0 = sig({"max_positions": 0})
        n1, h1 = sig({"max_positions": _DROP})
        return h0 == h1, "0 -> n=%d %s ; absent -> n=%d %s" % (n0, h0, n1, h1)

    check(3, "max_positions ABSENT equivalent to 0", a3, False)

    # ---- 4. the mode-conditional claim itself --------------------------------
    def a4():
        hs = {}
        for v in (40, 74):
            n, h = sig({"chop_thresh": v, "mode": "b2_vs_flip_chop"})
            hs[v] = (n, h)
        differs = hs[40][1] != hs[74][1]
        return differs, ("mode=b2_vs_flip_chop: 40 -> n=%d %s ; 74 -> n=%d %s"
                         % (hs[40][0], hs[40][1], hs[74][0], hs[74][1]))

    check(4, "chop_thresh IS live under mode=b2_vs_flip_chop", a4, True)

    print()
    bad = [r for r in results if not r["pass"]]
    out = {"stage": "knob_liveness", "probe_book": PROBE, "results": results}
    (HERE / "knob_liveness_results.json").write_text(json.dumps(out, indent=2),
                                                     encoding="utf-8")
    print("  wrote %s" % (HERE / "knob_liveness_results.json"))
    if bad:
        print()
        print("  RESULT: %d of %d FAILED." % (len(bad), len(results)))
        for r in bad:
            print("     - %d. %s" % (r["n"], r["label"]))
        print()
        print("  A failure here is NOT a bug to fix. It means the liveness claim")
        print("  changed - the engine started reading a key it used to ignore, or a")
        print("  mode stopped differentiating. Re-derive the claim before touching")
        print("  any book config. Do NOT 'fix' this by editing the books.")
        return 1
    print()
    print("  RESULT: pass - all 4 claims hold. The keys stay in the registry.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())