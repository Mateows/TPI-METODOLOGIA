# Tasks

## 1. Modelo y migración

- [ ] 1.1 Agregar modelos tipados `Box` y `Appointment` con `clinic_id`,
  referencias, estados e índices; verificar con tests de esquema que las
  columnas y relaciones esperadas existen.
- [ ] 1.2 Crear la migración PostgreSQL para boxes y turnos, incluyendo la
  estrategia de integridad para evitar solapamientos; verificar aplicando la
  migración desde una base vacía y ejecutándola por segunda vez.
- [ ] 1.3 Documentar en el módulo de persistencia las invariantes UTC y de
  aislamiento; verificar que la documentación coincide con la migración y la
  KB.

## 2. Servicio de agenda

- [ ] 2.1 Implementar creación y consulta de boxes filtradas por `clinic_id`;
  verificar con una prueba que un UUID de otra clínica no revela datos.
- [ ] 2.2 Implementar creación de turnos con referencias de la misma clínica,
  datetimes conscientes normalizados a UTC y `end_time > start_time`; verificar
  escenarios válido y rango inválido.
- [ ] 2.3 Implementar detección de solapamiento por profesional o box con
  límites consecutivos permitidos; verificar solapamiento rechazado y
  adyacencia aceptada.
- [ ] 2.4 Traducir conflictos de concurrencia y reglas de negocio a errores
  semánticos sin exponer trazas SQL; verificar respuesta estable ante
  reintento concurrente.
- [ ] 2.5 Implementar transiciones de estado permitidas y su aislamiento por
  clínica; verificar confirmación válida y estado desconocido rechazado.

## 3. API y documentación

- [ ] 3.1 Exponer endpoints FastAPI para boxes y turnos usando los servicios,
  esquemas Pydantic estrictos y el contexto multi-tenant de C-02; verificar
  payloads válidos, errores 4xx y ausencia de `any` en contratos TypeScript si
  se agrega cliente.
- [ ] 3.2 Actualizar la documentación de API y el flujo de agenda con los
  estados, códigos de error y formato UTC; verificar que los ejemplos sean
  reproducibles sin datos reales.
- [ ] 3.3 Agregar pruebas de integración de los tres escenarios obligatorios
  (funcionamiento, error de negocio y borde) contra la base aislada; verificar
  que la suite dirigida pase sin escribir en la base de desarrollo.

## 4. Integración

- [ ] 4.1 Ejecutar validación OpenSpec y revisión de reglas contra la KB;
  verificar que todos los requisitos tengan escenarios y que no se marque el
  change como implementado antes de completar las pruebas.

## Workflow follow-up

- Implementar las tareas cuando C-02 y el contexto de autenticación estén
  disponibles.
- Ejecutar la validación completa del change y archivarlo únicamente después
  de una implementación verificada.
