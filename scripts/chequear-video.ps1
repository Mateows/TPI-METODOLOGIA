<#
  CHEQUEO RÁPIDO ANTES DE GRABAR — TPI Metodología I

  Verifica en menos de 10 segundos TODO lo que los comandos de la hoja dan por
  hecho, para que un comando no falle en cámara por una causa que no se ve.

  Uso (desde la raíz del repo):
      .\scripts\chequear-video.ps1

  Salida: una línea [OK] o [FALTA] por chequeo.
  Código de salida 0 = listo para grabar; 1 = falta algo (dice qué).
#>

$ErrorActionPreference = "Continue"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$script:fail = 0
function Ok($m)   { Write-Host "  [OK]    $m" -ForegroundColor Green }
function Bad($m)  { Write-Host "  [FALTA] $m" -ForegroundColor Red; $script:fail++ }
function Info($m) { Write-Host "  [info]  $m" -ForegroundColor DarkGray }

Write-Host "`n=== CHEQUEO PREVIO A GRABAR ===" -ForegroundColor Cyan
Write-Host "  carpeta: $root" -ForegroundColor DarkGray

# ---------------------------------------------------------------- 1. Python
$py = Join-Path $root "backend\.venv\Scripts\python.exe"
if (Test-Path $py) {
  $v = (& $py --version 2>&1)
  Ok "Python del venv: $v"
} else {
  Bad "no existe backend\.venv\Scripts\python.exe (creá el venv del backend)"
}

# ---------------------------------------------------------------- 2. Docker
$ver = (docker version --format '{{.Server.Version}}' 2>$null)
if ($LASTEXITCODE -eq 0 -and $ver) {
  Ok "Docker engine $ver"
} else {
  Bad "Docker no responde: abrí Docker Desktop y esperá a que levante"
}

# ---------------------------------------------------------------- 3. PostgreSQL
$st = (docker inspect --format '{{.State.Health.Status}}' tpi-metodologia-db 2>$null)
if ($st -eq "healthy") {
  Ok "PostgreSQL tpi-metodologia-db healthy (puerto 5433)"
} else {
  Bad "PostgreSQL no está healthy (estado '$st'): corré .\scripts\preflight-demo.ps1"
}

# ---------------------------------------------------------------- 4. API
$code = ""
try { $code = (& curl.exe -sS -m 3 -o NUL -w "%{http_code}" "http://127.0.0.1:8000/health" 2>$null) } catch { }
if ("$code" -eq "200") {
  Ok "API responde /health 200 en http://127.0.0.1:8000"
} else {
  Bad "la API no responde en http://127.0.0.1:8000 (arrancala en OTRA ventana; comando abajo)"
}

# ---------------------------------------------------------------- 5. ids del preflight
$ids = Join-Path $env:TEMP "tpi-demo-ids.json"
if (Test-Path $ids) {
  Ok "ids del demo: $ids"
} else {
  Bad "falta ${ids}: corré .\scripts\preflight-demo.ps1"
}

# ---------------------------------------------------------------- 6. Archivos que se muestran
$files = @(
  "CHANGES.md",
  "openspec\changes\archive\2026-10-09-foundation-setup",
  "openspec\changes\archive\2026-11-04-core-models-tenants",
  "openspec\changes\archive\2026-11-04-patient-management",
  "openspec\changes\archive\2026-11-05-appointment-agenda",
  "openspec\specs\appointment-agenda\spec.md",
  "backend\app\repositories\patients.py",
  "backend\app\services\patients.py",
  "backend\app\services\appointments.py",
  "backend\app\repositories\appointments.py",
  "backend\tests\test_architecture.py",
  ".agents\skills\revisor-de-agendas-de-citas\SKILL.md",
  ".atl\skill-registry.md",
  "docs\skills-mcp\evidencias\mcp-github-c04.md"
)
$missing = @()
foreach ($f in $files) {
  if (-not (Test-Path (Join-Path $root $f))) { $missing += $f }
}
if ($missing.Count -eq 0) {
  Ok "todos los archivos que se muestran existen"
} else {
  Bad ("faltan archivos: " + ($missing -join ", "))
}

# ---------------------------------------------------------------- 7. opencode + token MCP
if (Get-Command opencode -ErrorAction SilentlyContinue) {
  Ok "opencode en PATH"
} else {
  Bad "opencode no está en PATH"
}
if ($env:GITHUB_PERSONAL_ACCESS_TOKEN) {
  Ok "token del MCP cargado (largo $($env:GITHUB_PERSONAL_ACCESS_TOKEN.Length); no se muestra)"
} else {
  Bad "falta GITHUB_PERSONAL_ACCESS_TOKEN en ESTA ventana"
}

# ---------------------------------------------------------------- 8. Scripts del demo
foreach ($s in @("scripts\demo-video.ps1", "scripts\preflight-demo.ps1")) {
  if (Test-Path (Join-Path $root $s)) { Ok "existe $s" } else { Bad "falta $s" }
}

# ---------------------------------------------------------------- Resumen
if ($script:fail -eq 0) {
  Write-Host "`n=== LISTO PARA GRABAR ===" -ForegroundColor Green
  exit 0
}

Write-Host "`n=== NO GRABES TODAVÍA: $($script:fail) chequeo(s) fallaron ===" -ForegroundColor Red

$backend = Join-Path $root "backend"
$ayuda = @"

Arreglos rápidos:
  - Docker/PostgreSQL:  abrí Docker Desktop y corré  .\scripts\preflight-demo.ps1
  - API caída:          abrí OTRA ventana y corré:

      Set-Location "$backend"
      `$env:DATABASE_URL="postgresql+asyncpg://tpi:tpi@localhost:5433/tpi_dev"
      `$env:TEST_DATABASE_URL="postgresql+asyncpg://tpi:tpi@localhost:5433/tpi_test"
      `$env:SECRET_KEY="dev-only-change-me"
      .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000

  - Token del MCP:      `$env:GITHUB_PERSONAL_ACCESS_TOKEN="tu_pat"   (en ESTA ventana)
"@
Write-Host $ayuda -ForegroundColor Gray

exit 1
