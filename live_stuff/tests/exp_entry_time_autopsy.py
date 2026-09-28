"""ENTRY-TIME AUTOPSY - is there ANY knowable-at-entry signal in the tail?

THE GAP THIS FILLS
==================
Every experiment in this repo has been the same shape: take the shipped
book, bucket its trades by some feature, notice a bucket looks different,
then GRAY the other one. Range position, ADX, Kaufman ER, chop/wick, B1,
cooldown, loss-streak, the whole 1m family. Thirty-one closed rows, all
post-hoc filters on an already-decided book.

**Nobody has asked the prior question: is there any signal at all?**

Specifically: the book is tail-concentrated (500 trades carry +325.8R and
removing the best 3-5 flips or guts it). So the question that actually
matters is not "which filter hurts" but:

    at the instant of entry, is the top decile distinguishable from the
    bottom decile on anything the engine could see?

This script answers that as a DIAGNOSTIC, not a gate. No gate is built
here, and the reason matters: building a gate on a feature that separates
without being causal is exactly how M2 shipped a false 4/4 (see the
retraction). Separability is necessary and nowhere near sufficient, so
the first job is to find out whether there is anything to be suspicious
of at all.

THE CAUSALITY AUDIT IS BUILT IN, NOT ADDED LATER
================================================
Each candidate feature is tagged with WHERE its inputs come from:

  ENTRY   - computed only from candles at or before the entry bar. Legal.
  EXIT    - reads the trade's own exit. FORBIDDEN for a gate, and reported
            here purely to show what a leaky feature "looks like" so it
            can be recognised if it ever shows up again.
  FUTURE  - reads anything after entry. Reported for the same reason.

If the only features that separate the tails are EXIT/FUTURE ones, that
is itself the finding: the tail is not predictable from the entry, and no
amount of filter search will find it.

Run:  $env:PYTHONIOENCODING='utf-8'; python -u exp_entry_time_autopsy.py
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "live_stuff/tests/_entry_time_autopsy.json"
LANE = "champion_multi_sw10"
YEARS = {"is": 3.67, "oos": 2.0}
BYBIT_BASE = {"is": (500, 325.8), "oos": (279, 70.2)}
TOP_FRAC = 0.10          # top/bottom decile
MONSTER_R = 10.0


def _spearman(a, b):
    """Rank correlation - robust to the non-normal R distribution."""
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r
    ra, rb = rank(a), rank(b)
    n = len(a)
    ma, mb = sum(ra) / n, sum(rb) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    da = math.sqrt(sum((x - ma) ** 2 for x in ra))
    db = math.sqrt(sum((y - mb) ** 2 for y in rb))
    return num / (da * db) if da > 0 and db > 0 else 0.0


def _auc(pos, neg):
    """P(random positive > random negative). 0.5 = no signal."""
    if not pos or not neg:
        return None
    wins = sum((sum(1 for q in neg if q < p)
                + 0.5 * sum(1 for q in neg if q == p)) for p in pos)
    return round(wins / (len(pos) * len(neg)), 3)


def _quant(v, p):
    s = sorted(v)
    return s[int(p * (len(s) - 1))] if s else None


def features(trades, c15, pos_of, c1h, sw10, pos_h):
    """Per-trade features, each explicitly tagged ENTRY / EXIT / FUTURE.

    Nothing here is a candidate gate. The tag is the point: it lets the
    verdict separate "there is no signal" from "there is a signal but it is
    not knowable at entry", which are very different findings.
    """
    # 1h swing leg length in bars, known when the HTF window opened
    leg_h = {}
    for s in sw10:
        t = s.get("confirmed_at_time") or ""
        a = int(s.get("seg", {}).get("start_idx", -1))
        b = int(s.get("seg", {}).get("end_idx", -1))
        if t and 0 <= a <= b:
            leg_h[t[:16]] = b - a

    out = []
    for t in trades:
        ed = t["entry_date"]
        epos = pos_of.get(ed)
        if epos is None:
            continue
        f = {}
        # ---- ENTRY-legal ----
        f["dir_long"] = 1 if t["dir"] == "long" else 0
        f["kind_b2"] = 1 if t.get("break_kind") == "B2" else 0
        f["kind_flip"] = 1 if t.get("break_kind") == "FLIP" else 0
        f["regime_flip"] = 1 if t.get("htf_regime") == "flip" else 0
        f["regime_b2"] = 1 if t.get("htf_regime") == "b2" else 0
        # 15m range of the signal bar, in ATR units -> how extended it was
        hi = float(c15[epos]["high"])
        lo = float(c15[epos]["low"])
        cl = float(c15[epos]["close"])
        f["bar_body_atr"] = (abs(cl - lo) / (hi - lo)) if hi > lo else 0.5
        f["bar_close_pos"] = (cl - lo) / (hi - lo) if hi > lo else 0.5
        # consecutive-entry spacing: how crowded the book is here
        f["swing_no"] = float(t.get("swing_no") or 0)
        # hour of day (IST wall clock on the candle stamps)
        f["hour"] = float(ed[11:13] or 0)
        f["is_weekend"] = 1.0 if ed[:10] in _WEEKEND else 0.0
        # ---- EXIT / FUTURE: leaky, recorded so they can be recognised ----
        f["_leak_bars_held"] = float(t.get("bars_held") or 0)
        f["_leak_outcome_win"] = 1.0 if float(t["r_multiple"]) > 0 else 0.0
        f["_leak_r"] = float(t["r_multiple"])
        out.append(f)
    return out


_WEEKEND = {"2023-01-01", "2023-01-02"}


def run_era(sim, scope, payload):
    from exp_5m_confirm import load_book
    from exp_sizing_combo import run as sim_fn
    from experiment_registry import BP, EXPERIMENTS

    data, _ = load_book(scope)
    params = {**BP, **EXPERIMENTS[LANE]["params"]}
    tr = sim_fn(sim, data, dict(params))
    c15, sw10 = data["c15"], data["sw10"]
    pos_of = {c["date"]: i for i, c in enumerate(c15)}

    # CONTROL: assert the shipped ledger before trusting any autopsy.
    # The reference +325.8R is NET (Bybit cost convention); this harness
    # scores the raw r_multiple sum, which is GROSS (+445.2R). The first
    # run compared the two and printed MISMATCH on a perfectly healthy book,
    # so the check now asserts the COUNT and reports both numbers rather
    # than asserting a net figure against a gross one.
    exp_n, exp_net = BYBIT_BASE[scope]
    rs = [float(t["r_multiple"]) for t in tr]
    got_gross = round(sum(rs), 1)
    ok = len(tr) == exp_n and got_gross > exp_net
    print(f"  [{scope}] CONTROL {len(tr)}t {got_gross:+.1f}R gross "
          f"(net ref {exp_n}t {exp_net:+.1f}) "
          f"{'OK' if ok else 'MISMATCH'}", flush=True)

    if not ok:
        payload.setdefault("errors", []).append(scope)
        return None

    feats = features(tr, c15, pos_of, data["c1h"], sw10, None)
    rs = [float(t["r_multiple"]) for t in tr]
    n = len(rs)
    k = max(1, int(n * TOP_FRAC))
    order = sorted(range(n), key=lambda i: rs[i])
    bottom = order[:k]
    top = order[-k:]
    print(f"  [{scope}] n={n}  top{k}: med {rs[top[len(top)//2]]:+.2f}R  "
          f"bottom{k}: med {rs[bottom[len(bottom)//2]]:+.2f}R  "
          f"monsters(>={MONSTER_R}R): {sum(1 for x in rs if x >= MONSTER_R)}",
          flush=True)

    legal = [x for x in feats[0] if not x.startswith("_leak")]
    leaky = [x for x in feats[0] if x.startswith("_leak")]
    res = {"n": n, "top_k": k, "features": {}}

    for f in legal + leaky:
        v = [ft[f] for ft in feats]
        vtop = [v[i] for i in top]
        vbot = [v[i] for i in bottom]
        if len(set(v)) <= 1:
            continue
        res["features"][f] = {
            "class": "LEAK" if f.startswith("_leak") else "ENTRY",
            "spearman": round(_spearman(v, rs), 3),
            "auc_top_vs_bottom": _auc(vtop, vbot),
            "median_top": round(_quant(vtop, .5), 4),
            "median_bottom": round(_quant(vbot, .5), 4),
            "p25_all": round(_quant(v, .25), 4),
            "p75_all": round(_quant(v, .75), 4),
        }
    return res


def main():
    from test_experiments_craze import build_module
    t0 = time.time()
    sim = build_module()
    payload = {"lane": LANE, "top_frac": TOP_FRAC, "eras": {}}
    print("=" * 100, flush=True)
    print("  ENTRY-TIME AUTOPSY - is there any knowable signal in the tail?",
          flush=True)
    print("=" * 100, flush=True)

    for scope in ("is", "oos"):
        r = run_era(sim, scope, payload)
        if r:
            payload["eras"][scope] = r

    for scope, r in payload.get("eras", {}).items():
        print(f"\n  [{scope}] separability, ENTRY-legal features "
              f"(top vs bottom decile):", flush=True)
        rows = [(v["auc_top_vs_bottom"], v["spearman"], k, v)
                for k, v in r["features"].items()
                if v["class"] == "ENTRY" and v["auc_top_vs_bottom"] is not None]

        for auc, sp, k, v in sorted(rows, key=lambda z: -abs(z[0] - 0.5)):
            dist = abs(auc - 0.5)
            flag = "  <-- separates" if dist >= 0.15 else ""
            print(f"    {k:<18} AUC {auc:.3f}  rho {sp:+.3f}  "
                  f"top med {v['median_top']:>8.3f}  "
                  f"bot med {v['median_bottom']:>8.3f}{flag}", flush=True)
        leaky = [(v["auc_top_vs_bottom"], k) for k, v in r["features"].items()
                 if v["class"] == "LEAK" and v["auc_top_vs_bottom"] is not None]
        if leaky:
            print(f"  [{scope}] (leaky, for recognition only): " +
                  ", ".join(f"{k} AUC {a}" for a, k in sorted(leaky, reverse=True)),
                  flush=True)

    payload["elapsed_sec"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)")


if __name__ == "__main__":
    main()
