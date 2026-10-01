import io
p = "backtest/tests/exp49_partial_champion.py"
s = io.open(p, encoding="utf-8").read()
old_pins = s[s.index("PINS = {"):s.index("}\n\n\ndef wf6") + 1]
new_pins = '''PINS = {
    ("lb30", "w24", "ext1.5"): (265, 231.6),
    ("lb30", "w24", "ext3.0"): (307, 222.4),
    ("A4", "w24", "ext1.5"): (250, 207.1),
    ("A4", "w24", "ext3.0"): (285, 218.8),
}
'''
s = s.replace(old_pins, new_pins)
s = s.replace('"""6-segment annual R breakdown."""', '"""NET by calendar year of EXIT (not WF segments)."""')
s = s.replace("def wf6(tr):", "def yearly_net(tr):")
s = s.replace("wf6(tr)", "yearly_net(tr)")
anchor = "    # ---------- PHASE 2: champion single (sw10 + sw20) ----------"
seg = '''    # ---------- 6-segment walk-forward helper (exp41 convention) ----------
    K6 = 6
    _ts0 = min(c1h[0]["ts"], c15[0]["ts"]); _ts1 = max(c1h[-1]["ts"], c15[-1]["ts"])
    _step = (_ts1 - _ts0) / float(K6)
    def seg6(tr):
        segs = [[] for _ in range(K6)]
        for t in tr:
            i = min(int((int(t["entry_ts"]) - _ts0) / _step), K6 - 1)
            if i < 0: i = 0
            segs[i].append(t)
        nets = [_net(sg) if sg else 0.0 for sg in segs]
        return nets, min(nets)
'''
s = s.replace(anchor, seg + anchor)
old_single = '''        print("  champion single %s: %3dt NET %+8.1f  WR %.1f%%  DD %.1f  partials=%d canary_fails=%d  WF=%s" %
              (sw_tag, len(tr), net, s["wr"], s["dd"], partial_count, canary_fail, yearly_net(tr)), flush=True)'''
new_single = '''        nets6, worst6 = seg6(tr)
        print("  champion single %s: %3dt NET %+8.1f  WR %.1f%%  DD %.1f  partials=%d canary_fails=%d  worst6=%+.1f  years=%s" %
              (sw_tag, len(tr), net, s["wr"], s["dd"], partial_count, canary_fail, worst6, yearly_net(tr)), flush=True)'''
assert old_single in s, "single print"
s = s.replace(old_single, new_single)
old_multi = '''        print("  champion multi  %s: %3dt NET %+8.1f  WR %.1f%%  DD %.1f  partials=%d  WF=%s" %
              (sw_tag, len(tr), net, s["wr"], s["dd"], partial_count, yearly_net(tr)), flush=True)'''
new_multi = '''        partial_count = 0; canary_fail = 0
        for t in tr:
            pep = t.get("partial_exit_price", 0.0)
            if pep > 0:
                partial_count += 1
                entry = float(t["entry_price"]); exit_px = float(t["exit_price"])
                risk = abs(entry - float(t["sl"])); d = 1 if t["dir"] == "long" else -1
                expected_r = 7.5 + ((exit_px - entry) * d / risk) * 0.5
                if abs(float(t["r_multiple"]) - expected_r) > 0.05: canary_fail += 1
        nets6, worst6 = seg6(tr)
        print("  champion multi  %s: %3dt NET %+8.1f  WR %.1f%%  DD %.1f  partials=%d canary_fails=%d  worst6=%+.1f  years=%s" %
              (sw_tag, len(tr), net, s["wr"], s["dd"], partial_count, canary_fail, worst6, yearly_net(tr)), flush=True)'''
assert old_multi in s, "multi print"
s = s.replace(old_multi, new_multi)
s = s.replace('    elapsed = time.time() - t0', '''    (ROOT / "backtest/tests/_exp49_results.json").write_text(json.dumps(
        {"note": "full metrics in _exp49_out.txt; CAVEAT: partial second-fill fee+slip not yet in _trade_costs (approx 0.02R/partial trade)"}, indent=1))
    elapsed = time.time() - t0''')
io.open(p, "w", encoding="utf-8", newline="").write(s)
print("exp49 harness fixed (pins=gross, yearly label, seg6 WF, multi canary, json)")
