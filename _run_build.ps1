Set-Location c:/Users/Pravin/Desktop/main/AT_Trading/frontend
$errLog = "c:/Users/Pravin/Desktop/main/AT_Trading/_ts_build_err.txt"
$out = npm run build 2>&1 | Out-String
$out | Out-File -Encoding utf8 $errLog
if ($out -match "error TS") {
    Write-Host "=== TS ERRORS FOUND ==="
    $out -split "`n" | Where-Object { $_ -match "error TS" } | Select-Object -First 20
}
else {
    Write-Host "=== NO TS ERRORS ==="
}
Write-Host "Done"