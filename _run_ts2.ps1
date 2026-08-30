Set-Location c:/Users/Pravin/Desktop/main/AT_Trading/frontend
$out = npx tsc --noEmit 2>&1
$out | Out-File -Encoding utf8 c:/Users/Pravin/Desktop/main/AT_Trading/_ts_out5.txt
Write-Host "---OUTPUT START---"
Get-Content c:/Users/Pravin/Desktop/main/AT_Trading/_ts_out5.txt
Write-Host "---OUTPUT END---"
Write-Host "Exit code captured separately."