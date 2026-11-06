# Ficha de investigación — Skill propia y servidor MCP

- **Autor:** Mateo Liendo (trabajo individual)
- **Fecha:** 30/10/2026 · **Actualizado:** 05/11/2026 (C-04 implementado y archivado)
- **Repositorio:** TPI Metodología — SaaS odontológico multi-tenant (FastAPI + React + PostgreSQL)
- **Base:** TP «Del Discovery al primer Change» (fundación con Active Stack + C-01 archivado)

> **Estado actual:** la investigación se hizo con C-04 todavía como especificación. Hoy C-04
> `appointment-agenda` está **implementado, verificado y archivado**; las 11 observaciones de la
> skill se aplicaron antes de implementar (`a0fc1cb`) y el MCP respaldó tanto C-02 como C-04.

---

## 1. Necesidad detectada

C-04 concentra tres reglas que se cruzan: aislamiento por `clinic_id`, prevención de
solapamiento de turnos (RN-01) y consistencia temporal en UTC. Revisar esos artefactos a
mano es **repetible** y propenso a omisiones: es fácil olvidar que un turno cancelado
libera el intervalo, o que un datetime *naive* no está cubierto por ningún escenario.

De ahí las dos incorporaciones: una **skill** con procedimiento fijo que obligue a
recorrer los mismos controles y clasifique hallazgos por severidad; y un **MCP** que dé
acceso verificable a información externa al repo (patrones de código reales) para
fundamentar decisiones que la KB local no cubre.

## 2. Change elegido

**C-04 `appointment-agenda`**. Cuando se hizo la investigación era el siguiente
change habilitado del roadmap y figuraba pendiente en `CHANGES.md` (§C-04: modelos
`Box`/`Appointment`, RN-01, endpoints de agenda; governance **ALTO**, dependía de C-02).
Hoy está implementado, verificado y archivado en
`openspec/changes/archive/2026-11-05-appointment-agenda/`, con la spec canónica en
`openspec/specs/appointment-agenda/spec.md` y 259 tests en verde.

## 3. Skill creadora y diseño de la skill propia

**Creadora:** `skill-creator`, de `anthropics/skills` (`skills/skill-creator/SKILL.md`).
Instalada en `.agents/skills/skill-creator/` y verificable en `skills-lock.json`
(source `github` + hash); referenciada en `.atl/skill-registry.md`.

**Propia:** `revisor-de-agendas-de-citas` → `.agents/skills/revisor-de-agendas-de-citas/SKILL.md`

| Aspecto | Definición |
|---|---|
| Propósito | Detectar ambigüedades, omisiones y contradicciones en artefactos de agenda antes de implementar |
| Cuándo se activa | Al preparar o revisar `appointment-agenda`; al validar solapamientos, `clinic_id`, UTC o estados |
| Entradas | proposal, specs, design y tasks del change; `CHANGES.md`; KB 04, 05 y 07; `AGENTS.md` |
| Procedimiento | 10 pasos: confirmar change → comparar artefactos → `clinic_id` → intervalos/UTC → solapamientos (parcial, contención, exacta, consecutivas, canceladas) → estados → 3 escenarios verificables → tareas → severidad → corrección propuesta |
| Salida | Informe con Resumen, Checklist de 8 puntos, Observaciones por severidad y Correcciones pendientes |
| Criterios | Cada observación cita archivo y sección; toda corrección es verificable por un escenario; no implementa código |

Vive en `.agents/skills/` (versionada), registrada en `.atl/skill-registry.md` y
mencionada en `AGENTS.md`.

## 4. Comparación de MCP y elección

| Criterio | **GitHub MCP Server** | **Context7** |
|---|---|---|
| Propósito | Plataforma GitHub: repos, código, issues, PRs, Actions | Documentación de librerías |
| Capacidades | 49 tools (repos, code search, issues, PRs, actions, users) | `resolve-library-id` + `query-docs` |
| Compatibilidad | Remoto HTTP; guía oficial para OpenCode | Remoto; ejemplo oficial en la doc de OpenCode |
| Credenciales | PAT *fine-grained*; OAuth inviable (sin DCR, cada host debe registrar su app) | Ninguna para uso básico |
| Permisos | Los scopes del PAT acotan todo; se puede usar solo lectura | Lectura de documentación pública |
| Costos | Gratuito dentro de la plataforma GitHub | Gratuito |
| Reproducibilidad | Media: cada integrante necesita su token | Alta: cero configuración |

**Elección: GitHub MCP Server.** El riesgo central de C-04 es de **diseño de datos**
(impedir solapamientos de forma confiable) y eso se valida mejor contra código real que
contra documentación. Con este MCP se verificó que `EXCLUDE USING gist` sobre rangos
`tstzrange` es el enfoque estándar en PostgreSQL (26.976 coincidencias) y que el dominio
«dental + FastAPI» casi no tiene implementaciones públicas (5 repos), lo que respalda el
alcance propio del change. Contra declarada: **Context7 es más reproducible**; se compensa
documentando la configuración y usando `{env:...}` para no versionar secretos.

## 5. Instalación y configuración (resumen)

Detalle reproducible, sin secretos, en [`mcp-github.md`](mcp-github.md).

1. PAT *fine-grained* de solo lectura sobre los repositorios a consultar.
2. Variable de usuario `GITHUB_PERSONAL_ACCESS_TOKEN` (**nunca** en el repo).
3. `opencode.json` del proyecto:

```json
"github": {
  "type": "remote",
  "url": "https://api.githubcopilot.com/mcp/",
  "enabled": true,
  "oauth": false,
  "headers": { "Authorization": "Bearer {env:GITHUB_PERSONAL_ACCESS_TOKEN}" }
}
```

4. Verificar con `opencode mcp list` (`✓ github connected`) y `opencode mcp debug github`.
5. Ejecutar una herramienta real (`get_me`, `search_code`).
6. Reiniciar el cliente completo: el backend conserva el entorno con el que arrancó.

**Límites:** token de solo lectura, alcance de un repositorio, uso sobre código y
metadatos. El repo no contiene datos reales de pacientes.

## 6. Archivos de la fundación que se actualizan

| Archivo | Cambio previsto |
|---|---|
| `.atl/skill-registry.md` | Alta de la skill propia con propósito y ubicación |
| `AGENTS.md` | Sección «Skill propia del práctico»: cuándo usarla y que no implementa |
| `README.md` | Enlace a la documentación del MCP |
| `docs/skills-mcp/mcp-github.md` | Requisitos, configuración, verificación y troubleshooting |
| `CHANGES.md` | Referencia a los artefactos de C-04, hoy con estado **implementado y archivado** |
| `knowledge-base/` | Sin cambios: no se modifican reglas de dominio en esta instancia |

## 7. Fuentes (consultadas el 30/10/2026)

| Fuente | URL | Qué se verificó |
|---|---|---|
| skill-creator (Anthropic) | https://github.com/anthropics/skills | Existencia del paquete y compatibilidad con Agent Skills |
| GitHub MCP Server (oficial) | https://github.com/github/github-mcp-server | Endpoint remoto, PAT en `Authorization`, toolsets y que OAuth exige app propia del host |
| OpenCode — MCP servers | https://opencode.ai/docs/mcp-servers/ | `type: remote`, `headers`, `{env:...}`, `oauth: false`; comandos `mcp list/auth/debug` |

**Pendiente:** no se contrastó documentación oficial de Context7 (solo se usó su endpoint
público); los toolsets del endpoint remoto pueden variar sin aviso.
