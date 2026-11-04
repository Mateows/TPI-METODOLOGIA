# API de autenticación (`/api/v1/auth`)

Estado: **C-02 (`core-models-tenants`), olas 2 y 3a**. Esta página cubre los
endpoints de autenticación y sesión, la administración de usuarios
(`/api/v1/users`, tareas 5.x) y la matriz RBAC aplicada. El procedimiento
operativo de bootstrap de clínica (tarea 6.3) se documenta en una sección
posterior.

Todos los valores de los ejemplos son ficticios. No uses estas credenciales en
ningún entorno real.

## Convenciones

| Aspecto | Valor |
|---|---|
| Base URL de desarrollo | `http://localhost:8000` |
| Prefijo | `/api/v1/auth` |
| Formato | JSON (`Content-Type: application/json`) |
| Autorización | `Authorization: Bearer <access_token>` |
| Access token | JWT HS256, vida `ACCESS_TOKEN_EXPIRE_MINUTES` (default 15 min) |
| Refresh token | Valor opaco de 256 bits, vida `REFRESH_TOKEN_EXPIRE_DAYS` (default 7 días) |
| Fechas persistidas | UTC (la conversión a `America/Argentina/Buenos_Aires` es de la UI) |
| Token de renovación | Se entrega **una sola vez**; en base de datos sólo se guarda su SHA-256 |

El email es único a nivel global, por lo que el login no requiere selector de
clínica. La clínica activa siempre se deriva de la sesión verificada, nunca de
un campo enviado por el cliente.

## Contrato de errores

Toda falla de dominio responde `{ "detail": "...", "code": "..." }`. El campo
`code` es el contrato estable; `detail` es texto humano y nunca incluye SQL,
mensajes del driver, contraseñas ni tokens.

| HTTP | `code` | Cuándo |
|---|---|---|
| 401 | `invalid_credentials` | email desconocido, contraseña incorrecta o usuario inactivo en el login (respuesta genérica e idéntica en los tres casos) |
| 401 | `session_revoked` | refresh token desconocido, expirado, ya rotado o revocado |
| 401 | `authentication_failed` | falta el header `Authorization`, o el access token es inválido, expirado, alterado, de otro usuario o de una cuenta desactivada |
| 403 | `forbidden` | la sesión es auténtica pero la clínica está inactiva, o el rol no está permitido para la operación |
| 404 | `not_found` | el recurso pertenece a otra clínica (idéntico a un id inexistente) |
| 409 | `duplicate_email` | email ya registrado (ver [Administración de usuarios](#administración-de-usuarios-apiv1users)) |
| 409 | `last_admin` | el cambio dejaría a la clínica sin ningún `admin` activo |
| 422 | `validation_error` | el cuerpo no cumple el esquema |

Ejemplo de error:

```json
{
  "detail": "invalid credentials",
  "code": "invalid_credentials"
}
```

## `POST /api/v1/auth/login`

Autentica por email y contraseña y abre una sesión nueva.

### Request

```bash
curl -i -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@clinica-ejemplo.com",
    "password": "Clave-Ficticia-123"
  }'
```

### Response `200 OK`

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.ejemplo.firma-ficticia",
  "refresh_token": "5tGk2rFicticioRefreshTokenOpacoDe256Bits000000",
  "token_type": "bearer",
  "role": "admin"
}
```

### Errores

| Caso | Respuesta |
|---|---|
| email desconocido | `401` `invalid_credentials` |
| contraseña incorrecta | `401` `invalid_credentials` (misma respuesta que el caso anterior) |
| usuario inactivo con credenciales correctas | `401` `invalid_credentials`, sin tokens |
| clínica inactiva | `403` `forbidden` |
| cuerpo inválido (falta `password`) | `422` `validation_error` |

La respuesta nunca incluye la contraseña ni el hash almacenado.

## `POST /api/v1/auth/refresh`

Rota el refresh token y emite un nuevo par de tokens.

### Request

```bash
curl -i -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "5tGk2rFicticioRefreshTokenOpacoDe256Bits000000"
  }'
```

### Response `200 OK`

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.renovado.firma-ficticia",
  "refresh_token": "Zx81FicticioNuevoRefreshTokenRotado0000000000",
  "token_type": "bearer",
  "role": "admin"
}
```

### Reglas de rotación

