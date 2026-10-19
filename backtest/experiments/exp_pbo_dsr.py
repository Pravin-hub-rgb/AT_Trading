"""PBO and Deflated Sharpe Ratio over the thirteen-book trial set.

The gap this closes
-------------------
Thirteen books were explored. The best-looking one was carried forward. That is
exactly the procedure PBO exists to price, and it had never been run. Without
it, "107 looked best on history" carries no more weight than it deserves for
having been one of thirteen.

Two statistics, both from the same literature, answering different questions:

  PBO  - "if I re-partition time, how often does my in-sample winner end up in
         the bottom half out of sample?" This is a property of the SELECTION
         PROCEDURE, not of any book. It says whether the whole exercise was
         noisy, before asking anything about any individual strategy.

  DSR  - "after accounting for thirteen trials, is this book's Sharpe still
         distinguishable from what pure luck produces?" This is a per-book
         question and it is the one that decides deployment.

CSCV implementation
-------------------
S even blocks of equal trade-count, all C(S, S/2) ways to pick the in-sample
half, complement is out-of-sample. For each split every book is ranked on IS,
and the rank of the IS-best book is read off the OOS ranking. The logit of that
relative rank is the per-split statistic; PBO is the fraction with a negative
logit, i.e. the fraction of splits where the winner fell out.

Reported per book as well, because a procedure can be fine overall while one
book is a persistent outlier.

Note on what this cannot do
---------------------------
Both statistics assume the trial set is the set that generated the selection.
That set is larger than these thirteen - the author also swept parameters
inside each book, so the true N is bigger than 13 and every number here is
therefore OPTIMISTIC. Using 13 makes this a floor, not a final verdict.

Usage: python exp_pbo_dsr.py
"""

import io
import json
import math
import os
from itertools import combinations

HERE = os.path.dirname(os.path.abspath(__file__))
SERIES = os.path.join(HERE, "trades_series.json")

S_BLOCKS = 8          # even. 8 -> C(8,4) = 70 splits. 10 -> 252, 12 -> 924.
PBO_THRESHOLD = 0.15  # the figure Bailey et al. propose as the cut
DSR_ALPHA = 0.05


# ---------------------------------------------------------------------------
def load():
    return json.load(io.open(SERIES, encoding="utf-8"))


def blocks_of(trades, S):
    """Split a sorted trade list into S blocks of near-equal SIZE.

    Equal trade-count, not equal calendar time, because the books trade at
    different rates and comparing them on a clock would silently compare
    activity levels instead of performance.
    """
    n = len(trades)
    per = n // S
    out = []
    for i in range(S):
        a = i * per
        b = (i + 1) * per if i < S - 1 else n
        out.append(trades[a:b])
    return out


def matrix(data, S):
    """[S][book] = sum of R in that block."""
    books = list(data)
    M = [[0.0] * len(books) for _ in range(S)]
    for j, b in enumerate(books):
        bl = blocks_of(data[b], S)
        for i in range(S):
            M[i][j] = sum(r for _, r in bl[i])
    return books, M


def sharpe(x):
    """Non-annualised, risk-free 0. Returns 0 for a degenerate series."""
    n = len(x)
    if n < 3:
        return 0.0
    m = sum(x) / n
    v = sum((a - m) ** 2 for a in x) / (n - 1)
    if v <= 0:
        return 0.0
    return m / math.sqrt(v)


def skew_kurt(x):
    """Sample skewness (g1) and non-excess kurtosis (g2)."""
    n = len(x)
    if n < 4:
        return 0.0, 3.0
    m = sum(x) / n
    s = math.sqrt(sum((a - m) ** 2 for a in x) / (n - 1))
    if s == 0:
        return 0.0, 3.0
    g1 = sum(((a - m) / s) ** 3 for a in x) / n
    g2 = sum(((a - m) / s) ** 4 for a in x) / n
    return g1, g2


