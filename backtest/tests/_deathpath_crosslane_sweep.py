"""Cross-lane candidate sweep on _deathpath_autopsy_results.json (read-only)."""
from __future__ import annotations
import json
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "backtest/tests/_deathpath_autopsy_results.json"

rows = json.loads(DATA.read_text(encoding="utf-8"))
champ = rows["champion"]
lb30 = rows["lb30"]


def dnet_cut(lane, pred, name):
    """dNET if we SKIP trades where pred(x) is True. Also report runners lost."""
    base = sum(x["r"] for x in lane)
    cut = [x for x in lane if pred(x)]
    keep_net = base - sum(x["r"] for x in cut)
    dnet = keep_net - base  # = -sum(cut)
    runners = sum(1 for x in cut if x["r"] >= 4.0)
    monsters = sum(1 for x in cut if x["r"] >= 10.0)
    return name, -sum(x["r"] for x in cut), len(cut), runners, monsters


def summarize(name, pred):
    a = dnet_cut(champ, pred, name)
    b = dnet_cut(lb30, pred, name)
    # both-lanes positive cut (cutting removes net-negative trades)
    both_pos = a[1] > 0 and b[1] > 0
    # runners bar: lose at most 3 runners >=4R on either lane
    runners_ok = a[3] <= 3 and b[3] <= 3
    monsters_ok = a[4] == 0 and b[4] == 0
    # meaningful: dNET >= +5 on both lanes (rough ship-ish for offline autopsy)
    meaningful = a[1] >= 5 and b[1] >= 5
    flag = ""
    if both_pos and runners_ok and monsters_ok and meaningful:
        flag = " *** CANDIDATE ***"
    elif both_pos and runners_ok and monsters_ok:
        flag = " *pos*"
    print(f"  {name:<48} champ dNET={a[1]:+7.1f} cut={a[2]:3d} run={a[3]} mon={a[4]} | "
          f"lb30 dNET={b[1]:+7.1f} cut={b[2]:3d} run={b[3]} mon={b[4]}{flag}")
    return both_pos and runners_ok and monsters_ok and meaningful


def npl(x):
    return x["n_prior_loss"] or 0


def np_(x):
    return x["n_prior"] or 0


def unreal(x):
    return x["unreal"]


def dist(x):
    return x["dist_sl"]


def body(x):
    return x["body"]


def upper(x):
    return x["upper"]


def lower(x):
    return x["lower"]


def wage(x):
    return x["wage_h"]


def ext(x):
    return x["ext_r"]


def kind(x):
    return x["kind"]


def regime(x):
    return x["regime"]


candidates = []

print("=" * 110)
print("  CROSS-LANE SWEEP — remaining combos on deathpath autopsy")
print("=" * 110)

# ---- A. n_prior × parent_u interactions ----
print("\n[A] n_prior_loss × parent_u (first-in-window × ubin refined)")
for nlo in (0, 1, 2):
    for ulo, uhi in [(-9, -0.5), (-0.5, 0), (0, 0.5), (0.5, 1.5), (1.5, 9)]:
        name = f"prior_loss={nlo} & parent_u[{ulo},{uhi})"
        def pred(x, nlo=nlo, ulo=ulo, uhi=uhi):
            if npl(x) != nlo:
                return False
            u = unreal(x)
            if u is None:
                return False
            return ulo <= u < uhi
        if summarize(name, pred):
            candidates.append(name)

print("\n[B] n_prior (raw) × parent_u")
for npr in (0, 1, 2, 3):
    for ulo, uhi in [(-9, 0), (0, 0.5), (0.5, 1.5), (1.5, 9)]:
        name = f"n_prior={npr} & parent_u[{ulo},{uhi})"
        def pred(x, npr=npr, ulo=ulo, uhi=uhi):
            if np_(x) != npr:
                return False
            u = unreal(x)
            if u is None:
                return False
            return ulo <= u < uhi
        if summarize(name, pred):
            candidates.append(name)

# ---- C. first-in-window (n_prior==0) more bins ----
print("\n[C] first-in-window refined parent_u gates")
for ulo, uhi in [(-9, -0.5), (-9, 0), (-9, 0.5), (0, 0.5), (0, 1.5),
                 (0.5, 1.5), (1, 1.5), (1.5, 9)]:
    name = f"FIRST & parent_u[{ulo},{uhi})"
    def pred(x, ulo=ulo, uhi=uhi):
        if np_(x) != 0:
            return False
        u = unreal(x)
        if u is None:
            return False
        return ulo <= u < uhi
    if summarize(name, pred):
        candidates.append(name)

# ---- D. later trades (n_prior>=1) parent_u ----
print("\n[D] LATER (n_prior>=1) × parent_u")
for ulo, uhi in [(-9, 0), (-9, 0.5), (0, 0.5), (0, 1.5), (0.5, 1.5), (1.5, 9)]:
    name = f"LATER & parent_u[{ulo},{uhi})"
    def pred(x, ulo=ulo, uhi=uhi):
        if np_(x) < 1:
            return False
        u = unreal(x)
        if u is None:
            return False
        return ulo <= u < uhi
    if summarize(name, pred):
        candidates.append(name)

