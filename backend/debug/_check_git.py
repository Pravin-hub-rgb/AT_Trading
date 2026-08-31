"""Check git history for firstswing.ts and find break logic in different commits."""
import subprocess, os

# Check which commits have firstswing.ts
for c in ['HEAD~3','HEAD~2','HEAD~1','HEAD']:
    r = subprocess.run(['git','show',f'{c}:frontend/src/lib/firstswing.ts'], 
                      capture_output=True, text=True, cwd=r'C:\Users\Pravin\Desktop\main\AT_Trading')
    content = r.stdout
    if content and len(content) > 100:
        # Find break logic
        for i, line in enumerate(content.split('\n')):
            if ('upBreak' in line or 'BreakLiving' in line or 
                ('up_break' in line and 'pivot' in line.lower())):
                print(f'{c} L{i+1}: {line.strip()}')
        # Also check first 100 lines for upBreak
        short = '\n'.join(content.split('\n')[:100])
        if 'upBreak' in short:
            for i, line in enumerate(short.split('\n')):
                if 'upBreak' in line:
                    print(f'{c} EARLY L{i+1}: {line.strip()}')
    else:
        print(f'{c}: not found or empty (stderr: {r.stderr[:100]})')
