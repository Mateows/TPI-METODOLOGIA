# ENTREGA — TP Metodología I: skill propia + servidor MCP

## Integrantes

- **Mateo Lautaro Liendo** — trabajo individual

## Datos de la entrega

| Campo | Valor |
|---|---|
| Repositorio | https://github.com/Mateows/TPI-METODOLOGIA |
| Rama | `master` (todo consolidado; las ramas de trabajo ya se fusionaron) |
| Tag de la entrega | `entrega-tpi` (congela exactamente la versión entregada) |
| Commits de la entrega | Historial completo con `git log --oneline`. Commits que aportan contenido: `1112134` skill propia · `49e15cf` MCP + evidencias · `95784ab` artefactos de C-04 · `3faf9b9` informes · `e4182c3` sección MCP en instrucciones · `f58e232` PDFs · `a0fc1cb` hallazgos de la skill aplicados · `0eff18b` C-04 implementado y archivado |
| Ficha de investigación | [`docs/skills-mcp/investigacion.md`](docs/skills-mcp/investigacion.md) — también en PDF: [`investigacion.pdf`](docs/skills-mcp/investigacion.pdf) |
| Informe de aplicación | [`docs/skills-mcp/aplicacion.md`](docs/skills-mcp/aplicacion.md) — también en PDF: [`aplicacion.pdf`](docs/skills-mcp/aplicacion.pdf) |
| Video de demostración | https://www.youtube.com/watch?v=yvxYBFweSwQ — acceso con el enlace |

## Contenido

| Elemento | Ubicación |
|---|---|
| Skill propia (`revisor-de-agendas-de-citas`) | `.agents/skills/revisor-de-agendas-de-citas/SKILL.md` |
| Skill creadora utilizada | `.agents/skills/skill-creator/` + `skills-lock.json` |
| Registro de skills | `.atl/skill-registry.md` |
| Instrucciones del agente | `AGENTS.md` y `CLAUDE.md` (secciones «Skill propia del práctico» y «Servidor MCP del práctico») |
| Configuración del MCP | `opencode.json` (sin secretos) |
| Documentación del MCP | [`docs/skills-mcp/mcp-github.md`](docs/skills-mcp/mcp-github.md) |
| Guion de demo del MCP | [`docs/skills-mcp/demo-mcp.md`](docs/skills-mcp/demo-mcp.md) |
| Chequeo previo a grabar (Docker, base, API, archivos, token) | [`scripts/chequear-video.ps1`](scripts/chequear-video.ps1) |
| Evidencias | `docs/skills-mcp/evidencias/` |
| Change C-04 (implementado y archivado) | `openspec/changes/archive/2026-11-05-appointment-agenda/` · spec canónica en `openspec/specs/appointment-agenda/spec.md` |

## Cómo comprobar la disponibilidad de ambas herramientas

**Skill** — debe aparecer en el registro y ser invocable por el agente:

```bash
grep revisor .atl/skill-registry.md
```

**MCP** — requiere un PAT propio en la variable `GITHUB_PERSONAL_ACCESS_TOKEN`:

```powershell
[Environment]::SetEnvironmentVariable("GITHUB_PERSONAL_ACCESS_TOKEN","<tu-token>","User")
# reiniciar el cliente completo, incluido el backend opencode-cli
opencode mcp list      # esperado: ✓ github connected
```

Luego, en el chat: pedir `get_me` y `search_code` como se describe en
`docs/skills-mcp/mcp-github.md`.

## Aclaraciones

- El change **C-04 está implementado, verificado y archivado** (2026-11-05): 12/12 tareas,
  259 tests en verde en SQLite y PostgreSQL. Cubre C-01 a C-04; C-05 a C-10 siguen
  pendientes y declarados como tales en `CHANGES.md`.
- El cambio de estado se produjo después de esta entrega: la ficha y el informe se
  actualizaron para reflejar que los hallazgos de la skill se aplicaron antes de implementar.
- **Sin secretos:** el token no está en el repositorio ni en esta entrega. La
  configuración usa `{env:GITHUB_PERSONAL_ACCESS_TOKEN}`.
- **Sin datos de pacientes:** todo el material usa datos ficticios.
