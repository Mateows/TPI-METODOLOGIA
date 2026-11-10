<#
  BLOQUES DEL VIDEO — TPI Metodología I
  Ejecuta, en orden, exactamente lo que se muestra en cámara. No imprime tokens:
  solo el rol y el largo del access token (la consigna pide no exponerlos).

  Requisitos previos (los deja listos scripts\preflight-demo.ps1):
    - PostgreSQL arriba con Clinica Demo Bootstrap (A) y Clinica Norte (B)
    - uvicorn corriendo en http://127.0.0.1:8000

  Uso (ventana aparte, desde la raíz del repo):
      .\scripts\demo-video.ps1                  # secuencia completa
      .\scripts\demo-video.ps1 -SkipGrace       # sin el bloque de 11 s de la ventana de gracia

  LÍNEA DE TIEMPO DEL VIDEO (este script cubre P7 y P8, de 6:45 a 9:45):
      P1-P4  editor: CHANGES.md, openspec/changes/archive/, specs y services
      P5-P6  editor: docs/skills-mcp/ (skill y MCP)
      P7     terminal: pytest -q  ->  259 passed
      P8     terminal: este script (bloques 0-18)

  Los bloques 9-18 crean en vivo un box, un dentista, un paciente y los turnos
  (no hay datos de agenda precargados). El preflight solo limpia lo que dejó
  una corrida anterior.
#>

