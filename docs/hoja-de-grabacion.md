# Hoja de grabación — qué mostrar, qué decir y qué ejecutar

> Una carilla (doble faz). **P0 ya está grabada.** Total: 10:00.
> Regla: si te pasás, recortá de P1–P3, nunca de P8. El demo no baja de 2:00.

## Antes de la primera toma

- [ ] `.\scripts\preflight-demo.ps1` (deja clínica A, clínica B y limpia los datos del demo).
- [ ] Tres ventanas: (1) terminal en `backend/` con env cargado, (2) navegador en `http://127.0.0.1:8000/docs`, (3) editor en la raíz.
- [ ] Abiertos: `CHANGES.md`, `openspec/changes/archive/`, `docs/skills-mcp/evidencias/`, `docs/skills-mcp/demo-mcp.md`.
- [ ] Token del MCP cargado: `$env:GITHUB_PERSONAL_ACCESS_TOKEN.Length` > 0 (**nunca** imprimir el valor).

---

## P1 · 0:30–1:40 · C-01 fundación (1:10)

**MOSTRÁS:** `docker compose ps` → healthy · `alembic current` · `/health` · carpeta archivada.

```powershell
cd "C:\Users\Mateows\Desktop\Parciales y Base de Datos\TPI METODOLOGIA"
docker compose ps
cd backend
$env:DATABASE_URL="postgresql+asyncpg://tpi:tpi@localhost:5433/tpi_dev"
$env:SECRET_KEY="dev-only-change-me"
.\.venv\Scripts\python.exe -m alembic current
curl.exe -s http://127.0.0.1:8000/health
cd ..
Get-ChildItem openspec\changes\archive
```

**DECÍS:** “C-01 es la fundación. Una sola instancia PostgreSQL con dos bases, `tpi_dev` y `tpi_test`, en el puerto 5433 para no chocar con un PostgreSQL local. La migración arranca en `0001_init` y el health no dice solo que la app arrancó: dice que habla con la base. Rechacé un segundo contenedor para tests y exigir Docker para correr la suite: corre en SQLite por defecto y se valida en PostgreSQL antes de archivar.”

---

## P2 · 1:40–3:20 · C-02 identidad y tenant (1:40)

**MOSTRÁS:** carpeta archivada · `openspec/specs/` · `app/repositories/` + `test_architecture.py`.

```powershell
Get-ChildItem openspec\changes\archive\2026-11-04-core-models-tenants
Get-ChildItem openspec\specs
Get-Content backend\tests\test_architecture.py -TotalCount 40
```

**DECÍS:** “C-02 es identidad y aislamiento multi-tenant. El `clinic_id` sale del token, nunca del payload: `extra=forbid` y un test lo verifican. Un registro de otra clínica devuelve el mismo 404 que uno inexistente: no se filtra la existencia de datos ajenos. RBAC es deny-by-default y denegar no produce efectos. La sesión es revocable de verdad: rotación, `family_id` y reuso revoca la familia. Y D13: ninguna consulta SQLAlchemy vive fuera de `app/repositories`; un test AST lo verifica. Rechacé confiar en el rol y el `clinic_id` del JWT, distinguir 403 de 404, y filtrar por tenant en los servicios.”

---

## P3 · 3:20–4:00 · C-03 pacientes (0:40)

**MOSTRÁS:** carpeta archivada · spec · `repositories/patients.py`.

```powershell
Get-ChildItem openspec\changes\archive\2026-11-04-patient-management
Select-String -Path backend\app\repositories\patients.py -Pattern "DuplicateDni"
```

**DECÍS:** “C-03 agrega pacientes. El paciente nace siempre en la clínica del token; mismo 404 para paciente ajeno e inexistente. El DNI es único por clínica, no global: dos clínicas pueden atender a la misma persona. Rechacé el DNI global y el borrado en duro; se desactiva con `is_active`.”

---

## P4 · 4:00–5:05 · C-04 agenda (1:05)

**MOSTRÁS:** carpeta archivada · spec · `services/appointments.py`.

```powershell
Get-ChildItem openspec\changes\archive\2026-11-05-appointment-agenda
Select-String -Path backend\app\services\appointments.py -Pattern "VALID_TRANSITIONS|lock|with_for_update"
Select-String -Path openspec\specs\appointment-agenda\spec.md -Pattern "Requirement:"
```

