"""P3-C - live_R>=0 as a REAL engine gate, not a post-hoc filter.

WHY A PATCHED COPY AND NOT THE POST-HOC FILTER
==============================================
ORACLE_EARLY.md found `live_R >= 0` improves WR, PF and trimmed mean in
BOTH eras. That was a post-hoc screen over trades the engine had already
decided to take. Screening cannot prove a gate works, because the engine
never had to decide anything. So this runs it as a genuine backtest: the
gate is inside the loop, the engine does not know a trade was skipped, and
maxDD / trade count / sequence all change the way they would in production.

THE TRICK, which is why no engine edit is needed
================================================
`to_intervals` (v18_streak_halt.py:226) turns each 1h HTF trade into a
5-tuple `(start, end, dir, entry_px, sl)`, and the LTF layer may only
enter while some interval contains its timestamp with a matching
direction. So "only trade while the 1h leg is in profit" is exactly
equivalent to SPLITTING each window into its maximal sub-runs where
live_R >= floor, and emitting each sub-run as its own interval with the
same dir / px / sl. Same representation, finer partition, no new concept.

So the patch touches one function and changes no trading logic.

IDENTITY GATE - run first, and it must be exact
==============================================
With `live_r_floor=None` this must reproduce the untouched engine's
trade count AND net R to the last decimal, in both eras. If it does not,
the patch changed behaviour and every other number here is void. This is
the check that has caught three of today's mistakes.

Also swept here, because a single threshold that survives is exactly the
kind of thing that evaporates when you look at its neighbours:
  - the floor, on a grid
  - the WINDOW-AGE floor, since ORACLE_EARLY found age > 0.5d was the only
    other both-eras arm
  - the two together
Nothing is adopted. The result decides.
"""
from __future__ import annotations

import bisect as bs
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

SRC = ROOT / "backend/src/btc/engines/htf_ltf/v18_streak_halt.py"
TMP = ROOT / "backtest/tests/_v18_livegate_tmp.py"

_ORIG = '''            wend = _r_touch_end(t, fine_ltf, fine_ts, ext_stop_r) if window_end=="r_touch" else int(t["exit_ts"])
            iv.append([int(t["entry_ts"]), wend, 1 if t["dir"]=="long" else -1, float(t["entry_price"]), float(t["sl"])])'''

_PATCHED = '''            wend = _r_touch_end(t, fine_ltf, fine_ts, ext_stop_r) if window_end=="r_touch" else int(t["exit_ts"])
            _a=int(t["entry_ts"]); _d=1 if t["dir"]=="long" else -1
            _p=float(t["entry_price"]); _s=float(t["sl"])
            _risk=abs(_p-_s)
            if live_r_floor is None or _risk<=0 or _a>=wend:
                iv.append([_a, wend, _d, _p, _s])
            else:
                # split [a,wend] into maximal runs where the 1h leg is
                # in profit by at least live_r_floor, measured on the 1m
                # close at or before each minute. Same dir/px/sl per run.
                _pxs=[float(c["close"]) for c in fine_ltf] if fine_ltf else []
                _run=None
                for _k in range(_a, wend+1, 60):
                    _j=bs.bisect_right(fine_ts,_k)-1
                    if _j<0 or _j>=len(_pxs): continue
                    _ok=(_d*(_pxs[_j]-_p))/_risk >= live_r_floor
                    if _ok and _run is None: _run=_k
                    if (not _ok) and _run is not None:
                        iv.append([_run,_k-1,_d,_p,_s]); _run=None
                if _run is not None: iv.append([_run,wend,_d,_p,_s])'''