param(
  [string]$Base = "http://127.0.0.1:8000",
  [switch]$SkipGrace
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

# ---------------------------------------------------------------- Credenciales
# Las contraseñas del demo no viven en el repo: se leen de variables de entorno.
# Copiá scripts/demo-env.example.ps1 a scripts/demo-env.ps1 (ignorado por git) y
# completá los valores de tu base local.
$envFile = Join-Path $PSScriptRoot "demo-env.ps1"
if (Test-Path $envFile) { . $envFile }

$DemoPasswordA         = $env:TPI_DEMO_PASSWORD_A
$DemoPasswordB         = $env:TPI_DEMO_PASSWORD_B
$DemoPasswordReception = $env:TPI_DEMO_PASSWORD_RECEPCION

$missing = @()
if (-not $DemoPasswordA)         { $missing += "TPI_DEMO_PASSWORD_A" }
if (-not $DemoPasswordB)         { $missing += "TPI_DEMO_PASSWORD_B" }
if (-not $DemoPasswordReception) { $missing += "TPI_DEMO_PASSWORD_RECEPCION" }
if ($missing.Count -gt 0) {
  Write-Host "`nFaltan credenciales del demo: $($missing -join ', ')." -ForegroundColor Red
  Write-Host "Copiá la plantilla y completá los valores de tu base local:" -ForegroundColor Yellow
  Write-Host "  Copy-Item scripts/demo-env.example.ps1 scripts/demo-env.ps1" -ForegroundColor Gray
  return
}

function Section($t) { Write-Host "`n============================================================" -ForegroundColor DarkCyan
                       Write-Host "  $t" -ForegroundColor Cyan
                       Write-Host "============================================================" -ForegroundColor DarkCyan }
function Note($t)    { Write-Host "  $t" -ForegroundColor DarkGray }

# ---------------------------------------------------------------- Precondición
# Si la API no está arriba, cada bloque fallaría con un error poco claro. Se
# corta acá con el comando exacto para arrancarla.
$health = ""
try { $health = (& curl.exe -sS -m 3 -o NUL -w "%{http_code}" "$Base/health" 2>$null) } catch { }
if ("$health" -ne "200") {
  Write-Host "`nLa API no responde en $Base/health (status '$health')." -ForegroundColor Red
  Write-Host "Abrí OTRA ventana de PowerShell y corré:" -ForegroundColor Yellow
  Write-Host @"
  Set-Location "$root\backend"
  `$env:DATABASE_URL="postgresql+asyncpg://tpi:tpi@localhost:5433/tpi_dev"
  `$env:TEST_DATABASE_URL="postgresql+asyncpg://tpi:tpi@localhost:5433/tpi_test"
  `$env:SECRET_KEY="dev-only-change-me"
  .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
"@ -ForegroundColor Gray
  Write-Host "Después volvé a correr este script." -ForegroundColor Yellow
  return
}

function Call($method, $path, $body, $token) {
  $cargs = @("-s", "-w", "`nHTTP %{http_code}`n", "-X", $method)
  if ($body) {
    # El cuerpo va por archivo: PowerShell 5.1 rompe las comillas dobles al
    # pasarlas como argumento nativo a curl.exe (provoca 422 por JSON inválido).
    $bodyFile = Join-Path $env:TEMP "tpi-demo-body.json"
    [System.IO.File]::WriteAllText($bodyFile, $body, [System.Text.UTF8Encoding]::new($false))
    $cargs += @("-H", "Content-Type: application/json", "--data-binary", "@$bodyFile")
  }
  if ($token) { $cargs += @("-H", "Authorization: Bearer $token") }
  $cargs += "$Base$path"
  Write-Host "> $method $path" -ForegroundColor Yellow
  & curl.exe @cargs
}

function Login($email, $password) {
  try {
    $r = Invoke-RestMethod "$Base/api/v1/auth/login" -Method Post `
           -ContentType "application/json" `
           -Body (@{ email = $email; password = $password } | ConvertTo-Json)
  } catch {
    Write-Host "`nFalló el login de $email." -ForegroundColor Red
    Write-Host "Causa probable: las clínicas del demo no existen o la contraseña cambió." -ForegroundColor Yellow
    Write-Host "Corré primero:  .\scripts\preflight-demo.ps1" -ForegroundColor Yellow
    throw
  }
  Write-Host ("  login OK -> rol={0}  token_type={1}  access_len={2}  refresh_len={3}" -f `
              $r.role, $r.token_type, $r.access_token.Length, $r.refresh_token.Length) -ForegroundColor Green
  Note "(Como se puede ver el Token no se va a exponer)"
  return $r
}

# Igual que Call, pero además captura el cuerpo para quedarse con el id que
# devuelve la API (el video crea box/dentista/paciente/turnos en vivo).
function CallJson($method, $path, $body, $token) {
  $out = Join-Path $env:TEMP "tpi-demo-capture.json"
  Remove-Item $out -ErrorAction SilentlyContinue
  $cargs = @("-s", "-o", $out, "-w", "%{http_code}", "-X", $method)
  if ($body) {
    $bodyFile = Join-Path $env:TEMP "tpi-demo-body.json"
    [System.IO.File]::WriteAllText($bodyFile, $body, [System.Text.UTF8Encoding]::new($false))
    $cargs += @("-H", "Content-Type: application/json", "--data-binary", "@$bodyFile")
  }
  if ($token) { $cargs += @("-H", "Authorization: Bearer $token") }
  $cargs += "$Base$path"
  Write-Host "> $method $path" -ForegroundColor Yellow
  $code = & curl.exe @cargs
  $raw = ""
  if (Test-Path $out) { $raw = Get-Content $out -Raw -ErrorAction SilentlyContinue }
  $color = "Green"; if ([int]$code -ge 400) { $color = "Magenta" }
  Write-Host ("  HTTP {0}" -f $code) -ForegroundColor $color
  if ($raw) { Write-Host "  $raw" }
  $parsed = $null
  if ($raw) { try { $parsed = $raw | ConvertFrom-Json } catch { } }
  return [pscustomobject]@{ status = [int]$code; body = $raw; json = $parsed }
}

# Corta con un mensaje útil cuando un bloque que espera 201/200 no los devuelve
# (por ejemplo, si se corrió el demo dos veces sin preflight y quedó un 409).
function Assert-Created($result, $what) {
  if ($result.status -eq 201 -or $result.status -eq 200) { return }
  Write-Host "`nEl bloque '$what' esperaba 201/200 y devolvió $($result.status)." -ForegroundColor Red
  Write-Host "Causa probable: los datos del video ya existen de una corrida anterior." -ForegroundColor Yellow
  Write-Host "Solución:  .\scripts\preflight-demo.ps1  y volvé a correr el demo." -ForegroundColor Yellow
  throw "bloque fallido: $what"
}

# ---------------------------------------------------------------- 0. Salud
Section "0. Salud del backend  ->  C-01 en ejecucion"
Call "GET" "/health" $null $null

# ---------------------------------------------------------------- 1. Login
Section "1. Login del admin de la clinica A"
$A = Login "admin@demo-bootstrap.com" $DemoPasswordA
$tokA = $A.access_token

# ---------------------------------------------------------------- 2. /me
Section "2. GET /auth/me  ->  solo mi usuario y MI clinica"
Call "GET" "/api/v1/auth/me" $null $tokA

# ---------------------------------------------------------------- 3. Listado
Section "3. GET /users  ->  solo usuarios de mi clinica"
Call "GET" "/api/v1/users" $null $tokA

# ---------------------------------------------------------------- 4. Alta
Section "4. POST /users  ->  201, y la respuesta no trae credenciales"
$newUser = '{"email":"recepcion@demo-bootstrap.com","full_name":"Rita Recepcion","role":"receptionist","password":"' + $DemoPasswordReception + '"}'
Call "POST" "/api/v1/users" $newUser $tokA

# ---------------------------------------------------------------- 5. Duplicado
Section "5. El mismo email otra vez  ->  409 sin revelar la clinica propietaria"
Call "POST" "/api/v1/users" $newUser $tokA

# ---------------------------------------------------------------- 6. RBAC
Section "6. RBAC  ->  la recepcionista NO puede administrar usuarios (403)"
$R = Login "recepcion@demo-bootstrap.com" $DemoPasswordReception
Call "GET" "/api/v1/users" $null $R.access_token

# ---------------------------------------------------------------- 7. Aislamiento
Section "7. Aislamiento multi-tenant  ->  registro ajeno e inexistente son identicos (404)"
$idsPath = Join-Path $env:TEMP "tpi-demo-ids.json"
if (-not (Test-Path $idsPath)) {
  Write-Host "  Falta $idsPath. Corré primero .\scripts\preflight-demo.ps1" -ForegroundColor Red
  return
}
$ajeno = (Get-Content $idsPath -Raw | ConvertFrom-Json).admin_b_ajeno

Note "7a. PATCH sobre un usuario REAL de la Clinica Norte"
Call "PATCH" "/api/v1/users/$ajeno" '{"full_name":"Intento"}' $tokA

Note "7b. PATCH sobre un UUID que no existe en ninguna clinica"
Call "PATCH" "/api/v1/users/00000000-0000-0000-0000-000000000000" '{"full_name":"Intento"}' $tokA

Note "Mismo status y mismo cuerpo: no se puede distinguir 'es de otra clínica' de 'no existe'."

# ---------------------------------------------------------------- 8. Sesiones
Section "8. Sesion revocable  ->  rotacion y deteccion de reuso"
$S = Login "admin@demo-bootstrap.com" $DemoPasswordA
$oldRefresh = $S.refresh_token
$refreshBody = (@{ refresh_token = $oldRefresh } | ConvertTo-Json -Compress)

Note "8a. Rotar el refresh (el anterior queda gastado)"
$rot = Invoke-RestMethod "$Base/api/v1/auth/refresh" -Method Post `
         -ContentType "application/json" -Body $refreshBody
Write-Host ("  refresh OK -> rol={0}  access_len={1}  refresh_len={2}" -f `
            $rot.role, $rot.access_token.Length, $rot.refresh_token.Length) -ForegroundColor Green
