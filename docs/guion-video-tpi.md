# Guía de demostración y guion — TPI Metodología I

> **Regla de oro (está en el PDF):** *"No se espera memorizar el código: se espera conocer lo que
> se aceptó y archivó."* Lo que se evalúa es que puedas explicar, con palabras propias, **qué se
> verificó** y **qué se rechazó**. Este documento no es un texto para leer: es una lista de qué
> mostrar en pantalla y qué tenés que poder defender mientras lo mostrás.

---

## 0. Alcance declarado (decirlo así, textual)

> "Fundación técnica ejecutable (C-01), identidad y sesiones revocables con aislamiento
> multi-tenant por clínica (C-02), gestión de pacientes (C-03) y agenda de turnos con
> prevención de solapamientos (C-04). Backend verificado con **259 tests en SQLite y
> PostgreSQL**. La skill propia revisó C-04, sus 11 observaciones se aplicaron y el MCP
> fundamentó decisiones de C-02 y C-04. C-05 en adelante queda **pendiente e identificado**,
> no presentado como completo."

Esa última frase es obligatoria y no resta: el PDF dice *"los pendientes están identificados
aparte"* y *"no se exige completar todo el roadmap"*.

---

## 1. Pre-flight — todo esto ANTES de grabar

El PDF pide *"preparen el entorno y los datos de prueba antes de grabar"*. Si esto no está listo,
los 10 minutos se van en arrancar Docker.

### 1.1 Entorno base

```powershell
Set-Location "C:\Users\Mateows\Desktop\Parciales y Base de Datos\TPI METODOLOGIA"
docker compose up -d db          # esperar "healthy"
Set-Location "C:\Users\Mateows\Desktop\Parciales y Base de Datos\TPI METODOLOGIA\backend"
$env:DATABASE_URL="postgresql+asyncpg://tpi:tpi@localhost:5433/tpi_dev"
$env:TEST_DATABASE_URL="postgresql+asyncpg://tpi:tpi@localhost:5433/tpi_test"
$env:SECRET_KEY="dev-only-change-me"      # ficticio, no es el de ningún entorno real
.\.venv\Scripts\python.exe -m alembic upgrade head
```

> `.\scripts\preflight-demo.ps1` hace todo esto y además deja las dos clínicas listas.
> Si ya lo corriste, esta sección está cubierta.

### 1.2 Crear la segunda clínica (para demostrar el aislamiento)

Con una sola clínica **no podés mostrar** que un registro ajeno es indistinguible de uno
inexistente. Creá la segunda antes de grabar:

```powershell
Set-Location "C:\Users\Mateows\Desktop\Parciales y Base de Datos\TPI METODOLOGIA\backend"
$env:BOOTSTRAP_ADMIN_PASSWORD="Dev-Norte-123"
.\.venv\Scripts\python.exe -m app.cli.bootstrap_clinic `
  --name "Clinica Norte" --tax-id "30-99999999-1" `
  --email "admin@clinica-norte.test" --full-name "Bruno Norte"
Remove-Item Env:BOOTSTRAP_ADMIN_PASSWORD
```

> Nota: la password por variable de entorno es la vía documentada; el comando sin la variable la
> pide en un prompt oculto. **No muestres el valor en pantalla al escribirla.**

### 1.3 Datos que necesitás anotados en un papel (no en el video)

| Dato | Valor ficticio |
|---|---|
| Admin clínica A | `admin@demo-bootstrap.com` / `Dev-Bootstrap-123` |
| Admin clínica B | `admin@clinica-norte.test` / `Dev-Norte-123` |
| **UUID del admin de clínica B** | el preflight lo deja en `%TEMP%\tpi-demo-ids.json` |
| Recepcionista de A | `recepcion@demo-bootstrap.com` / `Dev-Recepcion-123` (la crea el video) |
| Dentista de A | `dentista@demo-bootstrap.com` / `Dev-Dentista-123` (lo crea el video) |
| Paciente de A | DNI `DEMO0001` (lo crea el video) |
| Box de A | `Box Demo 1` (lo crea el video) |

