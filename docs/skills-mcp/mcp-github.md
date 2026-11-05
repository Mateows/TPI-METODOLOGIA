# Integración del MCP `github` en OpenCode

Documentación de la integración del servidor MCP elegido para el TP. **No contiene
secretos**: el token vive en una variable de entorno.

## Requisitos

- OpenCode 1.18.35 o superior (desktop o CLI).
- Un **Personal Access Token (PAT) fine-grained** de GitHub con permiso de lectura
  sobre los repositorios a consultar (`Contents: read`; `Issues` y `Pull requests` solo
  si se van a leer).
- Conectividad HTTPS a `https://api.githubcopilot.com/mcp/`.

## Variables de entorno

| Variable | Alcance | Uso |
|---|---|---|
| `GITHUB_PERSONAL_ACCESS_TOKEN` | Usuario (persistente) | Token que se inyecta en el header `Authorization` |

En Windows:

```powershell
[Environment]::SetEnvironmentVariable("GITHUB_PERSONAL_ACCESS_TOKEN","<tu-token>","User")
```

> Las variables de usuario solo las heredan los procesos **nuevos**. Ver *Solución de
> problemas*, punto 2.

## Configuración

Archivo: `opencode.json` en la raíz del proyecto (versionado, sin secretos).

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "github": {
      "type": "remote",
      "url": "https://api.githubcopilot.com/mcp/",
      "enabled": true,
      "oauth": false,
      "headers": {
        "Authorization": "Bearer {env:GITHUB_PERSONAL_ACCESS_TOKEN}"
      }
    }
  }
}
```

- `oauth: false` es obligatorio: el endpoint no soporta *Dynamic Client Registration*
  (ver *Solución de problemas*, punto 1).
- `{env:...}` evita escribir el token en el archivo.

## Cómo comprobar la conexión

```bash
opencode mcp list          # debe mostrar: ✓ github connected
opencode mcp debug github  # estado de OAuth/autenticación del server
```

Esperado:

```
●  ✓ github  connected
   https://api.githubcopilot.com/mcp/
```

## Cómo ejecutar una herramienta real

Desde el chat del agente, o verificando equivalencia con la API:

1. Pedir `get_me` → devuelve el usuario autenticado.
2. Pedir `search_code` con `EXCLUDE USING gist tstzrange` → devuelve `total_count`.

La evidencia de estas ejecuciones está en
[`evidencias/mcp-github-c04.md`](evidencias/mcp-github-c04.md).

## Solución de problemas

### 1. `Incompatible auth server: does not support dynamic client registration`

`opencode mcp auth github` falla porque el flujo OAuth de OpenCode requiere DCR y el
servidor de GitHub no lo expone (cada cliente debe registrar su propia OAuth App). **La
solución es no usar OAuth**: `oauth: false` + PAT en `headers`.

### 2. `Authorization header is badly formatted` o `SSE error: Non-200 status code (400)`

El header llega vacío porque el proceso de OpenCode no ve la variable de entorno.
Comprobar en el proceso actual:

```powershell
$env:GITHUB_PERSONAL_ACCESS_TOKEN.Length   # debe ser > 0
```

Si da 0 pero la variable de usuario está seteada, el proceso es anterior al cambio.
Dos pasos, en este orden:

1. Cerrar OpenCode **completo**, incluido el backend `opencode-cli.exe` (cerrar la
   ventana no lo termina; queda escuchando en un puerto local y la UI nueva se
   reconecta a ese proceso con el entorno viejo):

   ```powershell
   Get-Process opencode-cli, OpenCode -ErrorAction SilentlyContinue | Stop-Process -Force
   ```

2. Reabrir la app **desde el sistema** (no desde una terminal que ya estaba abierta).

### 3. Diferencias entre alcance global y de proyecto

- `github` está configurado en el `opencode.json` **del proyecto**: solo se carga si el
  cliente abre esa carpeta. Ejecutar `opencode mcp list` desde otra ruta no lo muestra.
- Otros servidores (`context7`, `engram`, `filesystem`, `playwright`) están en la config
  **global** (`~/.config/opencode/opencode.json`). Si se replica este TP en otra máquina,
  hay que reproducir también esa parte o declararlos por proyecto.

## Límites definidos para el TP

- Token de **solo lectura**, acotado a los repositorios necesarios.
- El repo no contiene datos reales de pacientes: solo datos ficticios de prueba.
- El MCP se usa para consultar código y metadatos; no se publican artefactos del TP sin
  revisión.
