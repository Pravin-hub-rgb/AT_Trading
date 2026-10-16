"""The full scorecard for the three books under consideration, side by side.

Every number comes from _results.json, which the exporter regenerates from the
engine. Nothing here is computed by this file - it exists so the three can be
read against each other without flipping between tabs, and so the columns are
the same ones for all three rather than the ones that favour whichever book was
being looked at.

IS and OOS are the two datasets in the registry: IS is 2023-01-01..2026-09-13,
OOS is 2021-01-01..2022-12-31, a separate file. Forward is the untouched slice
after the cutoff, scored by exp_forward_eval.py.

Output: pick_scorecard.md
"""
from __future__ import annotations

import io
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent / "tests" / "_results.json"
FWD = HERE.parent / "tests" / "_forward_eval.json"
CAP = HERE / "capital_normalised_risk.json"
MD = HERE / "pick_scorecard.md"

BOOKS = [
    ("fsent_champ_long_htffs", "htffs"),
    ("fsent_champ_long_mcloff_htf15", "mcloff_htf15"),
    ("fsent_champ_long", "champ_long"),
]


def load():
    d = json.loads(io.open(RESULTS, encoding="utf-8").read())
    books = {b["name"]: b for b in d["books"]}
    fwd = {}
    if FWD.exists():
        f = json.loads(io.open(FWD, encoding="utf-8").read())
        for k, v in (f.get("candidates") or {}).items():
            fwd[v.get("config")] = v
    cap = {}
    if CAP.exists():
        cap = (json.loads(io.open(CAP, encoding="utf-8").read()).get("books") or {})
    return books, fwd, cap


def g(b, k, scale=1.0, fmt="%.2f", dash="-"):
    v = b.get(k)
    if v is None:
        return dash
    if isinstance(v, str):
        return v
    return fmt % (v * scale) if scale != 1.0 else fmt % v


