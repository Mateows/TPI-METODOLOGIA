# Decisiones OPCIÓN A — TPI Metodologia

**Fecha:** 2026-10-08
**Alcance de este documento:** Resolver explícitamente las 6 decisiones abiertas de la Opción A. Solo documento de decisiones.
**Estado previo:** Opción B ya aplicada (roadmap GATE 4 + Paso 5 y registry completos en `CHANGES.md` / `.atl/skill-registry.md`). No se tocan en esta tarea.
**Fuera de alcance:** C-01 queda manual y fuera de alcance. No se implementa código, no se editan KB (`knowledge-base/`), ni `CHANGES.md`, ni `AGENTS.md` / `CLAUDE.md`.
**Lectura previa:** `knowledge-base/01_vision_y_objetivos.md`, `04_modelo_de_datos.md`, `05_reglas_de_negocio.md`, `06_funcionalidades.md`, `07_flujos_principales.md`, `09_decisiones_y_supuestos.md`, `10_preguntas_abiertas.md`, `discovery/discovery.md`, `CHANGES.md` (fases/gates), `AGENTS.md` (reglas duras).

## Tabla resumen

| # | Decisión | Resolución adoptada |
|---|---|---|
| D-1 | Presupuestos y comisiones | Budget básico SÍ en MVP (entidad Budget + cuenta corriente, sin firma digital; firma → V1.5); liquidación/comisiones → V2 |
| D-2 | Caja: Payment vs Invoice | Entidad propia Payment/Transaction con `idempotency_key` (Mercado Pago + AFIP), separada de Invoice (que guarda CAE) |
| D-3 | Multi-sucursal | V1 = clínica única, solo `clinic_id` (sin `branch_id`); multi-sucursal → V2; C-02 sin cambios |
| D-4 | Pasarela y hosting | Mercado Pago único en MVP (P-01 cerrada como "MP único"); hosting dev: Docker Compose local + Railway/Render para staging; P-03 cerrada así |
| D-5 | Versionado y espejo de instrucciones | Versionar `.atl/skill-registry.md` SÍ; AGENTS.md/CLAUDE.md = espejo intencional dual-plane (editar ambos siempre); `.gitignore` mínimo (venv, .env, `__pycache__`), NO ignorar `.atl/` |
| D-6 | Paralelismo | Modo 1 agente secuencial seguro: C-01→C-02→C-03→C-04→C-05→C-06→C-07→C-08→C-09→C-10 respetando gates; modo 3-agentes queda como alternativo documentado |

---

### D-1 Presupuestos y comisiones

**Decisión:** Budget básico SÍ entra en MVP como entidad `Budget` + cuenta corriente del paciente, sin firma digital (firma digital → V1.5). Liquidación de honorarios / comisiones de profesionales → V2 con alcance explícito. No bloquea C-05/C-07.

**Justificación (cita KB/discovery):**
- `discovery/discovery.md` §4 caso de uso "Como odontólogo, quiero registrar un tratamiento ... y que se actualice el presupuesto" y §7 "Pérdida de ingresos por ... deficiente seguimiento de presupuestos pendientes" + rol Administrador ("gestiona roles, comisiones") y rol Paciente ("visualiza presupuestos pendientes"): el presupuesto es flujo core, no accesorio.
- `knowledge-base/07_flujos_principales.md` Flujo 2 Paso 4: "el sistema genera automáticamente el ítem pendiente en la cuenta corriente del paciente" — presupone cuenta corriente/Budget aunque `04_modelo_de_datos.md` aún no lo modele.
- `knowledge-base/01_vision_y_objetivos.md` §2 (objetivo Administrador: "visibilidad financiera ... ingresos por profesional, comisiones") y §3-4 MVP: comisiones como métrica, no como liquidación automática → justifica diferir liquidación a V2.
- `discovery/discovery.md` §8.C: "Módulo de presupuestos con firma digital ... (V1.5)" — la firma es explícitamente V1.5, por eso se excluye del MVP básico.

