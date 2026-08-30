Set-Location c:/Users/Pravin/Desktop/main/AT_Trading/frontend
npx tsc --noEmit 2>&1 | Out-File -Encoding utf8 c:/Users/Pravin/Desktop/main/AT_Trading/_ts_out2.txt
Get-Content c:/Users/Pravin/Desktop/main/AT_Trading/_ts_out2.txt