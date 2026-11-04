# Design

## Context

Ver `proposal.md` — Why. Estado actual relevante:

- `app/core/database.py` expone `Base`, `engine`, `SessionLocal` y `get_db`;
  sus docstrings ya declaran como puntos de extensión para C-02 un mixin
  `clinic_id` y defaults UTC.
- `app/main.py` es una app factory con un único router (`health`).
- `app/core/config.py` ya exige `SECRET_KEY: SecretStr` (fail-fast) y admite
  `.env`; no hay variables de JWT.
- `backend/alembic/versions/0001_init.py` es una migración vacía que sólo
  abre la cadena; `alembic/env.py` corre en modo async y toma `Base.metadata`.
- El harness (`tests/conftest.py`) migra la DB de test una vez por sesión y
  da `test_session` con rollback por test y `client` con `get_db` overrideado.
  Por defecto usa SQLite (`aiosqlite`); con Docker usa PostgreSQL (`asyncpg`).
- `models/`, `schemas/`, `services/` están vacíos. No existe ningún
  endpoint autenticado ni dependencia de seguridad.
- Tres tests de C-01 asumen el estado previo a los modelos y hay que
  actualizarlos en este change: `test_database.py` (metadata vacía),
  `test_env_example.py` (conjunto exacto de claves requeridas) y
  `test_migrations.py` (head `0001_init`).

## Goals / Non-Goals

**Goals:**

- Identidad verificable por request: `Principal(user_id, clinic_id, role)`
  disponible como dependencia para todos los routers posteriores.
- Sesiones revocables de verdad (logout, rotación, reuso, baja de usuario).
- Un único punto de enforcement de aislamiento, testeable, que C-03/C-04 usen
  sin reimplementar la regla.
- Modelo de datos compatible con PostgreSQL (canónico) y con SQLite (harness
  sin Docker), sin bifurcar código.
- Flujo TDD estricto: tests de contrato por endpoint + tests unitarios de
  seguridad y de aislamiento.

**Non-Goals:**

- Cifrado en reposo de contenido clínico: no hay datos clínicos todavía
  (RN-02 se materializa en C-03/C-05).
- Throttling/lockout de login, MFA, rotación automática de `SECRET_KEY`,
  recuperación de contraseña por email (sin proveedor de mail en el stack).
- Entidad `AuditLog` y auditoría de eventos de agenda (C-06).
- Cookies HttpOnly y almacenamiento del refresh en el frontend (C-10).
- Multi-sucursal (`branch_id`, D-3).

## Decisions

### D1 — PyJWT + `bcrypt` directo, sin passlib

`PyJWT` para firmar/validar (HS256 con `SECRET_KEY`) y el paquete `bcrypt`
para hash (cost 12). Alternativa considerada: `python-jose` (arrastra
criptografía extra y menos mantenimiento) y `passlib[bcrypt]` (su capa de
compatibilidad se rompe con `bcrypt` 4.x). Un wrapper propio en
`app/core/security.py` aísla hash/verify y firma/decodificación, de modo que
los tests unitarios no dependan de FastAPI.

### D2 — Access token corto con claims mínimos

Access token de 15 minutos con `sub` (user id), `clinic_id`, `role`, `type`,
`jti`, `iat`, `exp`. El rol y la clínica viajan en el token **sólo como
indicación**; el servidor recarga usuario + clínica en cada request (ver D4).
Alternativa: token de 24 h sin refresh (rechazada: sin revocación) y token con
permisos embebidos (rechazada: cambios de rol no aplican hasta expirar).

### D3 — Refresh opaco, persistido y con familia

El refresh token es un valor aleatorio de 256 bits (no JWT) entregado una sola
vez; en DB se guarda solo su SHA-256 en `refresh_tokens` con `id`, `user_id`,
`clinic_id`, `family_id`, `issued_at`, `expires_at` (7 días), `rotated_at`,
`revoked_at`, `replaced_by_id`. Cada refresh rota el token y enlaza el
anterior; presentar uno ya rotado revoca toda la familia. Alternativa: refresh
JWT stateless (rechazada: no permite logout ni revocación, que el spec exige).

### D4 — Resolución de contexto en una dependencia

`get_current_principal` decodifica el token y obtiene `User` + `Clinic` vía
`UserRepository.get_with_clinic_by_id` (D13) y verifica `user.is_active` y `clinic.is_active`. Usuario
inactivo o token inválido → 401; clínica inactiva → 403, porque la sesión es
auténtica pero el tenant no puede operar (coincide con
`specs/tenant-isolation`). Así la baja de un usuario surte efecto en el
siguiente request aunque su access token siga vigente (lo exige el spec).
Alternativa: confiar en los claims (rechazada) y cachear el usuario (se
posterga hasta que haya métricas de carga).