**Impacto (a editar en KB/CHANGES cuando se implemente P1, sin editarlo ahora):**
- `04_modelo_de_datos.md`: agregar entidades `Budget` (+ `BudgetItem`) y `AccountEntry`/cuenta corriente (FK `patient_id`, `clinic_id`, `medical_record_id`/`budget_id`); P1-3 pendiente.
- `05_reglas_de_negocio.md`: agregar RN-06 (presupuesto → cuenta corriente) y RN-07 (comisiones V2, solo cálculo, sin liquidación en MVP); P1-3 pendiente.
- `06_funcionalidades.md` / `CHANGES.md`: explicitar Budget básico dentro del scope de C-05 (o C-07) y marcar liquidación/comisiones como V2 fuera de C-07/C-08.

**Reversibilidad:** Media-baja. Si Budget saliera del MVP, habría que recortar Flujo 2 Paso 4 y el caso de uso odontólogo→presupuesto; costo bajo porque es aditivo (nueva entidad, no refactor). Si comisiones se adelantaran a V1, costo alto: requiere motor de liquidación por prestación/período + reportes (nuevo change o expansión de C-07/C-10).

---

### D-2 Caja: entidad propia Payment/Transaction con `idempotency_key`, separada de Invoice

**Decisión:** Crear entidad propia `Payment`/`Transaction` (caja diaria: ingresos/egresos, método de pago, estado de conciliación) con `idempotency_key` obligatoria para Mercado Pago y llamadas críticas AFIP. `Invoice` queda separada y guarda el CAE. Justificación por R6 idempotencia.

**Justificación (cita KB/discovery):**
- `AGENTS.md` Regla dura 6 (Idempotencia en Pagos y Facturación): "Obligatoriedad de claves de idempotencia en pasarelas de pago (Mercado Pago) y llamados críticos de facturación AFIP/ARCA (C-08)".
- `knowledge-base/05_reglas_de_negocio.md` RN-03 (CAE antes de registrar el cobro definitivo) + RN-05 (no cerrar caja con transacciones pendientes de conciliar) + `07_flujos_principales.md` Flujo 3 Pasos 3-4 (pago → solicitud AFIP → CAE → registro en caja): el cobro y el comprobante fiscal son dos momentos distintos → dos entidades.
- `knowledge-base/04_modelo_de_datos.md` actual solo modela `Invoice` (con `cae`); no existe entidad de caja → P1-3 (agregar `Payment`) cubre el vacío sin contradecir nada.
- `knowledge-base/09_decisiones_y_supuestos.md` ADR-03 (conector AFIP modular): separar `Payment` de `Invoice` aísla cambios normativos del núcleo de caja.

**Impacto (a editar en KB/CHANGES cuando se implemente P1, sin editarlo ahora):**
- `04_modelo_de_datos.md`: agregar `Payment`/`Transaction` (`id`, `clinic_id`, `patient_id`, `method`, `amount`, `status`, `idempotency_key` UNIQUE, `invoice_id` nullable, `created_at`) y `AuditLog`; documentar relación Payment N:1 Invoice.
- `08_arquitectura_propuesta.md`: documentar uso de `idempotency_key` (UNIQUE + manejo de reintentos) y cifrado/UTC; P1-3 pendiente.
- `CHANGES.md` C-07/C-08: explicitar que C-07 crea `Payment` con idempotencia y C-08 crea `Invoice` con CAE referenciando el pago.

**Reversibilidad:** Baja (decisión estructural correcta). Fusionar Payment+Invoice en una sola tabla costaría una migración + pérdida de trazabilidad (un pago puede no tener factura, una factura puede agrupar pagos; RN-05 exige conciliar transacciones independientes). Cambiarla después de C-07/C-08 = refactor de caja + facturación + tests.

---

### D-3 Multi-sucursal: v1 = clínica única, solo `clinic_id`

**Decisión:** V1 = clínica única por tenant: solo `clinic_id`, sin `branch_id`. Multi-sucursal → V2. C-02 sin cambios.

**Justificación (cita KB/discovery):**
- `knowledge-base/09_decisiones_y_supuestos.md` ADR-02: "Arquitectura Multi-Tenant Lógica: uso de `clinic_id` en todas las tablas" — no menciona sucursales; agregar `branch_id` contradiría el ADR vigente.
- `knowledge-base/04_modelo_de_datos.md`: todas las entidades cuelgan de `clinic_id`; ningún flujo (`07_flujos_principales.md`) ni funcionalidad (`06_funcionalidades.md`) menciona sucursales.
- `discovery/discovery.md` §5: multi-sucursal aparece solo en competidores enterprise (Dentalink red de clínicas, Gesden Go corporativo); el segmento objetivo V1 es consultorio/clínica mediana unipersonal — rescatar multi-sucursal queda como pregunta abierta (ver P1 pendientes).

