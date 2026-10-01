"""SALVAGE from D3 alignment autopsy — what survives causal re-labeling?

Refuted: full-history dir-match / age10 gates (final chain labels).
Still testable (all causal at entry bar):
  A. Entry candle quality (body/range, close position) — OHLC only
  B. Risk as % of price — entry vs SL at decision
  C. LIVE forming engine age + dir (SwingEngine snapshot at bar i)
  D. LIVE running magnitude from live start_idx (not final batch start)
  E. Early-exit idea: if live dir FLIPS against you while swing still
     undeclared, cut the trade (management, not entry gate)

Run: python backtest/tests/exp_alignment_salvage.py
"""
import sys
import time
import bisect
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from run_experiment import get_data, BP, net_r
import test_experiments_craze as craze
from experiment_registry import EXPERIMENTS
from exp_alignment_live_state_audit import replay_live_state, age_band


def bucket(rows, title, key_fn, bins):
    print(f"\n--- {title} ---")
    for b in bins:
        lst = [r for r in rows if key_fn(r) == b]
        if not lst:
            print(f"  {b:<14} n=0")
            continue
        n = len(lst)
        rs = [r["r"] for r in lst]
        wr = 100.0 * sum(1 for x in rs if x > 0) / n
        big = sum(1 for x in rs if x >= 2.0)
        print(f"  {b:<14} n={n:4d}  R={sum(rs):+8.1f}  avg={sum(rs)/n:+6.3f}  "
              f"WR={wr:5.1f}%  bigW={big}")


