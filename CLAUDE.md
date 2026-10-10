# TPI MetodOLOGIA — Instrucciones para Agentes

## Stack Tecnológico

| Capa | Tecnología / Herramienta | Versión / Notas |
|---|---|---|
| **Backend** | Python 3.11+, FastAPI | API REST asincrónica, tipado estricto con Pydantic |
| **Frontend** | React 18+, TypeScript, Tailwind CSS | SPA responsiva orientada a componentes |
| **Base de Datos** | PostgreSQL, SQLAlchemy, Alembic | Base de datos relacional con migraciones y segregación por `clinic_id` |
| **DevOps / Infra** | Docker, Docker Compose | Contenerización para desarrollo y despliegue |

---

## Base de Conocimiento

La documentación canónica del proyecto se encuentra en la carpeta `knowledge-base/`:

- [01. Visión y Objetivos](knowledge-base/01_vision_y_objetivos.md)
- [02. Descripción General](knowledge-base/02_descripcion_general.md)
- [03. Actores y Roles](knowledge-base/03_actores_y_roles.md)
- [04. Modelo de Datos](knowledge-base/04_modelo_de_datos.md)
- [05. Reglas de Negocio](knowledge-base/05_reglas_de_negocio.md)
- [06. Funcionalidades](knowledge-base/06_funcionalidades.md)
- [07. Flujos Principales](knowledge-base/07_flujos_principales.md)
- [08. Arquitectura Propuesta](knowledge-base/08_arquitectura_propuesta.md)
- [09. Decisiones y Supuestos](knowledge-base/09_decisiones_y_supuestos.md)
- [10. Preguntas Abiertas](knowledge-base/10_preguntas_abiertas.md)

---

## Skills Disponibles por Agente

| Agente / Rol | Skills Asignadas | Trigger Principal |
|---|---|---|
| **Backend Core & Aux** | `openspec-propose`, `openspec-apply-change` | Implementación de modelos, endpoints FastAPI y reglas de negocio |
| **Frontend** | `openspec-apply-change`, `openspec-explore` | Desarrollo de componentes React y portal de turnos |
| **Orquestación (OPSX)** | `kb-creator`, `roadmap-generator`, `skill-registry`, `agents-md-generator`, `openspec-*` | Coordinación del ciclo de vida OpenSpec |

> **Nota:** Los compact rules de cada skill los resuelve el orquestador desde `.atl/skill-registry.md` (generado por `skill-registry`; versionado SÍ por D-5).

---

## Roadmap de Changes

El proyecto se ejecuta en base al índice canónico definido en `CHANGES.md` (**10 changes** organizados en **4 fases**).

- **Camino Crítico**: `C-01` (Foundation) → `C-02` (Core Models/Auth) → `C-04` (Appointment Agenda) → `C-07` (Cash & Payments) → `C-08` (AFIP Billing) → `C-10` (Frontend Dashboard).
- **Primer change recomendado para iniciar**: `C-01` (`foundation-setup`).

---

## Reglas Duras (Específicas del Proyecto)

> Reglas globales ya definidas en `~/.claude/CLAUDE.md` (orquestador, governance, TDD, engram): el proyecto las hereda. Acá viven solo las reglas específicas de este proyecto.

1. **Aislamiento Multi-Tenant**: Toda consulta o mutación a la base de datos debe filtrar y validar estrictamente por `clinic_id`. NUNCA permitir acceso cruzado entre clínicas (Cumplimiento Ley 25.326).
2. **Tipado Estricto**:
   - Backend: Uso obligatorio de type hints en Python y modelos Pydantic con validación estricta para payloads y respuestas.
   - Frontend: Prohibido el uso de `any` en TypeScript; tipado completo para props y respuestas de API.
3. **Validación Fiscal e Integridad**:
   - Las transacciones con AFIP/ARCA (`C-08`) requieren la obtención exitosa del CAE antes de confirmar el cobro en caja.
   - Prevención de solapamientos obligatoria en la agenda de turnos (`C-04`).
   - Presupuesto aceptado genera cargos en cuenta corriente del paciente (`Budget` → `AccountEntry`); sin firma digital en MVP (firma → V1.5) (RN-08, D-1).
   - Liquidación automática de comisiones/honorarios fuera del MVP → V2; en V1 solo métrica de visibilidad, sin motor de liquidación (RN-09, D-1).
4. **Clean Architecture en FastAPI**:
   - Separación estricta en capas: Routers (`api/`), Lógica de negocio (`services/`), y Persistencia (`models/` / SQLAlchemy).
5. **Manejo de Errores y Excepciones Tipadas**:
   - Backend: Uso de excepciones HTTP semánticas y customizadas; prohibido exponer trazas internas de base de datos.
   - Frontend: Control robusto de errores de red en peticiones asíncronas con feedback visual.
6. **Idempotencia en Pagos y Facturación**:
   - Obligatoriedad de claves de idempotencia en pasarelas de pago (Mercado Pago) y llamados críticos de facturación AFIP/ARCA (`C-08`) para evitar duplicaciones.
7. **Privacidad de Datos de Salud (Ley 25.326)**:
   - Prohibición absoluta de loguear datos sensibles de salud o identificatorios de pacientes en consola o archivos de logs del servidor.
8. **Consistencia Temporal (Timezones)**:
   - Persistencia estricta de fechas y horas en UTC en base de datos; conversión a hora local de Argentina (`America/Argentina/Buenos_Aires`) únicamente en la capa de interfaz.

---

## Flujo de Trabajo (OPSX)

1. **Leer la KB y CHANGES.md** para entender el contexto del change a implementar.
2. **Proponer el change**: `/opsx:propose C-NN-nombre`
3. **Aplicar la implementación**: `/opsx:apply C-NN-nombre` (bajo Strict TDD Mode cuando aplique).
4. **Archivar el change**: `/opsx:archive C-NN-nombre`