> El preflight **borra** esos cuatro recursos antes de cada corrida, para que el video
> siempre muestre `201` y no `409 duplicate_*`.

### 1.4 Verificar antes de grabar (2 minutos)

```powershell
Set-Location "C:\Users\Mateows\Desktop\Parciales y Base de Datos\TPI METODOLOGIA"
.\scripts\chequear-video.ps1                      # Docker, base, API, archivos, token: 5 segundos
Set-Location "C:\Users\Mateows\Desktop\Parciales y Base de Datos\TPI METODOLOGIA\backend"
.\.venv\Scripts\python.exe -m pytest -q          # debe dar 259 passed
```

Y dejá abiertas tres ventanas: (a) terminal en `backend/`, (b) navegador en `http://127.0.0.1:8000/docs`,
(c) editor mostrando `CHANGES.md` y `openspec/changes/archive/`.

### 1.5 Trampa de la consigna: **no exponer tokens ni contraseñas**

El PDF: *"Mantengan claves, tokens y contraseñas fuera del repositorio, de la entrega y del video."*

En Swagger el `POST /auth/login` **imprime `access_token` y `refresh_token` en pantalla**. Por eso:
Swagger se usa para **mostrar los endpoints y los esquemas**, y las llamadas se hacen por terminal
imprimiendo **solo el rol y la longitud del token**. Decilo en voz alta; es un punto a favor.

```powershell
$base = "http://127.0.0.1:8000"
$r = Invoke-RestMethod "$base/api/v1/auth/login" -Method Post -ContentType "application/json" `
     -Body (@{email="admin@demo-bootstrap.com";password="Dev-Bootstrap-123"} | ConvertTo-Json)
