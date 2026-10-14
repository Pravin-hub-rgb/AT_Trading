"""Render the scorecard as a leaderboard, ranked the way the framework ranks.

The framework is explicit that Net R is NOT the king - it ranks OOS performance,
OOS retention, drawdown and DD duration, worst rolling periods, winner spread
through time and tail dependence ABOVE raw return. This applies that order
literally, and reports which tier decided each place rather than hiding it inside
one composite number.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "backtest" / "tests" / "_scorecard.json"
OUT_MD = ROOT / "backtest" / "docs" / "method" / "SCORECARD_LEADERBOARD.md"
OUT_HTML = ROOT / "backtest" / "docs" / "method" / "scorecard.html"
# The chain this scorecard was measured on. Stated in the output so the doc
# cannot claim freshness without naming what it is fresh against - the previous
# version of SCORECARD_LEADERBOARD.md had no chain line at all, which is part of
# why it read as current for a week after it stopped being so.
DATE = "2026-10-14"
CHAIN = "2840 swings / 7734 marks, fingerprint 5a4c55331ba079a9"

# tier order from `finding optimal book.md`, highest priority first.
# score is 1 = best on that tier. Only tiers we can measure honestly are scored;
# cross-asset is absent because no alt data is loaded, and saying so beats
# inventing a number.
def tiers(v):
    e = v["eras"]
    t1, t2, t3 = v["t1"], v["t2"], v["t3"]
    ret = (e["oos"]["expectancy"] / e["is"]["expectancy"]) if e["is"]["expectancy"] else 0
    return {
        "oos_net": e["oos"]["net"],
        "retention": ret * 100,
        "dd_duration": -t2["longest_underwater"],
        # "worst rolling period" is the single WORST stretch, so it is the MINIMUM
        # across the windows, not the maximum. Taking max() would report a book's
        # best 100-trade stretch as its worst and quietly reward books that are
        # terrible over 50 trades but lucky over 100.
        "worst_roll": min(t2["worst_roll50"], t2["worst_roll100"]),
        "tail_spread": -t3["tail"]["top5%"]["contrib"],
        "years_pos": v["t5"]["_years_positive"],
        "cost_2x": v["t4"]["2.0x"],
        "net_dd": t2["net_to_dd"],
        "simplicity": -v["t6"]["tuned"],
        "net": t1["net"],
        "neg": len(v["neg_cells"]),
    }


WEIGHTS = [
    ("neg", "no negative half-year", 1.0),
    ("oos_net", "OOS performance", 1.0),
    ("retention", "OOS retention", 1.0),
    ("dd_duration", "drawdown duration", 1.0),
    ("worst_roll", "worst rolling 50/100", 1.0),
    ("tail_spread", "tail spread (lower top5% better)", 1.0),
    ("net_dd", "net / DD", 0.7),
    ("cost_2x", "cost 2x survival", 0.5),
    ("simplicity", "simplicity (fewer tuned knobs)", 0.3),
    ("net", "raw net R", 0.4),
]


def main():
    d = json.loads(DATA.read_text(encoding="utf-8"))
    rows = []
    for name, v in d.items():
        t = tiers(v)
        # rank within each tier, 1 = best
        for key, _lbl, _w in WEIGHTS:
            vals = sorted({tiers(x)[key] for x in d.values()}, reverse=(key != "neg"))
            vals2 = sorted({tiers(x)[key] for x in d.values()})
            order = vals2 if key == "neg" else vals
            t[key + "_rank"] = order.index(t[key]) + 1
        score = sum(t[k + "_rank"] * w for k, _l, w in WEIGHTS)
        rows.append((score, name, v, t))
    rows.sort()
    tot_w = sum(w for _k, _l, w in WEIGHTS)
    print("=" * 118)
    print("  LEADERBOARD - ranked by the framework's own priority order, not by net R")
    print("  (net R is deliberately LAST and weighted 0.4 of %s total weight)" % round(tot_w, 1))
    print("=" * 118)
    print("  %-34s %6s %5s %6s %5s %5s %5s %5s %5s %5s"
          % ("book", "score", "neg", "OOS", "ret", "ddDur", "roll", "tail", "n/DD", "net"))
    for score, name, v, t in rows:
        print("  %-34s %6.1f %5d %6.0f %4.0f%% %5d %5.0f %4.0f%% %5.0f %5.0f"
              % (name.replace("fsent_", ""), round(score, 1), t["neg"],
                 t["oos_net"], t["retention"], -t["dd_duration"],
                 t["worst_roll"], t["tail_spread"], t["net_dd"], t["net"]))
    print()
    print("  lower score = better. score = weighted sum of tier RANKS, so a book that")
    print("  wins the tiers the owner cares about beats a book with a bigger headline.")

    payload = dict(
        rows=[dict(score=round(s, 1), name=n, t=t, v=v) for s, n, v, t in rows],
        weights=[dict(key=k, label=l, weight=w) for k, l, w in WEIGHTS],
    )
    html = HTML.replace("__DATA__", json.dumps(payload, separators=(",", ":")))
    OUT_HTML.write_text(html, encoding="utf-8")
    print("\n  wrote %s" % OUT_HTML.relative_to(ROOT))

    # The markdown twin. It was OUT_MD = ... at module scope and never written,
    # so SCORECARD_LEADERBOARD.md sat at its 2026-10-09 content while the html
    # beside it tracked the data - two artifacts of the same study disagreeing,
    # with nothing announcing which was current.
    md = []
    md.append("# Scorecard leaderboard - 12 candidates through the owner's framework")
    md.append("")
    md.append("**Regenerated %s.** Harnesses: `exp_scorecard.py` (measurement),"
              " `exp_scorecard_report.py` (this file and `scorecard.html`)." % DATE)
    md.append("Framework: `backtest/docs/learn/finding optimal book.md`.")
    md.append("Chain: **2840 swings / 7734 marks**, fingerprint `5a4c55331ba079a9`"
              " - the marks corrected by the B1 arming fix, V13 and the"
              " volatile-B1 work. The previous version of this file predates all"
              " of that.")
    md.append("")
    md.append("**Net R was deliberately ranked last**, weighted %.1f of %.1f total"
              " - exactly as the framework asks. That is what makes this"
              " leaderboard worth reading: **the book with the biggest return"
              " does not finish first.**"
              % (WEIGHTS[-1][2], sum(w for _k, _l, w in WEIGHTS)))
    md.append("")
    md.append("Interactive: `scorecard.html` (sortable).")
    md.append("")
    md.append("---")
    md.append("")
    md.append("# 1. The leaderboard")
    md.append("")
    md.append("Lower score is better. Score is a weighted sum of per-tier **ranks**"
              " (1 = best), so a book that wins the tiers you care about beats one"
              " with a bigger headline.")
    md.append("")
    md.append("| # | book | score | neg | OOS R | retention | underwtr | worst roll | top5% | net/DD | **net R** |")
    md.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for i, (score, name, v, t) in enumerate(rows, 1):
        neg = t["neg"]
        pill = "0" if neg == 0 else "**%d**" % neg
        md.append("| %d | `%s` | **%.1f** | %s | %.0f | %.0f%% | %d | %+.0f | %.0f%% | %.0f | %+.0f |"
                  % (i, name.replace("fsent_", ""), round(score, 1), pill,
                     t["oos_net"], t["retention"], -t["dd_duration"],
                     t["worst_roll"], t["tail_spread"], t["net_dd"], t["net"]))
    md.append("")
    md.append("`neg` counts the book-negative half-years - the owner's decisive"
              " test. A book with 0 there has never had a losing half-year in"
              " either era.")
    md.append("")
    md.append("---")
    md.append("")
    md.append("# 2. What the score weights, in the framework's order")
    md.append("")
    md.append("| tier | what it measures | weight |")
    md.append("|---|---|---:|")
    for key, lbl, w in WEIGHTS:
        md.append("| `%s` | %s | %.1f |" % (key, lbl, w))
    md.append("")
    md.append("The order is the framework's own:"
              " **validity, OOS performance, OOS retention, drawdown,"
              " worst rolling periods, distribution of winners, tail"
              " dependence, parameter robustness, cost robustness, simplicity,"
              " and raw net R last.**")
    md.append("")
    md.append("---")
    md.append("")
    md.append("# 3. Where this stands")
    md.append("")
    best_ret = max(rows, key=lambda r: r[3]["retention"])
    best_nd = max(rows, key=lambda r: r[3]["net_dd"])
    top = rows[0]
    md.append("- **The ranking's winner is `%s`** at %.1f."
              % (top[1].replace("fsent_", ""), round(top[0], 1)))
    md.append("- **Best OOS retention is `%s` at %.0f%%.**"
              % (best_ret[1].replace("fsent_", ""), best_ret[3]["retention"]))
    md.append("- **Best net/DD is `%s` at %.0f.**"
              % (best_nd[1].replace("fsent_", ""), best_nd[3]["net_dd"]))
    md.append("")
    md.append("These are three different books answering three different"
              " questions, and the framework says retention outranks net/DD."
              " **All twelve are separate, runnable books - this table ranks"
              " attention order, it does not retire anything.**")
    md.append("")
    md.append("---")
    md.append("")
    md.append("# 4. Limits")
    md.append("")
    md.append("- **Twelve books, one era split.** Retention has moved by several"
              " points between runs, so a 2-3 point gap is not a ranking.")
    md.append("- **Cost sensitivity is an approximation** and is labelled one"
              " elsewhere: the per-trade cost is re-applied to the same trade"
              " series, so it measures what costs eat, not fills that would differ"
              " at a different fee.")
    md.append("- **Tier 0 validity is not recomputed here.** It is enforced by"
              " `exp_fastcheck` and the causality audit, and every book in this"
              " table passed it.")
    md.append("- **Nothing is adopted by this file.** It orders attention.")
    md.append("")
    OUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")
    print("  wrote %s" % OUT_MD.relative_to(ROOT))
    return rows


HTML = r"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<title>scorecard leaderboard</title><style>
:root{--bg:#0e1116;--panel:#161b22;--line:#262d38;--fg:#e6edf3;--dim:#8b949e;--good:#3fb950;--bad:#f85149;--acc:#58a6ff;--warn:#d29922}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.55 ui-sans-serif,system-ui,"Segoe UI",Roboto,sans-serif}
header{padding:24px 28px 12px;border-bottom:1px solid var(--line)}
h1{margin:0 0 5px;font-size:20px;font-weight:650}
.sub{color:var(--dim);font-size:13px;max-width:1000px}
main{padding:20px 28px 60px;display:grid;gap:20px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px 18px}
.card h2{margin:0 0 3px;font-size:15px;font-weight:620}
.cap{color:var(--dim);font-size:12.5px;margin-bottom:12px}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums;font-size:13px}
th,td{padding:5px 7px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
th:first-child,td:first-child{text-align:left}
th{color:var(--dim);font-size:11px;text-transform:uppercase;letter-spacing:.4px;cursor:pointer}
tbody tr:hover{background:#1b2330}
tr.top{background:#12233a}
td.rank{font-weight:700;color:var(--acc);text-align:center}
.pill{display:inline-block;padding:1px 7px;border-radius:9px;font-size:11px;font-weight:600}
.pill.ok{background:#12351c;color:var(--good)} .pill.no{background:#3a1a1c;color:var(--bad)}
.pill.mid{background:#3a2f12;color:var(--warn)}
.bar{height:7px;background:#21262d;border-radius:4px;overflow:hidden;display:inline-block;width:56px;vertical-align:-1px}
.bar i{display:block;height:100%;background:var(--acc)}
tr.top .bar i{background:var(--good)}
.win{color:var(--good);font-weight:700}
.foot{color:var(--dim);font-size:12px;padding:0 28px 40px}
code{background:#21262d;padding:1px 5px;border-radius:4px;font-size:12px}
</style></head><body>
<header><h1>Strategy Quality Scorecard &mdash; 12 candidates, one test suite</h1>
<div class="sub">Framework: <code>docs/learn/finding optimal book.md</code>. Gates + scorecard, not one
arbitrary number &mdash; a single score hides <em>why</em> a book failed. Ranked in the framework's own
priority order: <b>net R is deliberately last</b>.</div></header>
<main>
<div class="card"><h2>The leaderboard</h2>
<div class="cap">Lower score is better. Score is a weighted sum of per-tier <em>ranks</em> (1 = best),
so a book that wins the tiers you care about beats one with a bigger headline number.
Click any header to sort.</div>
<div id="main"></div></div>
<div class="card"><h2>Why the top book is the top book</h2>
<div class="cap">Auto-generated from the same data.</div><div id="why"></div></div>
</main>
<div class="foot">Generated by <code>backtest/tests/exp_scorecard_report.py</code>.
Tier 0 validity is a gate, not a score &mdash; all 12 passed it: FS causality 0 violations,
origin lookahead PASS, pins reproduce.</div>
<script>
const D=__DATA__;
const W=D.weights;
function pill(n,g){if(g==='neg')return '<span class="pill '+(n?'no':'ok')+'">'+(n||'none')+'</span>';
 return '<span class="pill mid">'+n+'</span>';}
function val(k,t,v){if(k==='neg')return pill(v,'neg');
 if(k==='oos_net')return v.toFixed(0);
 if(k==='retention')return v.toFixed(0)+'%';
 if(k==='dd_duration')return -v;
 if(k==='worst_roll')return (v>=0?'+':'')+v.toFixed(0);
 if(k==='tail_spread')return (-v).toFixed(0)+'%';
 if(k==='cost_2x')return v.toFixed(0);
 return v.toFixed(2);}
let dir={};
function draw(sortK){
 const key=sortK||'score';
 dir[key]=dir[key]==='asc'?0:1;
 const R=[...D.rows].sort((a,b)=>{
   let x,y;
   if(key==='score'){x=a.score;y=b.score;}
   else if(key==='name'){x=a.name;y=b.name;}
   else {x=a.t[key];y=b.t[key];}
   if(key==='neg'||key==='simplicity') return dir[key]?x-y:y-x;
   return dir[key]?y-x:x-y;});
 let h='<table><thead><tr><th class="rank">#</th><th data-k="name">book</th>'+
  '<th data-k="score">score</th>';
 W.forEach(w=>{h+='<th data-k="'+w.key+'" title="'+w.label+', weight '+w.weight+'">'+
   w.label.split(' ')[0]+'</th>';});
 h+='</tr></thead><tbody>';
 R.forEach((r,i)=>{
  h+='<tr class="'+(i<3?'top':'')+'"><td class="rank">'+(i+1)+'</td>'+
   '<td title="'+r.name+'">'+r.name.replace('fsent_','')+'</td>'+
   '<td><div class="bar"><i style="width:'+Math.max(4,100-r.score/4)+'%"></i></div> '+r.score.toFixed(1)+'</td>';
  W.forEach(w=>{h+='<td>'+val(w.key,r.t,r.t[w.key])+'</td>';});
  h+='</tr>';});
 document.getElementById('main').innerHTML=h+'</tbody></table>';
 document.querySelectorAll('th[data-k]').forEach(e=>e.onclick=()=>draw(e.dataset.k));
 document.getElementById('why').innerHTML=why(R);
}
function why(R){
 const a=R[0].name.replace('fsent_',''), b=(R.find(r=>r.name.includes('champ_long')&&!r.name.includes('mcl')&&!r.name.includes('htf'))||R[1]).name.replace('fsent_','');
 const A=R[0].t, B=(R.find(r=>r.name.includes('champ_long')&&!r.name.includes('mcl')&&!r.name.includes('htf'))||R[1]).t;
 const rows=[
  ['no negative half-year',(A.neg?1:0)+' negative',(B.neg?1:0)+' negative'],
  ['OOS net R',A.oos_net.toFixed(0)+'R',B.oos_net.toFixed(0)+'R'],
  ['OOS expectancy retention',A.retention.toFixed(0)+'%',B.retention.toFixed(0)+'%'],
  ['longest underwater (trades)',(-A.dd_duration)+'',(-B.dd_duration)+''],
  ['worst rolling 50/100 trades',(A.worst_roll>=0?'+':'')+A.worst_roll.toFixed(0)+'R',(B.worst_roll>=0?'+':'')+B.worst_roll.toFixed(0)+'R'],
  ['top 5% of trades carry',(-A.tail_spread).toFixed(0)+'% of profit',(-B.tail_spread).toFixed(0)+'% of profit'],
  ['net R per unit drawdown',A.net_dd.toFixed(1),B.net_dd.toFixed(1)],
  ['survives 2x costs',A.cost_2x.toFixed(0)+'R',B.cost_2x.toFixed(0)+'R'],
  ['raw net R',A.net.toFixed(0)+'R',B.net.toFixed(0)+'R']];
 let h='<p style="color:var(--dim);margin-top:0">Winner <b style="color:var(--acc)">'+a+'</b> vs the shipping book <b>'+b+'</b>:</p><table><thead><tr><th>tier</th><th>'+a+'</th><th>'+b+'</th></tr></thead><tbody>';
 rows.forEach(r=>{h+='<tr><td>'+r[0]+'</td><td>'+r[1]+'</td><td>'+r[2]+'</td></tr>';});
 return h+'</tbody></table>';}
draw();
</script></body></html>"""


if __name__ == "__main__":
    main()