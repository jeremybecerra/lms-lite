# Reset de base y seed
if (Test-Path ..\lms.db) { Remove-Item ..\lms.db }
Write-Host "DB eliminada. Inicia la API con: python run.py"
Write-Host "Luego corre el seed: powershell -ExecutionPolicy Bypass -File .\scripts\seed_http.ps1"