# ---- E. early-peak predictors (causal features that might flag giveback-prone) ----
print("\n[E] early-peak loss predictors — gate on features that separate early-peak")
ep = [x for x in champ if x["path"] == "early-peak"]
print(f"  champion early-peak n={len(ep)} NET={sum(x['r'] for x in ep):+.1f}")
# causal features at entry: body, upper, wage, n_prior, parent_u
for thr in (0.3, 0.5, 0.7):
    name = f"body>={thr}"
    if summarize(name, lambda x, t=thr: body(x) is not None and body(x) >= t):
        candidates.append(name)
for thr in (0.4, 0.5, 0.6):
    name = f"upper_wick>={thr}"
    if summarize(name, lambda x, t=thr: upper(x) is not None and upper(x) >= t):
        candidates.append(name)

# ---- F. wage × first ----
print("\n[F] wage_h × first/later")
for wlo, whi in [(0, 6), (6, 12), (12, 24), (24, 48), (48, 999)]:
    for ftag, fp in [("FIRST", lambda x: np_(x) == 0), ("LATER", lambda x: np_(x) >= 1)]:
        name = f"{ftag} & wage[{wlo},{whi})"
        def pred(x, wlo=wlo, whi=whi, fp=fp):
            w = wage(x)
            if w is None or not fp(x):
                return False
            return wlo <= w < whi
        if summarize(name, pred):
            candidates.append(name)

# ---- G. wage × parent_u ----
print("\n[G] wage × parent_u")
for wlo, whi in [(0, 12), (12, 48), (48, 999)]:
    for ulo, uhi in [(-9, 0), (0, 1.5), (1.5, 9)]:
        name = f"wage[{wlo},{whi}) & parent_u[{ulo},{uhi})"
        def pred(x, wlo=wlo, whi=whi, ulo=ulo, uhi=uhi):
            w, u = wage(x), unreal(x)
            if w is None or u is None:
                return False
            return (wlo <= w < whi) and (ulo <= u < uhi)
        if summarize(name, pred):
            candidates.append(name)

# ---- H. kind × regime ----
print("\n[H] break_kind alone (already know both contribute — confirm on this data)")
for k in ("B2", "FLIP"):
    summarize(f"kind={k}", lambda x, k=k: kind(x) == k)
# cut inverted: keep only one
for k in ("B2", "FLIP"):
    name = f"KEEP only {k} (cut {'FLIP' if k=='B2' else 'B2'})"
    # this is not a cut pred in the same sense — print absolute
    for lane, lab in ((champ, "champ"), (lb30, "lb30")):
        base = sum(x["r"] for x in lane)
        keep = [x for x in lane if kind(x) == k]
        cut = [x for x in lane if kind(x) != k]
        print(f"    {lab} {name}: keep n={len(keep)} NET={sum(x['r'] for x in keep):+.1f} "
              f"(base {base:+.1f} dNET={sum(x['r'] for x in keep)-base:+.1f}) "
              f"cut={len(cut)} NET={sum(x['r'] for x in cut):+.1f}")

# ---- I. retest / first_05 already known? path is post-hoc — skip path-based gates ----
# But: causal micro × micro combos
print("\n[I] microstructure combos")
combos = [
    ("body<0.5 & upper>0.4", lambda x: body(x) is not None and upper(x) is not None and body(x) < 0.5 and upper(x) >= 0.4),
    ("body<0.5 & upper>0.5", lambda x: body(x) is not None and upper(x) is not None and body(x) < 0.5 and upper(x) >= 0.5),
    ("body<0.3 & upper>0.5", lambda x: body(x) is not None and upper(x) is not None and body(x) < 0.3 and upper(x) >= 0.5),
    ("lower 0.4-0.6 band", lambda x: lower(x) is not None and 0.4 <= lower(x) < 0.6),
    ("body>=0.75 & upper<0.2", lambda x: body(x) is not None and upper(x) is not None and body(x) >= 0.75 and upper(x) < 0.2),
    ("body>=0.9 (marubozu)", lambda x: body(x) is not None and body(x) >= 0.9),
    ("body<0.2 (doji-ish)", lambda x: body(x) is not None and body(x) < 0.2),
    ("gap<-0.2", lambda x: x["gap"] is not None and x["gap"] < -0.2),
    ("gap>0.2", lambda x: x["gap"] is not None and x["gap"] > 0.2),
]
for name, pred in combos:
    if summarize(name, pred):
        candidates.append(name)

