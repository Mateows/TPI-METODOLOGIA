# Informe de aplicación — Skill propia y MCP integrados a la fundación

- **Autor:** Mateo Liendo (trabajo individual) · **Fechas:** 30/10/2026 (skill + primera pasada del MCP) · 04/11/2026 (MCP sobre C-02) · 05/11/2026 (C-04 implementado y archivado)
- **Changes asistidos:**
  - **C-04** `appointment-agenda` — **implementado, verificado y archivado** (2026-11-05). La skill se
    aplicó sobre sus artefactos; sus 11 observaciones se aplicaron antes de implementar (`a0fc1cb`)
    y quedaron cubiertas por escenarios. Cuenta para el mínimo.
  - **C-02** `core-models-tenants` — **implementado, verificado y archivado**. El MCP se aplicó sobre
    decisiones de este change; cuenta para el mínimo.


## 1. Resultados

### 1.1 Skill propia: `revisor-de-agendas-de-citas`

Invocada sobre los artefactos de C-04 en modo solo revisión: **11 observaciones — 1 crítica,
5 importantes, 5 menores**. Las tres de mayor impacto:

| Sev. | Hallazgo | Corrección propuesta |
|---|---|---|
| Crítica | `spec.md` §*Appointment creation*: no se define el origen del `clinic_id` persistido | Tomarlo solo del contexto autenticado, prohibirlo en el payload y agregar escenario de rechazo por `clinic_id` ajeno |
| Importante | `spec.md` §*Overlap prevention*: cobertura parcial de solapamientos | Agregar escenarios por box, cita contenida, coincidencia exacta y `cancelled` que libera el intervalo; reflejarlos en `tasks.md` 2.3 |
| Importante | `spec.md` §*Appointment creation*: datetimes con offset o *naive* fuera de la spec (la regla vive solo en `design.md` §Risks) | Exigir datetimes con zona, normalizar a UTC en el borde y rechazar *naive* |

Cada observación quedó respaldada con `knowledge-base/04_modelo_de_datos.md` (§1),
`05_reglas_de_negocio.md` (RN-01, RN-02, RN-04, RN-07), `07_flujos_principales.md` (Flujo 1),
`CHANGES.md` y las reglas duras 1, 4 y 8 de `AGENTS.md`.

**Cierre del ciclo:** la skill no editó nada. Las 11 observaciones se aplicaron como decisión
explícita del autor antes de implementar (commit `a0fc1cb`), y quedaron verificadas por la suite
de C-04. La skill aporta el diagnóstico; el change materializa la corrección.
**Evidencia:** [`evidencias/revision-skill-c04.md`](evidencias/revision-skill-c04.md)

### 1.2 MCP elegido: GitHub MCP Server

| Verificación | Resultado |
|---|---|
| `opencode mcp list` | `✓ github connected` (5/5 servidores) |
| Tools expuestas | 49 |
| `get_me` | autenticado como `Mateows` |
| `search_code` — `EXCLUDE USING gist tstzrange` | 26.976 coincidencias |
| `search_repositories` — `dental appointment scheduling fastapi` | 5 repositorios |

**Aporte al change:** el patrón de exclusión de rangos es estándar en PostgreSQL, lo que
respalda que RN-01 no se limite a validación en servicios (vulnerable a carreras entre
transacciones); la escasez de implementaciones públicas del dominio justifica que C-04 defina
su propio esquema desde la KB.
**Evidencia:** [`evidencias/mcp-github-c04.md`](evidencias/mcp-github-c04.md) · **Configuración:**
[`mcp-github.md`](mcp-github.md)

#### 1.2.1 Segunda pasada del MCP — sobre C-02 (change archivado)

La primera pasada quedó atada a C-04, que no cuenta para el mínimo. Para que la evidencia de
MCP se apoye en el alcance efectivamente entregado, se repitió el procedimiento sobre dos
decisiones de C-02:

| Consulta | Resultado | Decisión que respalda |
|---|---|---|
| `"token family" revoke reuse language:python` | 1.282 coincidencias (`django-oauth-toolkit`, `litestar-fullstack`) | `RefreshToken` con `family_id` y revocación de la familia ante reuso |
| `"tenant_id" where filter repository language:python` | 12.016 coincidencias, con el filtro dentro de módulos `repository` | Capa `app/repositories/` (**D13**) y guarda AST |

Lo que se **rechazó**: no se adoptó código externo (los resultados dependen de Django/Litestar,
con supuestos de sesión distintos) ni ningún repositorio de referencia (ninguno cubre el
dominio odontológico ni la Ley 25.326); y se descartó el estilo de filtrar por tenant en
handlers o queries sueltas, que es lo que D13 prohíbe.

