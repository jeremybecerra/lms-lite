param(
  [switch]$Seed
)

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$proj = Split-Path $root
$venv = Join-Path $proj ".venv\Scripts\Activate.ps1"

# 1) API en nueva ventana
Start-Process powershell -ArgumentList @(
  '-NoExit','-Command',
  "cd `"$proj`"; Set-ExecutionPolicy -Scope Process Bypass; . `"$venv`"; python run.py"
)

# 2) Esperar health
Write-Host "Esperando API..." -NoNewline
$ok=$false
for ($i=0; $i -lt 30; $i++) {
  Start-Sleep -Milliseconds 700
  try {
    $r = Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/health" -ErrorAction Stop
    if ($r.status -eq 'ok') { $ok=$true; break }
  } catch {}
  Write-Host "." -NoNewline
}
Write-Host ""
if (-not $ok) { Write-Host "API no respondió a tiempo." -ForegroundColor Yellow }

# 3) Seed opcional
if ($Seed -and $ok) {
  Write-Host "Corriendo seed..."
  powershell -ExecutionPolicy Bypass -File (Join-Path $root "seed_http.ps1")
}

# 4) Frontend en nueva ventana
Start-Process powershell -ArgumentList @(
  '-NoExit','-Command',
  "cd `"$proj\web`"; python -m http.server 8000"
)
Write-Host "Listo. Frontend: http://127.0.0.1:8000"