def main():
    t0 = time.time()
    data = get_data()
    c15 = data["c15"]
    ts15 = [int(c["ts"]) for c in c15]
    lo = [float(c["low"]) for c in c15]
    hi = [float(c["high"]) for c in c15]
    op = [float(c["open"]) for c in c15]
    cl = [float(c["close"]) for c in c15]

    print("replaying live swing state...")
    live = replay_live_state(data["f15"], craze.MB15)

    sim = craze.build_module()
    params = {**BP, **EXPERIMENTS["champion_multi_sw10"]["params"]}
    batch = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                fine_ltf=data["fine"], **params)["ltf_trades"]
    print(f"champion trades: {len(batch)}")

    rows = []
    for t in batch:
        E = int(t["entry_ts"])
        i = bisect.bisect_left(ts15, E)
        if not (0 <= i < len(c15)):
            continue
        d = 1 if t["dir"] == "long" else -1
        r = float(t["r_multiple"])
        entry = float(t["entry_price"])
        sl = float(t["sl"])
        st = live[i] if i < len(live) else None
        live_dir = 0
        live_start = -1
        declared = False
        if st:
            if st["dir"] == "up":
                live_dir = 1
            elif st["dir"] == "down":
                live_dir = -1
            live_start = int(st.get("start_idx", -1))
            declared = bool(st.get("declared"))

        body = abs(cl[i] - op[i])
        rng = hi[i] - lo[i]
        body_r = body / rng if rng > 0 else 0.0
        close_pos = (cl[i] - lo[i]) / rng if rng > 0 else 0.5
        risk_pct = abs(entry - sl) / entry * 100.0 if entry > 0 else 0.0

        live_age = i - live_start if live_start >= 0 else -1
        live_match = (live_dir != 0 and live_dir == d)

        # live running magnitude from LIVE start only
        run_mag = -1.0
        if live_start >= 0 and live_start <= i:
            if d == 1:
                rmin = min(lo[live_start:i + 1])
                run_mag = (entry - rmin) / entry * 100.0
            else:
                rmax = max(hi[live_start:i + 1])
                run_mag = (rmax - entry) / entry * 100.0

        # year for temporal
        yr = (t.get("exit_date") or t.get("entry_date") or "")[:4]

        rows.append({
            "r": r, "d": d, "i": i, "declared": declared,
            "live_dir": live_dir, "live_match": live_match,
            "live_age": live_age, "run_mag": run_mag,
            "body_r": body_r, "close_pos": close_pos, "risk_pct": risk_pct,
            "yr": yr, "t": t,
        })

    n = len(rows)
    print(f"\n=== A. ENTRY CANDLE (fully causal, OHLC at i) ===")
    bucket(rows, "body/range",
           lambda r: ("a:0-.2" if r["body_r"] < 0.2 else "b:.2-.5" if r["body_r"] < 0.5
                      else "c:.5-.8" if r["body_r"] < 0.8 else "d:.8+"),
           ["a:0-.2", "b:.2-.5", "c:.5-.8", "d:.8+"])
    bucket(rows, "close position (0=low 1=high)",
           lambda r: ("a:0-.2" if r["close_pos"] < 0.2 else "b:.2-.4" if r["close_pos"] < 0.4
                      else "c:.4-.6" if r["close_pos"] < 0.6
                      else "d:.6-.8" if r["close_pos"] < 0.8 else "e:.8+"),
           ["a:0-.2", "b:.2-.4", "c:.4-.6", "d:.6-.8", "e:.8+"])

    print(f"\n=== B. RISK % (causal: entry vs SL) ===")
    bucket(rows, "risk as pct of price",
           lambda r: ("a:0-.5" if r["risk_pct"] < 0.5 else "b:.5-1" if r["risk_pct"] < 1.0
                      else "c:1-2" if r["risk_pct"] < 2.0 else "d:2+"),
           ["a:0-.5", "b:.5-1", "c:1-2", "d:2+"])

    print(f"\n=== C. LIVE engine age + dir (snapshot at bar i) ===")
    bucket(rows, "live age",
           lambda r: age_band(r["live_age"]),
           ["a:0-10", "b:11-25", "c:26-50", "d:51+", "z:no_start"])
    bucket(rows, "live dir vs trade",
           lambda r: ("MATCH" if r["live_match"] else
                      ("OPPOSED" if r["live_dir"] != 0 else "NO_DIR")),
           ["MATCH", "OPPOSED", "NO_DIR"])
    bucket(rows, "live dir x only undeclared",
           lambda r: ("u_MATCH" if (not r["declared"] and r["live_match"]) else
                      "u_OPPOSED" if (not r["declared"] and r["live_dir"] != 0) else
                      "d_MATCH" if (r["declared"] and r["live_match"]) else
                      "d_OPPOSED" if (r["declared"] and r["live_dir"] != 0) else "other"),
           ["u_MATCH", "u_OPPOSED", "d_MATCH", "d_OPPOSED", "other"])

    print(f"\n=== D. LIVE running magnitude (from live start_idx only) ===")
    bucket(rows, "live run mag %",
           lambda r: ("z:na" if r["run_mag"] < 0 else
                      "a:0-.5" if r["run_mag"] < 0.5 else
                      "b:.5-1" if r["run_mag"] < 1.0 else
                      "c:1-2" if r["run_mag"] < 2.0 else
                      "d:2-4" if r["run_mag"] < 4.0 else "e:4+"),
           ["a:0-.5", "b:.5-1", "c:1-2", "d:2-4", "e:4+", "z:na"])

    # E) Early-exit simulation on trade list: walk bars after entry,
    # if live dir flips against trade while still undeclared -> treat as exit at that bar close
    # (approximate: R scaled by remaining move — actually need path; use simple:
    #  if flip bar's close would have been worse than final, count as early cut at close)
    # Better: recompute R if we exit at first adverse live-dir flip bar's close.
    print(f"\n=== E. EARLY-EXIT on live dir flip vs you (undeclared only) ===")
    # Build per-bar live dir array for fast walk
    ld = []
    for s in live:
        if s["dir"] == "up":
            ld.append(1)
        elif s["dir"] == "down":
            ld.append(-1)
        else:
            ld.append(0)
    ldec = [1 if s.get("declared") else 0 for s in live]

    flip_cut = []
    no_flip = []
    for row in rows:
        t = row["t"]
        i = row["i"]
        d = row["d"]
        r0 = row["r"]
        entry = float(t["entry_price"])
        sl = float(t["sl"])
        risk = abs(entry - sl)
        if risk <= 0:
            continue
        # find first bar after entry where live dir opposes and still undeclared
        cut_j = None
        jmax = min(len(ld), i + 400)  # cap walk
        for j in range(i + 1, jmax):
            if ldec[j]:
                break  # swing declared — stop looking for forming-flip
            if ld[j] != 0 and ld[j] != d:
                cut_j = j
                break
        if cut_j is None:
            no_flip.append(r0)
            continue
        # exit at close of cut_j
        exit_px = cl[cut_j]
        if d == 1:
            r_cut = (exit_px - entry) / risk
        else:
            r_cut = (entry - exit_px) / risk
        # also consider: only apply if worse than holding? no — management rule is absolute
        flip_cut.append(r_cut)

    def summ(tag, xs):
        if not xs:
            print(f"  {tag}: n=0")
            return
        wr = 100.0 * sum(1 for x in xs if x > 0) / len(xs)
        print(f"  {tag}: n={len(xs):4d}  R={sum(xs):+8.1f}  avg={sum(xs)/len(xs):+6.3f}  WR={wr:5.1f}%")

    base = [r["r"] for r in rows]
    summ("base (hold to natural exit)", base)
    summ("trades with forming-dir flip against", flip_cut)
    summ("trades without forming-dir flip", no_flip)
    # hybrid: use cut R when flip, else base
    # rebuild hybrid aligned
    hybrid = []
    fi = 0
    # re-walk to align
    for row in rows:
        t = row["t"]
        i = row["i"]
        d = row["d"]
        entry = float(t["entry_price"])
        sl = float(t["sl"])
        risk = abs(entry - sl)
        cut_j = None
        jmax = min(len(ld), i + 400)
        for j in range(i + 1, jmax):
            if ldec[j]:
                break
            if ld[j] != 0 and ld[j] != d:
                cut_j = j
                break
        if cut_j is None:
            hybrid.append(row["r"])
        else:
            exit_px = cl[cut_j]
            r_cut = (exit_px - entry) / risk if d == 1 else (entry - exit_px) / risk
            hybrid.append(r_cut)
    summ("hybrid: cut on forming flip else hold", hybrid)

    # What about only cutting when cut is a loss (rescue)?
    hybrid2 = []
    for row in rows:
        t = row["t"]
        i = row["i"]
        d = row["d"]
        entry = float(t["entry_price"])
        sl = float(t["sl"])
        risk = abs(entry - sl)
        cut_j = None
        jmax = min(len(ld), i + 400)
        for j in range(i + 1, jmax):
            if ldec[j]:
                break
            if ld[j] != 0 and ld[j] != d:
                cut_j = j
                break
        if cut_j is None:
            hybrid2.append(row["r"])
            continue
        exit_px = cl[cut_j]
        r_cut = (exit_px - entry) / risk if d == 1 else (entry - exit_px) / risk
        hybrid2.append(min(r_cut, row["r"]) if r_cut < 0 else row["r"])
        # actually always take cut if earlier loss? simpler: take r_cut if r_cut < r0 else r0
        # redo last append properly
    # fix hybrid2 cleanly
    hybrid2 = []
    for row in rows:
        t = row["t"]
        i = row["i"]
        d = row["d"]
        entry = float(t["entry_price"])
        sl = float(t["sl"])
        risk = abs(entry - sl)
        cut_j = None
        jmax = min(len(ld), i + 400)
        for j in range(i + 1, jmax):
            if ldec[j]:
                break
            if ld[j] != 0 and ld[j] != d:
                cut_j = j
                break
        if cut_j is None:
            hybrid2.append(row["r"])
            continue
        exit_px = cl[cut_j]
        r_cut = (exit_px - entry) / risk if d == 1 else (entry - exit_px) / risk
        hybrid2.append(r_cut if r_cut < row["r"] else row["r"])
    summ("rescue: cut only if better than natural R", hybrid2)

    # F) Combine salvage candidates that look positive: risk band + body + live age
    print(f"\n=== F. STACK preview (trade-list, not path-true) ===")
    def keep_body(r):
        return r["body_r"] >= 0.2
    def keep_risk(r):
        return 0.5 <= r["risk_pct"] < 2.0
    def keep_close(r):
        return r["close_pos"] >= 0.4
    def keep_liveage(r):
        return r["live_age"] < 0 or r["live_age"] <= 50

    filters = [
        ("base", lambda r: True),
        ("body>=0.2", keep_body),
        ("risk 0.5-2", keep_risk),
        ("close_pos>=0.4", keep_close),
        ("live_age<=50", keep_liveage),
        ("body+risk", lambda r: keep_body(r) and keep_risk(r)),
        ("body+risk+close", lambda r: keep_body(r) and keep_risk(r) and keep_close(r)),
        ("body+risk+close+age50",
         lambda r: keep_body(r) and keep_risk(r) and keep_close(r) and keep_liveage(r)),
    ]
    base_r = sum(r["r"] for r in rows)
    for tag, fn in filters:
        ks = [r for r in rows if fn(r)]
        rs = [r["r"] for r in ks]
        wr = 100.0 * sum(1 for x in rs if x > 0) / max(len(rs), 1)
        print(f"  {tag:<28} n={len(ks):>3}  R={sum(rs):+8.1f}  WR={wr:5.1f}%  dR={sum(rs)-base_r:+.1f}")

    # Per-year for top causal features
    print(f"\n=== G. Temporal — risk band + body by year ===")
    for yr in sorted({r["yr"] for r in rows if r["yr"]}):
        ys = [r for r in rows if r["yr"] == yr]
        yb = [r for r in ys if keep_body(r) and keep_risk(r)]
        if not ys:
            continue
        print(f"  {yr} base n={len(ys):3d} R={sum(r['r'] for r in ys):+7.1f}   "
              f"body+risk n={len(yb):3d} R={sum(r['r'] for r in yb):+7.1f}  "
              f"dR={sum(r['r'] for r in yb)-sum(r['r'] for r in ys):+.1f}")

    print(f"\n(done {time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