"rol=$($r.role)  token_type=$($r.token_type)  access_len=$($r.access_token.Length)"   # sin imprimir el token
$H = @{ Authorization = "Bearer $($r.access_token)" }
$RB = @{ Authorization = "Bearer $($r.refresh_token)" }   # solo para el bloque de refresh
```

---

## 2. Guion por bloques (10:00 máximo)

### 2.0 Plan de grabación por partes (revisión de tiempos)

**Presupuesto total: 10:00.** La presentación (P0) ya está grabada, así que quedan **9:30**
para el resto. Si grabás por partes, cada parte se edita sola y el único número que importa
es que la suma no pase de 10:00.

| Parte | Contenido | Ventana | Objetivo | Techo | Si te pasás, recortá esto |
|---|---|---|---|---|---|
| **P0** | Presentación y alcance | 0:00–0:30 | 0:30 | 0:30 | (ya grabada) |
| **P1** | C-01 fundación | 0:30–1:40 | 1:10 | 1:20 | Los 3 “rechazado”; dejá solo el de Docker en 5432 |
| **P2** | C-02 identidad y tenant | 1:40–3:20 | 1:40 | 1:55 | La tabla de 7 verificados: narrala como 3 frases, no fila por fila |
| **P3** | C-03 pacientes | 3:20–4:00 | 1:00 | 1:00 | El detalle de `IntegrityError`; dejá “DNI único por clínica” |
| **P4** | C-04 agenda | 4:00–5:05 | 1:05 | 1:15 | Las 3 open questions; dejá RN-01 y UTC |
| **P5** | Skill | 5:05–6:00 | 1:00 | 1:00 | Las 5 menores y 3 importantes; dejá la crítica y 2 importantes |
| **P6** | MCP | 6:00–6:45 | 0:45 | 0:55 | Las 2 consultas menos importantes; quedate con `EXCLUDE` y `token family` |
| **P7** | Tests | 6:45–7:15 | 0:30 | 0:35 | Nada: es el bloque más corto y el más contundente |
| **P8** | Demo terminal | 7:15–9:45 | 2:30 | 2:50 | Pasos 1–2 de Swagger y el detalle de refresh |
| **P9** | Cierre | 9:45–10:00 | 0:15 | 0:20 | Nada: es obligatorio |

> **Plan de rescate vigente:** C-03 y Skill van a 1:00 cada uno; el total cierra en
> **11:56** y el demo arranca en **8:56** (antes del minuto 10). La tabla de arriba ya
> refleja esos dos objetivos; el paso a paso está en la hoja.

**Reglas de la review:**

1. **El demo no se recorta por debajo de 2:00.** Es lo que el evaluador ve funcionando; si
   hay que sacar tiempo, se saca de P1/P2/P3, no de P8.
2. **Si una parte llega al techo, la siguiente baja a su objetivo mínimo** (no se acumula).
3. **Grabá P7 y P8 en la misma toma**: el test y la demo comparten terminal y narrativa.
4. **Usá `demo-video.ps1 -SkipGrace`**: ahorra 11 s reales y la revocación de la familia se
   explica en una frase, no se espera en cámara.
5. **No narres los 20 pasos del demo.** El script corre solo; vos hablás en 8 momentos
   (ver “Narrá solo estos 8” más abajo).

> **Diagnóstico de la versión anterior:** el bloque “Changes” iba de 0:30 a 3:00 (2:30),
> pero C-01 + C-02 + C-03 + C-04 suman ~4:30. Estaba sobrepresupuestado en ~2:00. La tabla
> de arriba corrige eso y desplaza Skill/MCP a 5:05–6:45.

**Hoja para tener al lado mientras grabás:** [`hoja-de-grabacion.md`](hoja-de-grabacion.md)
(versión imprimible de una hoja doble faz: [`hoja-de-grabacion.pdf`](hoja-de-grabacion.pdf)).
Tiene, por cada parte: qué mostrar, qué decir textual y los comandos exactos.

> **Si ya grabaste y te pasaste del tiempo:** usá el *plan de rescate* de la hoja.
> C-03 y Skill bajan a 1:00 cada uno, el resto queda igual y el total cierra en
> **11:56**, con el demo arrancando en **8:56** (antes del minuto 10).

### 0:00–0:30 — Presentación y alcance
**Mostrás:** cámara encendida, tu nombre, y `CHANGES.md` con las fases.
**Decís:** el párrafo de la Sección 0. Una frase: *"cuatro changes archivados, backend-only, C-05
en adelante pendiente y declarado como pendiente"*.

### 0:30–5:05 — Changes completos: propósito, resultado, verificación

**C-01 (`foundation-setup`) — 1:10 (P1)**

| Mostrás | Explicás |
|---|---|
| `docker compose ps` → `healthy` | Una sola instancia PostgreSQL, **dos bases** (`tpi_dev` y `tpi_test`), puerto host **5433** porque el 5432 suele estar ocupado |
| `.\.venv\Scripts\python.exe -m alembic current` | La cadena de migraciones arranca en `0001_init`; el harness migra una vez por sesión |
| `curl /health` | `{"app":"healthy","database":"healthy"}` — no es "arranca", es "arranca y habla con la base" |
| `openspec/changes/archive/2026-10-09-foundation-setup/` | Está archivado; su spec es hoy `openspec/specs/backend-foundation/spec.md` |

**Qué rechazaste (esto es lo que te preguntan):**
- **Rechazado: un segundo contenedor para la base de tests.** Una sola instancia con dos bases da
  la misma semántica con la mitad de recursos, y el healthcheck es uno solo.
- **Rechazado: exigir Docker para correr los tests.** La suite corre por defecto en SQLite
  (`aiosqlite`) y se vuelve a PostgreSQL cuando `TEST_DATABASE_URL` está seteada. Eso permite
  testear sin Docker, pero **obliga a probar en los dos motores antes de archivar** (lo hicimos).
- **Rechazado: levantar en 5432.** Choca con instalaciones locales de PostgreSQL.

**C-02 (`core-models-tenants`) — 1:40 (P2)**

| Mostrás | Explicás |
|---|---|
| `openspec/changes/archive/2026-11-04-core-models-tenants/` | 30/30 tareas en 8 secciones; la 8 es la remediación de la revisión |
| `openspec/specs/identity-access/` + `tenant-isolation/` | Al archivar, las specs delta pasaron a ser **specs principales** |
| `backend/app/repositories/` + `test_architecture.py` | D13: ninguna consulta SQLAlchemy vive fuera de los repositorios; un test AST lo verifica |

**Qué verificaste / qué rechazaste (el núcleo del TPI):**

| Verificado | Cómo |
|---|---|
| El `clinic_id` sale **del token**, nunca del cliente | `extra="forbid"` en los payloads + `test_client_supplied_clinic_id_is_never_trusted` |
| Un registro de otra clínica es **indistinguible de uno inexistente** | `TenantScopedRepository` devuelve `None` → mismo 404 |
| RBAC deny-by-default, **sin efectos al denegar** | `require_roles(...)` + `test_forbidden_role_is_denied_without_side_effects` |
| Usuario inactivo → **401**; clínica inactiva → **403** | join en la dependencia de contexto |
| Sesión revocable de verdad | rotación + `family_id` + reuso → revoca la familia |
| Sin secretos en respuestas ni logs | `{detail, code}` + logger `app.auth` sin PII |
| 259 tests en **SQLite y PostgreSQL**, sin tocar `tpi_dev` | conteos de filas antes/después |

**Qué rechazaste:**
- **Rechazado: confiar en el rol y el `clinic_id` del JWT.** Son indicativos; el usuario y la
  clínica se **recargan de la base en cada request**. Un usuario desactivado con token válido no entra.
- **Rechazado: distinguir "no existe" de "es de otra clínica"** (403 vs 404). Distinguirlos filtra
  la existencia de datos de otro tenant.
- **Rechazado: filtrar por tenant en los servicios.** Si el filtro está disperso, ningún test
  puede garantizar que no falte en un endpoint nuevo. De ahí D13.
- **Rechazado: marcar `xfail` las diferencias de dialecto.** No hubo ninguna: los 259 pasaron
  igual en los dos motores. Si hubiera habido, se documentaba el fallo, no se debilitaba el assert.
- **Diferido, no oculto:** el listado de profesionales para el rol `receptionist` **no** entra en
  C-02; quedó como open question de C-04. Mostralo: es honestidad de alcance.

**C-03 (`patient-management`) — 0:40 (P3)**

| Mostrás | Explicás |
|---|---|
| `openspec/changes/archive/2026-11-04-patient-management/` | 10/10 tareas bajo Strict TDD; migración `0003_patient_management` |
| `openspec/specs/patient-management/spec.md` | spec canónica ya sincronizada |
| `backend/app/repositories/patients.py` + `test_patients.py` | el `dni` duplicado se traduce en el repositorio (`IntegrityError` → `DuplicateDni`, 409) |

**Qué verificaste / qué rechazaste:**

| Verificado | Cómo |
|---|---|
| El paciente nace **siempre** en la clínica del token | `extra="forbid"` + mismo 404 para paciente ajeno e inexistente |
| Anamnesis médica en JSON, sin PII en logs | `medical_history_summary` + logger sin datos del paciente |
| DNI único **por clínica**, no global | índice único `(clinic_id, dni)` y test de dos clínicas con el mismo DNI |

- **Rechazado: DNI único global.** Dos clínicas pueden atender a la misma persona.
- **Rechazado: borrar pacientes en duro.** `is_active` desactiva sin romper turnos históricos.

**C-04 (`appointment-agenda`) — 1:05 (P4)**

| Mostrás | Explicás |
|---|---|
| `openspec/changes/archive/2026-11-05-appointment-agenda/` | 12/12 tareas bajo Strict TDD; migraciones `0004_boxes` y `0005_appointments` |
| `openspec/specs/appointment-agenda/spec.md` | requisitos de scope server-side, RN-01, UTC y transiciones |
| `backend/app/services/appointments.py` | RN-01 con doble garantía: lock en memoria + `with_for_update` + `EXCLUDE USING gist` en PostgreSQL |
| `docs/skills-mcp/evidencias/revision-skill-c04.md` | las 11 observaciones de la skill, **aplicadas** (`a0fc1cb`) |

**Qué verificaste / qué rechazaste:**

| Verificado | Cómo |
|---|---|
| `clinic_id` server-side también en box y turno | `extra="forbid"` + escenario "Payload cannot set clinic_id" |
| Solapamiento por **dentista o box**, intervalo abierto | 09:00–09:30 vs 09:15–09:45 → 409; 09:30–10:00 → 201 |
| Horas normalizadas a UTC y `naive` rechazado | `-03:00` se guarda como `Z`; sin tz → 422 `validation_error` |
| Transiciones válidas | `scheduled → confirmed`, `confirmed → attended/cancelled`; el resto 409 |
| Turno de otra clínica | 404 idéntico a inexistente |

- **Rechazado: resolver el solapamiento solo en Python.** Dos requests concurrentes pueden pasar
  la validación a la vez; por eso la restricción física en PostgreSQL.
- **Rechazado: permitir `no_show` como transición de C-04.** Queda para el change de
  recordatorios/asistencia; forzarlo acá inventaba reglas que la KB no definió.
- **Rechazado: validar `box.status = maintenance` en C-04.** Es una open question de `design.md`;
  se documentó en vez de inventar la regla.

### 5:05–6:45 — Skill propia y MCP

**Skill `revisor-de-agendas-de-citas` — 0:55 (P5) — qué necesidad resuelve**

> "Antes de implementar la agenda, los artefactos tienen que ser revisables: que el `clinic_id` no
> venga del payload, que los solapamientos cubran todos los casos, que las horas sean UTC. La skill
> es un procedimiento que recorre esos artefactos y devuelve observaciones clasificadas. **No
> implementa código**: solo revisa y propone."

**Mostrás:** `docs/skills-mcp/evidencias/revision-skill-c04.md` — la solicitud, las 11 fuentes
leídas y las **11 observaciones (1 crítica, 5 importantes, 5 menores)**.

**Explicás la más grave:** la spec de C-04 no definía el origen del `clinic_id` persistido →
corrección: tomarlo solo del contexto autenticado y agregar un escenario de rechazo. Esa misma
regla es la que C-02 ya implementó (`extra="forbid"` + `test_client_supplied_clinic_id_is_never_trusted`).

**Cierre del ciclo:** la skill **no** editó nada. Sus 11 observaciones se aplicaron después, como
decisión explícita del autor, en el commit `a0fc1cb` (artefactos) y en la implementación de C-04.
Mostralo: la skill produce el diagnóstico; el humano decide y el change lo materializa.

**Qué rechazaste con la skill:**
- **Rechazado: aplicar la skill sobre C-01/C-02.** Su alcance declarado es agenda; sus entradas son
  `appointment-agenda/**` + KB de reglas de negocio. Sobre auth no tendría nada que validar y su
  propio criterio prohíbe presentar una revisión como exitosa sin las fuentes necesarias.
- **Rechazado: dejar las observaciones como propuestas eternas.** Se aplicaron antes de implementar
  y quedaron verificadas por escenarios; no se presentaron como "revisadas" sin efecto.
- **Rechazado: que la skill completara la sección `## UI Mockups`** que faltaba en C-04: la reportó
  como pendiente y no la agregó, respetando su límite.

**MCP `github` — 0:45 (P6) — qué aporta y cómo se verificó**

**Mostrás:** `docs/skills-mcp/evidencias/mcp-github-c02.md` y `mcp-github-c04.md`.
Guion corto y comandos exactos para el vivo: [`docs/skills-mcp/demo-mcp.md`](skills-mcp/demo-mcp.md).

| Solicitud | Resultado | Aporte |
|---|---|---|
| `get_me` | `login = Mateows` | confirma que las consultas corren con el alcance de una cuenta personal, solo lectura |
| `search_code` `"token family" revoke reuse language:python` | 1.282 coincidencias (`django-oauth-toolkit`, `litestar-fullstack`) | el patrón familia + rotación + revocación por reuso es estándar, no inventado |
| `search_code` `"tenant_id" where filter repository language:python` | 12.016, con el filtro dentro de módulos `repository` | respalda D13 (capa `app/repositories/`) |
| `search_repositories` `fastapi multi-tenant saas backend` | 126 repos | el multi-tenant genérico tiene soluciones canónicas: se reutiliza el patrón |
| `search_code` `EXCLUDE USING gist tstzrange` | 26.976 | (C-04) el anti-solapamiento a nivel de base es estándar |

**Qué rechazaste con el MCP:**
- **Rechazado: copiar código de los 1.282 resultados.** Se tomó la *forma* del patrón; la
  implementación es propia (hash SHA-256 del token opaco, reloj inyectable, ventana de gracia de
  10 s) porque los resultados dependen de Django/Litestar con supuestos de sesión distintos.
- **Rechazado: adoptar un repositorio como referencia.** Ninguno es del dominio odontológico ni
  cubre Ley 25.326.
- **Rechazado: el estilo de filtrar por tenant en handlers o queries sueltas**, que es mayoritario
  en los resultados: si el filtro está disperso no hay guarda posible. De ahí `test_architecture.py`.
- **Rechazado: considerar la skill y el MCP "instalados" como evidencia.** La consigna lo prohíbe
  explícitamente; por eso hay solicitud, resultado y aporte por cada uno.

### 6:45–10:00 — Tests y demostración funcionando

**6:45–7:15 · Tests (P7, 0:30)**
```powershell
.\.venv\Scripts\python.exe -m pytest -q     # 259 passed
```
Explicás: *"259 tests con rollback por test, sin escribir en la base de desarrollo; la misma suite
corrió en SQLite y en el PostgreSQL de Compose."* Si querés mostrarlo en vivo en PostgreSQL:
`$env:TEST_DATABASE_URL=...` y volver a correr.

**7:15–9:45 · Demo continua (P8, 2:30)** — una sola narrativa, no casos sueltos

> **Narrá solo estos 8 momentos** (el script corre solo; no comentes los 20 pasos):
> 1) `GET /health` · 2) login + `GET /me` · 3) `POST /users` 201 · 4) email repetido 409 ·
> 5) `GET /users` como recepcionista 403 · 6) PATCH a usuario de otra clínica 404 ·
> 7) turno 201 → solapamiento 409 → contiguo 201 · 8) transición inválida 409 → naive 422 →
> lectura cruzada 404.
> Corré con `.\scripts\demo-video.ps1 -SkipGrace` para no esperar los 11 s en cámara.

| Paso | Comando | Qué confirma |
|---|---|---|
| 1 | `GET /health` | base conectada |
| 2 | Swagger abierto en `/docs` | los endpoints existen y están documentados |
| 3 | login admin A (token **no** se imprime) | devuelve rol `admin`, access + refresh |
| 4 | `GET /api/v1/auth/me` | solo tu usuario y **tu** clínica |
| 5 | `POST /api/v1/users` creando un `dentist` | 201; la respuesta **no** trae credenciales |
| 6 | mismo email otra vez | **409**, sin decir a qué clínica pertenece |
| 7 | login como `recepcion@demo-bootstrap.com` → `GET /api/v1/users` | **403** sin efectos |
| 8 | admin A `PATCH /api/v1/users/<UUID del admin de B>` | **404** |
| 9 | admin A `PATCH /api/v1/users/<UUID inventado>` | **404 idéntico** ← el paso que demuestra el aislamiento |
| 10 | `POST /auth/refresh` y reusar el anterior | **401 reuse**; dentro de los 10 s la sesión sigue viva; pasados los 10 s se revoca la familia entera |
| 11 | `POST /api/v1/boxes` con `{"name":"Box Demo 1"}` | **201**, sin `clinic_id` en el payload |
| 12 | `POST /api/v1/users` creando un `dentist` | **201**, el rol se valida contra `USER_ROLES` |
| 13 | `POST /api/v1/patients` con DNI `DEMO0001` | **201**, paciente en la clínica del token |
| 14 | `POST /api/v1/appointments` 09:00–09:30 | **201**, status `scheduled`, horas devueltas en UTC |
| 15 | mismo dentista/box 09:15–09:45 | **409 `appointment_overlap`** (RN-01) |
| 16 | mismo dentista/box 09:30–10:00 (contiguo) | **201**: el intervalo es abierto, el borde no solapa |
| 17 | `PATCH /{id}/status` con `attended` sobre un turno `scheduled` | **409 `invalid_appointment_transition`** |
| 18 | `PATCH /{id}/status` con `confirmed` | **200**, avanza la máquina de estados |
| 19 | `POST /appointments` con `start_time` sin zona | **422 `validation_error`** |
| 20 | login B → `GET /api/v1/appointments/<id de A>` | **404 idéntico** al de un id inexistente |

Comandos del bloque (HTTP 401/403/404 sin que PowerShell corte):

```powershell
curl.exe -s -w "`nHTTP %{http_code}`n" -H "Authorization: Bearer $($r.access_token)" "$base/api/v1/users"
curl.exe -s -w "`nHTTP %{http_code}`n" -X PATCH -H "Content-Type: application/json" `
  -H "Authorization: Bearer $($r.access_token)" -d '{"full_name":"Intento"}' `
  "$base/api/v1/users/<UUID_AJENO>"
```

**Cierre (P9, 0:15):** *"Queda pendiente C-05 a C-10, incluido el frontend. Los cuatro changes de la
fase 1 y 2 están implementados, verificados y archivados; no presento como completo nada que no
esté en `openspec/changes/archive/`."*

---

## 3. Frases prohibidas

| No digas | Decí |
|---|---|
| "terminamos el sistema" | "completamos el alcance declarado: C-01 a C-04" |
| "C-04 está preparado / pendiente" | "C-04 está **implementado, verificado y archivado**; C-05 en adelante sigue pendiente" |
| "los tests pasan" (a secas) | "259 tests en SQLite **y** PostgreSQL, sin escribir en la base de desarrollo" |
| "usamos el MCP para buscar código" | "el MCP respondió X y con eso **rechazamos** Y / **adoptamos** Z" |
| "la skill arregló la spec" | "la skill **detectó** 11 observaciones; yo las apliqué antes de implementar" |
| mostrar el token "para que se vea" | mostrar `access_len`, y decir que lo ocultás por la consigna |

---

## 4. TXT de entrega

Nombre sugerido: `TPI-C1-Liendo.txt`

```
ENTREGA — TPI METODOLOGÍA I
Comisión: 1
Video explicativo: <enlace con permiso de acceso>
Repositorio del proyecto: <enlace con permiso de acceso>
Cantidad de integrantes: 1
Integrantes:
1. Mateo Lautaro Liendo
```

Antes de subirlo: abrí los dos enlaces en una ventana privada y confirmá que se ven sin sesión.
El PDF lo pide explícitamente (*"Comprueben los permisos de ambos enlaces"*).
