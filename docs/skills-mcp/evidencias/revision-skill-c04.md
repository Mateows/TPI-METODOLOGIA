# Evidencia — Revisión con skill propia sobre C-04

| Campo | Valor |
|---|---|
| **Skill invocada** | `revisor-de-agendas-de-citas` |
| **Ruta de la skill** | `.agents/skills/revisor-de-agendas-de-citas/SKILL.md` |
| **Change revisado** | `openspec/changes/appointment-agenda/` (C-04 — Appointment Agenda & Boxes) |
| **Fecha** | 30/10/2026 |
| **Solicitud realizada** | Aplicar el procedimiento de la skill sobre los artefactos de `appointment-agenda` y emitir el informe con la estructura "Resultado obligatorio", en modo solo revisión (sin editar archivos ni implementar código). |

## Fuentes efectivamente leídas

- `openspec/changes/appointment-agenda/proposal.md`
- `openspec/changes/appointment-agenda/specs/appointment-agenda/spec.md`
- `openspec/changes/appointment-agenda/design.md`
- `openspec/changes/appointment-agenda/tasks.md`
- `openspec/changes/appointment-agenda/.openspec.yaml`
- `CHANGES.md`
- `knowledge-base/README.md`
- `knowledge-base/04_modelo_de_datos.md`
- `knowledge-base/05_reglas_de_negocio.md`
- `knowledge-base/07_flujos_principales.md`
- `AGENTS.md` (raíz del proyecto)

---

# Revisión de agenda de citas

## Resumen

El change corresponde efectivamente a la agenda de citas (C-04) y es coherente en su
propósito general: propone modelos `Box`/`Appointment`, aislamiento por `clinic_id`,
persistencia UTC y la regla RN-01 de no solapamiento. La spec es verificable en su
mayoría y las tareas no marcan el change como implementado ni archivado.

Sin embargo, quedan **11 observaciones: 1 crítica, 5 importantes y 5 menores**. Las
brechas principales son (a) la spec no define el origen del `clinic_id` persistido, lo
que abre la puerta a suplantación de tenant vía payload; (b) la cobertura de escenarios
de solapamiento es parcial (falta box, contención, coincidencia exacta y turnos
cancelados); (c) el comportamiento ante datetimes con offset o naive solo vive en
`design.md` y no en la spec; (d) no existe matriz de transiciones de estado, solo una
lista de valores válidos; y (e) la spec no cubre la consulta/listado de turnos, aunque
el proposal la declara en alcance.

El change **no está listo para apply** sin resolver al menos la observación crítica y
las dos primeras importantes.

## Checklist

- [x] Aislamiento por clinic_id — cubierto en requisitos y escenarios de Box, y en
  `design.md` Decisión 3, pero con la salvedad de la observación crítica sobre el
  origen del `clinic_id` del turno.
- [x] Validación de intervalos — `end_time > start_time` exigido con escenario de
  rechazo (spec, "Appointment creation").
- [ ] Prevención de solapamientos — la regla está, pero faltan escenarios para box,
  contención, coincidencia exacta y turnos cancelados.
- [ ] Consistencia UTC — la persistencia UTC está afirmada; el comportamiento frente a
  datetimes con offset o naive no está especificado como requisito verificable.
- [ ] Estados permitidos — la lista de valores está alineada con la KB, pero no hay
  matriz de transiciones permitidas ni rechazo de transiciones inválidas.
- [x] Escenarios verificables — existen funcionamiento, error de negocio y borde, aunque
  con las faltas señaladas.
- [x] Tareas verificables — cada tarea incluye un criterio de verificación explícito.
- [x] Dependencias y alcance — C-02 declarada como dependencia y el change no se marca
  como completado; con la salvedad de la observación menor sobre secuenciación.

## Observaciones

### [CRÍTICA] El origen del `clinic_id` del turno no está especificado

- **Archivo y sección:** `specs/appointment-agenda/spec.md` → "Requirement: Appointment
  creation" y "Requirement: Appointment state transitions"; contraste con
  `design.md` → "Decisions" (3).
