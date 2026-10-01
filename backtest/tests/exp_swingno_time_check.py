"""FOLLOW-UP: is `swing_no` a signal, or just a proxy for calendar time?

WHY THIS FILE IS URGENT
=======================
`exp_entry_time_autopsy.py` found exactly ONE entry-legal feature that
separates the top decile from the bottom decile in BOTH eras:

    swing_no    AUC 0.831 (IS)   AUC 0.918 (OOS)

That is the kind of number that ends careers. It is also exactly the shape
of result that produced the M2 false 4/4: a feature that separates, that
is legal at entry, and that nobody has asked *what it actually measures*.

`signing_no` is a CHAIN INDEX. It rises monotonically with calendar time.
So before it can be called a signal, one question has to die first:

    is the effect "later swings are better", or is it "the later part of
    the dataset was a better market"?

These are not the same claim and they have opposite consequences. The
first is a (weak, exotic) feature. The second is a calendar-window
artefact: a gate on it would be a disguised "trade only after <date>",
which cannot be deployed because nobody knows at the start of a sample
which half will be good.

THE TEST
========
Bucket the book by CALENDAR position (decile of the era), independently of
swing_no, and compare the two profiles:

  * if the calendar profile explains the swing_no profile  -> ARTEFACT
  * if swing_no separates WITHIN a calendar bucket       -> real signal

Also reported: the rank correlation of swing_no with wall-clock index. A
value near 1.0 means the feature IS time, whatever the AUC says.

Run:  $env:PYTHONIOENCODING='utf-8'; python -u exp_swingno_time_check.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "backtest/tests/_swingno_time_check.json"
LANE = "champion_multi_sw10"
YEARS = {"is": 3.67, "oos": 2.0}
BYBIT_BASE = {"is": (500, 325.8), "oos": (279, 70.2)}


def _spearman(a, b):
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
    da = sum((x - ma) ** 2 for x in ra) ** 0.5
    db = sum((y - mb) ** 2 for y in rb) ** 0.5
    return num / (da * db) if da > 0 and db > 0 else 0.0


def _auc(pos, neg):
    if not pos or not neg:
        return None
    w = sum(sum(1 for q in neg if q < p) + 0.5 * sum(1 for q in neg if q == p)
            for p in pos)
    return round(w / (len(pos) * len(neg)), 3)


def _med(v):
    s = sorted(v)
    return round(s[len(s) // 2], 2) if s else None


def main():
    from test_experiments_craze import build_module
    from exp_5m_confirm import load_book
    from exp_sizing_combo import run as sim_fn
    from experiment_registry import BP, EXPERIMENTS

    t0 = time.time()
    sim = build_module()
    payload = {"lane": LANE, "eras": {}}
    print("=" * 100, flush=True)
    print("  IS swing_no A SIGNAL, OR A PROXY FOR CALENDAR TIME?", flush=True)
    print("=" * 100, flush=True)

    for scope in ("is", "oos"):
        data, _ = load_book(scope)
        params = {**BP, **EXPERIMENTS[LANE]["params"]}
        tr = sim_fn(sim, data, dict(params))
        exp_n, exp_net = BYBIT_BASE[scope]
        rs = [float(t["r_multiple"]) for t in tr]
        if len(tr) != exp_n:
            print(f"  [{scope}] CONTROL MISMATCH {len(tr)}t vs {exp_n}", flush=True)
            continue
        print(f"\n  [{scope}] {len(tr)}t, gross {sum(rs):+.1f}R "
              f"(net ref {exp_net:+.1f})", flush=True)

        sno = [float(t.get("swing_no") or 0) for t in tr]
        tix = list(range(len(tr)))          # wall-clock position in the book
        rho = _spearman(sno, tix)
        print(f"    corr(swing_no, calendar index) = {rho:+.3f}"
              f"   {'<-- swing_no IS time' if rho > 0.9 else ''}", flush=True)

        # calendar deciles
        n = len(tr)
        dec = [min(9, int(i / n * 10)) for i in tix]
        print("    net R by calendar decile of the era:", flush=True)
        prof = []
        for d in range(10):
            v = [rs[i] for i in range(n) if dec[i] == d]
            sn = [sno[i] for i in range(n) if dec[i] == d]
            prof.append(_med(v))
            print(f"      dec{d}  n={len(v):>3}  medR {_med(v):>7}  "
                  f"med swing_no {_med(sn):>8.0f}", flush=True)

        # does swing_no separate WITHIN a calendar bucket?
        print("    within-decile: AUC of swing_no, top-third vs bottom-third "
              "of R, in the 2nd and 8th calendar deciles:", flush=True)
        within = {}
        for d in (2, 8):
            idxs = [i for i in range(n) if dec[i] == d]
            if len(idxs) < 30:
                continue
            sub = sorted(idxs, key=lambda i: rs[i])
            k = max(1, len(sub) // 3)
            lo, hi = sub[:k], sub[-k:]
            a = _auc([sno[i] for i in hi], [sno[i] for i in lo])
            within[f"dec{d}"] = {"n": len(idxs), "auc_swing_no": a}
            print(f"      dec{d}: n={len(idxs)}  AUC {a}", flush=True)
        payload["eras"][scope] = {
            "n": n, "corr_swing_no_calendar": round(rho, 3),
            "calendar_decile_median_r": prof, "within_decile_auc": within,
        }

    payload["elapsed_sec"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)")


if __name__ == "__main__":
    main()
