---
name: revisor-de-agendas-de-citas
description: Revisa y mejora cambios OpenSpec de agenda de citas odontológicas. Usar al preparar o revisar appointment-agenda, sus proposal, specs, design o tasks, y al validar solapamientos, aislamiento por clinic_id, horarios UTC, estados y escenarios verificables. No implementa código.
---

# Revisor de agendas de citas

## Propósito

Detectar ambigüedades, omisiones y contradicciones en los artefactos
OpenSpec relacionados con la agenda de citas del sistema odontológico antes de
su implementación.

## Cuándo usar esta skill

Usar esta skill cuando se prepare o revise el change `appointment-agenda` o
cualquier artefacto equivalente de agenda. También usarla cuando se solicite
validar reglas de solapamiento, aislamiento por clínica, consistencia temporal
o estados de citas.

## Entradas necesarias

Leer, cuando existan:

1. `openspec/changes/appointment-agenda/proposal.md`
2. `openspec/changes/appointment-agenda/specs/**/spec.md`
3. `openspec/changes/appointment-agenda/design.md`
4. `openspec/changes/appointment-agenda/tasks.md`
5. `CHANGES.md`
6. `knowledge-base/README.md`
7. `knowledge-base/04_modelo_de_datos.md`
8. `knowledge-base/05_reglas_de_negocio.md`
9. `knowledge-base/07_flujos_principales.md`
10. `AGENTS.md`

Si falta un archivo obligatorio para evaluar una afirmación, informarlo como
limitación. No inventar reglas de dominio ni completar silenciosamente
información ausente.

## Procedimiento

1. Identificar el change y confirmar que corresponde a la agenda de citas.
2. Comparar proposal, specification, design y tasks entre sí.
3. Verificar que toda operación sobre boxes, pacientes, profesionales y citas
   valide el mismo `clinic_id`.
4. Verificar que una cita exija `end_time > start_time`, use horarios UTC y
   defina el comportamiento de datetimes con offset.
5. Verificar solapamientos por profesional y box, incluyendo:
   - solapamiento parcial;
   - una cita contenida dentro de otra;
   - coincidencia exacta;
   - citas consecutivas;
   - citas canceladas.
6. Verificar que los estados permitidos estén alineados con la KB y que los
   cambios de estado inválidos sean rechazados.
7. Verificar que existan al menos tres escenarios comprobables:
   funcionamiento esperado, error de negocio y caso de borde.
8. Verificar que las tareas indiquen cómo se probará cada escenario y que no
   marquen el change como implementado o archivado prematuramente.
9. Clasificar cada observación como crítica, importante o menor.
10. Proponer una corrección concreta para cada observación sin editar archivos,
    salvo que el usuario lo solicite explícitamente.

## Resultado obligatorio

Entregar un informe con esta estructura:

```markdown
# Revisión de agenda de citas

## Resumen

Estado general y cantidad de observaciones.

## Checklist

- [ ] Aislamiento por clinic_id
- [ ] Validación de intervalos
- [ ] Prevención de solapamientos
- [ ] Consistencia UTC
- [ ] Estados permitidos
- [ ] Escenarios verificables
- [ ] Tareas verificables
- [ ] Dependencias y alcance

## Observaciones

### [CRÍTICA|IMPORTANTE|MENOR] Título

- Archivo y sección:
- Problema:
- Regla o fuente relacionada:
- Corrección sugerida:

## Correcciones aplicadas o pendientes

Indicar qué fue corregido y qué requiere decisión del usuario.
```

No presentar una revisión como exitosa si no se pudieron leer las fuentes
necesarias. No incluir datos reales de pacientes ni secretos.

## Criterios de calidad

- Cada observación debe apuntar a un archivo y sección concretos.
- Las recomendaciones deben poder verificarse mediante un escenario o prueba.
- Las reglas deben estar respaldadas por la KB o por los artefactos del change.
- No agregar implementación, dependencias o decisiones fuera del alcance.
- Mantener separados los problemas de especificación de los problemas de
  implementación futura.
