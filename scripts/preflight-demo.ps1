<#
  PRE-FLIGHT del video — TPI Metodología I
  Deja listo TODO lo que el video da por sentado. Es idempotente: se puede correr
  las veces que haga falta y no duplica datos.

  Uso (desde la raíz del repo, en PowerShell):
      .\scripts\preflight-demo.ps1

  Qué hace, en orden:
    1. Verifica que el engine de Docker esté arriba.
    2. Levanta PostgreSQL y espera "healthy".
    3. Exporta DATABASE_URL / TEST_DATABASE_URL / SECRET_KEY en ESTA ventana.
    4. Aplica migraciones a tpi_dev.
    5. Crea la clínica B (Clinica Norte) + su admin, si no existe.
    6. Borra lo que el video crea en vivo (box, dentista, paciente, turnos y
       recepcionista) para que cada corrida dé 201 y no 409.
    7. Anota los UUID que el video necesita.
    8. Corre la suite (259 tests) para confirmar que está en verde.
#>

# Los ejecutables nativos (docker, alembic) escriben en stderr aunque todo salga
# bien; con "Stop" eso aborta el script. Se usa "Continue" y se chequea a mano.
$ErrorActionPreference = "Continue"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Step($n, $t) { Write-Host "`n[$n] $t" -ForegroundColor Cyan }
function Ok($t)       { Write-Host "    OK  $t" -ForegroundColor Green }
function Bad($t)      { Write-Host "    !!  $t" -ForegroundColor Red }
function Stop-Here($msg) { Bad $msg; Set-Location $root; exit 1 }

$tmp = Join-Path $env:TEMP "tpi-preflight.log"
Remove-Item $tmp -ErrorAction SilentlyContinue

# ---------------------------------------------------------------- 1. Docker
$ErrorActionPreference = "Continue"
Step "1/8" "Engine de Docker"
$ver = (docker version --format '{{.Server.Version}}' 2>$null)
if ($LASTEXITCODE -ne 0 -or -not $ver) {
  Stop-Here "Docker no está corriendo. Abrí Docker Desktop y esperá a que levante."
}
Ok "engine $ver"

# ---------------------------------------------------------------- 2. PostgreSQL
Step "2/8" "PostgreSQL (puerto 5433)"
docker compose up -d db 2>&1 | Out-File $tmp -Append
if ($LASTEXITCODE -ne 0) { Stop-Here "falló 'docker compose up -d db' (ver $tmp)" }
$st = ""
for ($i = 0; $i -lt 40; $i++) {
  $st = (docker inspect --format '{{.State.Health.Status}}' tpi-metodologia-db 2>$null)
  if ($st -eq "healthy") { break }
  Start-Sleep -Seconds 2
}
if ($st -ne "healthy") { Stop-Here "la base no llegó a healthy (estado: '$st')" }
Ok "tpi-metodologia-db healthy"

# ---------------------------------------------------------------- 3. Entorno
Step "3/8" "Variables de entorno (solo en esta ventana)"
$env:DATABASE_URL      = "postgresql+asyncpg://tpi:tpi@localhost:5433/tpi_dev"
$env:TEST_DATABASE_URL = "postgresql+asyncpg://tpi:tpi@localhost:5433/tpi_test"
$env:SECRET_KEY        = "dev-only-change-me"
Ok "DATABASE_URL / TEST_DATABASE_URL / SECRET_KEY"

Set-Location "$root\backend"
$py = ".\.venv\Scripts\python.exe"

# ---------------------------------------------------------------- 4. Migraciones
Step "4/8" "Migraciones en tpi_dev"
$log = & $py -m alembic upgrade head 2>&1
if ($LASTEXITCODE -ne 0) { $log | ForEach-Object { "    $_" }; Stop-Here "fallaron las migraciones" }
$cur = (& $py -m alembic current 2>&1 | Select-Object -Last 1)
Ok $cur

# ---------------------------------------------------------------- 5. Clínica B
Step "5/8" "Clínica B (para demostrar el aislamiento)"
$env:BOOTSTRAP_ADMIN_PASSWORD = "Dev-Norte-123"
$log = & $py -m app.cli.bootstrap_clinic `
        --name "Clinica Norte" --tax-id "30-99999999-1" `
        --email "admin@clinica-norte.test" --full-name "Bruno Norte" 2>&1
$log | ForEach-Object { "    $_" }
Remove-Item Env:BOOTSTRAP_ADMIN_PASSWORD -ErrorAction SilentlyContinue
if ($LASTEXITCODE -ne 0) { Stop-Here "falló el bootstrap de Clinica Norte" }