def main() -> int:
    books, fwd, cap = load()
    rows = [(books.get(n), lbl, fwd.get(n), (cap.get(n) or {}).get("oos") or {})
            for n, lbl in BOOKS]
    rows = [r for r in rows if r[0]]
    L = ["# Three candidates, every number the repo keeps", ""]

    L.append("**IS** = 2023-01-01..2026-09-13. **OOS** = 2021-01-01..2022-12-31 (separate file).")
    L.append("**Forward** = after 2026-09-13 10:03, never searched. Tiny sample - it is a")
    L.append("tie-breaker, not a verdict.")
    L.append("")

    def table(title, rows_spec, header):
        L.append("## %s" % title)
        L.append("")
        L.append("| %s | %s |" % (header, " | ".join(lbl for _b, lbl, _f, _c in rows)))
        L.append("|---" * (len(rows) + 1) + "|")
        for label, fn, fmt in rows_spec:
            vals = []
            for b, _l, f, cp in rows:
                v = fn(b, f, cp)
                if isinstance(v, str):
                    vals.append(v)
                elif v == -1:
                    # -1 is the sentinel for "this book was not in that file",
                    # which must never render as a measured 0 or 1.
                    vals.append("not measured")
                else:
                    vals.append(fmt % v)
            L.append("| %s | %s |" % (label, " | ".join(vals)))
        L.append("")

    table("Size and shape", [
        ("class (0=multi, 1=serial)", lambda b, f, cp: 1 if (b.get("max_positions") or 0) == 1 else 0, "%d"),
        ("positions held", lambda b, f, cp: b.get("max_positions", 0), "%d"),
        ("trades", lambda b, f, cp: b["n"], "%d"),
        ("peak concurrent", lambda b, f, cp: cp.get("peak_concurrent", -1), "%d"),
        ("mean concurrent", lambda b, f, cp: cp.get("mean_concurrent", -1), "%.2f"),
    ], "metric")

    table("IS era (where the books were chosen)", [
        ("trades", lambda b, f, cp: b.get("is_n") or 0, "%d"),
        ("net R", lambda b, f, cp: b.get("is_net") or 0.0, "%+.2f"),
        ("R per trade", lambda b, f, cp: ((b.get("is_net") or 0) / b["is_n"]) if b.get("is_n") else 0, "%+.4f"),
    ], "metric")

    table("OOS era (2021-22, the crash period)", [
        ("trades", lambda b, f, cp: b.get("oos_n") or 0, "%d"),
        ("net R", lambda b, f, cp: b.get("oos_net") or 0.0, "%+.2f"),
        ("R per trade", lambda b, f, cp: ((b.get("oos_net") or 0) / b["oos_n"]) if b.get("oos_n") else 0, "%+.4f"),
    ], "metric")

    table("Both eras", [
        ("net R", lambda b, f, cp: b["net"], "%+.2f"),
        ("R per trade", lambda b, f, cp: b["expectancy"], "%+.4f"),
        ("win rate", lambda b, f, cp: b["wr"], "%.1f"),
        ("profit factor", lambda b, f, cp: b.get("pf") or 0, "%.3f"),
        ("payoff ratio", lambda b, f, cp: (b["pf"] / (b["wr"] / 100.0) * (b["wr"] / 100.0)) if b.get("pf") else 0, "%.2f"),
        ("avg win R", lambda b, f, cp: b.get("avg_win") or 0, "%+.3f"),
        ("avg loss R", lambda b, f, cp: b.get("avg_loss") or 0, "%+.3f"),
        ("t-stat", lambda b, f, cp: b.get("tstat") or 0, "%.2f"),
        ("retention OOS/IS", lambda b, f, cp: (100.0 * (b.get("oos_net") or 0) / b["is_net"]) if b.get("is_net") else 0, "%.0f"),
    ], "metric")

    table("Risk", [
        ("max drawdown R", lambda b, f, cp: b.get("max_dd") or 0, "%.2f"),
        ("drawdown % of peak", lambda b, f, cp: b.get("dd_pct_of_peak") or 0, "%.2f"),
        ("net / drawdown", lambda b, f, cp: b.get("net_to_dd") or 0, "%.1f"),
        ("days under water", lambda b, f, cp: b.get("longest_underwater") or 0, "%d"),
        ("recovery days", lambda b, f, cp: b.get("recover_days") if b.get("recover_days") is not None else -1, "%d"),
        ("p90 recovery days", lambda b, f, cp: b.get("p90_recover_days") if b.get("p90_recover_days") is not None else -1, "%d"),
        ("still underwater?", lambda b, f, cp: 1 if b.get("recover_band") in ("serious", "major", "unresolved") else 0, "%d"),
        ("worst 3 months", lambda b, f, cp: b.get("worst_3m") if b.get("worst_3m") is not None else 0, "%.2f"),
        ("worst 12 months", lambda b, f, cp: b.get("worst_12m") if b.get("worst_12m") is not None else 0, "%.2f"),
    ], "metric")

    table("How dependent on the best few trades", [
        ("top 10% of trades carry", lambda b, f, cp: (b.get("top5_contrib") or 0.0), "%.0f"),
        ("net after removing best 10", lambda b, f, cp: b.get("cap10_net") or 0, "%+.2f"),
        ("survives that cut?", lambda b, f, cp: 1 if (b.get("cap10_net") or 0) > 0 else 0, "%d"),
    ], "metric")

    table("Consistency", [
        ("negative half-years", lambda b, f, cp: len(b.get("neg_cells") or []), "%d"),
        ("half-years tested", lambda b, f, cp: len(b.get("halfs") or []), "%d"),
        ("50-trade windows positive", lambda b, f, cp: b.get("roll50_prof_pct") or 0, "%.0f"),
        ("p value, OOS", lambda b, f, cp: (b.get("null_p_oos") if b.get("null_p_oos") is not None else -1), "%.4f"),
        ("significant at 5%?", lambda b, f, cp: 1 if (b.get("null_p_oos") or 1) < 0.05 else 0, "%d"),
    ], "metric")

    table("Capital actually deployed", [
        ("DD per peak-capital R", lambda b, f, cp: cp.get("dd_per_capital_R", -1), "%.2f"),
        ("DD per mean-concurrent R", lambda b, f, cp: cp.get("dd_per_mean_R", -1), "%.1f"),
        ("net per mean-concurrent R", lambda b, f, cp: cp.get("net_per_mean_R", -1), "%.1f"),
    ], "metric")

    L.append("## Forward window - after the hard cutoff, never searched")
    L.append("")
    L.append("| book | trades | net R | win rate | profit factor | max DD | months positive |")
    L.append("|---|---:|---:|---:|---:|---:|---:|")
    for b, lbl, f, cp in rows:
        fo = ((f or {}).get("forward") or {})
        n = (fo.get("net") or {})
        gg = (fo.get("gross") or {})
        pos, tot = fo.get("positive_months", 0), fo.get("months", 0)
        L.append("| `%s` | %d | %+.2f | %.1f%% | %.2f | %.1fR | %d/%d |" % (
            lbl, n.get("n", 0), n.get("sum_r", 0.0), gg.get("wr_pct", 0.0),
            gg.get("pf", 0.0), n.get("max_dd", 0.0), pos, tot))
    L.append("")
    L.append("Sample is 3 to 13 trades. It cannot settle anything on its own. It is")
    L.append("listed because it is the only data nobody has searched.")
    L.append("")
    L.append("---")
    L.append("")
    L.append("Legend for risk band: 0 = no band recorded or recovered, 1 = serious,")
    L.append("major or unresolved.")
    L.append("")
    L.append("`payoff ratio` is derived from PF and win rate and is approximate; the")
    L.append("authoritative pair is `avg win R` and `avg loss R` above it.")
    io.open(MD, "w", encoding="utf-8").write("\n".join(L))
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())