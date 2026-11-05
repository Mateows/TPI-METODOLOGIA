# Evidencia — Invocaciones reales del MCP `github` sobre C-02

| Campo | Valor |
|---|---|
| **MCP** | `github` (remoto) — `https://api.githubcopilot.com/mcp/` |
| **Cliente** | OpenCode (desktop) sobre Windows |
| **Change asistido** | `C-02` — `openspec/changes/archive/2026-11-04-core-models-tenants/` |
| **Fecha** | 04/11/2026 |
| **Herramientas usadas** | `get_me`, `search_code`, `search_repositories` |

Todas las invocaciones fueron de **solo lectura**. No se creó ni modificó nada en GitHub
ni se envió ningún dato del proyecto.

---

## 1. `get_me` — identidad y alcance del token

- **Solicitud:** verificar qué usuario autentica el PAT y con qué alcance operan las
  consultas.
- **Resultado:** `login = Mateows`, `name = Liendo Mateo Lautaro`, `public_repos = 12`.
- **Aporte:** confirma que las búsquedas se ejecutan con el alcance de una cuenta personal
  de solo lectura, no con permisos de servicio.

## 2. `search_code` — patrón de revocación de sesiones por reuso de refresh token

- **Solicitud:** verificar si "rotar el refresh token en cada uso y revocar toda la
  familia al detectar un token ya consumido" es un patrón establecido o una invención del
  proyecto.
- **Consultas y resultados:**

| Consulta | `total_count` | Muestra |
|---|---|---|
| `"token family" revoke reuse language:python` | **1.282** | `django-oauth/django-oauth-toolkit` · `oauth2_provider/models.py`; `dj-bolt/django-bolt` · `python/django_bolt/auth/revocation.py`; `sillohq/core` · `sillo/auth/jwt_auth/models.py` |
| `"reuse detection" refresh token language:python` | **3.816** | `litestar-org/litestar-fullstack` · `src/py/app/db/models/_refresh_token.py`; `kesa0v0/Stonks` · `backend/schemas/token.py` |
| `"refresh token" family revoke reuse language:python` | **5.944** | `django-oauth/django-oauth-toolkit`; `sillo/auth/jwt_auth/models.py`; `app/services/token_service.py` |

- **Aporte a C-02:** respalda la decisión de implementar `RefreshToken` con `family_id`,
  rotación en cada `refresh` y revocación de toda la familia ante reuso. El patrón aparece
  en frameworks de OAuth2 maduros (`django-oauth-toolkit`, `litestar-fullstack`), por lo
  que el diseño no es ad hoc. Además justifica mantener la **ventana de gracia de 10 s**
  como decisión propia: la familia se revoca igual, pero sin castigar el doble refresh
  legítimo de dos pestañas.

## 3. `search_code` — filtrado explícito por columna de tenant

- **Solicitud:** comprobar si la práctica de filtrar por la columna de tenant **dentro de
  la consulta** (y no delegar el aislamiento a una capa implícita) está extendida.
- **Consultas y resultados:**

| Consulta | `total_count` | Muestra |
|---|---|---|
| `"tenant_id" where filter repository language:python` | **12.016** | `vinaynettem09/hiring-intelligence` · `backend/app/shared/repository.py`; `bhargavatejagolla/Laminar` · `backend/app/core/repository.py`; `Percolation-Labs/p8k8` · `p8/services/repository.py` |
| `"clinic_id" language:python` | **18.688** | `cutlass/Visit.py`; `luxmed_sniper.py`; `scripts/seed.py` |

- **Aporte a C-02:** las coincidencias relevantes concentran el filtro por tenant dentro de
  un **módulo `repository`**, no en los servicios ni en los handlers. Esa observación
  respalda la remediación **D13** (capa `app/repositories/` con `TenantScopedRepository`),
  que centraliza el filtro y prohíbe construir consultas fuera de ella, verificado por
  `backend/tests/test_architecture.py`.

## 4. `search_repositories` — estado del arte del dominio

- **Solicitud:** buscar backends públicos de SaaS multi-tenant con FastAPI:
  `fastapi multi-tenant saas backend`.
- **Resultado:** `total_count = 126`. Muestra: `abhishektarun09/multi_tenant_saas_fastapi`,
  `ASR134/multi-tenant-saas-backend`, `mahadi-hasan-kamrul/multi-tenant-saas-backend`,
  `SaaS-Maker-Stack/backend`, `p2p-lanes/edgeos-monorepo`.
- **Aporte a C-02:** a diferencia del dominio odontológico (5 repositorios, ninguno con
  tracción), el multi-tenant genérico sí tiene material abundante. Eso confirma que el
  aislamiento por `clinic_id` es una **variante concreta de un problema resuelto** y que
  corresponde reutilizar el patrón en lugar de diseñarlo desde cero — decisión que se
  materializó en `TenantScopedRepository`.

---

## Rechazos explícitos

Que una consulta devuelva resultados **no** significa que se haya adoptado lo que muestra:

1. **`search_code` sobre reuso de refresh token — no se adoptó código externo.** Se tomó
   solo la **forma** del patrón (familia + rotación + revocación). La implementación de
   C-02 es propia: hash SHA-256 del token opaco, reloj inyectable y ventana de gracia
   parametrizable, porque los resultados encontrados dependen de frameworks (Django,
   Litestar) con supuestos de sesión distintos a los de FastAPI + SQLAlchemy async.
2. **`search_repositories` — no se adoptó ningún repositorio como referencia.** Ninguno de
   los 126 repositorios es del dominio odontológico ni cubre el requisito de Ley 25.326
   que exige la KB; se usaron únicamente como confirmación de que el problema de
   multi-tenancy tiene soluciones canónicas.
3. **`search_code` sobre `clinic_id` — se rechazó el filtrado en el servicio.** Varias
   coincidencias filtran en handlers o en queries sueltas. Ese estilo se descartó
   explícitamente en D13: si el filtro vive disperso, ninguna prueba de arquitectura puede
   garantizar que no falte en un endpoint nuevo. De ahí la guarda AST en
   `test_architecture.py`.

## Trazabilidad

| Consulta MCP | Decisión de C-02 que respalda | Artefacto |
|---|---|---|
| `"token family" revoke reuse` | `RefreshToken` con `family_id` y revocación por reuso | `design.md` §Decisiones de sesión; `app/services/auth.py` |
| `"reuse detection" refresh token` | Ventana de gracia de 10 s antes de revocar | `test_reuse_after_the_grace_window_revokes_the_whole_family` |
| `"tenant_id" where filter repository` | Capa `app/repositories/` (**D13**) | `app/repositories/base.py`; `test_architecture.py` |
| `fastapi multi-tenant saas backend` | Reutilizar el patrón de multi-tenancy en vez de inventarlo | `openspec/specs/tenant-isolation/spec.md` |