# ---------------------------------------------------------------- 6. Limpieza
Step "6/8" "Borrar lo que el video crea en vivo (turnos, box, dentista, paciente, recepcionista)"
# Orden obligatorio: primero los turnos (FK a box/user/patient), después los
# recursos. La clínica se identifica por su tax_id para no tocar la Clinica Norte.
$sql = "DELETE FROM appointments WHERE clinic_id = (SELECT id FROM clinics WHERE tax_id = '30-12345678-9') " +
       "AND (dentist_id IN (SELECT id FROM users WHERE email = 'dentista@demo-bootstrap.com') " +
       "OR patient_id IN (SELECT id FROM patients WHERE dni = 'DEMO0001') " +
       "OR box_id IN (SELECT id FROM boxes WHERE name = 'Box Demo 1')); " +
       "DELETE FROM users WHERE email = 'dentista@demo-bootstrap.com'; " +
       "DELETE FROM patients WHERE dni = 'DEMO0001'; " +
       "DELETE FROM boxes WHERE name = 'Box Demo 1'; " +
       "DELETE FROM refresh_tokens WHERE user_id IN (SELECT id FROM users WHERE email = 'recepcion@demo-bootstrap.com'); " +
       "DELETE FROM users WHERE email = 'recepcion@demo-bootstrap.com';"
docker exec tpi-metodologia-db psql -U tpi -d tpi_dev -q -c $sql 2>&1 | Out-File $tmp -Append
if ($LASTEXITCODE -ne 0) { Bad "no se pudo limpiar (ver $tmp)" } else { Ok "turnos + box + dentista + paciente + recepcionista eliminados" }

# ---------------------------------------------------------------- 7. UUID
Step "7/8" "UUID que el video necesita"
function Scalar($q) {
  $v = (docker exec tpi-metodologia-db psql -U tpi -d tpi_dev -t -A -c $q 2>$null | Select-Object -First 1)
  return "$v".Trim()
}

$clinicA = Scalar "select id from clinics where tax_id = '30-12345678-9'"
$adminA  = Scalar "select id from users where email = 'admin@demo-bootstrap.com'"
$adminB  = Scalar "select id from users where email = 'admin@clinica-norte.test'"
$clinics = Scalar "select count(*) from clinics"
$users   = Scalar "select count(*) from users"

if (-not $adminB) { Stop-Here "no se pudo obtener el admin de Clinica Norte" }

$idsPath = Join-Path $env:TEMP "tpi-demo-ids.json"
[ordered]@{
  clinic_a      = $clinicA
  admin_a       = $adminA
  admin_b_ajeno = $adminB
  generado      = (Get-Date -Format "yyyy-MM-dd HH:mm")
} | ConvertTo-Json | Set-Content -Path $idsPath -Encoding utf8

Write-Host "    clínicas en tpi_dev : $clinics"  -ForegroundColor Gray
Write-Host "    usuarios en tpi_dev : $users"    -ForegroundColor Gray
Write-Host "    admin de Norte      : $adminB"  -ForegroundColor Yellow
Write-Host "    guardado en         : $idsPath" -ForegroundColor DarkGray

# ---------------------------------------------------------------- 8. Suite
Step "8/8" "Suite de tests (259 tests sobre PostgreSQL)"
$log = & $py -m pytest -q 2>&1
$log | Select-Object -Last 2 | ForEach-Object { "    $_" }
if ($LASTEXITCODE -ne 0) { Stop-Here "la suite NO está en verde; no grabes todavía" }
Ok "suite en verde"

Set-Location $root

Write-Host "`n=== LISTO PARA GRABAR ===" -ForegroundColor Green
Write-Host "Abrí una SEGUNDA ventana de PowerShell y arrancá el servidor:" -ForegroundColor White
Write-Host @'
  cd "C:\Users\Mateows\Desktop\Parciales y Base de Datos\TPI METODOLOGIA\backend"
  $env:DATABASE_URL="postgresql+asyncpg://tpi:tpi@localhost:5433/tpi_dev"
  $env:TEST_DATABASE_URL="postgresql+asyncpg://tpi:tpi@localhost:5433/tpi_test"
  $env:SECRET_KEY="dev-only-change-me"
  .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
'@ -ForegroundColor Gray
Write-Host "Después, en una TERCERA ventana:  .\scripts\demo-video.ps1" -ForegroundColor White
