# Mapeo de escenarios a Dado–Cuando–Entonces

Mapeo de forma de los 8 escenarios de `openspec/specs/backend-foundation/spec.md`. El contrato vigente sigue en el spec; este documento solo expresa la equivalencia.

| Escenario (spec) | DADO | CUANDO | ENTONCES |
|---|---|---|---|
| Boot with valid configuration (boot-válido) | Configuración completa provista por entorno | Todas las variables de entorno requeridas están definidas y el operador arranca la API | La aplicación queda lista para servir requests sin cambios de código |
| Missing required variable fails fast (boot-failfast) | Falta una variable requerida (p. ej. URL de BD o clave secreta) | El operador arranca la API sin esa variable | El arranque falla con un error que nombra la variable faltante y no hay servicio parcial |
| Healthy system (health-200) | La base de datos está alcanzable | Un cliente llama a `GET /health` | El sistema responde `200` con payload que indica estado healthy para app y base de datos |
| Database unreachable (health-unhealthy) | La base de datos no está alcanzable | Un cliente llama a `GET /health` | El sistema responde estado de BD no-saludable (no-`200` o payload explícito de unhealthy) |
| Fresh provision from empty state (fresh-provision) | Base de datos vacía y orquestación de contenedores disponible | El operador provisiona los contenedores y aplica las migraciones desde la BD vacía | La BD alcanza el esquema vigente sin SQL manual y la API conecta exitosamente |
| Migration chain is ordered and repeatable (migration-repeatable) | La BD ya está al día tras una primera aplicación de migraciones | Las migraciones se aplican dos veces en secuencia | La segunda corrida es no-op y reporta que no hay migraciones pendientes |
| Full suite passes in isolation (suite-isolation) | La BD de test está configurada y separada de la BD de desarrollo | El operador corre la suite completa de tests | Todos los tests pasan y ningún dato se escribe en la BD de desarrollo |
| No health data in logs (no-logging) | Tests que ejercitan rutas de API o BD con datos similares a pacientes | Cualquier test usa datos patient-like | Ningún contenido identificatorio o clínico aparece en los logs capturados (prohibición de logueo, Ley 25.326) |
