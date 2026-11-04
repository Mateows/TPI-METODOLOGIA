# Tasks

## 1. Dependencias y núcleo de seguridad

- [x] 1.1 Agregar `PyJWT` y `bcrypt` a `backend/requirements.txt` con versión
  fijada, instalarlas y verificar con `pip install -r requirements.txt` seguido
  de `python -c "import jwt, bcrypt"`.
- [x] 1.2 Implementar `app/core/security.py` (hash/verify de contraseña, firma y
  decodificación de access token, generación y hash del refresh, reloj
  inyectable) y verificar con tests unitarios en
  `backend/tests/test_security.py` (hash y token expirado, alterado y con firma
  ajena).
- [x] 1.3 Agregar a `Settings` las duraciones de access/refresh token con
  default y validación de rango (fail-fast ante valor inválido) y
  `BOOTSTRAP_ADMIN_PASSWORD` como opcional; documentar cada variable nueva en
  `.env.example` de la raíz y actualizar `backend/tests/test_env_example.py`,
  que hoy exige un conjunto exacto de claves requeridas. Verificar con un test
  de configuración que un valor de duración inválido impide el arranque.

## 2. Modelos y migración

- [x] 2.1 Implementar `Clinic`, `User` y `RefreshToken` en `app/models/` con
  UUID, `clinic_id` indexado, `is_active`, timestamps UTC y `naming_convention`
  de índices/constraints en `Base.metadata` de `app/core/database.py`;
  verificar con tests de esquema que existen las columnas, la unicidad de
  `email`/`slug` y las relaciones, y que el rol `dentist` identifica al
  profesional (design D12).
- [x] 2.2 Crear `alembic/versions/0002_core_models_tenants.py` con
  `revision = "0002_core_models_tenants"` y `down_revision = "0001_init"`;
  verificar aplicando `alembic upgrade head` sobre una base vacía, una segunda
  corrida no-op, `alembic downgrade 0001_init` seguido de `upgrade head` sin
  errores, y actualizar `backend/tests/test_migrations.py` (hoy espera
  `0001_init` como head).
- [x] 2.3 Importar los modelos desde `app/models/__init__.py` y cargarlos en la
  cadena que usa `alembic/env.py` (vía `Base.metadata`) de modo que Alembic
  detecte las tablas; verificar con `alembic check` (sin diferencias pendientes),
  actualizar `backend/tests/test_database.py` (hoy afirma `metadata.tables == {}`)
  y correr el harness completo en verde.

## 3. Contexto multi-tenant, errores y guardas

- [x] 3.1 Implementar las excepciones de dominio y sus handlers (401/403/404/
  409/422 con `code` estable, sin trazas SQL) y verificar con tests de contrato
  que el cuerpo no expone texto del driver.
- [x] 3.2 Implementar `get_current_principal` (decodifica token, recarga
  usuario y clínica, rechaza inactivos) y verificar con tests de token válido,
  expirado, de usuario desactivado (401) y de clínica inactiva (403).
- [x] 3.3 Implementar `require_roles(...)` y `TenantScopedRepository`, y
  verificar con tests que un rol no permitido recibe 403 sin efectos, que una
  lectura por id de otra clínica devuelve el mismo resultado que un id
  inexistente y que un `clinic_id` enviado por el cliente que difiere del token
  se rechaza o se ignora sin efecto.

## 4. Autenticación

- [x] 4.1 Implementar `POST /api/v1/auth/login` y registrar el router en
  `create_app()` (`app/main.py`) con credenciales válidas, credenciales
  inválidas genéricas y usuario inactivo; verificar los tres escenarios contra
  `client` con la base aislada.
- [x] 4.2 Implementar `POST /api/v1/auth/refresh` con rotación y detección de
  reuso; verificar refresco válido, token viejo inutilizable y reuso que revoca
  la familia completa.
- [x] 4.3 Implementar `POST /api/v1/auth/logout` y `GET /api/v1/auth/me`;
  verificar que el logout invalida el refresh y que `/me` devuelve sólo datos
  del usuario autenticado, sin hash ni tokens.
- [x] 4.4 Implementar `PATCH /api/v1/auth/password` (cambio por el propio
  usuario) y verificar que la contraseña vieja deja de funcionar y que las
  otras sesiones del usuario quedan revocadas.
- [x] 4.5 Crear `backend/docs/api-auth.md` (la carpeta `backend/docs/` no existe
  todavía) y documentar los endpoints de autenticación con ejemplos
  reproducibles (curl con valores ficticios); verificar que cada ejemplo
  respeta los códigos de error implementados.

## 5. Administración de usuarios

- [x] 5.1 Implementar `POST /api/v1/users` y `GET /api/v1/users` acotados al
  `clinic_id` del admin y registrar el router en `create_app()`; verificar alta
  exitosa, rol inválido rechazado, email duplicado con 409 y listado que nunca
  incluye usuarios de otra clínica.
- [x] 5.2 Implementar `PATCH /api/v1/users/{id}` para actualizar nombre, rol y
  estado; verificar que un admin no puede modificar usuarios de otra clínica
  (misma respuesta que id inexistente) ni degradarse a sí mismo sin dejar la
  clínica sin administrador.
- [x] 5.3 Verificar con tests que `receptionist` y `dentist` reciben 403 en
  todos los endpoints de administración y que ningún intento persiste cambios.
- [x] 5.4 Documentar la administración de usuarios y la matriz RBAC aplicada en
  `backend/docs/api-auth.md`; verificar que la matriz coincide con
  `knowledge-base/03_actores_y_roles.md` §2 (roles `admin`, `receptionist`,
  `dentist`; el paciente no es usuario del sistema).

## 6. Bootstrap de clínica

- [x] 6.1 Crear el paquete `app/cli/` e implementar
  `python -m app.cli.bootstrap_clinic` idempotente por `tax_id`/`email`, con
  contraseña tomada de `BOOTSTRAP_ADMIN_PASSWORD` o de prompt oculto; verificar
  con un test de integración que dos corridas dejan una sola clínica y un solo
  usuario (admin activo con rol `admin`).
- [x] 6.2 Verificar que no existe ruta pública de alta de clínica y que el
  bootstrap no imprime la contraseña ni el hash en stdout.
- [x] 6.3 Documentar el procedimiento de bootstrap en `backend/docs/api-auth.md`
  y verificar que el comando documentado funciona contra la base de desarrollo
  provista por `docker-compose.yml`.

## 7. Integración y cierre

- [x] 7.1 Ejecutar la suite completa con SQLite y con PostgreSQL
  (`DATABASE_URL`/`TEST_DATABASE_URL` de Compose) y verificar que todos los
  tests pasan sin escribir en la base de desarrollo.
- [x] 7.2 Ejecutar `openspec validate core-models-tenants --strict` y revisar
  los escenarios contra la KB; verificar que cada requisito tiene escenarios y
  que no se marca el change como implementado antes de las pruebas.
- [x] 7.3 Actualizar el estado de `C-02` en `CHANGES.md` y verificar que
  `appointment-agenda` deja de estar bloqueado por su dependencia.

## Workflow follow-up

- Aplicar Strict TDD: escribir primero el test o comando de verificación
  descrito en cada tarea y recién después el código que lo satisface.
- Archivar el change sólo después de la revisión de governance CRÍTICO
  (checkpoint de autorización y aislamiento con el usuario).
- Verificar el resultado archivado en `openspec/specs/` y que
  `openspec/specs/identity-access` y `openspec/specs/tenant-isolation`
  reemplazan los placeholders de `Purpose`.
