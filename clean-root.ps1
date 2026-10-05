<#
.SYNOPSIS
    Clear the transient captures that collect in the repo root.

.DESCRIPTION
    Every gate writes its output next to whatever ran it, and everything in this
    repository runs from the root. So a session leaves behind a `_gate.txt`, a
    `_gatee.txt` for stderr, a `_fa1.txt` per batch, and so on. They are all
    covered by the `/_*.txt` and friends entries in .gitignore, which is why
    git never complains - and also why they accumulate: ignored is not the same
    as cleaned. Two hundred and eighteen files had built up in the root before
    this script existed.

    This removes only those. It touches nothing tracked, nothing in a
    subdirectory, and nothing that .gitignore does not already exclude, so it is
    strictly narrower than `git clean -fdx`, which would also take the Bybit
    CSVs if they were still inside the repo. That is not a hypothetical: those
    datasets were lost exactly that way once already, and they now live in
    <repo>/../btc_data for the reason.

    Safe to run without a dry-run. Run it at the end of a session.

.PARAMETER DryRun
    List what would be removed without removing it.

.EXAMPLE
    .\clean-root.ps1
.EXAMPLE
    .\clean-root.ps1 -DryRun
#>
[CmdletBinding()]
param([switch]$DryRun)

Set-Location $PSScriptRoot

# Exactly the patterns .gitignore already applies at the root. Anything not
# matching these is a real file and is not touched.
$patterns = @('_*.txt', '_*.log', '_*.json', '_*.jsonl', '_*.py', '_*.ps1')

$tracked = @{}
git ls-files 2>$null | ForEach-Object {
    $tracked[(Split-Path $_ -Leaf)] = $true
    $tracked[$_] = $true
}

$victims = Get-ChildItem -File | Where-Object {
    $n = $_.Name
    -not $tracked.ContainsKey($n) -and
    -not $tracked.ContainsKey($n) -and
    ($patterns | Where-Object { $n -like $_ })
}

if ($DryRun) {
    Write-Host "would remove $($victims.Count) file(s):" -ForegroundColor Cyan
    $victims | ForEach-Object { Write-Host "   $($_.Name)" }
    return
}

$freed = ($victims | Measure-Object Length -Sum).Sum
$victims | Remove-Item -Force -ErrorAction SilentlyContinue
Write-Host ("root scratch: removed {0} file(s), {1:N1} KB" -f $victims.Count, ($freed / 1KB))
Write-Host ("root files remaining: {0}" -f (Get-ChildItem -File).Count)