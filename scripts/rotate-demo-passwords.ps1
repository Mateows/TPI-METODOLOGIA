<#
  ROTA LAS CONTRASEÑAS DEMO DE LA BASE LOCAL — TPI Metodología I

  Las contraseñas demo originales quedaron en el historial de git. Este script
  las reemplaza en la base local por las de scripts/demo-env.ps1, así los valores
  históricos dejan de servir.

  Uso (desde la raíz del repo, con Docker arriba):
      .\scripts\rotate-demo-passwords.ps1

  No imprime contraseñas ni hashes. Es idempotente: se puede correr las veces
  que haga falta.
#>

$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Stop-Here($msg) {
  Write-Host "`n[!!] $msg" -ForegroundColor Red
  Set-Location $root
  exit 1
}

$envFile = Join-Path $PSScriptRoot "demo-env.ps1"
if (-not (Test-Path $envFile)) {
  Stop-Here "falta scripts/demo-env.ps1. Copiá la plantilla: Copy-Item scripts/demo-env.example.ps1 scripts/demo-env.ps1"
}
. $envFile

$missing = @()
if (-not $env:TPI_DEMO_PASSWORD_A)         { $missing += "TPI_DEMO_PASSWORD_A" }
if (-not $env:TPI_DEMO_PASSWORD_B)         { $missing += "TPI_DEMO_PASSWORD_B" }
if (-not $env:TPI_DEMO_PASSWORD_RECEPCION) { $missing += "TPI_DEMO_PASSWORD_RECEPCION" }
if ($missing.Count -gt 0) { Stop-Here "faltan variables: $($missing -join ', ')" }

Write-Host "`n[1/3] PostgreSQL" -ForegroundColor Cyan
$st = (docker inspect --format '{{.State.Health.Status}}' tpi-metodologia-db 2>$null)
if ($st -ne "healthy") {
  $st = (docker inspect --format '{{.State.Health.Status}}' tpi-metodologia-db-1 2>$null)
}
if ($st -ne "healthy") {
  Stop-Here "la base no está healthy (estado: '$st'). Levantala con: docker compose up -d db"
}
Write-Host "    OK  tpi-metodologia-db healthy" -ForegroundColor Green

Write-Host "`n[2/3] Rotación de contraseñas" -ForegroundColor Cyan
Set-Location "$root\backend"
$py = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { Stop-Here "no existe $py" }

$env:DATABASE_URL = "postgresql+asyncpg://tpi:tpi@localhost:5433/tpi_dev"

$rotate = @'
import asyncio
import os
from sqlalchemy import select
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User

TARGETS = [
    ("admin@demo-bootstrap.com", "TPI_DEMO_PASSWORD_A"),
    ("admin@clinica-norte.test", "TPI_DEMO_PASSWORD_B"),
    ("recepcion@demo-bootstrap.com", "TPI_DEMO_PASSWORD_RECEPCION"),
]

async def main():
    async with SessionLocal() as s:
        for email, var in TARGETS:
            u = (await s.execute(select(User).where(User.email == email))).scalar_one_or_none()
            if u is None:
                print(f"{email}: ausente (se crea en el demo)")
                continue
            u.password_hash = hash_password(os.environ[var])
            print(f"{email}: rotada")
        await s.commit()

asyncio.run(main())
'@

$out = ($rotate | & $py - 2>&1)
if ($LASTEXITCODE -ne 0) {
  $out | ForEach-Object { "    $_" }
  Stop-Here "falló la rotación"
}
$out | ForEach-Object { Write-Host "    $_" }

Write-Host "`n[3/3] Verificación (sin imprimir secretos)" -ForegroundColor Cyan
$verify = @'
import asyncio
import os
from sqlalchemy import select
from app.core.database import SessionLocal
from app.core.security import verify_password
from app.models.user import User

TARGETS = [
    ("admin@demo-bootstrap.com", "TPI_DEMO_PASSWORD_A"),
    ("admin@clinica-norte.test", "TPI_DEMO_PASSWORD_B"),
]

async def main():
    ok = True
    async with SessionLocal() as s:
        for email, var in TARGETS:
            u = (await s.execute(select(User).where(User.email == email))).scalar_one_or_none()
            if u is None:
                print(f"{email}: AUSENTE")
                ok = False
            elif verify_password(os.environ[var], u.password_hash):
                print(f"{email}: OK")
            else:
                print(f"{email}: MISMATCH")
                ok = False
    print("RESULT:", "OK" if ok else "FAIL")

asyncio.run(main())
'@

$out = ($verify | & $py - 2>&1)
if ($LASTEXITCODE -ne 0) {
  $out | ForEach-Object { "    $_" }
  Stop-Here "falló la verificación"
}
$out | ForEach-Object { Write-Host "    $_" }
if (($out | Select-Object -Last 1) -notmatch "RESULT: OK") { Stop-Here "la verificación no dio OK" }

Set-Location $root
Write-Host "`n=== CONTRASEÑAS DEMO ROTADAS ===" -ForegroundColor Green
Write-Host "Las credenciales vigentes están en scripts/demo-env.ps1 (ignorado por git)." -ForegroundColor Gray