Note "(el par nuevo tampoco se imprime)"

Note "8b. Reusar el refresh gastado (dentro de la ventana de gracia)"
Call "POST" "/api/v1/auth/refresh" $refreshBody $null

if (-not $SkipGrace) {
  Note "8c. Esperando 11 s para salir de la ventana de gracia..."
  Start-Sleep -Seconds 11
  Note "8d. Reusar otra vez: ahora se trata como sesion comprometida"
  Call "POST" "/api/v1/auth/refresh" $refreshBody $null
  Note "La familia entera quedo revocada (el 401 devuelve code = session_revoked)."
}

# ================================================================ C-03 / C-04
# A partir de acá se crean en vivo los recursos de la agenda. Si ya corriste el
# preflight, no existen: cada bloque espera 201/200 y captura el id.

$day = (Get-Date).AddDays(7).ToString("yyyy-MM-dd")
Note "Fecha de los turnos de la demo: $day (hora local -03:00, se persiste en UTC)"

# ---------------------------------------------------------------- 9. Box
Section "9. POST /boxes  ->  recurso de agenda de MI clinica (201)"
$boxBody = (@{ name = "Box Demo 1" } | ConvertTo-Json -Compress)
$box = CallJson "POST" "/api/v1/boxes" $boxBody $tokA
Assert-Created $box "9. alta de box"
$boxId = $box.json.id

# ---------------------------------------------------------------- 10. Dentista
Section "10. POST /users  ->  dentista de la clinica A (201)"
$dentistBody = (@{ email = "dentista@demo-bootstrap.com"; full_name = "Dario Dentista"; role = "dentist"; password = "Dev-Dentista-123" } | ConvertTo-Json -Compress)
$dentist = CallJson "POST" "/api/v1/users" $dentistBody $tokA
Assert-Created $dentist "10. alta de dentista"
$dentistId = $dentist.json.id