### D5 — Aislamiento explícito y testeable, no mágico

Todo servicio recibe el `Principal` y agrega `clinic_id == principal.clinic_id`
en cada consulta; no se usa un event listener global del ORM ni un `with_tenant()`
implícito porque ambos ocultan el filtro y son difíciles de auditar. Se agrega
`TenantScopedRepository[T]` como base mínima para lecturas por id, que devuelve
`None` cuando el registro es de otra clínica (ubicado en `app/repositories/base.py`, D13), y un test de contrato que lo
verifica. Los routers declaran rol con `require_roles(...)`; un endpoint
protegido sin anotación de roles exige autenticación y contexto de clínica, pero
no restringe rol, y cualquier rol fuera de la lista declarada recibe 403. El
"deny by default" del spec se cumple en la frontera: sin token válido, sin
clínica activa o con rol no listado, la petición no se procesa.

### D6 — Email único global

`users.email` es único global (case-insensitive vía normalización a
minúsculas + índice único), no por clínica. Permite `login(email, password)`
sin selector de clínica y garantiza una identidad única por persona; el alta
duplicada responde 409 sin indicar a qué clínica pertenece el email, de modo que
el admin no obtiene datos del otro tenant. Alternativa (email único por clínica)
obligaría a `clinic_slug` en el login; se descarta para el MVP.

### D7 — `Clinic` con `slug` reservado para C-09

Se incluye `slug` único en `Clinic` porque la KB define rutas públicas
`/portal/reserva/{clinic_slug}`; agregarlo ahora evita un backfill con datos
reales en C-09. Se genera en el bootstrap a partir del nombre si no se indica.

### D8 — Bootstrap por comando de operador

`python -m app.cli.bootstrap_clinic` crea clínica + admin de forma idempotente
(clave: `clinic.tax_id` y `user.email`). La contraseña se toma de una variable
de entorno (`BOOTSTRAP_ADMIN_PASSWORD`) o de un prompt oculto, nunca de un
argumento de línea de comandos (evita filtrarla en el historial/`ps`). No se
expone endpoint público de alta de clínica.

### D9 — Tipos portables entre PostgreSQL y SQLite

`Uuid` de SQLAlchemy 2.0, `String` con longitudes explícitas, `DateTime`
con `timezone=True` y helper `utcnow()` que devuelve `datetime.now(UTC)`.
SQLite no conserva el offset, por lo que los schemas Pydantic serializan con
`Z` explícito y los tests de contrato asumen UTC normalizado. Índices únicos
con nombres deterministas (convención de `naming_convention` en `Base.metadata`)
para que Alembic no genere DDL divergente.

### D10 — Errores semánticos con `code` estable

Excepciones de dominio (`AuthenticationError`, `AuthorizationError`,
`TenantViolation`, `InvalidCredentials`, `SessionRevoked`, `DuplicateEmail`)
mapeadas por handlers a 401/403/404/409/422 con cuerpo `{detail, code}`:
credenciales inválidas o sesión revocada → 401, rol no permitido o clínica
inactiva → 403, registro de otra clínica → 404 (idéntico a inexistente), email
duplicado → 409, payload inválido → 422. Nunca se propaga texto de SQLAlchemy
ni mensajes del driver. Los tests verifican `status_code` y `code`, no el texto
libre.

### D11 — Reloj inyectable

`security.py` recibe `now: Callable[[], datetime]` con default `utcnow`, de
modo que expiración y rotación se prueben sin dormir ni depender de
`freezegun` (no instalado).

### D12 — `dentist` es el profesional de la agenda

La KB (`04_modelo_de_datos`) modela `Appointment.dentist_id` como FK a `User`
con rol `dentist`; no existe entidad `Professional`. C-02 no crea una tabla
aparte: el profesional es un `User` activo de la clínica con rol `dentist`, de
modo que C-04 puede referenciar `users.id` y filtrar por `clinic_id`. Cualquier
atributo profesional futuro (matrícula, especialidad) se agrega como columna
nullable en `User`, no como entidad paralela.

### D13 — Capa Repository para toda la persistencia

Toda consulta o escritura SQLAlchemy vive en `app/repositories/`; los services
(`auth`, `users`, `principal`) y el CLI de bootstrap sólo orquestan reglas de
negocio y nunca construyen `select(...)` ni llaman a `db.execute/scalar/get/add`.
Repositorios:

- `base.py`: `TenantScopedRepository[T]` (movido desde `services/tenant.py`, que
  lo re-exporta por compatibilidad; `resolve_clinic_id` queda en services).
- `users.py`: `UserRepository` — `get_with_clinic_by_email`,
  `get_with_clinic_by_id`, `email_exists`, `add`, `list_for_clinic`,
  `get_in_clinic`, `count_other_active_admins`.
- `refresh_tokens.py`: `RefreshTokenRepository` — `add`,
  `get_with_account_by_hash`, `revoke_family`, `revoke_all_for_user`.
- `clinics.py`: `ClinicRepository` — `get_by_tax_id`, `slug_exists`, `add`.

Los repositorios hacen `flush`, nunca `commit`: la frontera transaccional sigue
donde estaba (router, o el service en los caminos de revocación que deben
sobrevivir a la respuesta de error, D3). Las lecturas acotadas a una clínica
reciben `clinic_id` explícito (D5); las únicas lecturas globales son las previas
a tener un `Principal` (login por email, refresh por hash, unicidad global de
email D6, bootstrap) y están nombradas como tales. Un test de arquitectura
impide que reaparezcan consultas en `app/services/`.
Alternativa: dejar consultas en services (rechazada en la revisión de C-02:
viola la separación de capas de AGENTS.md regla 4) y Unit of Work genérico
(rechazado: sobredimensionado para el MVP).

## Risks / Trade-offs

- **Fuga de refresh tokens en el cuerpo de la respuesta** → el spec sólo exige
  entrega única; en C-10 se evalúa cookie HttpOnly (open question). Mitigación
  interina: vida de 7 días, rotación y revocación por familia.
- **Lógica de reuso mal implementada puede revocar sesiones legítimas** (dos
  pestañas refrescando en paralelo) → mitigación: ventana de gracia corta y
  test explícito de doble refresh concurrente.
- **Divergencia SQLite/PostgreSQL en `citext`, timezone y `ON DELETE`** →
  mitigación: normalización en capa de aplicación, sin extensiones, y corrida
  del harness en ambos motores antes de cerrar.
- **Governance CRÍTICO**: un error de autorización es un incidente de datos
  personales → mitigación: checkpoints de revisión antes de escribir servicios
  de auth y revisión obligatoria de los escenarios 401/403 con el usuario.
- **`SECRET_KEY` compartida entre dev y prod** → mitigación: el bootstrap y
  `.env.example` exigen valor propio; la rotación de claves queda documentada
  como deuda para C-10/despliegue.
- **Migración 0002 sobre una DB con datos**: no hay datos reales aún, pero el
  `downgrade` debe existir y probarse (drop de tres tablas y sus índices).

## Migration Plan

1. Generar la migración con
   `alembic revision --autogenerate -m "clinics users refresh tokens"` sobre
   `Base.metadata` con los modelos nuevos y fijar los identificadores
   explícitos: archivo `alembic/versions/0002_core_models_tenants.py`,
   `revision = "0002_core_models_tenants"`,
   `down_revision = "0001_init"` (revisar a mano que no incluya cambios
   espurios de SQLite).
2. `alembic upgrade head` en DB de test (lo hace el harness) y en dev;
   verificar idempotencia de la segunda corrida y actualizar
   `backend/tests/test_migrations.py`, cuya verificación de `heads` hoy espera
   `0001_init`.
3. Correr bootstrap con `BOOTSTRAP_ADMIN_PASSWORD` para dejar una clínica
   operable.
4. Rollback: `alembic downgrade 0001_init` elimina las tres tablas; el
   bootstrap es idempotente, así que re-aplicar es seguro.

## Open Questions

- ¿El refresh token debería viajar en cookie `HttpOnly` cuando exista el
  frontend (C-10)? Se puede decidir allí sin cambiar estos specs.
- ¿Se necesita bloqueo por intentos fallidos antes de exponer la API fuera de
  la red local? Queda como hardening de despliegue, posterior a este change.
- **Confirmado, se resuelve en C-04**: `GET /api/v1/users` es exclusivo de
  `admin` en este change, pero `appointment-agenda` necesita que un
  `receptionist` elija profesionales (`dentist`) para agendar. Este change
  **no** amplía la matriz RBAC ni toca C-04; el listado de profesionales queda
  como responsabilidad de C-04, que deberá exponerlo (endpoint propio de
  profesionales o lectura acotada) al implementarse. Si al llegar a C-04 se
  prefiere reutilizar `/api/v1/users`, será una modificación de la capacidad
  `identity-access` en un change posterior, no un requisito de este.