1. El token presentado queda inutilizable de inmediato; el cliente debe guardar
   el nuevo `refresh_token`.
2. **Ventana de gracia (10 s):** si el token ya rotado se vuelve a presentar
   dentro de esa ventana (dos pestañas refrescando en paralelo), la respuesta es
   `401 session_revoked` pero la familia **no** se revoca, para no cerrar una
   sesión legítima. El sucesor emitido sigue siendo válido.
3. **Reuso fuera de la ventana:** se considera sesión comprometida y se revoca
   la familia completa (todos los tokens emitidos en esa cadena).
4. Un refresh token expirado, revocado o desconocido responde `401
   session_revoked` sin emitir tokens.

| Caso | Respuesta |
|---|---|
| token desconocido / expirado / revocado / reusado | `401` `session_revoked` |
| usuario desactivado con token todavía vigente | `401` `authentication_failed` |
| clínica inactiva | `403` `forbidden` |
| cuerpo inválido (falta `refresh_token`) | `422` `validation_error` |

## `POST /api/v1/auth/logout`

Revoca la sesión de refresh del llamante. Requiere access token válido.

### Request

```bash
curl -i -X POST http://localhost:8000/api/v1/auth/logout \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.ejemplo.firma-ficticia" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "5tGk2rFicticioRefreshTokenOpacoDe256Bits000000"
  }'
```

### Response `204 No Content`

Sin cuerpo.

### Errores

| Caso | Respuesta |
|---|---|
| sin `Authorization` o token inválido | `401` `authentication_failed` |
| refresh token desconocido o de otro usuario | `401` `session_revoked` (no se revoca nada ajeno) |

Después del logout, cualquier intento de refresh con ese token responde `401
session_revoked`.

## `GET /api/v1/auth/me`

Devuelve únicamente el perfil del usuario autenticado.

### Request

```bash
curl -i http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.ejemplo.firma-ficticia"
```

### Response `200 OK`

```json
{
  "id": "0f2b6b7e-8f4a-4a1e-9f14-2b0c7a3d1111",
  "email": "admin@clinica-ejemplo.com",
  "full_name": "Ada Administradora",
  "role": "admin",
  "is_active": true,
  "clinic": {
    "id": "6d1c9e2a-3b4f-4c8d-8e7a-1f2a3b4c5555",
    "name": "Clínica Ejemplo Norte",
    "slug": "clinica-ejemplo-norte"
  }
}
```

La respuesta nunca contiene el hash de la contraseña, tokens ni datos de otro
usuario. Parámetros como `?user_id=<otro>` se ignoran: el endpoint siempre
responde por el llamante.

### Errores

| Caso | Respuesta |
|---|---|
| sin token o token inválido/expirado | `401` `authentication_failed` |
| usuario desactivado | `401` `authentication_failed` |
| clínica inactiva | `403` `forbidden` |

## `PATCH /api/v1/auth/password`

Cambio de contraseña por el propio usuario. Requiere access token válido.

### Request

```bash
curl -i -X PATCH http://localhost:8000/api/v1/auth/password \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.ejemplo.firma-ficticia" \
  -H "Content-Type: application/json" \
  -d '{
    "current_password": "Clave-Ficticia-123",
    "new_password": "Nueva-Clave-Ficticia-456"
  }'
```

### Response `204 No Content`

Sin cuerpo.

### Reglas

- `new_password` exige entre 8 y 72 caracteres (72 bytes es el límite de
  bcrypt).
- La contraseña anterior deja de funcionar inmediatamente.
- Se revocan **todas** las sesiones de refresh del usuario (el endpoint no
  recibe un refresh token, por lo que no puede distinguir la sesión actual; el
  access token del llamante sigue vigente hasta que expira).
- No se registra la contraseña ni el hash en logs.

### Errores

| Caso | Respuesta |
|---|---|
| `current_password` incorrecta | `401` `invalid_credentials` (la contraseña no cambia) |
| `new_password` fuera de rango | `422` `validation_error` |
| sin token o token inválido | `401` `authentication_failed` |

## Administración de usuarios (`/api/v1/users`)

Gestión de las cuentas de **una misma clínica**. Todo el prefijo es exclusivo
del rol `admin`: cualquier otro rol autenticado recibe `403` antes de que el
servicio se ejecute, de modo que el intento no persiste ningún cambio.

Reglas de contrato:

