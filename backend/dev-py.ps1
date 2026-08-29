param([string]$Py, [string]$Srv)

# Dev wrapper: auto-restarts the backend when it dies with a non-zero exit
# (e.g. the sporadic exit code 4294967295 native crash on Windows).
# A clean shutdown (exit 0, e.g. Ctrl+C handled by uvicorn) stops the loop.
while ($true) {
  Write-Host "[py] backend starting..."
  & $Py $Srv
  $code = $LASTEXITCODE
  if ($code -eq 0) {
    Write-Host "[py] backend exited cleanly ($code) — not restarting."
    break
  }
  Write-Host "[py] backend CRASHED with exit code $code — restarting in 2s ..."
  Start-Sleep -Seconds 2
}