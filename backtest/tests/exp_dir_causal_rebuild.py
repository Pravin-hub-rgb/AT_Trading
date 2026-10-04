"""DIRMATCH, REBUILT PATH-TRUE - is the FAMILY dead, or only its lookahead?

THE QUESTION
    `dirmatch` was closed on 2026-10-04: `exp_require_dir_match` read the swing's
    FINAL direction, which is only final at `confirmed_at_idx` - a median 8 hours
    after the entry bar. That label IS the trade outcome, so it read the answer.
    All nine books that carried it are now `status: "reference"`.

    But that closes the LOOKAHEAD version. It does not answer a different
    question: does direction-matching survive when it is only allowed to use
    information that exists at the entry bar? With `exp_dir_causal=1` the
    selector skips any swing not yet confirmed, so every label it reads was
    knowable when the decision was made. That is a different feature and it has
    never been measured on its own.

THREE ARMS, AND THE CONTROL THAT DECIDES IT
    A  causal dirmatch on a CLEAN base (champion leg). If this adds nothing over
       plain champion, the family is dead outright - the lookahead was the only
       thing it ever had, and rebuilding it on dirmatch's own base is pointless.
    B  causal dirmatch + directional FS, clean base. Does the two stack or does
       one absorb the other?
    C  causal dirmatch + directional FS on the dirmatch base - the rebuild of
       `fsent_dirmatch_long/short` that went to the graveyard.

    A is the one that matters. C only makes sense if A shows something.

READ-ONLY. No engine change, no registry write.
"""
import sys, json, time, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend", ""):
    sys.path.insert(0, str(ROOT / p) if p else str(ROOT))

import run_experiment as re_
import exp_equity_quality as EQ
from src.btc.btc_routes import _trade_costs
import experiment_registry as reg

OUT = ROOT / "backtest" / "tests" / "_dir_causal_rebuild.json"

ARMS = [
    # name, base book, extra params
    ("A0 champion control", "champion_multi_sw10_leg", {}),
    ("A1 champion + causal dirmatch", "champion_multi_sw10_leg",
     {"exp_require_dir_match": 1, "exp_dir_causal": 1}),
    ("A2 champion + FS long", "champion_multi_sw10_leg", {"exp_fs_entry_side": "long"}),
    ("A3 champion + FS long + causal dirmatch", "champion_multi_sw10_leg",
     {"exp_fs_entry_side": "long", "exp_require_dir_match": 1, "exp_dir_causal": 1}),
    ("A4 champion + FS short", "champion_multi_sw10_leg", {"exp_fs_entry_side": "short"}),
    ("A5 champion + FS short + causal dirmatch", "champion_multi_sw10_leg",
     {"exp_fs_entry_side": "short", "exp_require_dir_match": 1, "exp_dir_causal": 1}),
    ("C0 dirmatch base control", "dirmatch_multi_sw10", {"exp_dir_causal": 1}),
    ("C1 dirmatch base + causal dirmatch", "dirmatch_multi_sw10",
     {"exp_require_dir_match": 1, "exp_dir_causal": 1}),
    ("C2 dirmatch base + FS long + causal dirmatch", "dirmatch_multi_sw10",
     {"exp_fs_entry_side": "long", "exp_require_dir_match": 1, "exp_dir_causal": 1}),
    ("C3 dirmatch base + FS short + causal dirmatch", "dirmatch_multi_sw10",
     {"exp_fs_entry_side": "short", "exp_require_dir_match": 1, "exp_dir_causal": 1}),
]


def run(scope, key, extra):
    cfg = reg.EXPERIMENTS[key]
    d = EQ.load_scope(scope)
    sim = re_.build_module()
    o = dict(re_.BP)
    o.update(cfg["params"])
    o.update(extra)
    sw = d["sw10"] if cfg["swing"] == "sw10" else d["sw20"]
    fine = d["fine"] if cfg.get("basis", "fine") == "fine" else []
    tr = sim(d["c1h"], sw, d["c15"], d["sw15"], fine_ltf=fine, **o)["ltf_trades"]
    _trade_costs(tr, 0.055, 2, 0.005, 0.01, 0.01)
    tr = [t for t in tr if t.get("outcome") != "open"]
    rs = [float(t.get("r_multiple", 0.0)) - float(t.get("cost_r", 0.0)) for t in tr]
    eq = pk = dd = 0.0
    for r in rs:
        eq += r
        pk = max(pk, eq)
        dd = max(dd, pk - eq)
    gp = sum(r for r in rs if r > 0)
    ll = -sum(r for r in rs if r < 0)
    return {"n": len(tr), "net": round(eq, 2), "dd": round(dd, 2),
            "per": round(eq / max(len(tr), 1), 3),
            "wr": round(100.0 * sum(1 for r in rs if r > 0) / max(len(tr), 1), 1),
            "pf": round(gp / ll, 2) if ll > 0 else 0.0}
def main():
    res = {}
    print("=" * 104)
    print("DIRMATCH REBUILT PATH-TRUE. exp_dir_causal=1 on every arm that uses direction-match.")
    print("A = clean base (does causal dir-match earn anything?)   C = the graveyard rebuild")
    print("=" * 104)
    print("%-46s | %-31s | %-31s" % ("arm", "IS  n / net / DD / WR", "OOS  n / net / DD / WR"))
    print("-" * 104)
    base_a = {}
    for name, key, extra in ARMS:
        a = run("is", key, extra)
        b = run("oos", key, extra)
        res[name] = {"is": a, "oos": b, "base": key}
        if name.startswith("A") and "control" in name:
            base_a["is"] = a
            base_a["oos"] = b
            d = ""
        elif name.startswith("A"):
            d = "  dIS %+.1f  dOOS %+.1f" % (
                a["net"] - base_a["is"]["net"], b["net"] - base_a["oos"]["net"])
        elif name.startswith("C0"):
            d = "  (C control)"
        else:
            d = "  dIS %+.1f  dOOS %+.1f" % (
                a["net"] - res["C0 dirmatch base control"]["is"]["net"],
                b["net"] - res["C0 dirmatch base control"]["oos"]["net"])
        print("%-46s | %4d /%+8.1f /%6.1f /%4.1f%% | %4d /%+8.1f /%6.1f /%4.1f%%%s"
              % (name, a["n"], a["net"], a["dd"], a["wr"],
                 b["n"], b["net"], b["dd"], b["wr"], d))
    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("\nwrote %s" % OUT)


if __name__ == "__main__":
    main()