# ---------------------------------------------------------------- 11. Paciente
Section "11. POST /patients  ->  paciente de la clinica A (201)"
$patientBody = (@{ first_name = "Paula"; last_name = "Paciente"; dni = "DEMO0001"; email = "paula.paciente@example.com" } | ConvertTo-Json -Compress)
$patient = CallJson "POST" "/api/v1/patients" $patientBody $tokA
Assert-Created $patient "11. alta de paciente"
$patientId = $patient.json.id

# ---------------------------------------------------------------- 12. Turno
Section "12. POST /appointments  ->  201, status scheduled (RN-07: fin > inicio)"
$apptBody = (@{
  patient_id = $patientId
  dentist_id = $dentistId
  box_id     = $boxId
  start_time = "${day}T09:00:00-03:00"
  end_time   = "${day}T09:30:00-03:00"
  notes      = "Demo C-04"
} | ConvertTo-Json -Compress)
$appt = CallJson "POST" "/api/v1/appointments" $apptBody $tokA
Assert-Created $appt "12. alta de turno"
$apptId = $appt.json.id
Note "La respuesta trae start/end normalizados a UTC (09:00-03:00 = 12:00Z; 09:30 = 12:30Z)."

# ---------------------------------------------------------------- 13. Solapamiento
Section "13. Mismo dentista y box, 09:15-09:45  ->  409 appointment_overlap (RN-01)"
$overBody = (@{
  patient_id = $patientId
  dentist_id = $dentistId
  box_id     = $boxId
  start_time = "${day}T09:15:00-03:00"
  end_time   = "${day}T09:45:00-03:00"
} | ConvertTo-Json -Compress)
CallJson "POST" "/api/v1/appointments" $overBody $tokA | Out-Null

# ---------------------------------------------------------------- 14. Borde
Section "14. Turno contiguo 09:30-10:00  ->  201 (el intervalo es abierto: borde no solapa)"
$adjBody = (@{
  patient_id = $patientId
  dentist_id = $dentistId
  box_id     = $boxId
  start_time = "${day}T09:30:00-03:00"
  end_time   = "${day}T10:00:00-03:00"
} | ConvertTo-Json -Compress)
$adj = CallJson "POST" "/api/v1/appointments" $adjBody $tokA
Assert-Created $adj "14. turno contiguo"
$adjId = $adj.json.id

# ---------------------------------------------------------------- 15. Transiciones
Section "15. Maquina de estados: scheduled -> attended no es valida (409)"
CallJson "PATCH" "/api/v1/appointments/$adjId/status" '{"status":"attended"}' $tokA | Out-Null
Note "La matriz solo permite scheduled -> {confirmed, cancelled}."

Note "15b. Transicion valida: scheduled -> confirmed (200)"
CallJson "PATCH" "/api/v1/appointments/$apptId/status" '{"status":"confirmed"}' $tokA | Out-Null

# ---------------------------------------------------------------- 16. Datetime naive
Section "16. start_time sin zona horaria  ->  422 validation_error (se exige tz-aware)"
$naiveBody = (@{
  patient_id = $patientId
  dentist_id = $dentistId
  box_id     = $boxId
  start_time = "${day}T11:00:00"
  end_time   = "${day}T11:30:00"
} | ConvertTo-Json -Compress)
CallJson "POST" "/api/v1/appointments" $naiveBody $tokA | Out-Null

# ---------------------------------------------------------------- 17. Aislamiento
Section "17. Clinica B pide el turno de la clinica A  ->  404 not_found"
$B = Login "admin@clinica-norte.test" $DemoPasswordB
CallJson "GET" "/api/v1/appointments/$apptId" $null $B.access_token | Out-Null
Note "Mismo 404 que un id inexistente: no se revela que el turno existe en otra clinica."

# ---------------------------------------------------------------- 18. Listado
Section "18. GET /appointments  ->  solo los turnos de mi clinica"
CallJson "GET" "/api/v1/appointments" $null $tokA | Out-Null

Write-Host "`n=== FIN DE LOS BLOQUES DE DEMO ===" -ForegroundColor Green
Note "Recordá mostrar fuera de la terminal: CHANGES.md · archive/ · evidencias skill+MCP · app/repositories/"
