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

  LÍNEA DE TIEMPO DEL VIDEO (este script cubre de 6:40 a 10:00):
      0:30-3:00  editor: CHANGES.md, openspec/changes/archive/,
                 backend/app/repositories/ + tests/test_architecture.py
      3:00-6:00  editor: docs/skills-mcp/evidencias/ (skill y MCP)
      6:00-6:40  terminal: pytest -q  ->  162 passed
      6:40-10:00 terminal: este script
#>

param(
  [string]$Base = "http://127.0.0.1:8000",
  [switch]$SkipGrace
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

function Section($t) { Write-Host "`n============================================================" -ForegroundColor DarkCyan
                       Write-Host "  $t" -ForegroundColor Cyan
                       Write-Host "============================================================" -ForegroundColor DarkCyan }
function Note($t)    { Write-Host "  $t" -ForegroundColor DarkGray }

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
  $r = Invoke-RestMethod "$Base/api/v1/auth/login" -Method Post `
         -ContentType "application/json" `
         -Body (@{ email = $email; password = $password } | ConvertTo-Json)
  Write-Host ("  login OK -> rol={0}  token_type={1}  access_len={2}  refresh_len={3}" -f `
              $r.role, $r.token_type, $r.access_token.Length, $r.refresh_token.Length) -ForegroundColor Green
  Note "(Como se puede ver el Token no se va a exponer)"
  return $r
}

# ---------------------------------------------------------------- 0. Salud
Section "0. Salud del backend  ->  C-01 en ejecucion"
Call "GET" "/health" $null $null

# ---------------------------------------------------------------- 1. Login
Section "1. Login del admin de la clinica A"
$A = Login "admin@demo-bootstrap.com" "Dev-Bootstrap-123"
$tokA = $A.access_token

# ---------------------------------------------------------------- 2. /me
Section "2. GET /auth/me  ->  solo mi usuario y MI clinica"
Call "GET" "/api/v1/auth/me" $null $tokA

# ---------------------------------------------------------------- 3. Listado
Section "3. GET /users  ->  solo usuarios de mi clinica"
Call "GET" "/api/v1/users" $null $tokA

# ---------------------------------------------------------------- 4. Alta
Section "4. POST /users  ->  201, y la respuesta no trae credenciales"
$newUser = '{"email":"recepcion@demo-bootstrap.com","full_name":"Rita Recepcion","role":"receptionist","password":"Dev-Recepcion-123"}'
Call "POST" "/api/v1/users" $newUser $tokA

# ---------------------------------------------------------------- 5. Duplicado
Section "5. El mismo email otra vez  ->  409 sin revelar la clinica propietaria"
Call "POST" "/api/v1/users" $newUser $tokA

# ---------------------------------------------------------------- 6. RBAC
Section "6. RBAC  ->  la recepcionista NO puede administrar usuarios (403)"
$R = Login "recepcion@demo-bootstrap.com" "Dev-Recepcion-123"
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
$S = Login "admin@demo-bootstrap.com" "Dev-Bootstrap-123"
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

Write-Host "`n=== FIN DE LOS BLOQUES DE DEMO ===" -ForegroundColor Green
Note "Recordá mostrar fuera de la terminal: CHANGES.md · archive/ · evidencias skill+MCP · app/repositories/"