- **Problema:** La spec exige que paciente, profesional y box "belong to the same clinic",
  pero no define de dónde sale ese valor ni prohíbe que el cliente lo envíe en el
  payload. Un `clinic_id` aceptado desde la entrada permitiría crear un turno apuntando
  a otra clínica aunque las FKs existan, que es exactamente el vector que la regla dura
  de aislamiento multi-tenant busca cerrar. `design.md` Decisión 3 solo describe el
  filtrado en consultas, no la derivación del valor al escribir.
- **Regla o fuente relacionada:** `AGENTS.md` → "Reglas Duras", punto 1 (aislamiento
  multi-tenant, Ley 25.326); `knowledge-base/04_modelo_de_datos.md` §1 (`Appointment`
  lleva `clinic_id` FK); `knowledge-base/05_reglas_de_negocio.md` §RN-02.
- **Corrección sugerida:** Agregar al requisito "Appointment creation" que el
  `clinic_id` persiste se toma **exclusivamente** del contexto autenticado y que el
  campo no es aceptado en el payload (o, si se acepta, debe coincidir o rechazarse con
  404/403). Añadir dos escenarios: (1) payload con `clinic_id` de otra clínica →
  rechazo sin persistencia; (2) payload sin `clinic_id` → se persiste el del contexto.

### [IMPORTANTE] Cobertura incompleta de casos de solapamiento

- **Archivo y sección:** `specs/appointment-agenda/spec.md` → "Requirement: Overlap
  prevention" (escenarios "Professional overlap is rejected" y "Boundary intervals do
  not overlap"); `tasks.md` → 2.3.
- **Problema:** El requisito menciona "same professional **or the same box**" y "existing
  non-cancelled appointment", pero los escenarios solo cubren solapamiento por
  profesional y adyacencia. No hay escenario para: solapamiento por box, cita contenida
  dentro de otra, coincidencia exacta de intervalos y exclusión de turnos cancelados. La
  tarea 2.3 solo verifica "solapamiento rechazado y adyacencia aceptada".
- **Regla o fuente relacionada:** `knowledge-base/05_reglas_de_negocio.md` §RN-01
  (solapamiento por `dentist_id` **o** `box_id`); `design.md` Decisión 1 (intervalo
  abierto `existing.start < new.end` y `existing.end > new.start`) y Decisión 4
  (cancelados liberan el intervalo).
- **Corrección sugerida:** Agregar cuatro escenarios verificables: (a) solapamiento por
  box rechazado; (b) cita nueva contenida en una existente rechazada; (c) coincidencia
  exacta de inicio y fin rechazada; (d) turno `cancelled` en el mismo intervalo no
  bloquea el alta. Ampliar `tasks.md` 2.3 con esos cuatro casos como criterio de
  verificación.

### [IMPORTANTE] Comportamiento ante datetimes con offset o naive no es requisito

- **Archivo y sección:** `specs/appointment-agenda/spec.md` → "Requirement: Appointment
  creation" (escenario "Valid appointment is scheduled"); contraste con `design.md` →
  "Risks / Trade-offs" (UTC) y `tasks.md` → 2.2.
- **Problema:** La spec habla de "a UTC interval" como si la entrada ya viniera en UTC,
  pero no define qué ocurre con un datetime con offset (`-03:00`) ni con uno naive. La
  decisión de "validar datetimes conscientes y normalizarlos a UTC" está solo en
  `design.md`, que no es normativo, y la tarea 2.2 la implementa sin escenario que la
  respalde. Un datetime naive silenciosamente tratado como UTC produce corrimientos de
  tres horas en Argentina.
- **Regla o fuente relacionada:** `knowledge-base/05_reglas_de_negocio.md` §RN-07;
  `AGENTS.md` → "Reglas Duras", punto 8 (persistencia UTC, conversión local solo en
  interfaz).
- **Corrección sugerida:** Añadir a "Appointment creation" que solo se aceptan datetimes
  con información de zona, que se normalizan a UTC antes de persistir y que un datetime
  naive se rechaza con error semántico. Agregar escenario: "WHEN an appointment is
  submitted with a naive datetime THEN the system rejects it with a validation error";
  y otro para offset `-03:00` verificando que el valor persistido es el equivalente UTC.

### [IMPORTANTE] No hay matriz de transiciones de estado permitidas