- La clínica **siempre** se deriva del access token verificado. El cuerpo no
  admite `clinic_id` (`extra="forbid"`): enviarlo responde `422`. Un `id` de
  otra clínica responde exactamente igual que un `id` inexistente (`404
  not_found`), sin revelar a qué clínica pertenece.
- Roles permitidos: `admin`, `receptionist`, `dentist` (conjunto cerrado de
  `app/models/user.py`). Cualquier otro valor es `422 validation_error`.
- El email se normaliza a minúsculas y es único **global**. Un alta con email ya
  registrado responde `409 duplicate_email` sin indicar la clínica dueña; el
  mismo criterio aplica si el email ya existe en otra clínica.
- La clínica nunca puede quedar sin al menos un `admin` activo: degradar o
  desactivar al último responde `409 last_admin` y no persiste el cambio.
- Las respuestas nunca incluyen contraseña ni hash (sólo `id`, `email`,
  `full_name`, `role`, `is_active`).

### `POST /api/v1/users`

Alta de una cuenta en la clínica del admin autenticado.

```bash
curl -i -X POST http://localhost:8000/api/v1/users \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.ejemplo.firma-ficticia" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "recepcion@clinica-ejemplo.com",
    "full_name": "Rita Recepcionista",
    "role": "receptionist",
    "password": "Clave-Inicial-Ficticia-123"
  }'
```

#### Response `201 Created`

```json
{
  "id": "9a1e4c2d-5b6f-4a70-8c3d-1e2f3a4b5c6d",
  "email": "recepcion@clinica-ejemplo.com",
  "full_name": "Rita Recepcionista",
  "role": "receptionist",
  "is_active": true
}
```

La cuenta creada puede autenticarse de inmediato con esa contraseña inicial y
cambiarla luego con `PATCH /api/v1/auth/password`.

#### Errores

| Caso | Respuesta |
|---|---|
| rol fuera de `admin`/`receptionist`/`dentist` | `422` `validation_error`, sin crear usuario |
| falta `password`, `email` o `full_name` | `422` `validation_error` |
| se envía `clinic_id` en el cuerpo | `422` `validation_error` |
| email ya registrado (misma u otra clínica) | `409` `duplicate_email`, sin datos de la otra clínica |
| rol `receptionist` o `dentist` | `403` `forbidden`, sin cambios |
| sin token o token inválido | `401` `authentication_failed` |

### `GET /api/v1/users`

Lista las cuentas de la clínica del admin, ordenadas por email. Nunca incluye
usuarios de otra clínica.

```bash
curl -i http://localhost:8000/api/v1/users \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.ejemplo.firma-ficticia"
```

#### Response `200 OK`

```json
[
  {
    "id": "0f2b6b7e-8f4a-4a1e-9f14-2b0c7a3d1111",
    "email": "admin@clinica-ejemplo.com",
    "full_name": "Ada Administradora",
    "role": "admin",
    "is_active": true
  },
  {
    "id": "9a1e4c2d-5b6f-4a70-8c3d-1e2f3a4b5c6d",
    "email": "recepcion@clinica-ejemplo.com",
    "full_name": "Rita Recepcionista",
    "role": "receptionist",
    "is_active": true
  }
]
```

#### Errores

| Caso | Respuesta |
|---|---|
| rol `receptionist` o `dentist` | `403` `forbidden` |
| sin token o token inválido | `401` `authentication_failed` |

### `PATCH /api/v1/users/{id}`

Actualiza parcialmente `full_name`, `role` y/o `is_active`. Se puede enviar
cualquier subconjunto; los campos omitidos no cambian.

```bash
curl -i -X PATCH http://localhost:8000/api/v1/users/9a1e4c2d-5b6f-4a70-8c3d-1e2f3a4b5c6d \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.ejemplo.firma-ficticia" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Rita Recepción",
    "role": "dentist",
    "is_active": false
  }'
```

#### Response `200 OK`

Devuelve la cuenta actualizada con la misma forma que el listado.

Desactivar una cuenta surte efecto en el request siguiente: su access token
vigente deja de servir (`401 authentication_failed`) y no puede volver a
autenticarse (`401 invalid_credentials`).

#### Errores