def build_patched():
    """Copy the engine, patch to_intervals, write a temp module."""
    src = SRC.read_text(encoding="utf-8")
    if _ORIG not in src:
        raise SystemExit("PATCH TARGET NOT FOUND - engine changed, "
                         "refusing to run a stale patch")
    out = src.replace(_ORIG, _PATCHED)
    # add the kwarg to the signature
    sig_old = '    max_consecutive_losses=0,  # 0 = no halt, N = halt after N consecutive losses\n'
    if sig_old not in out:
        raise SystemExit("SIGNATURE TARGET NOT FOUND")
    out = out.replace(
        sig_old,
        sig_old + "    live_r_floor=None,  # TEMP probe: only trade while 1h leg >= this R\n")
    # fine_ts must exist before to_intervals is defined/called
    if "    fine_ts=[int(c[\"ts\"]) for c in fine_ltf] if fine_ltf else []" not in out:
        raise SystemExit("fine_ts TARGET NOT FOUND")
    TMP.write_text(out, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("_v18_livegate_tmp", TMP)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_v18_livegate_tmp"] = mod
    spec.loader.exec_module(mod)
    return mod


def tm(x):
    if not x:
        return 0.0
    x = sorted(x)
    k = max(1, len(x) // 20)
    return sum(x) / len(x) if len(x) <= k else sum(x[:-k]) / (len(x) - k)


def pf(rs):
    return sum(x for x in rs if x > 0) / max(1e-9, -sum(x for x in rs if x < 0))


def maxdd(rs):
    eq = peak = dd = 0.0
    for x in rs:
        eq += x
        peak = max(peak, eq)
        dd = max(dd, peak - eq)
    return dd


def stats(rs):
    n = len(rs)
    if not n:
        return "n=0"
    return (f"n={n:<4} net={sum(rs):+8.1f}R  "
            f"WR={100.0*sum(1 for x in rs if x>0)/n:>5.1f}%  "
            f"PF={pf(rs):>5.2f}  tm={tm(rs):+.3f}  DD={maxdd(rs):>6.1f}R")


def main():
    from exp_5m_confirm import load_book
    from src.btc.engines.htf_ltf.v18_streak_halt import (
        simulate_htf_ltf_streak_halt as ORIG)

    print("=" * 94)
    print("  P3-C  live_R >= 0 AS A REAL ENGINE GATE")
    print("=" * 94)
    print("  gate is inside the loop; the engine never 'decides to skip'")
    print("  control must reproduce the untouched engine EXACTLY\n")

    mod = build_patched()
    NEW = mod.simulate_htf_ltf_streak_halt

    books = {}
    for scope in ("is", "oos"):
        data, _ = load_book(scope)
        args = (data["c1h"], data["sw10"], data["c15"],
                data["sw15"], data["fine"])
        kw = {"mode": "atr_high"}

        def net(eng):
            rs = [float(t["r_multiple"]) for t in eng["ltf_trades"]
                  if t.get("outcome") != "open"]
            return rs

        o = net(ORIG(*args, **kw))
        n = net(NEW(*args, live_r_floor=None, **kw))
        same = (len(o) == len(n) and
                abs(sum(o) - sum(n)) < 1e-9 and
                all(abs(a - b) < 1e-9 for a, b in zip(o, n)))
        print(f"  [{scope}] IDENTITY GATE  original vs patched(floor=None)")
        print(f"    original : {stats(o)}")
        print(f"    patched  : {stats(n)}")
        print(f"    -> {'IDENTICAL' if same else '*** MISMATCH - VOID ***'}")
        if not same:
            print("    patch changed behaviour; refusing to report arms")
            return
        books[scope] = (data, args, kw, o)
        print()

    # ---- the floor sweep, both eras --------------------------------
    print("=" * 94)
    print("  SWEEP  live_R floor   (None = control)")
    print("=" * 94)
    grid = [None, -0.50, -0.25, -0.10, 0.0, 0.10, 0.25, 0.50, 0.75, 1.00]
    print(f"  {'floor':>8}   {'IS':<44} {'OOS':<44} both?")
    for f in grid:
        cells = []
        nets = {}
        for scope in ("is", "oos"):
            data, args, kw, o = books[scope]
            rs = [float(t["r_multiple"])
                  for t in NEW(*args, live_r_floor=f, **kw)["ltf_trades"]
                  if t.get("outcome") != "open"]
            nets[scope] = sum(rs)
            cells.append(f"n={len(rs):<4} net={sum(rs):+7.1f} "
                         f"WR={100.0*sum(1 for x in rs if x>0)/max(len(rs),1):>4.1f}% "
                         f"PF={pf(rs):>5.2f}")
        di = nets["is"] - sum(books["is"][3])
        do = nets["oos"] - sum(books["oos"][3])
        ok = "YES" if di > 0 and do > 0 else ("no" if di < 0 and do < 0
                                              else "MIXED")
        lab = "None" if f is None else f"{f:+.2f}"
        print(f"  {lab:>8}   {cells[0]:<44} {cells[1]:<44} {ok}")
    print()

    # ---- detail on the survivor, with DD ----------------------------
    print("=" * 94)
    print("  DETAIL  control vs floor=0.0")
    print("=" * 94)
    for scope in ("is", "oos"):
        data, args, kw, o = books[scope]
        rs = [float(t["r_multiple"])
              for t in NEW(*args, live_r_floor=0.0, **kw)["ltf_trades"]
              if t.get("outcome") != "open"]
        print(f"  [{scope}] control  {stats(o)}")
        print(f"  [{scope}] floor0.0 {stats(rs)}")
        print(f"           dNet {sum(rs)-sum(o):+.1f}R   "
              f"trades {len(o)}->{len(rs)} "
              f"({100.0*(len(rs)-len(o))/max(len(o),1):+.0f}%)")
    print()


if __name__ == "__main__":
    main()