- **Archivo y sección:** `specs/appointment-agenda/spec.md` → "Requirement: Appointment
  state transitions" (escenarios "Appointment is confirmed" y "Unknown state is
  rejected"); `tasks.md` → 2.5.
- **Problema:** La spec solo enumera valores válidos y rechaza valores fuera del
  conjunto. No dice qué transiciones están permitidas: no queda claro si
  `cancelled → confirmed`, `attended → scheduled` o `no_show → confirmed` son válidas.
  El escenario "Appointment is confirmed" parte de `scheduled` sin afirmar que sea el
  único origen posible. La tarea 2.5 pide "transiciones permitidas" sin que exista la
  definición que debe implementar.
- **Regla o fuente relacionada:** `knowledge-base/07_flujos_principales.md` §Flujo 1
  (pasos 4–6: alta en `scheduled`, confirmación a `confirmed`, cancelación a
  `cancelled`); `knowledge-base/04_modelo_de_datos.md` §1 (`status` con cinco valores);
  `CHANGES.md` §[C-04] (menciona cambios de estado).
- **Corrección sugerida:** Declarar explícitamente las transiciones soportadas —como
  mínimo `scheduled → confirmed`, `scheduled → cancelled`, `confirmed → attended`,
  `confirmed → cancelled`, `confirmed → no_show`— y agregar escenario de transición
  inválida (por ejemplo `cancelled → confirmed`) rechazada con error de negocio y estado
  previo preservado. Aquellas transiciones no respaldadas por la KB deben quedar como
  decisión explícita del usuario, no inferidas por el implementador.

### [IMPORTANTE] La spec no cubre la consulta o listado de turnos declarada en el proposal

- **Archivo y sección:** `proposal.md` → "What Changes" (segundo bullet: "creación,
  consulta y cambio de estado de turnos"); `specs/appointment-agenda/spec.md` (no existe
  requisito de lectura de turnos); `tasks.md` → 3.1 (endpoints de turnos).
- **Problema:** El proposal incluye la consulta de turnos en el alcance y las tareas
  exigen exponer endpoints de turnos, pero no hay requisito ni escenario para listar o
  leer turnos. Tampoco se define el filtrado por rango de fechas, ni qué estados se
  devuelven por defecto, ni el comportamiento de una lectura cross-clinic de un turno
  (solo está cubierto para boxes).
- **Regla o fuente relacionada:** Coherencia interna proposal ↔ spec ↔ tasks exigida por
  el procedimiento de la skill (paso 2); `knowledge-base/07_flujos_principales.md`
  §Flujo 1 (paso 2: el paciente elige horario disponible en la agenda).
- **Corrección sugerida:** Agregar el requisito "Appointment read isolation" con
  escenarios: (a) listado filtrado por `clinic_id` y rango de fechas; (b) lectura de un
  turno de otra clínica → 404/403 sin revelar datos. Si la consulta se considera fuera
  de C-04, quitarla del "What Changes" del proposal y de la tarea 3.1.

### [IMPORTANTE] El mecanismo de integridad concurrente no está definido de forma verificable

- **Archivo y sección:** `design.md` → "Decisions" (2) y "Risks / Trade-offs"
  (Concurrencia); `tasks.md` → 1.2 y 2.4.
- **Problema:** La decisión 2 afirma que "la transacción protegerá la escritura" usando
  "el mecanismo compatible con PostgreSQL", sin nombrarlo. No se puede verificar si se
  trata de una restricción de exclusión (`EXCLUDE USING gist` sobre `tstzrange`), de
  aislamiento `SERIALIZABLE` o de un lock a nivel de aplicación. La tarea 1.2 exige una
  "estrategia de integridad" que el diseño no entrega, y la 2.4 pide verificar "respuesta
  estable ante reintento concurrente" sin criterio de aceptación concreto.
- **Regla o fuente relacionada:** Procedimiento de la skill, paso 10 (correcciones
  verificables); `AGENTS.md` → "Reglas Duras", punto 4 (Clean Architecture, separación de
  capas); `design.md` "Goals" (consistencia ante concurrencia).