| Caso | Respuesta |
|---|---|
| `id` inexistente | `404` `not_found` |
| `id` de otra clínica | `404` `not_found` (mismo cuerpo que el caso anterior) |
| rol desconocido | `422` `validation_error`, sin persistir nada |
| degradar o desactivar al último `admin` activo | `409` `last_admin`, sin persistir nada |
| rol `receptionist` o `dentist` | `403` `forbidden`, sin persistir nada |
| sin token o token inválido | `401` `authentication_failed` |

## Matriz RBAC aplicada

La fuente de verdad es
[`knowledge-base/03_actores_y_roles.md` §2](../../knowledge-base/03_actores_y_roles.md).
`C-02` implementa únicamente la fila de identidad y administración de usuarios;
las demás filas describen capacidades de changes posteriores y **no** se
anticipan acá.

Roles del sistema: `admin`, `receptionist`, `dentist`. El **paciente no es un
usuario del sistema**: accede por el portal público
(`/portal/reserva/{clinic_slug}`, C-09) y no tiene cuenta, token ni fila en
`users`.

| Capacidad | `admin` | `receptionist` | `dentist` | Paciente |
|---|---|---|---|---|
| Autenticarse y gestionar la propia sesión (`/auth/*`) | Sí | Sí | Sí | No es usuario del sistema |
| Administrar usuarios de la clínica (`/api/v1/users`) | Total | `403` | `403` | No aplica |
| Configurar la clínica / crear tenants | Sólo por bootstrap de operador (sin endpoint HTTP) | Sin acceso | Sin acceso | Sin acceso |
| Agenda general (C-04) | Lectura/escritura total | Lectura/escritura total | Sólo la propia, lectura | Sólo propios turnos por portal |
| Historia clínica (C-03/C-05) | Lectura (auditoría) | Sin acceso | Lectura/escritura total | Sólo resumen propio |
| Odontograma (C-05) | Sin acceso | Sin acceso | Lectura/escritura total | Sólo visualización |
| Caja y pagos (C-07) | Control total y cierres | Lectura/escritura diaria | Sin acceso | Sólo comprobantes propios |
| Facturación AFIP (C-08) | Configuración y emisión total | Emisión básica | Sin acceso | Descarga de la propia |
| Configuración clínica (C-09) | Control total | Sin acceso | Sin acceso | Sin acceso |

Notas de alcance:

- `C-02` **no amplía** la matriz: `/api/v1/users` es exclusivo de `admin`. El
  listado de profesionales (`dentist`) que necesita un `receptionist` para
  agendar es responsabilidad de **C-04** (`appointment-agenda`), que expondrá su
  propio endpoint o lectura acotada. Reutilizar `/api/v1/users` para ese fin
  exigiría un change posterior que modifique `identity-access`.
- La clínica activa y el rol efectivo se recargan en cada request
  (`get_current_principal`), por lo que una baja o un cambio de rol aplican sin
  esperar a que expire el access token.
- No existe ninguna ruta HTTP de alta de clínica: el único camino es el comando
  de operador `python -m app.cli.bootstrap_clinic` (design D8).

## Bootstrap de clínica (operador)

No existe una ruta HTTP para crear clínicas (design D8). El primer tenant de una
instalación se provisiona con el comando de operador
`python -m app.cli.bootstrap_clinic`, que crea la clínica y su primer usuario
`admin`. El comando es **idempotente** por `tax_id` (clínica) y `email`
(usuario): correrlo dos veces deja una sola clínica y un solo admin.

### Prerrequisitos

Desde la raíz del repositorio, con PostgreSQL arriba:

```bash
docker compose up -d db
```

La configuración se toma de las variables de entorno de
[`.env.example`](../../.env.example):

- `DATABASE_URL`: base de **desarrollo**
  (`postgresql+asyncpg://tpi:tpi@localhost:5433/tpi_dev` por defecto en Compose).
- `TEST_DATABASE_URL`: requerida por `Settings` aunque el bootstrap no la use;
  usar la de test de Compose.
- `SECRET_KEY`: obligatoria para que arranque cualquier proceso que importe
  `app.core.config` (incluido Alembic y el CLI).
- `BOOTSTRAP_ADMIN_PASSWORD` (opcional): contraseña inicial del admin. Si falta o
  está vacía, el comando la pide por **prompt oculto**.

En PowerShell (valores ficticios de desarrollo; no usar en producción):