**Impacto (a editar en KB/CHANGES cuando se implemente P1, sin editarlo ahora):**
- `10_preguntas_abiertas.md`: rescatar/agregar pregunta multi-sucursal con estado "Movido a V2" (P1 pendiente).
- `CHANGES.md` / C-02: sin cambios — se confirma explícitamente que C-02 no agrega `branch_id`.
- Si V2 la retoma: nueva entidad `Branch` + FK opcional en `Box`/`Appointment`/`User`, migración dedicada.

**Reversibilidad:** Alta en V1 (no se construye nada que estorbe). Costo de revertirla (es decir, introducir multi-sucursal antes) = medio-alto: migración con `branch_id` en 4+ tablas + reescritura de filtros tenant + tests de aislamiento por sucursal. Por eso se difiere a V2.

---

### D-4 Pasarela y hosting: Mercado Pago único en MVP; Docker Compose local + Railway/Render staging

**Decisión:** Mercado Pago como pasarela ÚNICA en MVP (sin secundaria). Hosting dev: Docker Compose local + Railway/Render para staging (C-01 usa `.env` + compose). P-01 y P-03 cerradas así.

**Justificación (cita KB/discovery):**
- `knowledge-base/01_vision_y_objetivos.md` §3 MVP: "Caja diaria y registro de cobros (efectivo, transferencias, Mercado Pago)" — una sola pasarela nombrada; `06_funcionalidades.md` F-06 repite el trío sin secundaria.
- `knowledge-base/10_preguntas_abiertas.md` P-01 (pasarela secundaria: Todo Pago, MODO) "Pendiente de validación comercial" — sin evidencia comercial en discovery que la exija para V1; discovery §7 recomienda "conciliación con Mercado Pago" como apuesta nativa argentina, y §5 muestra MP solo como integración estándar (Dentalink, Alegra), no dual.
- `AGENTS.md` stack DevOps: "Docker, Docker Compose" + `CHANGES.md` C-01 scope ("Docker Compose (PostgreSQL)", "Pydantic Settings (`.env`)") — Compose local es lo ya comprometido; Railway/Render es staging PaaS barato coherente con supuesto "suscripción mensual en pesos (ARS)" (`09_decisiones_y_supuestos.md`) y pain point "Costo en dólares" (discovery §7).

**Impacto (a editar en KB/CHANGES cuando se implemente P1, sin editarlo ahora):**
- `10_preguntas_abiertas.md`: cerrar P-01 como "MP único en MVP; secundaria → V2" y P-03 como "dev: Compose local; staging: Railway/Render; prod VPS diferido".
- `CHANGES.md` C-01: sin cambio de scope (ya dice Compose + `.env`); opcionalmente anotar target staging Railway/Render.
- Diseño del conector de pagos (C-07): interfaz abstracta aunque haya un solo provider, para no bloquear una segunda pasarela en V2.

**Reversibilidad:** Alta. Agregar segunda pasarela después = nuevo adapter tras interfaz + tests; no toca caja ni facturación si la abstracción existe. Cambiar hosting staging (p.ej. a VPS propio) = solo config/deploy, sin impacto en código si todo va en Compose + `.env`.

---

### D-5 Versionado: `.atl/skill-registry.md` SÍ; AGENTS.md/CLAUDE.md espejo dual-plane; `.gitignore` mínimo

**Decisión:** Versionar `.atl/skill-registry.md` SÍ (equipo, trazabilidad). AGENTS.md/CLAUDE.md = espejo intencional dual-plane (editar ambos siempre). Crear `.gitignore` mínimo (`venv/`, `.env`, `__pycache__/`, etc.) pero NO ignorar `.atl/`.

