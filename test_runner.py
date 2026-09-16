import traceback
import sys
sys.argv = ['test']

tests = [
    ('live_stuff/tests/test_entry_verify.py', 'test_entry_verify'),
    ('live_stuff/tests/test_daily_reset.py', 'test_daily_reset'),
]

for path, name in tests:
    print(f'\n{"="*50}\nRunning {name}...\n{"="*50}')
    ns = {}
    try:
        with open(path) as f:
            code = f.read()
        exec(compile(code, path, 'exec'), ns)
        if 'main' in ns:
            ns['main']()
        print(f'{name}: ALL PASSED')
    except SystemExit as e:
        if e.code == 0:
            print(f'{name}: SystemExit(0) - likely passed')
        else:
            print(f'{name}: SystemExit({e.code})')
            traceback.print_exc()
        break
    except Exception:
        print(f'{name}: FAILED')
        traceback.print_exc()
        break