# ---- J. parent_u × kind ----
print("\n[J] parent_u × kind")
for k in ("B2", "FLIP"):
    for ulo, uhi in [(-9, 0), (0, 1.5), (1.5, 9)]:
        name = f"kind={k} & parent_u[{ulo},{uhi})"
        def pred(x, k=k, ulo=ulo, uhi=uhi):
            u = unreal(x)
            if kind(x) != k or u is None:
                return False
            return ulo <= u < uhi
        if summarize(name, pred):
            candidates.append(name)

# ---- K. dist_sl refined ----
print("\n[K] parent dist-to-SL refined cuts")
for thr in (0.3, 0.5, 0.7, 1.0):
    name = f"parent_dist<{thr}"
    if summarize(name, lambda x, t=thr: dist(x) is not None and dist(x) < t):
        candidates.append(name)

# ---- L. ext_r as feature (note: parent_u ≡ ext_r — already tested) + wage×kind ----
print("\n[L] wage × kind")
for wlo, whi in [(0, 12), (12, 48), (48, 999)]:
    for k in ("B2", "FLIP"):
        name = f"wage[{wlo},{whi}) & kind={k}"
        def pred(x, wlo=wlo, whi=whi, k=k):
            w = wage(x)
            if w is None or kind(x) != k:
                return False
            return wlo <= w < whi
        if summarize(name, pred):
            candidates.append(name)

# ---- M. first-in-window + micro ----
print("\n[M] FIRST × micro")
for name, pred in [
    ("FIRST & body<0.5", lambda x: np_(x) == 0 and body(x) is not None and body(x) < 0.5),
    ("FIRST & upper>=0.5", lambda x: np_(x) == 0 and upper(x) is not None and upper(x) >= 0.5),
    ("FIRST & body>=0.75", lambda x: np_(x) == 0 and body(x) is not None and body(x) >= 0.75),
    ("FIRST & lower 0.4-0.6", lambda x: np_(x) == 0 and lower(x) is not None and 0.4 <= lower(x) < 0.6),
    ("LATER & body<0.5", lambda x: np_(x) >= 1 and body(x) is not None and body(x) < 0.5),
    ("LATER & upper>=0.5", lambda x: np_(x) >= 1 and upper(x) is not None and upper(x) >= 0.5),
]:
    if summarize(name, pred):
        candidates.append(name)

# ---- N. Look at the BEST positive-dNET cuts more carefully (side-by-side) ----
print("\n" + "=" * 110)
print("  POSITIVE-BOTH-LANES CUTS (dNET>0 both) — runners check detail")
print("=" * 110)
# re-run all preds we care about and filter
all_preds = []
# reuse a curated set
for thr in (-0.5, 0.0, 0.5, 1.0, 1.5):
    all_preds.append((f"parent_u<{thr}", lambda x, t=thr: unreal(x) is not None and unreal(x) < t))
for thr in (0.3, 0.5, 0.7):
    all_preds.append((f"parent_dist<{thr}", lambda x, t=thr: dist(x) is not None and dist(x) < t))
all_preds += [
    ("prior_loss>=1", lambda x: npl(x) >= 1),
    ("prior_loss>=2", lambda x: npl(x) >= 2),
    ("body>=0.75", lambda x: body(x) is not None and body(x) >= 0.75),
    ("upper>=0.6", lambda x: upper(x) is not None and upper(x) >= 0.6),
    ("lower 0.4-0.6", lambda x: lower(x) is not None and 0.4 <= lower(x) < 0.6),
    ("wage<6", lambda x: wage(x) is not None and wage(x) < 6),
    ("wage<12", lambda x: wage(x) is not None and wage(x) < 12),
    ("wage>=48", lambda x: wage(x) is not None and wage(x) >= 48),
    ("FIRST & u[0,1.5)", lambda x: np_(x) == 0 and unreal(x) is not None and 0 <= unreal(x) < 1.5),
    ("FIRST & u[0.5,1.5)", lambda x: np_(x) == 0 and unreal(x) is not None and 0.5 <= unreal(x) < 1.5),
    ("LATER & u[0,0.5)", lambda x: np_(x) >= 1 and unreal(x) is not None and 0 <= unreal(x) < 0.5),
    ("FIRST & prior_loss=0", lambda x: np_(x) == 0 and npl(x) == 0),
]
for name, pred in all_preds:
    a = dnet_cut(champ, pred, name)
    b = dnet_cut(lb30, pred, name)
    if a[1] > 0 and b[1] > 0:
        runners = max(a[3], b[3])
        mons = max(a[4], b[4])
        print(f"  {name:<36} champ={a[1]:+7.1f} (cut {a[2]:3d} run {a[3]} mon {a[4]}) | "
              f"lb30={b[1]:+7.1f} (cut {b[2]:3d} run {b[3]} mon {b[4]}) "
              f"maxRun={runners} maxMon={mons}")

print("\n" + "=" * 110)
print(f"  MEANINGFUL CANDIDATES (both dNET>=5, runners<=3, monsters=0): {len(candidates)}")
for c in candidates:
    print(f"    - {c}")
print("=" * 110)
