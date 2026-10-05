"""Move the root's loose debug scripts and notes into the folders that already exist.

The repository root had 22 debug_*.ts files, 12 markdown notes and four loose
scripts sitting next to package.json. Two of the three destination folders
already existed - debug/ for traces and backtest/docs/ for writing - so this is
not a new taxonomy, it is the one already in use being applied to the files that
were never put in it.

What moves:
    debug_*.ts, debug_25aug*, codemod.cjs, research_firstswing.cjs, probe_upstox.py
        -> debug/          traces and one-off probes
    entry*.md, chat dump.md, talk.md, Start.md, PLAN.md, swing whole day chat.md,
    script for swing high and low.md, getting ohlcv data of 5min candle.md,
    trading bot roadmap.md, build_out.txt, sweep_logical_*.txt
        -> docs/notes/     writing and captured output
    backend.js, dev.js, start.bat
        -> frontend/       node entry points that belong with the node project

What stays in the root, because a root is where these belong:
    package.json  bun.lock  .gitignore  .gitattributes  verify.ps1
    AGENT_COORDINATION.md  backbencher.db

$null, 0 and .FullName are PowerShell redirect accidents and are removed: the
first two were already untracked by the previous commit, .FullName is a
14-byte file whose name is a PowerShell property that was never expanded.

Everything moves with git mv, so history follows. Nothing is deleted except the
three accidents.

    python _tidy_root.py --dry-run
    python _tidy_root.py --apply
"""
import argparse
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

NOTES = [
    "entry 1.md", "entry 2.md", "entry english 1.md", "entry english 2.md",
    "chat dump.md", "talk.md", "Start.md", "PLAN.md", "swing whole day chat.md",
    "script for swing high and low.md", "getting ohlcv data of 5min candle.md",
    "trading bot roadmap.md", "build_out.txt", "sweep_logical_err.txt",
    "sweep_logical_out.txt",
    "UsersPravinDesktopmainAT_Tradinglive_stuffdocsdesign.md",
]
DEBUG_RE = re.compile(r"^debug_.*\.ts$")
DEBUG_EXTRA = ["codemod.cjs", "research_firstswing.cjs", "probe_upstox.py"]
FRONTEND = ["backend.js", "dev.js", "start.bat"]
ACCIDENTS = ["$null", "0", ".FullName"]


def build_plan():
    plan = {}
    for name in NOTES:
        if (ROOT / name).exists():
            plan[name] = "docs/notes"
    for p in sorted(ROOT.glob("debug_*.ts")):
        plan[p.name] = "debug"
    for name in DEBUG_EXTRA + FRONTEND:
        if (ROOT / name).exists():
            plan[name] = "debug" if name in DEBUG_EXTRA else "frontend"
    return plan


def apply(plan):
    for sub in ("docs/notes", "debug", "frontend"):
        (ROOT / sub).mkdir(parents=True, exist_ok=True)
    moved = 0
    for name, dest in sorted(plan.items()):
        src, dst = ROOT / name, ROOT / dest / name
        if not src.exists():
            continue
        tracked = subprocess.run(["git", "ls-files", "--error-unmatch", str(src.relative_to(ROOT))],
                                 capture_output=True, text=True).returncode == 0
        if tracked:
            r = subprocess.run(["git", "mv", str(src), str(dst)], cwd=ROOT,
                               capture_output=True, text=True)
            if r.returncode:
                print("git mv failed:", name, r.stderr.strip()[:80])
                continue
        else:
            shutil.move(str(src), str(dst))
        moved += 1
    for name in ACCIDENTS:
        p = ROOT / name
        if p.exists():
            subprocess.run(["git", "rm", "--cached", "--", name], cwd=ROOT,
                           capture_output=True, text=True)
            p.unlink()
    print("moved %d file(s), removed %d accident(s)" % (moved, len(ACCIDENTS)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    plan = build_plan()
    if a.apply:
        apply(plan)
        return 0
    for dest in ("docs/notes", "debug", "frontend"):
        names = sorted(n for n, d in plan.items() if d == dest)
        print("%-12s %d" % (dest, len(names)))
        for n in names:
            print("   %s" % n)
    print("\nroot files currently: %d" % len([p for p in ROOT.iterdir() if p.is_file()]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())