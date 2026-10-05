<#
.SYNOPSIS
    Run only the checks a change actually needs.

.DESCRIPTION
    Every gate in backtest/tests answers a different question, and running all of
    them after every edit is slow and mostly meaningless. This script reads what
    changed against git and picks the gates that can be affected, so a one-line
    registry edit costs two seconds and an engine change costs the ten minutes it
    genuinely needs.

    The mapping is deliberately conservative - a change to a shared file runs
    every gate that reads that file, including the slow ones. Being wrong in that
    direction wastes minutes; being wrong in the other direction ships a number
    nobody checked.

    Always:
      exp_craze_patch_gate check     ~20s   patched engine byte-identical
      exp_origin_lookahead          ~30s   no candidate carries a closed knob
      exp_registry_snapshot         ~3s    registry surface, when registry changed

    Scoped:
      exp_fastcheck <book>...       ~50s per book
      exp_port_differential         ~10 min, engine only

    Slow, needs -AllowAll:
      exp_fastcheck --all            ~2 h
      exp_pinverify --all            ~30 min

.PARAMETER Book
    Books to fastcheck. Omitted means the fastcheck step is skipped unless
    -AllowAll, so this script never silently runs two hours.

.PARAMETER AllowAll
    Permit the slow gates.

.PARAMETER WhatIf
    Print the plan and stop.

.PARAMETER Base
    Commit to diff against when deciding what changed. Defaults to the merge-base
    with main, which is wrong when main has moved ahead of where this branch
    started - the diff then lists files this branch never touched. Pass the
    branch's first commit explicitly when that happens:  git log --oneline
    will show it, or use the commit before the branch's work began.

.EXAMPLE
    .\verify.ps1
    The three fast gates.

.EXAMPLE
    .\verify.ps1 -Book fsent_sig_full
    Fast gates plus one book's fastcheck.

.EXAMPLE
    .\verify.ps1 -Base 6cbb46a
    Judge the change set from this branch's real starting point.

.EXAMPLE
    .\verify.ps1 -Book fsent_sig_full,champion_multi_sw10 -WhatIf
#>
[CmdletBinding()]
param(
    [string[]]$Book = @(),
    [string]$Base = "",
    [switch]$AllowAll,
    [switch]$WhatIf
)

# PowerShell turns any stderr from a native command into a terminating error
# under "Stop", and git writes CRLF notices there routinely. The exit code is
# what actually decides whether a gate passed, so that is what this checks.
$ErrorActionPreference = "Continue"

# The script lives at the repo root, so that is where the tools expect to be.
Set-Location $PSScriptRoot

function Write-Step($m) { Write-Host "==> $m" -ForegroundColor Cyan }
function Write-Skip($m) { Write-Host "    skip: $m" -ForegroundColor DarkGray }
function Hit([string]$p) {
    foreach ($f in $script:changed) { if ($f -like $p) { return $true } }
    return $false
}
# git diff/list, with stderr discarded so a CRLF warning cannot abort the run.
function GitOut([string[]]$gitArgs) {
    return @(git @gitArgs 2>$null)
}

# ---------------------------------------------------------------------------
# What changed, since the branch point AND in the working tree, so this works
# mid-edit and not only on a finished branch.
# ---------------------------------------------------------------------------
$branch = (git rev-parse --abbrev-ref HEAD 2>$null).Trim()
if (-not $Base) {
    foreach ($cand in @("origin/main", "origin/master", "main", "master")) {
        $found = git merge-base HEAD $cand 2>$null
        if ($LASTEXITCODE -eq 0 -and $found) { $Base = $found.Trim(); break }
    }
}
if ($Base) {
    $committed = @(git diff --name-only "$Base..HEAD" 2>$null)
} else {
    $committed = @()
    Write-Host "no base found; judging only the working tree" -ForegroundColor Yellow
}
$uncommitted = @(git diff --name-only HEAD 2>$null)
$untracked   = @(git ls-files --others --exclude-standard 2>$null)
$changed = @($committed + $uncommitted + $untracked |
             Where-Object { $_ } | Sort-Object -Unique)

Write-Host ""
Write-Host "branch: $branch   base: $(if($Base -and $Base.Length -ge 7){$Base.Substring(0,7)}else{$Base})   changed: $($changed.Count) file(s)" -ForegroundColor White
foreach ($c in $changed) { Write-Host "    $c" -ForegroundColor DarkGray }
Write-Host ""

$engine    = Hit "backend/src/btc/engines/htf_ltf/*"
$patch     = Hit "backtest/tests/test_experiments_craze.py"
$registry  = (Hit "backtest/tests/registry/*") -or (Hit "backtest/tests/experiment_registry.py")
$fastcheck = $registry -or (Hit "backtest/tests/exp_fastcheck.py") -or $engine -or $patch

$plan = @()
$plan += [pscustomobject]@{ Name = "exp_craze_patch_gate check"
                           Cost = "~20s"; Args = @("backtest/tests/exp_craze_patch_gate.py", "check") }
$plan += [pscustomobject]@{ Name = "exp_origin_lookahead"
                           Cost = "~30s"; Args = @("backtest/tests/exp_origin_lookahead.py") }