**Evidencia:** [`evidencias/mcp-github-c02.md`](evidencias/mcp-github-c02.md)


### 1.3 Integración a la fundación

La skill quedó ubicada, registrada y referenciada en las instrucciones del agente; el MCP quedó
documentado como *integración* (no como skill), con propósito, capacidades, uso y límites. No se
regeneró ninguna etapa de la fundación.


## 2. Archivos modificados y motivo

| Archivo | Estado | Motivo |
|---|---|---|
| `.agents/skills/revisor-de-agendas-de-citas/SKILL.md` | nuevo | Skill propia del TP |
| `.agents/skills/skill-creator/` + `skills-lock.json` | nuevo | Skill creadora versionada (origen y hash) para que la creación sea reproducible |
| `.atl/skill-registry.md` | modificado | Alta de la skill propia |
| `AGENTS.md` | modificado | Secciones «Skill propia» y «Servidor MCP» (propósito, capacidades, uso, límites) |
| `CLAUDE.md` | modificado | Espejo de las dos secciones para que ambos archivos coincidan |
| `opencode.json` | nuevo | Configuración del MCP, sin secretos |
| `docs/skills-mcp/` | nuevo | Investigación, aplicación, doc del MCP y evidencias |
| `README.md` | modificado | Enlace a la documentación del MCP |


## 3. Revisión crítica

### 3.1 Error 1 — diagnóstico incompleto del agente

- **Antes:** concluyó que bastaba cerrar y reabrir la aplicación para que el MCP tomara la
  variable nueva.
- **Detección:** seguía `✗ github failed` con `token len = 0`. La UI se inició 10:19, pero
  `opencode-cli.exe` seguía vivo desde las **8:55** escuchando en `127.0.0.1:28894`: la UI se
  reconectó a ese backend viejo.
- **Corrección:** terminar también `opencode-cli.exe`, no solo la ventana. **Después:**
  `token len = 93`, `5/5 connected`.

### 3.2 Error 2 — sugerencia inadecuada del propio agente

- **Antes:** relanzó la app desde una consola hija del backend viejo; el proceso nuevo heredó
  el **entorno vacío** y el fallo se repitió.
- **Detección:** el log mostraba el relanzamiento exitoso, pero seguía con `token len = 0`.
- **Corrección:** leer la variable del registro y pasarla explícita con
  `ProcessStartInfo.EnvironmentVariables` en vez de confiar en la herencia. **Después:** el
  server arrancó con el token y las tools quedaron disponibles.

### 3.3 Corrección de una recomendación previa

- **Antes:** el agente recomendó Context7 como MCP elegido, por no requerir credenciales.
- **Qué la corrigió:** el enunciado pide comparar dos MCP, documentar **nombres de variables
  de entorno** y registrar los **problemas de compatibilidad resueltos**: valora el trabajo de
  integración con credenciales.
- **Después:** GitHub pasó a ser el elegido, con la desventaja de reproducibilidad de Context7
  declarada.

### 3.4 Límite detectado en el MCP de archivos

`filesystem` tiene su *root* en el proyecto y **no pudo leer** un PDF en `Downloads` (verificado
con `list_allowed_directories`); el texto se extrajo por otra vía. El límite no se corrigió: se
adoptó como decisión, porque un root acotado es la restricción que el TP pide declarar.

### 3.5 Omisión que la skill sí detectó

`design.md` de C-04 no incluía la sección `## UI Mockups` con la decisión de política del
proyecto. La skill la reportó como pendiente y **no** la agregó, respetando su límite. Se
resolvió después con `Decision: no (no UI)`: C-04 es backend-only.


## 4. Limitaciones

1. **Reproducibilidad:** cada integrante necesita su propio PAT; no es «cero-config».
2. **Endpoint remoto:** las tools pueden cambiar del lado de GitHub; no se fija versión.
3. **Cobertura de la skill:** no incluye `knowledge-base/06_funcionalidades.md`, así que
   requisitos de la épica de agenda podrían quedar sin contrastar.
4. **Alcance:** la skill produce observaciones de especificación, verificables por escenarios,
   pero no mide calidad de implementación; para eso está la suite de C-04.
5. **Alcance entregado:** C-04 quedó implementado y archivado (2026-11-05) con 259 tests en
   verde; C-05 a C-10 siguen pendientes y declarados como tales en `CHANGES.md`.
