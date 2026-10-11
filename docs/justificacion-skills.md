# Justificación de Skills — TPI Metodología

Decisión 1-línea-por-skill (Etapa 5, `find-skill` solo recomienda — las instalaciones del 2026-10-10 se hicieron con autorización explícita del equipo).

Alcance: las 5 evaluadas son el 100% de las recomendaciones de `find-skill`; las 12 restantes del registry son inventario preexistente, no recomendaciones.

Verificación de rutas del registro (`.atl/skill-registry.md`, 2026-10-10): 17/17 `SKILL.md` existen. Los patrones `...\Mateows.config\...`, `...\Mateows.agents\...` (sin barra) y `...\METODOLOGIA.opencode\...` se buscaron literalmente en el registro y NO aparecen: las rutas declaradas usan separadores correctos. Sin correcciones necesarias.

| Skill recomendada | Funcionalidad | Decisión | Justificación |
|---|---|---|---|
| `tdd` | TDD red-green-refactor con vertical slices y seams | Instalar (instalada) | Strict TDD activo en el proyecto. |
| `fastapi-expert` | APIs async FastAPI + Pydantic V2 + JWT + SQLAlchemy async | Instalar (instalada) | Backend C-01/C-02, contenido auditado limpio. |
| `auth-implementation-patterns` | Patrones JWT/refresh/RBAC/bcrypt/rate-limit | Instalar (instalada) | Auth de C-02, contenido auditado limpio. |
| `review-and-refactor` | Review contra guidelines propias del repo | No instalar | TrustHub Fail en auditoría de seguridad. |
| `react-nextjs-development` | Workflow React 18+TS + Tailwind | Pendiente de decisión | Frontend recién en C-09/C-10. |