def norm_cdf(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def norm_ppf(p):
    """Acklam-style rational approximation. Adequate for reported figures."""
    if p <= 0 or p >= 1:
        return float("nan")
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    pl, ph = 0.02425, 1 - 0.02425
    if p < pl:
        q = math.sqrt(-2 * math.log(p))
        x = (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    elif p > ph:
        q = math.sqrt(-2 * math.log(1 - p))
        x = -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    else:
        q = p - 0.5
        r = q * q
        x = (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)
    # one Newton refinement
    e = norm_cdf(x) - p
    u = e * math.sqrt(2 * math.pi) * math.exp(x * x / 2)
    return x - u / (1 + x * u / 2)


# ---------------------------------------------------------------------------
def pbo(books, M, S, log):
    """CSCV. Returns (pbo_overall, per_book_pbo, loser_logit_list)."""
    half = S // 2
    splits = list(combinations(range(S), half))
    log("  %d blocks, %d splits (%d choose %d)" % (S, len(splits), S, half))

    logits = []
    winners = {}
    for combo in splits:
        test = [i for i in range(S) if i not in combo]
        is_perf = [sum(M[i][j] for i in combo) / half for j in range(len(books))]
        oos_perf = [sum(M[i][j] for i in test) / half for j in range(len(books))]
        order_is = sorted(range(len(books)), key=lambda j: -is_perf[j])
        best = order_is[0]
        winners[best] = winners.get(best, 0) + 1
        order_oos = sorted(range(len(books)), key=lambda j: -oos_perf[j])
        rank = order_oos.index(best) + 1          # 1 = best in OOS
        rel = (rank - 0.5) / len(books)           # 0 = best, 1 = worst
        logits.append(math.log(rel / (1 - rel)))

    pbo_overall = sum(1 for x in logits if x < 0) / len(logits)
    per_book = {}
    nsp = len(splits)
    for j, code in enumerate(books):
        per_book[code] = 0.0
    # recompute per book: how often each book's IS-win landed bottom-half
    for combo in splits:
        test = [i for i in range(S) if i not in combo]
        is_perf = [sum(M[i][j2] for i in combo) / half for j2 in range(len(books))]
        oos_perf = [sum(M[i][j2] for i in test) / half for j2 in range(len(books))]
        best = sorted(range(len(books)), key=lambda j2: -is_perf[j2])[0]
        order_oos = sorted(range(len(books)), key=lambda j2: -oos_perf[j2])
        rank = order_oos.index(best) + 1
        if rank > len(books) / 2:
            per_book[books[best]] += 1
    for k in per_book:
        per_book[k] = per_book[k] / nsp
    return pbo_overall, per_book, winners


def dsr(books, data, log):
    """Deflated Sharpe Ratio per book.

    SR* is the expected maximum Sharpe under the null of no skill across N
    independent trials. A book only clears the bar if its Sharpe exceeds what
    the best of N coin-flips would produce by luck.
    """
    N = len(books)
    gamma = 0.5772156649015329
    rows = []
    for b in books:
        rs = [r for _, r in data[b]]
        n = len(rs)
        sr = sharpe(rs)
        g1, g2 = skew_kurt(rs)
        # variance of the Sharpe estimate under iid, per observation
        v = 1.0
        sr_star = math.sqrt(v) * ((1 - gamma) * norm_ppf(1 - 1.0 / N)
                                 + gamma * norm_ppf(1 - 1.0 / (N * math.e)))
        denom = 1 - g1 * sr + (g2 - 1) / 4 * sr * sr
        if denom <= 0:
            rows.append({"book": b, "n": n, "sr": sr, "dsr": 0.0, "p": 1.0,
                         "g1": g1, "g2": g2})
            continue
        dsr = (sr - sr_star) * math.sqrt(n - 1) / math.sqrt(denom)
        p = 1 - norm_cdf(dsr)
        rows.append({"book": b, "n": n, "sr": sr, "sr_star": sr_star,
                     "dsr": dsr, "p": p, "g1": g1, "g2": g2})
    rows.sort(key=lambda r: -r["dsr"])
    return rows


# ---------------------------------------------------------------------------
def main():
    def log(m):
        print(m, flush=True)

    data_all = load()
    books = [k for k in data_all]

    for era in ("oos", "is"):
        # combine both eras for the OOS run so each book has a full return
        # history; IS is analysed on its own below.
        pass

    results = {}

    for era in ("oos", "is"):
        d = {b: (data_all[b]["oos"] if era == "oos" else data_all[b]["is"]) for b in books}
        log("=" * 70)
        log("  ERA: %s   (%d books)" % (era.upper(), len(books)))
        log("=" * 70)
        log("  trades: %s" % ", ".join("%s=%d" % (data_all[b]["code"], len(d[b]))
                                       for b in books))

        for S in (8, 10, 12):
            bk, M = matrix(d, S)
            pbo_v, per_book, winners = pbo(bk, M, S, log)
            flag = "  <-- FAILS the 0.15 bar" if pbo_v > PBO_THRESHOLD else ""
            log("  PBO (S=%2d splits): %.3f%s" % (S, pbo_v, flag))
            if S == 8:
                results.setdefault(era, {})["pbo8"] = pbo_v
                results[era]["per_book"] = per_book
                results[era]["is_win_count"] = {bk[k]: v for k, v in winners.items()}
                results[era]["blocks"] = 8

        log("")
        rows = dsr(books, d, log)
        log("  DSR  (N=%d trials, alpha=%.2f)" % (len(books), DSR_ALPHA))
        log("  %-7s %6s %8s %9s %8s %8s %7s" % ("book", "n", "SR", "SR*", "DSR", "p", "verdict"))
        log("  " + "-" * 58)
        for r in rows:
            v = "PASS" if r["p"] < DSR_ALPHA else "fail"
            log("  %-7s %6d %8.4f %9.4f %8.3f %8.4f %7s"
                % (r["book"], r["n"], r["sr"], r.get("sr_star", 0), r["dsr"], r["p"], v))
        results.setdefault(era, {})["dsr"] = rows
        log("")

    with io.open(os.path.join(HERE, "pbo_dsr.json"), "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=1)

    # summary
    log("=" * 70)
    log("  SUMMARY")
    log("=" * 70)
    for era in ("oos", "is"):
        r = results[era]
        log("  %s: PBO=%.3f   (%s)" % (era.upper(), r["pbo8"],
            "noisy selection" if r["pbo8"] > PBO_THRESHOLD else "selection looks stable"))
        passing = [x["book"] for x in r["dsr"] if x["p"] < DSR_ALPHA]
        log("        books clearing DSR: %s" % (", ".join(passing) if passing else "NONE"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())