- **Corrección sugerida:** Nombrar el mecanismo elegido y su justificación (por ejemplo
  restricción de exclusión por `clinic_id` + `dentist_id`/`box_id` con rango
  `[start_time, end_time)`, que además expresa el límite abierto de turnos
  consecutivos), y definir el criterio de verificación de la tarea 2.4 como "dos
  inserciones concurrentes del mismo intervalo → exactamente una persiste y la otra
  recibe 409". Si el mecanismo queda abierto, marcarlo como decisión pendiente del
  usuario en lugar de como decisión tomada.

### [MENOR] `CHANGES.md` omite el estado `no_show` al describir el alcance de C-04

- **Archivo y sección:** `CHANGES.md` §[C-04] `appointment-agenda` → "Scope", tercer
  bullet.
- **Problema:** El scope enumera `scheduled`, `confirmed`, `attended`, `cancelled`, sin
  `no_show`; la spec (líneas de "Unknown state is rejected") y
  `knowledge-base/04_modelo_de_datos.md` §1 sí incluyen `no_show`. Un implementador que
  siga solo `CHANGES.md` produciría un enum incompleto.
- **Regla o fuente relacionada:** `knowledge-base/04_modelo_de_datos.md` §1
  (`Appointment.status`); `spec.md` → "Requirement: Appointment state transitions".
- **Corrección sugerida:** Actualizar el bullet de `CHANGES.md` para listar los cinco
  estados y remitir a la spec como fuente normativa del enum.

### [MENOR] Ciclo de vida y estado del box no están especificados

- **Archivo y sección:** `specs/appointment-agenda/spec.md` → "Requirement: Box
  isolation" (escenario "Box is listed for its clinic"); `tasks.md` → 2.1.
- **Problema:** El escenario habla de "the active boxes", lo que presupone un estado, pero
  no hay requisito de creación de boxes ni de transición `active`/`maintenance`, pese a
  que la tarea 2.1 exige implementar su creación. Tampoco se define si se puede agendar
  sobre un box en `maintenance`.
- **Regla o fuente relacionada:** `knowledge-base/04_modelo_de_datos.md` §1 (`Box` con
  `name`, `status` (active, maintenance)). No hay regla en la KB que prohíba agendar en
  un box en mantenimiento: **no debe inventarse**.
- **Corrección sugerida:** Agregar requisito de alta de box con escenario de validación,
  y dejar como decisión explícita del usuario si el alta de turno debe rechazar boxes en
  `maintenance`. Si no se decide, documentar que C-04 solo filtra por `active` al listar
  y no restringe el alta.

### [MENOR] Terminología divergente entre "professional" y `dentist_id`

- **Archivo y sección:** `specs/appointment-agenda/spec.md` → "Requirement: Appointment
  creation" y "Requirement: Overlap prevention"; contraste con
  `knowledge-base/04_modelo_de_datos.md` §1.
- **Problema:** La spec usa "professional" de forma genérica mientras la KB y RN-01 usan
  `dentist_id`. La tarea 3.1 habla de "profesionales", sin mapear el término al campo
  real. Genera ambigüedad sobre si el campo se llamará `dentist_id` o `professional_id`.
- **Regla o fuente relacionada:** `knowledge-base/04_modelo_de_datos.md` §1;
  `knowledge-base/05_reglas_de_negocio.md` §RN-01.
- **Corrección sugerida:** Unificar el término en la spec como `dentist_id` (o declarar
  explícitamente que "professional" designa la FK `dentist_id`) y usarlo igual en
  `tasks.md`.

### [MENOR] Las cancelaciones no mencionan registro de auditoría

- **Archivo y sección:** `specs/appointment-agenda/spec.md` → "Requirement: Appointment
  state transitions"; `tasks.md` → 2.5.
- **Problema:** El cambio a `cancelled` se especifica sin referirse al log de auditoría,
  aunque RN-04 exige registrar el evento al cancelar. No queda claro si C-04 debe emitir
  el registro o si esa responsabilidad queda íntegramente en C-06 (WhatsApp).
- **Regla o fuente relacionada:** `knowledge-base/05_reglas_de_negocio.md` §RN-04;
  `knowledge-base/04_modelo_de_datos.md` §1 (`AuditLog`, "exigido por RN-04").
- **Corrección sugerida:** Declarar explícitamente el límite: si la auditoría de
  cancelaciones pertenece a C-06, dejar una nota en `tasks.md` 2.5 indicando que C-04 no
  crea `AuditLog`; si pertenece a C-04, agregar escenario "cancelación registra evento en
  `AuditLog` con `clinic_id` y `actor_id`".