**Justificación (cita KB/discovery):**
- Trazabilidad de equipo: el registry documenta qué skills usa cada agente (`AGENTS.md` §Skills por agente); si no se versiona, cada clon pierde el contrato operativo. (Nota: `AGENTS.md` actual dice "no versionado" — esa línea es la que P1-4 propone corregir, no se toca ahora.)
- Espejo dual-plane: `AGENTS.md` (proyecto) y `CLAUDE.md` global/orquestador cumplen audiencias distintas (agente ejecutor vs. orquestador OPSX); mantener ambos sincronizados evita deriva de reglas duras (tenant, idempotencia, Ley 25.326).
- `.gitignore` mínimo: protege secretos (`.env`) y ruido (`venv/`, `__pycache__/`) sin ocultar decisiones operativas (`.atl/` visible).

**Impacto (a editar en KB/CHANGES cuando se implemente P1, sin editarlo ahora):**
- `AGENTS.md`: quitar `kb-creator`/`roadmap-generator` de skills por agente (ya cumplieron; P1-4) y corregir nota "no versionado" → "versionado SÍ".
- Crear `openspec/config.yaml` (P1-4) y `.gitignore` mínimo + initial commit (fuera de esta tarea).
- `CLAUDE.md` espejo: replicar cualquier cambio de reglas duras en ambos archivos.

**Reversibilidad:** Alta. Dejar de versionar `.atl/` después = un commit; ignorarlo por error se revierte con `git add -f`. Romper el espejo (editar solo uno) = deriva silenciosa de reglas → costo de reconciliación manual; por eso la norma "editar ambos siempre".

---

### D-6 Paralelismo: 1 agente secuencial seguro

**Decisión:** Ejecutar en modo 1 agente secuencial seguro: C-01→C-02→C-03→C-04→C-05→C-06→C-07→C-08→C-09→C-10 respetando gates. El modo 3-agentes de `CHANGES.md` queda como alternativo documentado, no como plan de ejecución.

**Justificación (cita KB/discovery):**
- `CHANGES.md` gates: GATE 1 exige C-02✓ antes de C-03/C-04; GATE 2 exige C-03✓&C-04✓; GATE 3 exige C-07✓; GATE 4 exige C-05✓&C-08✓&C-09✓. La secuencia propuesta respeta todos los gates (verificación: C-03 tras C-02 ✓; C-05 tras C-03 ✓; C-06/C-07 tras C-04 ✓; C-08 tras C-07 ✓; C-10 tras C-05/C-08/C-09 ✓).
- Un solo agente elimina riesgo de forks inconsistentes (migraciones Alembic divergentes, contratos API inventados entre C-03/C-04 paralelos) en un TPI con governance CRÍTICO en C-02/C-08.
- El plan óptimo 3-agentes (`CHANGES.md` tabla Paso 1-6) se conserva como alternativo para cuando haya capacidad real de paralelizar.

**Impacto (a editar en KB/CHANGES cuando se implemente P1, sin editarlo ahora):**
- Ninguno obligatorio: `CHANGES.md` ya documenta ambos (gates + tabla 3-agentes). Si se quiere, anotar en `CHANGES.md` cuál es el modo de ejecución activo (1-agente) vs. alternativo (3-agentes). No se edita ahora.

**Reversibilidad:** Total. Cambiar de modo es solo reordenar ejecución; los gates y dependencias no cambian. Pasar a 3-agentes después solo exige disciplina de contratos (migraciones secuenciales, APIs congeladas por gate).

---

## Próximos pasos (fuera de esta tarea)

Checklist pendiente — NO implementarlos aquí:

- [ ] **P1-3 (KB modelo/negocio/arquitectura):** agregar `Payment`/`Budget`/`AuditLog` en `04_modelo_de_datos.md`; agregar RN-06/RN-07 en `05_reglas_de_negocio.md`; documentar cifrado/UTC/idempotencia en `08_arquitectura_propuesta.md`; rescatar pregunta multi-sucursal en `10_preguntas_abiertas.md`.
- [ ] **P1-4 (higiene repo/agentes):** quitar `kb-creator`/`roadmap-generator` de `AGENTS.md` §Skills; corregir nota `.atl/` "no versionado" → versionado SÍ; crear `openspec/config.yaml`.
- [ ] **Infra inicial:** crear `.gitignore` mínimo (`venv/`, `.env`, `__pycache__/`, sin ignorar `.atl/`) + initial commit.
- [ ] **C-01 manual:** ejecutar `foundation-setup` a mano (fuera del alcance de este documento).
