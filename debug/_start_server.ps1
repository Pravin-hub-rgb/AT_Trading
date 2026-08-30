cd "C:\Users\Pravin\Desktop\main\AT_Trading\backend"
$proc = Start-Process -FilePath "powershell.exe" -ArgumentList "-ExecutionPolicy","Bypass","-File","dev-py.ps1","C:\Users\Pravin\Desktop\main\AT_Trading\backend\venv\Scripts\python.exe","server.py" -PassThru -WindowStyle Hidden
Write-Host "Started server with PID: $($proc.Id)"
Start-Sleep -Seconds 8
$connections = Get-NetTCPConnection -State Listen | Where-Object {$_.LocalPort -in 8003,8004}
foreach ($c in $connections) {
    $p = Get-Process -Id $c.OwningProcess -ErrorAction SilentlyContinue
    Write-Host "Port $($c.LocalPort) -> PID $($c.OwningProcess) -> $($p.Path)"
}
