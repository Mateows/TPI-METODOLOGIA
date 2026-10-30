# ENTREGA — TP Metodología I: skill propia + servidor MCP

## Integrantes

- **Mateo Lautaro Liendo** — trabajo individual

## Datos de la entrega

| Campo | Valor |
|---|---|
| Repositorio | https://github.com/Mateows/TPI-METODOLOGIA |
| Rama | `tp-skills-mcp` |
| Commits de la entrega | `1112134` skill propia · `49e15cf` MCP + evidencias · `95784ab` artefactos de C-04 · `3faf9b9` informes · `e4182c3` sección MCP en instrucciones |
| Ficha de investigación | [`docs/skills-mcp/investigacion.md`](docs/skills-mcp/investigacion.md) — también en PDF: [`investigacion.pdf`](docs/skills-mcp/investigacion.pdf) |
| Informe de aplicación | [`docs/skills-mcp/aplicacion.md`](docs/skills-mcp/aplicacion.md) — también en PDF: [`aplicacion.pdf`](docs/skills-mcp/aplicacion.pdf) |
| Video de demostración | _(pendiente — completar con el enlace accesible)_ |

## Contenido

| Elemento | Ubicación |
|---|---|
| Skill propia (`revisor-de-agendas-de-citas`) | `.agents/skills/revisor-de-agendas-de-citas/SKILL.md` |
| Skill creadora utilizada | `.agents/skills/skill-creator/` + `skills-lock.json` |
| Registro de skills | `.atl/skill-registry.md` |
| Instrucciones del agente | `AGENTS.md` y `CLAUDE.md` (secciones «Skill propia del práctico» y «Servidor MCP del práctico») |
| Configuración del MCP | `opencode.json` (sin secretos) |
| Documentación del MCP | [`docs/skills-mcp/mcp-github.md`](docs/skills-mcp/mcp-github.md) |
| Evidencias | `docs/skills-mcp/evidencias/` |
| Artefactos del change C-04 | `openspec/changes/appointment-agenda/` |

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

- El change **C-04 sigue pendiente**: esta entrega prepara sus artefactos y los revisa;
  no implementa, verifica ni archiva el change.
- **Sin secretos:** el token no está en el repositorio ni en esta entrega. La
  configuración usa `{env:GITHUB_PERSONAL_ACCESS_TOKEN}`.
- **Sin datos de pacientes:** todo el material usa datos ficticios.