### [MENOR] Secuenciación frente a C-02 pendiente no está operacionalizada

- **Archivo y sección:** `design.md` → "Risks / Trade-offs" (Dependencia C-02) y
  "Migration Plan" (paso 3); `tasks.md` → "Workflow follow-up" y 3.1; `proposal.md` →
  "Impact".
- **Problema:** `CHANGES.md` marca C-02 como `[ ]` pendiente y C-04 depende de ella. El
  diseño propone "adaptadores explícitos para el contexto" y bloquea la integración,
  pero las tareas igualmente exigen endpoints "usando ... el contexto multi-tenant de
  C-02" sin indicar cómo se verificarán las pruebas de aislamiento mientras ese contexto
  no exista. El riesgo es que 2.1 se valide con un stub que no refleje el middleware
  real.
- **Regla o fuente relacionada:** `CHANGES.md` §[C-02] (estado pendiente) y árbol de
  dependencias; procedimiento de la skill, paso 8 (no marcar el change como implementado
  prematuramente).
- **Corrección sugerida:** Añadir a `tasks.md` el criterio de que las pruebas de
  aislamiento se ejecutan contra un adaptador de contexto documentado y que deben
  repetirse contra el middleware real de C-02 antes de archivar; o bien mover 3.1 a un
  change de integración posterior.

## Correcciones aplicadas o pendientes

Revisión aplicada el **2026-11-04** sobre `openspec/changes/appointment-agenda/`.
No se implementó código, no se marcaron tareas y C-04 sigue `[ ]` en `CHANGES.md`.

| # | Observación (severidad) | Archivo y sección | Qué se cambió |
|---|---|---|---|
| 1 | Origen del `clinic_id` del turno (**crítica**) | `spec.md` → nuevo requisito "Agenda clinic scope is server-derived"; "Appointment creation"; `design.md` Decisión 3; `tasks.md` 2.1 y 3.1; `proposal.md` "What Changes" | El `clinic_id` persiste solo del contexto autenticado (token + recarga desde DB, según `tenant-isolation`); el payload no acepta `clinic_id` y un campo extra devuelve `422 validation_error`; escenarios de rechazo y de persistencia con el tenant del contexto. Tareas alineadas. |
| 2 | Cobertura incompleta de solapamientos (**importante**) | `spec.md` → "Overlap prevention"; `tasks.md` 2.3 | Seis escenarios: solapamiento parcial por `dentist_id`, por `box_id`, cita contenida, coincidencia exacta, consecutivas permitidas (`end == start`) y turno `cancelled` que libera el intervalo. La tarea 2.3 los enumera como criterio de verificación. |
| 3 | Datetimes con offset o naive (**importante**) | `spec.md` → "Appointment creation" (escenarios "Naive datetime is rejected" y "Offset datetime is normalized to UTC"); `design.md` Decisión 5 y Risks; `tasks.md` 2.2 | La regla pasa a la spec como requisito verificable: zona obligatoria, normalización a UTC en el borde, rechazo `422` del naive. `design.md` deja de ser la única fuente. |
| 4 | Falta matriz de transiciones (**importante**) | `spec.md` → requisitos "Appointment states" y "Appointment transition matrix"; `tasks.md` 2.5; `design.md` §Open Questions (2) | Matriz declarada solo con las transiciones que respalda la KB (`scheduled→confirmed`, `scheduled→cancelled`, `confirmed→attended`, `confirmed→cancelled`), escenario de transición no declarada rechazada conservando el estado previo. El origen de `no_show` queda como decisión pendiente, no inferida. |
| 5 | Spec sin consulta/listado de turnos (**importante**) | `spec.md` → nuevo requisito "Appointment read isolation"; `tasks.md` 3.1 | Listado filtrado por clínica y rango de fechas sobre `start_time`, y lectura cross-clinic con el mismo `404` que un ID inexistente. Cierra la inconsistencia proposal ↔ spec ↔ tasks. |
| 6 | Mecanismo de integridad concurrente sin definir (**importante**) | `design.md` Decisión 2, §Open Questions (1) y Risks; `tasks.md` 1.2 y 2.4; `spec.md` "Overlap prevention" | Dejó de presentarse como decisión tomada: la Decisión 2 remite a la pregunta abierta con las dos opciones (chequeo en servicio con bloqueo, portable; `EXCLUDE USING gist` + `btree_gist`, solo PostgreSQL con guarda por dialecto) y su consecuencia sobre la suite SQLite/PostgreSQL. Tareas con criterio explícito (`409` a la perdedora) condicionado a esa decisión. |
| 7 | Terminología "professional" vs `dentist_id` (**menor**) | `spec.md` (todos los requisitos), `tasks.md` 1.1 y 2.3, `proposal.md` "What Changes" | Se unificó en `dentist_id` (y `box_id`) en la spec y en las tareas; el escenario pasó a llamarse "Dentist overlap is rejected". |
| 8 | Ciclo de vida del box no especificado (**menor**) | `spec.md` → nuevo requisito "Box creation"; `design.md` §Open Questions (3); `tasks.md` 2.1 | Se agregó el alta de box con nombre no vacío y `clinic_id` del contexto. La restricción de agendar sobre un box en `maintenance` queda explícitamente como decisión pendiente; C-04 no la inventa y la tarea 2.1 lo dice. |
| 9 | Auditoría de cancelaciones (**menor**) | `design.md` §Open Questions (4); `tasks.md` 2.5 | Se documentó el límite: C-04 no crea `AuditLog` mientras no se decida si RN-04 pertenece a C-04 o a C-06. No se resolvió por inferencia. |
| 10 | Secuenciación frente a C-02 (**menor**) | `design.md` Risks; `tasks.md` "Workflow follow-up" y 3.3 | C-02 figura como archivada y disponible (2026-11-02); se exige que las pruebas de aislamiento corran contra el contexto real de C-02, no contra un stub, antes de archivar. |
| 11 | 403/404 divergente con C-02 (transversal) | `spec.md` → "Box isolation", "Appointment states", "Appointment read isolation" | Se reemplazó "not-found **or** authorization error" por `404 not_found` único, con la misma forma que un ID inexistente, alineado con `tenant-isolation` §Cross-clinic disclosure prevention. |
| 12 | Falta `## UI Mockups` en `design.md` (menor) | `design.md` → nueva sección "## UI Mockups" | `Decision: no (no UI)` con fecha 2026-11-04 y justificación (C-04 backend-only, sin `design-system/` registrado). No se inventó política de mockups. |

