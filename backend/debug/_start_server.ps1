$projectDir = "C:\Users\Pravin\Desktop\main\AT_Trading"
$backendDir = Join-Path $projectDir "backend"

# Kill any existing Python servers on port 8003
Get-NetTCPConnection -LocalPort 8003 -ErrorAction SilentlyContinue | ForEach-Object {
    Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Milliseconds 500

# Start new server using the script file
$proc = Start-Process -FilePath "python" -ArgumentList "debug\_run_server.py" -WorkingDirectory $backendDir -PassThru -NoNewWindow

Start-Sleep -Seconds 6

# Check health
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8003/api/swings?limit=1" -TimeoutSec 5
    Write-Host "Server ready, status: $($response.StatusCode)"
}
catch {
    Write-Host "Server health check failed: $_"
}