**DECÍS:** “C-04 es la agenda: turno con paciente, dentista y box. RN-01: no se solapa por dentista ni por box, con intervalo abierto: 09:00–09:30 contra 09:15–09:45 da 409, y 09:30–10:00 es válido. Horas siempre con zona, normalizadas a UTC; naive da 422. Transiciones: `scheduled` a `confirmed`, `confirmed` a `attended` o `cancelled`; el resto 409. Y no alcanza con validar en Python: hay lock, `with_for_update` y restricción física `EXCLUDE USING gist` en PostgreSQL.”

---

## P5 · 5:05–6:00 · Skill (0:55)

**MOSTRÁS:** `SKILL.md` · línea del registro · `evidencias/revision-skill-c04.md`.

```powershell
Get-Content .agents\skills\revisor-de-agendas-de-citas\SKILL.md -TotalCount 25
Select-String -Path .atl\skill-registry.md -Pattern "revisor"
```

**DECÍS:** “La skill es un procedimiento de auditoría, no implementa código. Revisó los artefactos de C-04: 11 observaciones, 1 crítica, 5 importantes, 5 menores. La crítica era que la spec no definía el origen del `clinic_id`. Yo apliqué las 11 antes de implementar, en el commit `a0fc1cb`, y la suite las verifica. La skill detecta; la decisión es mía.”

---

## P6 · 6:00–6:45 · MCP (0:45)

**MOSTRÁS:** conexión · `get_me` · una búsqueda · luego la evidencia.

```powershell
opencode mcp list
$env:GITHUB_PERSONAL_ACCESS_TOKEN.Length
```

En el chat del agente:

```text
Usá el MCP github: get_me
```

```text
Usá search_code con: EXCLUDE USING gist tstzrange
```

**DECÍS:** “El MCP es una integración, no una skill: publica tools de solo lectura. Acá está conectado. `get_me` confirma que corre con mi cuenta y permisos de lectura. Busqué `EXCLUDE USING gist tstzrange`: 26.976 resultados, o sea que el patrón es estándar, no inventado. Y `token family revoke reuse`: 1.282, que respaldan C-02. No copié código: tomé la forma del patrón.”

> Si falla la red o el token: mostrá `docs/skills-mcp/evidencias/mcp-github-c04.md` y decí “la conexión la muestro desde la evidencia porque el token es personal y no lo expongo en cámara”.

---

## P7 · 6:45–7:15 · Tests (0:30)

**MOSTRÁS:** la suite completa.

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
```

**DECÍS:** “259 tests, rollback por test, sin escribir en la base de desarrollo. La misma suite corrió en SQLite y en el PostgreSQL de Compose.”

---

## P8 · 7:15–9:45 · Demo (2:30)

**MOSTRÁS:** el script corriendo solo. **Narrá solo estos 8 momentos.**

```powershell
cd "C:\Users\Mateows\Desktop\Parciales y Base de Datos\TPI METODOLOGIA"
.\scripts\demo-video.ps1 -SkipGrace
```

| Momento | Decís |
|---|---|
| 1. `/health` | “App y base conectadas.” |
| 2. login + `/me` | “Rol admin; el token no se imprime, solo su longitud.” |
| 3. `POST /users` 201 | “Alta correcta, sin credenciales en la respuesta.” |
| 4. mismo email 409 | “Duplicado, sin decir a qué clínica pertenece.” |
| 5. recepcionista 403 | “RBAC sin efectos.” |
| 6. PATCH usuario de otra clínica 404 | “Mismo 404 que un UUID inexistente: no se filtra el tenant.” |
| 7. turno 201 → 409 → 201 | “Solapamiento rechazado; el borde contiguo sí entra.” |
| 8. transición 409 → naive 422 → cruce 404 | “Estados, zona horaria y aislamiento, los tres verificados.” |

**No comentes los 20 pasos.** El script ya muestra los códigos; vos explicás solo estos 8.

---

## P9 · 9:45–10:00 · Cierre (0:15)

**DECÍS:** “Queda pendiente C-05 a C-10, incluido el frontend. Los cuatro changes de la fase 1 y 2 están implementados, verificados y archivados; no presento como completo nada que no esté en `openspec/changes/archive/`.”

---

## Si algo falla en cámara

| Falla | Qué hacés |
|---|---|
| Docker no levanta | Cortá la toma; corré `preflight` y volvé a grabar P7/P8 |
| El demo da 409 inesperado | Corré `preflight` de nuevo: limpia los datos del video |
| El MCP no conecta | Plan B: evidencia + “token personal, no lo expongo” |
| `pytest` no da 259 | No sigas: hay un cambio sin commitear o un entorno mal cargado |
