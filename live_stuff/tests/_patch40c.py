import io
p = r"live_stuff/tests/exp40c_wage_gate.py"
lines = io.open(p, encoding="utf-8").read().splitlines(True)
assert 'rw=sim' in lines[131] and 'trw=rw' in lines[132] and 'prefill fine' in lines[133]
lines[131] = '    rw=sim(c1h,swh,c15,sw15,fine_ltf=fine,**{**BP,**kw,**{"exp_wage_h":w},"ext_stop_r":1.5})\n'
lines[132] = '    trw=rw["ltf_trades"]\n'
lines[133] = '    print("    [prefill fine] %dt NET %+8.1f (doc %dt %+.1f)"%(len(trw),_net(trw),en,eg),flush=True)\n'
io.open(p, "w", encoding="utf-8", newline="").writelines(lines)
print("repaired lines 132-134")
