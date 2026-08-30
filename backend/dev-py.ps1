param([string]$Py, [string]$Srv)

# Dev wrapper: auto-restarts the backend when it dies with a non-zero exit
# (e.g. the sporadic exit code 4294967295 native crash on Windows).
# A clean shutdown (exit 0, e.g. Ctrl+C handled by uvicorn) stops the loop.
# NOTE: ASCII ONLY - PowerShell 5.1 reads BOM-less ps1 files as ANSI and any
# non-ASCII char (em-dash etc.) corrupts parsing.
while ($true) {
  Write-Host "[py] backend starting..."
  & $Py $Srv
  $code = $LASTEXITCODE
  if ($code -eq 0) {
    Write-Host "[py] backend exited cleanly ($code) - not restarting."
    break
  }
  # Exit code 3 = uvicorn startup failure, almost always "port already in
  # use" (10048). Another backend instance is holding the port - restarting
  # forever just spams the log. Stop and tell the user.
  if ($code -eq 3) {
    Write-Host "[py] backend could not START (exit 3) - port 8003 is already in use by another instance."
    Write-Host "[py] Not restarting. Kill the other backend (or close this window) and run again."
    break
  }
  Write-Host "[py] backend CRASHED with exit code $code - restarting in 2s ..."
  Start-Sleep -Seconds 2
}