```powershell
$env:DATABASE_URL="postgresql+asyncpg://tpi:tpi@localhost:5433/tpi_dev"
$env:TEST_DATABASE_URL="postgresql+asyncpg://tpi:tpi@localhost:5433/tpi_test"
$env:SECRET_KEY="dev-only-change-me"
```

### 1. Aplicar migraciones a la base de desarrollo

```powershell
cd backend
& .\.venv\Scripts\python.exe -m alembic upgrade head
```

Salida real contra `tpi_dev` (la base venía en `0001_init`):

```text
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0001_init -> 0002_core_models_tenants, clinics users refresh tokens
```

Verificación:

```powershell
& .\.venv\Scripts\python.exe -m alembic current
```

```text
0002_core_models_tenants (head)
```

### 2. Crear la clínica y su admin

La contraseña **nunca** se pasa como argumento (argv queda en el historial y en
la tabla de procesos). Se toma de `BOOTSTRAP_ADMIN_PASSWORD` o del prompt oculto:

```powershell
$env:BOOTSTRAP_ADMIN_PASSWORD="Dev-Bootstrap-123"
& .\.venv\Scripts\python.exe -m app.cli.bootstrap_clinic `
  --name "Clinica Demo Bootstrap" `
  --tax-id "30-12345678-9" `
  --email "admin@demo-bootstrap.com" `
  --full-name "Ada Administradora"
```

Salida real de la primera corrida (sin contraseña ni hash):

```text
clinic created: 'Clinica Demo Bootstrap' (tax_id=30-12345678-9, slug=clinica-demo-bootstrap, id=ae0696a9-af84-422e-9925-def2be080101)
admin user created: admin@demo-bootstrap.com (id=4cd11d5c-b0a3-4028-95e2-d4523d1a8e27, role=admin)
```

Si se omite `--slug`, se deriva del nombre (`clinica-demo-bootstrap`); ante una
colisión se agrega `-2`, `-3`, etc.

### 3. Verificar la idempotencia

Repetir exactamente el mismo comando:

```text
clinic already exists: 'Clinica Demo Bootstrap' (tax_id=30-12345678-9, id=ae0696a9-af84-422e-9925-def2be080101)
admin user already exists: admin@demo-bootstrap.com (id=4cd11d5c-b0a3-4028-95e2-d4523d1a8e27, role=admin)
```

Estado resultante en `tpi_dev` (consulta real):

```text
clinics=1
users=1
refresh_tokens=0
```

### 4. Usar el prompt oculto (sin `BOOTSTRAP_ADMIN_PASSWORD`)

Quitar la variable y volver a correr el comando contra una clínica/email nuevos:

```powershell
Remove-Item Env:BOOTSTRAP_ADMIN_PASSWORD
& .\.venv\Scripts\python.exe -m app.cli.bootstrap_clinic `
  --name "Otra Clinica" --tax-id "30-00000000-0" `
  --email "otra@example.com" --full-name "Otro Admin"
```

El comando muestra `Initial admin password:` y lee la clave con
`getpass.getpass`, que no la ecoa ni la deja en argv. Este camino está cubierto
por el test `test_password_comes_from_the_hidden_prompt_when_env_is_absent`
(`backend/tests/test_cli_bootstrap.py`).

### Reglas y errores del comando

- La contraseña debe tener entre 8 y 72 bytes (límite de bcrypt). Un valor
  inválido imprime sólo la regla violada y termina con código `2`; no persiste
  nada y nunca repite la clave.
- Un `--password` (u otra opción desconocida) es rechazado por `argparse` con
  código `2`: la clave no se acepta por línea de comandos.
- Si el `email` ya existe en **otra** clínica, el comando se niega (el email es
  único global, design D6) y termina con código `1`.
- La salida sólo incluye identificadores y estado; nunca la contraseña ni el
  hash almacenado.
- No hay endpoint HTTP de alta de clínicas: el comando es el único camino.

## Notas operativas

- En producción el tráfico debe ir por TLS; el refresh token viaja en el cuerpo
  de la respuesta (evaluación de cookie `HttpOnly` queda para C-10).
- `SECRET_KEY` firma los access tokens y debe ser propia de cada entorno; nunca
  se versiona ni se comparte entre dev y producción.
- Los ejemplos anteriores usan `curl` de POSIX. En PowerShell, `curl` es un
  alias de `Invoke-WebRequest`; usá `curl.exe` o `Invoke-RestMethod` con el mismo
  cuerpo JSON.
