# Skill Registry

**Delegator use only.** Any agent that launches sub-agents reads this registry to resolve compact rules, then injects them directly into sub-agent prompts. Sub-agents do NOT read this registry or individual SKILL.md files.

## User Skills

| Trigger | Skill | Path |
|---------|-------|------|
| Crear o actualizar AGENTS.md / CLAUDE.md | agents-md-generator | ~/.config/opencode/skills/agent-instruction/SKILL.md |
| Investigar competidores / Discovery | discovery-research | ~/.config/opencode/skills/discovery-research/SKILL.md |
| Encontrar y buscar skills | find-skills | ~/.config/opencode/skills/find-skill/SKILL.md |
| Crear base de conocimiento (KB) | kb-creator | ~/.config/opencode/skills/kb-creator/SKILL.md |
| Implementar tasks de OpenSpec change | openspec-apply-change | .agents/skills/openspec-apply-change/SKILL.md |
| Archivar change de OpenSpec | openspec-archive-change | .agents/skills/openspec-archive-change/SKILL.md |
| Explorar ideas en OpenSpec | openspec-explore | .agents/skills/openspec-explore/SKILL.md |
| Proponer change en OpenSpec | openspec-propose | .agents/skills/openspec-propose/SKILL.md |
| Sincronizar delta specs | openspec-sync-specs | .agents/skills/openspec-sync-specs/SKILL.md |
| Actualizar planning de change | openspec-update-change | .agents/skills/openspec-update-change/SKILL.md |
| Generar roadmap CHANGES.md | roadmap-generator | ~/.config/opencode/skills/roadmap-generator/SKILL.md |
| Crear y modificar skills | skill-creator | ~/.config/opencode/skills/skill-creator/SKILL.md |
| Crear o actualizar skill registry | skill-registry | ~/.config/opencode/skills/skill-registry/SKILL.md |
| Investigar competidores por URL | web-scraper | ~/.config/opencode/skills/web-scraper/SKILL.md |
| Build features / fix bugs test-first, red-green-refactor | tdd | .agents/skills/tdd/SKILL.md |
| FastAPI, Pydantic, async Python, SQLAlchemy async, JWT, OpenAPI | fastapi-expert | .agents/skills/fastapi-expert/SKILL.md |
| Implementar auth/RBAC, securizar APIs, debug seguridad | auth-implementation-patterns | .agents/skills/auth-implementation-patterns/SKILL.md |

> **Nota naming:** el nombre canónico es `find-skills` (plural, según frontmatter `name: find-skills` del SKILL.md); el directorio en disco es `find-skill/` (singular). La fila usa el nombre canónico; el path conserva el directorio real.
>
> **Nota naming (2):** idem para `agents-md-generator` (frontmatter `name: agents-md-generator`) cuyo directorio en disco es `agent-instruction/`. Sin duplicada: `~/.claude/skills/` y `~/.config/opencode/skills/` contienen el mismo set global (9 dirs, mismo frontmatter); el registry apunta al path de opencode por convención.
>
> **Nota portabilidad (2026-10-11):** `tdd`, `fastapi-expert` y `auth-implementation-patterns`
> viven versionadas en `.agents/skills/` del proyecto (visibles para todos los agentes y el
> equipo); las copias en `~/.agents/skills/` quedan como fallback global.
> Las copias locales son snapshots (no se auto-actualizan con `npx skills update`).
>
> **Nota dedupe openspec-*:** `.agents/skills/openspec-*/SKILL.md` y `.opencode/skills/openspec-*/SKILL.md` son el mismo skill (difieren solo en el naming del slash-command: `/opsx-*` vs `/openspec-*`); canónico `.agents/` (proyecto, naming `/opsx-*` coherente con `.claude/commands/opsx/`), con una sola fila por skill, sin duplicadas. `.claude/commands/opsx/*.md` (apply/archive/explore/propose/sync/update) son wrappers de comando sin SKILL.md → correctamente no registrados. `active-orchestrator` (solo global, meta-orquestador del flujo de fundación ya completada) queda excluido a propósito: nunca lo invoca un ejecutor.

## Compact Rules

### kb-creator
- Generates 10 canonical markdown files in `knowledge-base/`
- Mode A (silent ingest from docs/) or Mode B (interactive Q&A)
- Enforces strict canonical file naming (01_vision_y_objetivos.md to 10_preguntas_abiertas.md)
- Foundation/orchestrator-only: nunca la invoca un ejecutor Backend/Frontend (AGENTS.md la asigna solo a Orquestación OPSX)

### roadmap-generator
- Reads `knowledge-base/` and generates root `CHANGES.md`
- Defines atomic changes (C-01, C-02...), dependency tree, parallelism gates, and critical path
- Foundation/orchestrator-only: nunca la invoca un ejecutor Backend/Frontend (AGENTS.md la asigna solo a Orquestación OPSX)

### openspec-apply-change
- Implements tasks from OpenSpec changes following strict TDD when active
- Updates task checklist [x] upon task completion

