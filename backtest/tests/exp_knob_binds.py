"""exp_knob_binds - which knobs on a book actually do anything?

METHOD
======
For each parameter, drive it to a value that is OBVIOUSLY not what it is - not a
neighbour, a different world - and compare the resulting trade list to the base,
field by field. A knob that leaves the trade list byte-identical is not
"insensitive", it is INERT: the engine never reads it on this configuration. A
knob that changes the list binds, and the size of the change says how much it
carries.

This is the test that catches a knob nobody suspects, and it is the reason
ext_stop_r turned out to be dead only after C17 rather than before it: the knob
was live, and the gate underneath it moved.

READ IT WITH
============
  INERT   -> safe to remove from this book's config (verify pins first)
  BINDS   -> keep, and the delta column is its weight in the book

Run:  cd backtest/tests
      python -u exp_knob_binds.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

BOOK = "fsent_champ_long"

# knob -> (label, a value that cannot mean what the book has)
PROBES = {
    "chop_thresh": ("0.0 (never read under mode=atr_high)", 0.0),
    "atr_low_thresh": ("0.99 (only used by the atr_low family)", 0.99),
    "atr_high_thresh": ("0.0 (routing flips to decisive everywhere)", 0.0),
    "sl_buf_atr": ("0.0 (no ATR buffer on the stop)", 0.0),
    "cooldown_bars": ("0 (no post-loss cooldown)", 0),
    "max_consecutive_losses": ("0 (no streak halt)", 0),
    "ext_stop_r": ("1.5 (BP default, a live filter)", 1.5),
    "exp_partial_r": ("1.0 (take half at 1R)", 1.0),
    "exp_mltf": ("False (multi-timeframe gate off)", False),
    "exp_persist": ("0 (no regime hysteresis)", 0),
    "window_end": ("r_touch (window closes at 1.5R)", "r_touch"),
    "pivot_rule": ("origin (lookahead pivot)", "origin"),
    "exp_fs_entry_side": ("empty (both sides back on break)", ""),
    "htf_rr": ("2.0 (1h target half)", 2.0),
    "exp_cap_days": ("4 (1h window capped at 4 days)", 4),
    "sl_mode": ("pct (percent stop instead of swing stop)", "pct"),
}

FIELDS = ("entry_ts", "dir", "entry_price", "sl", "exit_ts", "exit_price",
          "outcome", "r_multiple")


def sig(trades):
    return {tuple(t.get(f) for f in FIELDS) for t in trades}


def main() -> int:
    from exp_tf_family import build_family_module
    from run_experiment import BP, net_r, get_swings
    from exp_multi_metrics import load_era
    from exp_full_metrics import compute
    from experiment_registry import EXPERIMENTS

    sim = build_family_module()
    cfg = EXPERIMENTS[BOOK]
    base = {**BP, **cfg["params"]}
    base.setdefault("exp_partial_r", 0.0)

    data, sw = {}, {}
    for era in ("is", "oos"):
        data[era] = load_era(era)
        sw[era] = get_swings(data[era], cfg.get("swing") or "sw10")

    def run(era, params):
        out = sim(data[era]["c1h"], sw[era], data[era]["c15"], data[era]["sw15"],
                  fine_ltf=data[era]["fine"], **params)
        tr = [t for t in out["ltf_trades"] if t.get("outcome") != "open"]
        m = compute([net_r([t]) for t in tr], [t.get("entry_date", "") for t in tr])
        return tr, m

    print("=" * 100)
    print("KNOB BINDS AUDIT - %s" % BOOK)
    print("=" * 100)
    print("base config:")
    for k, v in sorted(cfg["params"].items()):
        print("    %-22s %s" % (k, v))
    print()

    base_sig, base_m = {}, {}
    for era in ("is", "oos"):
        tr, m = run(era, base)
        base_sig[era], base_m[era] = sig(tr), m

    # Probe the EFFECTIVE config (BP + book params), not just the book's own
    # params - htf_rr, exp_cap_days and sl_mode live in BP and bind every bit as
    # much as anything the book names.
    rows = []
    for knob, (label, alt) in sorted(PROBES.items()):
        if knob not in base:
            rows.append((knob, label, "NO SUCH PARAM", None, None, None, None))
            continue
        p = dict(base)
        p[knob] = alt
        got = {}
        err = None
        try:
            for era in ("is", "oos"):
                tr, m = run(era, p)
                got[era] = (sig(tr), m)
        except Exception as e:
            err = repr(e)[:70]
        if err:
            rows.append((knob, label, "ERROR", None, None, err, None))
            continue
        inert = all(got[e][0] == base_sig[e] for e in ("is", "oos"))
        dn = {e: got[e][1]["n"] - base_m[e]["n"] for e in ("is", "oos")}
        dnet = {e: got[e][1]["net"] - base_m[e]["net"] for e in ("is", "oos")}
        rows.append((knob, label, "INERT" if inert else "BINDS",
                     dn, dnet, None, alt))

    print("%-22s %-44s %-6s %14s %14s" % ("knob", "probe value", "verdict",
                                           "d n (IS/OOS)", "d net (IS/OOS)"))
    for knob, label, verdict, dn, dnet, err, alt in rows:
        if dn is None:
            # NO SUCH PARAM or ERROR - neither carries deltas. Testing `err`
            # alone sent "NO SUCH PARAM" down the else branch into dn["is"].
            print("%-22s %-44s %-12s %s" % (knob, label, verdict,
                                             err or "not in the effective config"))
        elif verdict == "INERT":
            print("%-22s %-44s %-6s %14s %14s" % (knob, label, verdict, "-", "-"))
        else:
            print("%-22s %-44s %-6s %14s %14s"
                  % (knob, label, verdict,
                     "%+d / %+d" % (dn["is"], dn["oos"]),
                     "%+.1f / %+.1f" % (dnet["is"], dnet["oos"])))
    inert = [r[0] for r in rows if r[2] == "INERT"]
    binds = [r[0] for r in rows if r[2] == "BINDS"]
    other = [(r[0], r[2]) for r in rows if r[2] not in ("INERT", "BINDS")]
    print()
    print("INERT (%d): %s" % (len(inert), ", ".join(inert) or "none"))
    print("BINDS (%d): %s" % (len(binds), ", ".join(binds) or "none"))
    if other:
        print("OTHER (%d): %s" % (len(other), ", ".join("%s=%s" % o for o in other)))
    print()
    print("INERT is not yet DEAD. Three reasons a knob can be inert here and live")
    print("elsewhere, and they need different answers:")
    print("  mode-gated   - the engine reads it only under another mode. Removing it")
    print("                  changes nothing until someone changes `mode`.")
    print("  knob-gated   - inert only because ANOTHER knob is set a certain way.")
    print("                  exp_mltf looks dead and is not: at max_positions=0 it")
    print("                  matches False exactly, at max_positions=1 it moves n")
    print("                  from 528 to 355. Calling that dead would be a lie.")
    print("  value-collapsed - it is set to a value the surrounding gates already")
    print("                  enforce, so it cannot bind at this operating point.")
    print()
    print("OMITTING A KEY IS NOT THE SAME AS TURNING IT OFF. BP supplies defaults,")
    print("so a deleted field inherits them. Write the value you mean. For this book")
    print("that matters for ext_stop_r (BP is 1.5, a live filter) and it is safer in")
    print("general to keep an inert value written out explicitly than to let it drift")
    print("with BP.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