**Pendientes de decisión del usuario** (registradas en `design.md` §Open Questions, sin resolver):

1. Mecanismo de RN-01 portable entre SQLite y PostgreSQL (servicio con bloqueo vs. `EXCLUDE` de PostgreSQL con guarda por dialecto).
2. Origen de `no_show` y cualquier transición fuera de la matriz declarada.
3. Si el alta de turno debe rechazar boxes en `maintenance`.
4. Titularidad de la auditoría de cancelaciones de RN-04 (C-04 vs. C-06).
5. Si el listado de turnos incluye `cancelled` por defecto.

**No aplicado por límite explícito de la tarea:** el bullet de "Scope" de C-04 en
`CHANGES.md` sigue enumerando cuatro estados y omitiendo `no_show`. El alcance de esta
tarea solo permitía ajustar la línea de "Hallazgos a resolver antes de implementar";
la spec es la fuente normativa del enum de cinco estados.

**Limitaciones de esta revisión:**

- No existe `knowledge-base/06_funcionalidades.md` leído en esta pasada porque la skill no
  lo exige; si la épica correspondiente a agenda impusiera requisitos adicionales, esta
  revisión no los contrastó. La ruta de lectura de `knowledge-base/README.md` para
  "implementar turnos/agenda" (04 + 05 + 07) quedó cubierta en su totalidad.
- `design.md` no contenía la sección `## UI Mockups` con `Decision: no (no UI)` que la
  política global del harness pide para trabajo no visual. Se agregó el 2026-11-04
  (ver tabla de correcciones, fila 12).
- No se verificó la existencia de código de implementación para C-04 (el change está en
  etapa de propuesta y las tareas están sin marcar), por lo que todas las observaciones
  son de especificación y no de implementación.
