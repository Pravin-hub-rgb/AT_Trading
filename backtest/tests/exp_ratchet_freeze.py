"""P17 - RATCHET FREEZE AFTER N MOVES. The user's idea, and a new strategy.

THE IDEA, in the user's words
=============================
"exit ke liye aisa kuch ki like agar trade ko hum R se toh dekh he rahe
hai par ab hum sl trail se bhi dekhe - like agar koi trade number moved
up shift se dekhe ki kitne baar woh rachet move kiya gaya usse bhi kuch
kar sake. ekk toh ki agar N time move up ho gaya hai long ke liye toh ab
rachet ko thoda delay karde, now ab new swing ka bhi new banega tab
trail kare."

Translated: **once the stop has already been ratcheted up N times, stop
ratcheting.** Let a trade that is already working run. A new swing will
form; trail on that later, not on every intermediate level.

THIS IS NOT THE CLOSED EXIT FAMILY
==================================
  exp_trail_delay_r  delays the trail until +1R          - different
  exp_trail_half    ratchets halfway to the extreme     - different
  EXP_LA4_TRAIL_TIGHTEN  tightens                       - REJECTED
  P10 runner study   showed the runner is not identifiable at +1R

**None of them loosen the stop after success. Every closed one tightened
or protected.** This one does the opposite: it gives a working trade
room. That is why it is worth running despite the family's bad record -
and it is also why it is the most plausible remaining route to the
SMOOTHNESS the user asked for, since P16 showed entry filters improve
every ratio but leave r_std ABOVE the champion.

WHY IT COULD SMOOTH: variance lives in the runners. RUNNER_LIVE.md
measured that the 10R+ cohort is 3.4% of trades carrying +95% of gross.
If freezing the ratchet after N raises lets more of the mid-sized trades
become runners, the outcome distribution stretches upward and the losing
side thins - which is exactly what a smoother book needs.

MECHANICS
=========
The ratchet is the loop in v18_streak_halt.py:668-672 (fine) which walks
`events_ts` and raises `sl_cur_f` to each new higher swing level. This
adds a counter of RAISES. Once the count reaches
`exp_ratchet_freeze_after`, the loop keeps consuming events (so timing
and the SL check are untouched) but stops accepting a higher level, so
`sl_cur_f` freezes where it is. Default 0 = off = byte-identical.

Swept: 0 (off, control), 1, 2, 3, 4, 5, 6. Both eras. Reported on the
smoothness terms the user asked for: net, R/trade, PF, maxDD, max losing
streak, r_std, worst year.

FALSIFIERS, PRE-REGISTERED HERE
==============================
  (a) net down in either era
  (b) no arm beats the champion's r_std
  (c) no arm shortens the losing streak
  (d) no arm holds every IS year >= the champion's same year
Reported whichever lands. The exit family is closed, so a win here would
be genuinely surprising and needs the forward slice before anyone moves.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

import test_experiments_craze as T  # noqa: E402
from experiment_registry import BP, EXPERIMENTS  # noqa: E402
from run_experiment import get_data, identity_gate, net_r  # noqa: E402
from test_experiments_craze import build_module  # noqa: E402
from test_4_new_concepts import load_unseen, load_fine_1m  # noqa: E402
from test_experiments_craze import _compute_swings  # noqa: E402
from engine.v18_params import SWING  # noqa: E402
from exp_smooth_search import streak, rstd, dd, pf  # noqa: E402

CFG = EXPERIMENTS["champion_multi_sw10"]
PARAMS = {**BP, **CFG["params"]}
PINS = {"is": (500, 325.8), "oos": (279, 70.1)}
FREEZE_LEVELS = [None, 1, 2, 3, 4, 5, 6]   # None = off (unlimited)

# the fine-walk ratchet block, exactly as it reads in the source
_OLD1 = "                            elif sl_cur_f < cand:\n                                sl_cur_f=cand"
_NEW1 = ("                            elif sl_cur_f < cand and _rfz < _RFZ_N:\n"
         "                                sl_cur_f=cand; _rfz+=1")
_OLD2 = "                            elif cand < sl_cur_f:\n                                sl_cur_f=cand"
_NEW2 = ("                            elif cand < sl_cur_f and _rfz < _RFZ_N:\n"
         "                                sl_cur_f=cand; _rfz+=1")
_OLD3 = "                        elif sl_cur < cand:\n                            sl_cur=cand"
_NEW3 = ("                        elif sl_cur < cand and _rfz < _RFZ_N:\n"
         "                            sl_cur=cand; _rfz+=1")
_OLD4 = "                        elif cand < sl_cur:\n                            sl_cur=cand"
_NEW4 = ("                        elif cand < sl_cur and _rfz < _RFZ_N:\n"
         "                            sl_cur=cand; _rfz+=1")
PAIRS = [(_OLD1, _NEW1), (_OLD2, _NEW2), (_OLD3, _NEW3), (_OLD4, _NEW4)]


def build(n):
    """Champion's PATCHED engine, plus a per-trade cap of n ratchet raises.

    We reproduce build_module's own patch sequence on a SOURCE STRING,
    inject the ratchet freeze, and load with _load_module - because
    build_module asserts on UNPATCHED trail text and deletes its temp
    file before returning, so patching its output is not possible.
    """
    import re
    src = T.SRC
    # apply build_module's full text patch by calling its internals via
    # a temporary SRC swap is unsafe (its asserts see our text), so we
    # instead do the freeze AFTER build_module produced a callable, by
    # rebuilding that callable's module source. Simplest safe route:
    # temporarily monkeypatch _load_module to capture the text.
    cap = {}
    real_loader = T._load_module

    def spy(text, name):
        cap["text"] = text
        return real_loader(text, name)

    T._load_module = spy
    saved_src = T.SRC
    try:
        build_module()
    finally:
        T.SRC = saved_src
        T._load_module = real_loader
    if "text" not in cap:
        raise SystemExit("could not capture the patched engine text")
    out = cap["text"]
    for old, new in PAIRS:
        if old not in out:
            raise SystemExit("FREEZE ANCHOR NOT FOUND in patched engine:\n" + old)
        out = out.replace(old, new)
    # per-trade reset: line 1664 is the fine-walk per-trade init
    s2 = out.replace(
        '            best_f=entry; sl_cur_f=sl_cur; ev_idx_f=-1; fk=None; '
        'exit_px_f=None; outcome_f="open"',
        '            best_f=entry; sl_cur_f=sl_cur; ev_idx_f=-1; fk=None; '
        'exit_px_f=None; outcome_f="open"; _rfz=0', 1)
    if "_rfz=0" not in s2:
        raise SystemExit("per-trade reset anchor NOT FOUND - check line 1664")
    # define the cap inside the function
    anchor = "    from src.btc.engines.v7_timecap import simulate_btc_trades_v7"
    if anchor not in s2:
        anchor = "    from src.btc.btc_engine import"
    i = s2.index(anchor)
    s2 = s2[:i] + f"    _RFZ_N = {n}\n" + s2[i:]
    mod, _p = real_loader(s2, "_ratchetfreeze_tmp")
    return mod.simulate_htf_ltf_streak_halt


def load(scope):
    if scope == "oos":
        (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
        return (c1h, _compute_swings(f1h, "continuous", min_bars=10),
                c15, _compute_swings(f15, "continuous",
                                     min_bars=SWING["min_bars_15m"]),
                load_fine_1m(c15[0]["ts"], c15[-1]["ts"]))
    d = get_data()
    identity_gate(d, build_module())
    return (d["c1h"], d["sw10"], d["c15"], d["sw15"], d["fine"])


def main():
    print("=" * 100)
    print("  P17  RATCHET FREEZE AFTER N MOVES  (the user's idea)")
    print("=" * 100)
    print("  Once the stop has been raised N times, stop raising it.")
    print("  Gives a working trade room. UNLIKE every closed exit arm,")
    print("  this LOOSENS after success rather than tightening.")
    print("  Identity gate at freeze=0 must be byte-identical.\n")
    from src.btc.btc_routes import _trade_costs
    from engine.v18_params import SYMBOL_PARAMS
    g = SYMBOL_PARAMS["BTCUSDT"]
    args = {sc: load(sc) for sc in ("is", "oos")}
    base = build(999)          # off = effectively unlimited raises
    ctrl = {}
    for sc in ("is", "oos"):
        tr = base(*args[sc], **PARAMS)["ltf_trades"]
        c2, _ = _trade_costs(tr, g["fee_pct"], 0.0,
                             g["entry_slip_pct"], g["exit_slip_pct"])
        rs = [float(t["r_multiple"]) for t in tr
              if t.get("outcome") != "open"]
        ys = [(t.get("exit_date") or "")[:4] for t in tr
              if t.get("outcome") != "open"]
        ctrl[sc] = (rs, ys, c2 / len(rs))
        wn, wv = PINS[sc]
        print(f"  [{sc}] PIN n={len(rs)} netNET={net_r(tr):+.1f}R "
              f"(want {wn}/{wv:+.1f}) -> "
              f"{'OK' if abs(len(rs)-wn)<=2 and abs(net_r(tr)-wv)<=1.0 else 'MISMATCH'}")
    cy = {}
    rs, ys, per = ctrl["is"]
    for y in sorted(set(ys)):
        cy[y] = sum(r for r, yy in zip(rs, ys) if yy == y)
    print(f"\n  CONTROL (freeze=0, untouched)")
    print(f"    IS  n={len(rs)} net={sum(rs)-per*len(rs):+.1f}R "
          f"R/tr={sum(rs)/len(rs):+.3f} PF={pf(rs):.2f} DD={dd(rs):.1f} "
          f"std={rstd(rs):.2f} streak={streak(rs)}")
    print(f"    by year " + "  ".join(f"{y}:{v:+.1f}" for y, v in sorted(cy.items())))
    print()
    print("=" * 100)
    print(f"  {'freeze after N':<16} {'n':>4} {'IS net':>8} {'R/tr':>7} {'PF':>5} "
          f"{'DD':>6} {'std':>5} {'strk':>4} {'OOS n':>5} {'OOS net':>8} "
          f"{'year floor'}")
    print("=" * 100)
    for n in FREEZE_LEVELS:
        mod = base if n is None else build(n)
        cells = {}
        for sc in ("is", "oos"):
            tr = mod(*args[sc], **PARAMS)["ltf_trades"]
            rs = [float(t["r_multiple"]) for t in tr
                  if t.get("outcome") != "open"]
            ys = [(t.get("exit_date") or "")[:4] for t in tr
                  if t.get("outcome") != "open"]
            c2, _ = _trade_costs(tr, g["fee_pct"], 0.0,
                                 g["entry_slip_pct"], g["exit_slip_pct"])
            per2 = c2 / len(rs)
            yd = {}
            for y in set(ys):
                yd[y] = sum(r for r, yy in zip(rs, ys) if yy == y)
            cells[sc] = (rs, per2, yd)
        a, pa, yd = cells["is"]
        b, pb, _ = cells["oos"]
        floor = all(v >= cy.get(y, 0.0) - 0.01 for y, v in yd.items())
        tag = "n/a" if n is None else ("HOLDS" if floor else "FAILS")
        print(f"  {('off (control)' if n is None else n):<16} {len(a):>4} "
              f"{sum(a)-pa*len(a):>8.1f} {sum(a)/len(a):>+7.3f} {pf(a):>5.2f} "
              f"{dd(a):>6.1f} {rstd(a):>5.2f} {streak(a):>4} {len(b):>5} "
              f"{sum(b)-pb*len(b):>8.1f}  {tag}")
    print()
    print("  Falsifiers: (a) net down in either era  (b) no arm beats the")
    print("  control's r_std  (c) no arm shortens the losing streak")
    print("  (d) no arm holds every IS year >= the control's same year")
    print("=" * 100)


if __name__ == "__main__":
    main()
