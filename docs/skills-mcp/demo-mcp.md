# Demo en cámara — MCP `github`

> Guion de 2–3 minutos para explicar y demostrar el MCP elegido. La idea central:
> **el MCP no decide ni implementa: aporta evidencia externa para adoptar o rechazar
> una decisión de diseño.** La skill audita artefactos; el MCP consulta código real.

---

## 1. Antes de grabar (2 minutos)

- [ ] Token cargado en la sesión: `$env:GITHUB_PERSONAL_ACCESS_TOKEN.Length` > 0
      (**nunca** imprimir el token; mostrar solo el largo).
- [ ] `opencode mcp list` desde la raíz del repo → `✓ github connected`.
- [ ] Abiertas en el editor: `opencode.json`, `docs/skills-mcp/mcp-github.md`,
      `docs/skills-mcp/evidencias/mcp-github-c04.md`,
      `docs/skills-mcp/evidencias/mcp-github-c02.md`.
- [ ] Plan B listo: si falla la red o el token, se muestran las evidencias (Sección 5).

---

## 2. Frase de entrada (decirla textual)

> “La skill audita mis artefactos con un procedimiento mío. El MCP no audita nada:
> me da acceso **de solo lectura** a código real de GitHub para fundamentar o
> rechazar decisiones que mi base de conocimiento no puede probar sola.”

---

## 3. Guion por tiempos

| Tiempo | Qué hacés | Qué decís |
|---|---|---|
| 0:00–0:20 | Mostrás `opencode.json` | “Es un servidor remoto; el token va por variable de entorno, el archivo no tiene secretos.” |
| 0:20–0:40 | `opencode mcp list` | “Está conectado en este proyecto. No es una skill: es una integración que publica tools.” |
| 0:40–0:55 | `get_me` | “Confirma con qué identidad corre: mi cuenta, con alcance de lectura.” |
| 0:55–1:35 | `search_code EXCLUDE USING gist tstzrange` | “~26.976 resultados: el anti-solapamiento a nivel de base es estándar. Por eso C-04 agregó la restricción física en PostgreSQL.” |
| 1:35–2:10 | `search_code "token family" revoke reuse language:python` | “~1.282 resultados: familia de tokens y revocación por reuso respaldan C-02.” |
| 2:10–2:40 | Abrís `evidencias/mcp-github-c04.md` | “Queda transcripto solicitud, resultado y aporte; no se copió código.” |
| 2:40–2:55 | Cierre | “El MCP da evidencia; la decisión y los 259 tests son míos.” |

---

## 4. Comandos y prompts exactos

```powershell
# 1. Conexión (desde la raíz del repo)
opencode mcp list
# esperado: ✓ github connected

# 2. Token presente, sin exponerlo
$env:GITHUB_PERSONAL_ACCESS_TOKEN.Length
# esperado: un número > 0 (nunca imprimir el valor)
```

En el chat del agente:

```text
Usá el MCP github: get_me
```

```text
Usá search_code con: EXCLUDE USING gist tstzrange
```

```text
Usá search_code con: "token family" revoke reuse language:python
```

Opcional para C-02 (si sobra tiempo):

```text
Usá search_code con: "tenant_id" where filter repository language:python
```

---

## 5. Plan B — si falla la red o el token

No improvises ni muestres un error en cámara. Abrí la evidencia ya transcripta:

1. `docs/skills-mcp/evidencias/mcp-github-c04.md` — `get_me`, `search_code`,
   `search_repositories` con resultados reales.
2. `docs/skills-mcp/evidencias/mcp-github-c02.md` — familia de tokens y capa de repositorios.
3. `docs/skills-mcp/mcp-github.md` — configuración y problemas resueltos.

Frase:

> “La conexión la muestro desde la evidencia porque el token es personal y no lo
> expongo en cámara. Acá está la solicitud, el resultado y qué decisión cambió.”

---

## 6. Tabla de evidencias (la que más convence)

| Consulta | Resultado | Decisión que respalda | Alternativa rechazada |
|---|---|---|---|
| `EXCLUDE USING gist tstzrange` | ~26.976 | Restricción física en PostgreSQL para RN-01 | Validar solapamientos solo en Python |
| `"token family" revoke reuse` | ~1.282 | `family_id` + revocar la familia ante reuso (C-02) | Refresh token simple sin detección de reuso |
| `"tenant_id" where filter repository` | ~12.016 | Capa `app/repositories/` + guarda AST (D13) | Filtrar por tenant en handlers o queries sueltas |
| `dental appointment scheduling fastapi` | 5 repos | El dominio casi no tiene implementaciones públicas | Adoptar un repositorio como referencia |

Cierre de la tabla:

> “El MCP no decide; yo decido. El MCP me dice si la decisión tiene respaldo externo
> o si estoy inventando.”

---

## 7. Preguntas probables

| Pregunta | Respuesta corta |
|---|---|
| ¿Por qué GitHub y no Context7? | “Necesitaba código real de patrones de datos, no documentación de API. Context7 era más reproducible; lo declaré como desventaja.” |
| ¿No es copiar código? | “No. Se tomó la forma del patrón; la implementación es propia y los resultados son Django/Litestar con otros supuestos.” |
| ¿Qué riesgo tiene el token? | “Es fine-grained, solo lectura, vive en una variable de entorno y no está en el repo ni en la entrega.” |
| ¿Qué pasa si GitHub cambia el endpoint? | “El endpoint remoto no fija versión; lo declaré como limitación y la evidencia queda transcripta en el repo.” |
| ¿El MCP reemplaza los tests? | “No. El MCP fundamenta decisiones; los 259 tests verifican la implementación.” |
| ¿Qué problema de compatibilidad resolviste? | “OAuth no soporta DCR → `oauth:false` + PAT; y el `opencode-cli.exe` viejo conservaba el entorno vacío → cerrarlo y reabrir.” |

---

## 8. No digas / decí

| No digas | Decí |
|---|---|
| “Usé el MCP para buscar código” | “El MCP respondió X; con eso adopté Y y rechacé Z” |
| “Tengo el MCP instalado” | “Acá está la solicitud, el resultado y el aporte” |
| “El MCP me dio la solución” | “El MCP me dio evidencia; la decisión es mía” |
| Mostrar el token “para que se vea” | Mostrar `access_len` / `.Length` y decir que se oculta por la consigna |

---

## 9. Límites (decirlos sin que pregunten)

- Solo lectura; el PAT acota el alcance.
- Cada integrante necesita su propio token (reproducibilidad media).
- Endpoint remoto sin versión fija: puede cambiar del lado de GitHub.
- El repo no contiene datos reales de pacientes; todo es ficticio.
