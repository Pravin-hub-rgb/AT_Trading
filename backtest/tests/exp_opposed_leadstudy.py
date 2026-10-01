"""DEEP STUDY: what LED TO the 125-opposed = 125-losers pattern (2026-09-22).

The dir-match label was refuted as lookahead (final swing dir computed on the
path that produced the loss). But the 125 trades are REAL losers. If a feature
knowable at entry predicts the leaky label, and that same feature predicts LOSS
on all trades, the phenomenon has a causal footprint we can gate on.

PART 1 — causal lead-study:
  * leaky opposed label (autopsy selector) as TARGET, never as a gate
  * causal features at entry: adverse drift over last K bars, fraction of
    opposing closes, chase position in range, causal running mag / age / ER,
    break kind, htf regime (both known at entry)
  * AUC of each causal feature vs the leaky label
  * top feature bucketed vs OUTCOME over all 500 trades (the salvage test)

PART 2 — bias-momentum leak audit (same class as dir-match):
  * gate attaches FINAL 1h swing magnitudes to break times that fire while the
    swing is still forming -> ratio may read post-entry price action
  * count entries where owning swing unconfirmed at entry / end after entry /
    start rewritten after entry (FLIP), and gate decision flips under
    entry-truncated running magnitudes

Run:  python backtest/tests/exp_opposed_leadstudy.py
"""
import sys
import bisect
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from run_experiment import get_data, BP, EXPERIMENTS
import test_experiments_craze as craze


def auc(feat, label):
    """Mann-Whitney AUC: P(feat_opposed > feat_matched) + 0.5*ties."""
    pos = [f for f, y in zip(feat, label) if y]
    neg = [f for f, y in zip(feat, label) if not y]
    if not pos or not neg:
        return 0.5
    allv = sorted(feat)
    rank = {}
    i = 0
    while i < len(allv):
        j = i
        while j + 1 < len(allv) and allv[j + 1] == allv[i]:
            j += 1
        for k in range(i, j + 1):
            rank[allv[k]] = (i + j) / 2.0 + 1  # 1-based avg rank
        i = j + 1
    rpos = sum(rank[f] for f in pos)
    n1, n0 = len(pos), len(neg)
    return (rpos - n1 * (n1 + 1) / 2.0) / (n1 * n0)


