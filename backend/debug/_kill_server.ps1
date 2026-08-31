$conns = Get-NetTCPConnection -LocalPort 8003 -State Listen -ErrorAction SilentlyContinue
foreach ($c in $conns) {
    $p = $c.OwningProcess
    Write-Host "Killing PID $p"
    try { Stop-Process -Id $p -Force -ErrorAction Stop } catch { Write-Host "  (already gone)" }
}
Start-Sleep -Seconds 2
Write-Host "--- After kill ---"
Get-NetTCPConnection -LocalPort 8003 -ErrorAction SilentlyContinue | Format-Table -AutoSize