### openspec-propose
- Planning-only: `openspec new change "<kebab>"`, then builds ALL artifacts in dependency order (proposal → specs delta → design → tasks); never edits project code nor starts apply
- Drive via `openspec status --change "<name>" --json` (applyRequires + requires edges) + `openspec instructions <artifact> --change "<name>" --json` (template/instruction/resolvedOutputPath); re-run status after each artifact
- Clarify material ambiguity upfront (scope/behavior/compat/acceptance); minor details = reasonable assumption recorded in artifacts
- context/rules are constraints, never copied into files; confirm root via `openspec list --json` first; never hand-create `openspec/` files

### openspec-explore
- Thinking stance, not a workflow: no fixed steps; read/search/investigate freely, visualize with plain-ASCII diagrams only (`+ - |`, `-->`, no unicode)
- NEVER implements: no code, no schemas/config edits; capturing agreed OpenSpec artifacts within confirmed scope only after explicit yes/no confirmation (user's own capture request counts as confirmation)
- Ground in `openspec list --json`, `list --specs`, full specs incl. scenarios, and config.yaml context/rules (constraints, never reproduced)
- Ends in `/opsx-propose` handoff, artifact updates on request, or just clarity; never scaffold by hand (always `openspec new change`)

### openspec-archive-change
- Select change (announce "Using change:" + override); check `openspec status --json` (artifacts done/skipped) + task counts from `openspec list --json` (only x/X = complete); warn + confirm on incompletes, never silently block
- With delta specs: assess per-capability sync (ADDED/MODIFIED/REMOVED/RENAMED vs main spec); offer Sync now / Archive without syncing / Cancel; run sync inline and re-verify before moving
- Archive = move changeRoot to `archive/YYYY-MM-DD-<name>` (no double date); preserve `.openspec.yaml`
- Summary reports specs state (synced / no deltas / skipped) + warnings (incomplete artifacts/tasks)

### openspec-sync-specs
- Agent-driven merge over `artifactPaths.specs.existingOutputPaths` only (honor caller-narrowed subset, never widen or infer); main spec at `<planningHome.root>/openspec/specs/<capability-path>/spec.md`
- ADDED→add, MODIFIED→apply preserving untouched scenarios, REMOVED→delete block (retire dir only if empty + Purpose intact + `retire_capabilities:true`), RENAMED FROM→TO; never copy delta as-is, no delta headers in main spec
- New capability only from ADDED (+ verbatim delta Purpose or TBD placeholder); fetch `openspec instructions specs` snapshot once, apply as constraint without copying
- Validate with `openspec validate --specs`; idempotent; report per-capability changes + TBD purposes + retirements

### openspec-update-change
- Revises EXISTING planning artifacts only, never code; edit only concrete `existingOutputPaths` files, never a glob `resolvedOutputPath`; leave `skipped` artifacts untouched
- Draft edits in conversation, reconcile in ALL directions (later→earlier too), then confirm each revision one artifact at a time before writing
- Missing artifact (ready/blocked, no files) = point to `openspec instructions`, don't create — except a confirmed concrete path under a non-empty glob artifact
- Intent change (not refinement) → recommend fresh `openspec new change`; end by pointing to next step (`/opsx-apply` or `/opsx-archive`), never acting on it

### find-skills
- Discovers installable skills via `npx skills find <query>` + skills.sh leaderboard before recommending
- Verifies quality first: prefer 1K+ installs, reputable source, starred repo; never recommends on search hits alone
- Presents name + what it does + installs/source + install cmd + skills.sh link; installs with `npx skills add <owner/repo@skill> -g -y` on request
- If none found: says so, helps directly, suggests `npx skills init` for a custom skill

### discovery-research
- Pre-KB Discovery: sources (web-scraper per URL → `discovery/sources/`) → 11-point Q&A checklist → user-confirmed summary gate → write `discovery/discovery.md`
- Never writes `discovery.md` nor touches state without explicit user confirmation of the summary (governance MEDIA)
- Reuses scraping results instead of re-asking; unverified assumptions go to risks/open questions
- Output is INPUT to `kb-creator`, not a replacement; needs `web-scraper` sub-skill when URLs exist

### skill-registry
- Scans ALL skill dirs (global + project-level), dedupes (project wins), SKIPS sdd-*/_shared/skill-registry; reads full SKILL.md (200-line guard → frontmatter + patterns only)
- Compact rules 5-15 lines per skill: actionable constraints only, no purpose/install/full examples; this is the MOST IMPORTANT output
- Conventions: reads AGENTS.md/CLAUDE.md index + extracts every referenced path into the table (index + refs, zero extra hops)
- Always writes `.atl/skill-registry.md` (+ engram upsert via topic_key); adds `.atl/` to .gitignore if present

### agents-md-generator
- Generates root `AGENTS.md` + `CLAUDE.md` copy from KB 02 (stack table), CHANGES.md (roadmap summary), skill-registry (skill→role map); never inside `.claude/` or `openspec/`
- Pre-checks: `knowledge-base/` + `02_descripcion_general.md` required; without CHANGES.md omits roadmap section with warning
- Hard rules are the ONLY interactive part: derives stack-aware candidates, confirms via AskUserQuestion, writes only confirmed rules (`NUNCA X → hacer Y`)
- Never duplicates `~/.claude/CLAUDE.md` global rules — references them with the inherit line instead

### skill-creator
- Captures intent first (what / trigger phrases / output format / need for evals), then drafts skill, writes test prompts, runs evals, iterates on feedback
- Interviews edge cases + I/O formats + success criteria upfront; researches via subagents/MCPs in parallel where useful
- Verifiable outputs (transforms/workflows) get test cases; subjective outputs (style/art) skip quantitative evals
- Ships with description-optimizer pass for triggering accuracy; adapts jargon level to the user

### web-scraper
- One URL → one note `discovery/sources/<slug>.md` (slug via scripts/slugify.py) with the fixed 8-field schema in fixed order; `(no publicado)` instead of inventing
- Fetches via WebFetch with schema-prompt; on empty/403/paywall/CAPTCHA reports the limitation and continues — no evasion, no mass crawling, single pages only
- Read-only, no approval gate per URL; processes lists one-by-one, reports resolved vs failed counts at the end
- Invoked standalone ("investigar competidor X") or as sub-skill of `discovery-research` before its Q&A

### tdd
- Red → green en vertical slices: un seam, un test, una implementación mínima por ciclo; nunca horizontal slicing (todos los tests primero)
- Testear solo en seams pre-acordados (boundary pública); confirmar seams con el usuario antes de escribir tests
- Tests verifican comportamiento vía interfaz pública (sobreviven refactors); un assertion lógica por test, valores esperados de fuente independiente (literal/spec), nunca tautológicos
- Mock solo en boundaries del sistema (APIs externas, DB/test-DB, tiempo/random, FS); nunca mockear clases/colaboradores propios ni métodos privados
- Refactor no es parte del loop (va en review); ver tests.md (buenos/malos ejemplos) + mocking.md (DI + SDK-style interfaces)

### fastapi-expert
- Async en todo I/O: `async def` endpoints + `AsyncSession`; nunca sync DB ni mezclar sync/async
- Pydantic V2 siempre (`field_validator`, `model_validator`, `model_config`, `EmailStr`, `from_attributes=True`); prohibido sintaxis V1 (`@validator`, `class Config`)
- DI con patrón `Annotated`: `DbDep = Annotated[AsyncSession, Depends(get_db)]`, `CurrentUser = Annotated[str, Depends(get_current_user)]`
- JWT: `OAuth2PasswordBearer` + `create_access_token(sub, 30min)` + `get_current_user` con 401 ante token inválido; nunca plaintext passwords ni datos sensibles en responses
- Schemas → router (`APIRouter(prefix, tags)`, status codes correctos) → crud (`select().where()`, commit/refresh); test async con pytest+httpx y verificar `/docs`
- Refs en `references/`: pydantic-v2, async-sqlalchemy, endpoints-routing, authentication, testing-async, migration-from-django

### auth-implementation-patterns
- AuthN (quién sos) vs AuthZ (qué podés hacer): JWT stateless (access 15-30min + refresh 7d con rotación) u OAuth2/SSO; validar siempre server-side
- RBAC + ownership de recurso en cada endpoint; nunca solo checks client-side
- Passwords solo con bcrypt/argon2; JWT en httpOnly+secure+sameSite cookies (nunca localStorage); HTTPS + CSRF en sesiones + rotación de secretos
- Rate-limit en endpoints de auth (anti brute-force); validar input (email/password strength); reset con tokens seguros con expiración
- NOTA: `references/details.md` está escrito en Express/TS (jsonwebtoken, middleware `authenticate`) — los patrones transfieren a FastAPI/OAuth2PasswordBearer tal cual

## Notas de seguridad (verificadas por orquestador, sin re-auditoría)
- `tdd`: triple-pass limpio.
- `fastapi-expert`: installer Gen=Critical, contenido auditado limpio.
- `auth-implementation-patterns`: Socket 1 alerta heurística, contenido auditado limpio.

## Project Conventions

| File | Path | Notes |
|------|------|-------|
| CHANGES.md | CHANGES.md | Roadmap maestro de implementation |
| Knowledge Base | knowledge-base/ | 10 archivos canónicos de arquitectura y requerimientos |
| OpenSpec root | openspec/ | Fuente de verdad de estado (`openspec list/status --json`); nunca adivinar estado ni crear archivos a mano |
| Discovery | discovery/ | Contexto de mercado (`discovery.md` + `sources/` de web-scraper); insumo de kb-creator |
| Reglas del proyecto | AGENTS.md | Reglas duras del proyecto (stack, convenciones, roadmap por rol); hereda el global sin duplicarlo |