def main():
    data = get_data()
    sim = craze.build_module()
    params = {**BP, **EXPERIMENTS["champion_multi_sw10"]["params"]}
    batch = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                fine_ltf=data["fine"], **params)["ltf_trades"]
    print("batch: %d trades (champion_multi_sw10)" % len(batch))

    c15, sw15 = data["c15"], data["sw15"]
    ts15 = [int(c["ts"]) for c in c15]
    lo15 = [float(c["low"]) for c in c15]
    hi15 = [float(c["high"]) for c in c15]
    cl15 = [float(c["close"]) for c in c15]

    # confirmation events for causal reference (same as causal autopsy)
    conf_evs = []
    for s in sw15:
        ca = s.get("confirmed_at_idx")
        e_idx = (s.get("seg") or {}).get("end_idx", -1)
        if ca is not None and int(ca) >= 0 and int(e_idx) >= 0:
            conf_evs.append((int(ca), int(e_idx)))
    conf_evs.sort()
    conf_times = [c[0] for c in conf_evs]

    rows = []
    for t in batch:
        E = int(t["entry_ts"])
        e_idx = bisect.bisect_left(ts15, E)
        entry = float(t["entry_price"])
        d = 1 if t["dir"] == "long" else -1
        r = float(t["r_multiple"])

        # leaky opposed label (autopsy selector) — TARGET ONLY
        gen_dir = 0
        for s in sw15:
            s_idx = int((s.get("seg") or {}).get("start_idx", -1))
            if 0 <= s_idx <= e_idx:
                gen_dir = 1 if s.get("dir") == "up" else -1
        opposed = (gen_dir != 0 and gen_dir != d)

        # causal reference: last swing confirmed at/before entry
        ci = bisect.bisect_right(conf_times, e_idx) - 1
        ref_idx = conf_evs[ci][1] if ci >= 0 else 0
        ref_idx = max(0, min(ref_idx, e_idx))
        if d == 1:
            run_ext = min(lo15[ref_idx:e_idx + 1])
            causal_mag = (entry - run_ext) / entry * 100
        else:
            run_ext = max(hi15[ref_idx:e_idx + 1])
            causal_mag = (run_ext - entry) / entry * 100
        causal_age = e_idx - conf_evs[ci][0] if ci >= 0 else -1

        # causal adverse features: signed so + = price moved AGAINST trade
        feats = {}
        for K in (5, 10, 20):
            a = max(0, e_idx - K)
            drift = (cl15[e_idx] - cl15[a]) / cl15[a] * 100 * d
            feats["adv_drift%d" % K] = -drift  # + = against trade
            opp = 0
            for k in range(a + 1, e_idx + 1):
                if (cl15[k] - cl15[k - 1]) * d < 0:
                    opp += 1
            feats["adv_frac%d" % K] = opp / float(e_idx - a)
        a = max(0, e_idx - 10)
        rlo, rhi = min(lo15[a:e_idx + 1]), max(hi15[a:e_idx + 1])
        rng10 = rhi - rlo
        if d == 1:
            feats["chase10"] = (entry - rlo) / rng10 if rng10 > 0 else 0.5
        else:
            feats["chase10"] = (rhi - entry) / rng10 if rng10 > 0 else 0.5

        # causal ER20 (signed toward trade)
        a = max(0, e_idx - 19)
        disp = (cl15[e_idx] - cl15[a]) * d
        path = sum(abs(cl15[k] - cl15[k - 1]) for k in range(a + 1, e_idx + 1))
        feats["er20"] = disp / path if path > 0 else 0.0
        feats["causal_mag"] = causal_mag
        feats["causal_age"] = causal_age

        rows.append({
            "r": r, "opposed": opposed, "dir": d, "feats": feats,
            "break_kind": t.get("break_kind") or "?",
            "htf": t.get("htf_regime") or "?",
        })

    n_op = sum(1 for x in rows if x["opposed"])
    print("leaky opposed label: %d / %d" % (n_op, len(rows)))
    print("opposed outcome: R=%+.1f  WR=%.1f%%" % (
        sum(x["r"] for x in rows if x["opposed"]),
        100.0 * sum(1 for x in rows if x["opposed"] and x["r"] > 0) / max(n_op, 1)))
    print("")

    # ---- PART 1a: group means + AUC ----
    print("=== PART 1: CAUSAL FEATURES THAT LEAD TO THE OPPOSED LABEL ===")
    print("%-16s %14s %14s %8s" % ("feature", "opposed mean", "matched mean", "AUC"))
    feat_names = ["adv_drift5", "adv_drift10", "adv_drift20",
                  "adv_frac5", "adv_frac10", "adv_frac20",
                  "chase10", "er20", "causal_mag", "causal_age"]
    aucs = {}
    for fn in feat_names:
        vals = [x["feats"][fn] for x in rows]
        labels = [x["opposed"] for x in rows]
        op = [v for v, y in zip(vals, labels) if y]
        mt = [v for v, y in zip(vals, labels) if not y]
        a = auc(vals, labels)
        aucs[fn] = a
        print("%-16s %14.3f %14.3f %8.3f" % (
            fn, sum(op) / max(len(op), 1), sum(mt) / max(len(mt), 1), a))
    print("")

    # ---- PART 1b: break kind / htf regime (known at entry) ----
    print("-- break_kind x opposed-label x outcome (ALL causal at entry) --")
    bk = defaultdict(lambda: [0, 0, 0.0])
    for x in rows:
        v = bk[x["break_kind"]]
        v[0] += 1
        if x["opposed"]:
            v[1] += 1
        v[2] += x["r"]
    for k in sorted(bk):
        n, op, R = bk[k]
        print("  %-6s n=%4d  opposed=%4d (%.0f%%)  R=%+8.1f  avg=%+.3f" % (
            k, n, op, 100.0 * op / n, R, R / n))
    print("")
    print("-- htf_regime x opposed-label x outcome --")
    hk = defaultdict(lambda: [0, 0, 0.0])
    for x in rows:
        v = hk[x["htf"]]
        v[0] += 1
        if x["opposed"]:
            v[1] += 1
        v[2] += x["r"]
    for k in sorted(hk):
        n, op, R = hk[k]
        print("  %-8s n=%4d  opposed=%4d (%.0f%%)  R=%+8.1f  avg=%+.3f" % (
            k, n, op, 100.0 * op / n, R, R / n))
    print("")

    # ---- PART 1c: the salvage test — top causal feature vs OUTCOME ----
    top = sorted(aucs, key=lambda f: abs(aucs[f] - 0.5), reverse=True)
    print("=== SALVAGE TEST: top causal features bucketed vs OUTCOME (all %d) ===" % len(rows))
    for fn in top[:3]:
        buckets = sorted(set(x["feats"][fn] for x in rows))
        nb = len(buckets)
        cuts = [buckets[(qi + 1) * nb // 4 - 1] for qi in range(3)]

        def qkey(v, cuts=cuts):
            for qi in range(4):
                if qi == 3 or v <= cuts[qi]:
                    return "q%d" % (qi + 1)
            return "q4"
        print("  -- %s (AUC=%.3f) quartiles --" % (fn, aucs[fn]))
        bq = defaultdict(lambda: [0, 0, 0.0, 0])
        for x in rows:
            v = bq[qkey(x["feats"][fn])]
            v[0] += 1
            if x["opposed"]:
                v[1] += 1
            v[2] += x["r"]
            if x["r"] < 0:
                v[3] += 1
        for q in sorted(bq):
            n, op, R, nl = bq[q]
            print("     %s n=%4d opposed=%4d(%3.0f%%)  R=%+8.1f  avg=%+.3f  loss=%3.0f%%" % (
                q, n, op, 100.0 * op / n, R, R / n, 100.0 * nl / n))
        print("")

    # ---- PART 2: bias-momentum leak audit (same class as dir-match) ----
    print("=== PART 2: BIAS-MOMENTUM LEAK AUDIT ===")
    print("(gate attaches FINAL 1h swing mags to break times fired DURING formation)")
    sw10, c1h = data["sw10"], data["c1h"]
    ts1h = [int(c["ts"]) for c in c1h]
    lo1h = [float(c["low"]) for c in c1h]
    hi1h = [float(c["high"]) for c in c1h]

    bm_min = 0.5
    for k, v in EXPERIMENTS.items():
        pv = v.get("params", {}).get("exp_bias_momentum_min", 0)
        if pv and "bm05" in k:
            bm_min = float(pv)
    print("  using bm_min=%.2f" % bm_min)

    mags = []
    for s in sw10:
        seg = s.get("seg") or {}
        mags.append(abs(float(seg.get("end_px", 0) or 0) -
                        float(seg.get("start_px", 0) or 0)))
    evs = []  # (time_str, ratio_leaky, owning_swing_idx)
    for bmi in range(1, len(sw10)):
        if mags[bmi - 1] <= 0:
            continue
        ratio = mags[bmi] / mags[bmi - 1]
        for b in (sw10[bmi].get("breaks") or []):
            bt = b.get("time", "")
            if bt:
                evs.append((bt[:19], ratio, bmi))
    evs.sort(key=lambda z: z[0])
    ev_times = [e[0] for e in evs]

    applied = unconf = end_after = start_rewrite = flip_after = flip_dec = 0
    for t in batch:
        bar_t = (t.get("entry_date") or "")[:19]
        idx = bisect.bisect_right(ev_times, bar_t) - 1
        if idx < 0:
            continue
        applied += 1
        _, ratio_leaky, bmi = evs[idx]
        s = sw10[bmi]
        conf = int(s.get("confirmed_at_idx", -1))
        seg = s.get("seg") or {}
        e1h = bisect.bisect_right(ts1h, int(t["entry_ts"])) - 1
        e1h = max(0, min(e1h, len(c1h) - 1))

        if conf < 0 or conf > e1h:
            unconf += 1
        if int(seg.get("end_idx", -1)) > e1h:
            end_after += 1
        s_idx_final = int(seg.get("start_idx", -1))
        if s_idx_final > e1h:
            start_rewrite += 1
        if any((b.get("time") or "")[:19] > bar_t
               for b in (s.get("breaks") or []) if b.get("kind") == "FLIP"):
            flip_after += 1

        # causal recompute: running mags truncated at entry bar
        if s_idx_final < 0 or s_idx_final > e1h:
            flip_dec += 1
            continue
        dsw = 1 if s.get("dir") == "up" else -1
        if dsw == 1:
            run_end = max(hi1h[s_idx_final:e1h + 1])
        else:
            run_end = min(lo1h[s_idx_final:e1h + 1])
        cur_causal = abs(run_end - float(seg.get("start_px", 0) or 0))

        prev = sw10[bmi - 1]
        pconf = int(prev.get("confirmed_at_idx", -1))
        if 0 <= pconf <= e1h:
            prev_causal = mags[bmi - 1]
        else:
            pseg = prev.get("seg") or {}
            p_start = int(pseg.get("start_idx", -1))
            p_d = 1 if prev.get("dir") == "up" else -1
            if p_start < 0 or p_start > e1h:
                flip_dec += 1
                continue
            p_run = max(hi1h[p_start:e1h + 1]) if p_d == 1 else min(lo1h[p_start:e1h + 1])
            prev_causal = abs(p_run - float(pseg.get("start_px", 0) or 0))
        if prev_causal <= 0:
            flip_dec += 1
            continue
        ratio_causal = cur_causal / prev_causal
        if (ratio_leaky < bm_min) != (ratio_causal < bm_min):
            flip_dec += 1

    n = len(batch)
    print("  entries with a bm break at/before entry: %d / %d" % (applied, n))
    print("  owning 1h swing UNCONFIRMED at entry:    %d (%.1f%%)" % (unconf, 100.0 * unconf / n))
    print("  owning swing END after entry:            %d (%.1f%%)" % (end_after, 100.0 * end_after / n))
    print("  owning swing START rewritten after:      %d (%.1f%%)" % (start_rewrite, 100.0 * start_rewrite / n))
    print("  owning swing FLIP break after entry:     %d (%.1f%%)" % (flip_after, 100.0 * flip_after / n))
    pct = 100.0 * flip_dec / max(applied, 1)
    print("  gate DECISION flips under causal recompute: %d (%.1f%% of %d)" % (flip_dec, pct, applied))
    print("  VERDICT: %s" % ("LEAKY" if pct > 5 else "mostly causal"))


if __name__ == "__main__":
    main()



if __name__ == "__main__":
    main()
