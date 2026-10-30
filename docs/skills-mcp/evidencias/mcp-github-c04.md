# Evidencia — Invocaciones reales del MCP `github` sobre C-04

| Campo | Valor |
|---|---|
| **MCP** | `github` (remoto) — `https://api.githubcopilot.com/mcp/` |
| **Cliente** | OpenCode 1.18.35 (desktop) sobre Windows |
| **Change asistido** | `openspec/changes/appointment-agenda/` (C-04) |
| **Fecha** | 30/10/2026 |
| **Herramientas usadas** | `get_me`, `search_code`, `search_repositories` |

Todas las invocaciones fueron de **solo lectura**. No se creó ni modificó nada en GitHub.

---

## 1. Comprobación de conexión

```
●  ✓ context7    connected
●  ✓ engram      connected
●  ✓ filesystem  connected
●  ✓ playwright  connected
●  ✓ github      connected
—  5 server(s)
```

## 2. `get_me` — identidad y permisos del token

- **Solicitud:** verificar qué usuario autentica el PAT y, por tanto, con qué permisos
  opera el servidor.
- **Resultado:** `login = Mateows` (token válido, cuenta personal).
- **Aporte:** confirma que el resto de las consultas se ejecutan con el alcance de ese
  usuario y no con permisos de servicio.

## 3. `search_code` — patrón de prevención de solapamientos

- **Solicitud:** buscar implementaciones del patrón de exclusión de rangos en PostgreSQL:
  `EXCLUDE USING gist tstzrange`.
- **Resultado:** `total_count = 26.976`. Muestra de rutas devueltas:
  `202606/20260601_15.md`, `201205/20120517_01.md`, `202605/20260531_22.md`.
- **Aporte a C-04:** confirma que la restricción `EXCLUDE USING gist` sobre rangos es un
  mecanismo estándar y ampliamente usado para impedir solapamientos a nivel de base de
  datos. Respalda la decisión de diseño de no limitar RN-01 a una validación en la capa
  de servicios, que es vulnerable a condiciones de carrera entre transacciones
  concurrentes.

## 4. `search_repositories` — estado del arte del dominio

- **Solicitud:** buscar proyectos públicos que combinen agenda odontológica y FastAPI:
  `dental appointment scheduling fastapi`.
- **Resultado:** `total_count = 5`. Muestra: `DiegoCP89/dental-scheduling` (1 estrella),
  `ncreighton/c72bf5e129f3d15a-dental-practice-appointment-sc` (0),
  `awais-ai-engineer/Dental-ai-receptionist-crm` (0).
- **Aporte a C-04:** con solo 5 repositorios públicos (y ninguno con tracción), no existe
  una implementación de referencia que copiar. Eso justifica que el change defina su
  propio modelo de `Box`/`Appointment` a partir de la KB, en lugar de adoptar un esquema
  externo, y refuerza que las reglas RN-01/RN-02 deban especificarse explícitamente.

---

## 5. Diagnóstico del endpoint (antes / después)

Se probó directamente el endpoint con un `initialize` JSON-RPC, variando solo el header:

| Header `Authorization` | Resultado |
|---|---|
| `Bearer ` (variable de entorno sin resolver → valor vacío) | **HTTP 400** — `Authorization header is badly formatted` |
| `Bearer <PAT>` (variable de entorno real) | **HTTP 200** |

Esto permitió separar dos causas que producían el mismo síntoma (`✗ github failed`):
credencial ausente versus proceso con entorno desactualizado.