if ($registry) {
    $snap = "backtest/tests/_registry_before.json"
    $regDirty = $false
    foreach ($f in $uncommitted) {
        if ($f -like "backtest/tests/registry/*" -or
            $f -eq "backtest/tests/experiment_registry.py") { $regDirty = $true; break }
    }
    if (-not $WhatIf -and $regDirty) {
        if (-not (Test-Path $snap)) {
            Write-Host "    note: registry edited but no baseline - writing one now." -ForegroundColor Yellow
            & python backtest/tests/exp_registry_snapshot.py write $snap | Out-Null
        }
    }
    if ($regDirty) {
        $plan += [pscustomobject]@{ Name = "exp_registry_snapshot check (vs pre-edit baseline)"
                                   Cost = "~3s"; Args = @("backtest/tests/exp_registry_snapshot.py", "check", $snap) }
    } else {
        $plan += [pscustomobject]@{ Name = "exp_registry_snapshot (re-anchor baseline to HEAD)"
                                   Cost = "~3s"; Args = @("backtest/tests/exp_registry_snapshot.py", "write", $snap) }
    }
}

# Docs or the registry changed: the number gate has something new to judge.
# It is only meaningful once the db exists, so it is skipped rather than failed
# on a fresh clone - an absent db is not evidence of anything being wrong.
$docsOrRegistry = $registry -or (Hit "backtest/docs/*") -or (Hit "backtest/tests/_artefacts.json")
if ($docsOrRegistry) {
    if (Test-Path "backtest/tests/results.db") {
        $plan += [pscustomobject]@{ Name = "exp_resultsdb check (doc numbers vs the database)"
                                   Cost = "~20s"; Args = @("backtest/tests/exp_resultsdb.py", "check") }
    } else {
        Write-Skip "exp_resultsdb check needs backtest/tests/results.db - run: python backtest/tests/exp_resultsdb.py ingest"
    }
}
if ($engine) {
    $plan += [pscustomobject]@{ Name = "exp_port_differential"
                               Cost = "~10 min"; Args = @("backtest/tests/exp_port_differential.py") }
}
# An explicit -Book is a request, not a hint: run it even if no tracked file
# changed. Otherwise a typo'd name or a wrong -Base silently skips the one gate
# the user asked for, and the run still reports PASS.
#
# -Book a,b arrives here as ONE string, and passing that through verbatim makes
# exp_fastcheck look for a book literally named "a,b" and report "not pinned
# books". Split on commas and whitespace so both forms work.
$bookNames = @()
foreach ($b in $Book) { $bookNames += ($b -split '[,\s]+' | Where-Object { $_ }) }
if ($bookNames.Count -gt 0) {
    $plan += [pscustomobject]@{ Name = "exp_fastcheck $($bookNames -join ', ')"
                               Cost = "~50s/book"
                               Args = (@("backtest/tests/exp_fastcheck.py") + $bookNames) }
} elseif ($fastcheck -and $AllowAll) {
    $plan += [pscustomobject]@{ Name = "exp_fastcheck --all"
                               Cost = "~2 h"; Args = @("backtest/tests/exp_fastcheck.py", "--all") }
} elseif ($fastcheck) {
    Write-Skip "exp_fastcheck needs -Book <name> (or -AllowAll for all 209)"
}

Write-Host "PLAN" -ForegroundColor Cyan
if ($plan.Count -eq 0) { Write-Host "    nothing to run" -ForegroundColor DarkGray }
foreach ($p in $plan) { Write-Host ("    {0,-46} {1}" -f $p.Name, $p.Cost) }
Write-Host ""
if ($WhatIf) { Write-Host "--WhatIf: stopping." -ForegroundColor Yellow; return }

$failed = @()
foreach ($p in $plan) {
    Write-Step $p.Name
    & python @($p.Args)
    if ($LASTEXITCODE -ne 0) { $failed += $p.Name }
    Write-Host ""
}

Write-Host ("=" * 62)

# Every gate in this repo writes its output next to whatever ran it, and this
# script runs from the root, so a session leaves _gate.txt, _gatee.txt and a
# _faN.txt per batch behind. They are all covered by .gitignore, which is
# exactly why they pile up unnoticed - ignored is not cleaned. Two hundred and
# eighteen had built up in this root before clean-root.ps1 existed, and the
# Bybit CSVs were lost once already for being ignored in the wrong place.
# Running the clear here means a verification leaves the root as it found it.
$cleaner = Join-Path $PSScriptRoot "clean-root.ps1"
if (Test-Path $cleaner) {
    & powershell -ExecutionPolicy Bypass -File $cleaner 2>$null |
        Select-Object -First 1 | ForEach-Object { Write-Host $_ -ForegroundColor DarkGray }
}

if ($failed.Count -eq 0) {
    Write-Host "PASS - $($plan.Count) gate(s) green." -ForegroundColor Green
    if (-not $AllowAll) {
        Write-Host "      fastcheck was scoped or skipped. For the registry-wide" -ForegroundColor DarkGray
        Write-Host "      claim run: .\verify.ps1 -Book <name>   or   -AllowAll" -ForegroundColor DarkGray
    }
} else {
    Write-Host "FAIL - $($failed.Count) gate(s):" -ForegroundColor Red
    foreach ($f in $failed) { Write-Host "    $f" -ForegroundColor Red }
}
Write-Host ("=" * 62)
if ($failed.Count -gt 0) { exit 1 }