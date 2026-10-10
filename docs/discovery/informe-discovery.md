# Informe de Discovery — TPI Metodología (SaaS odontológico)

**Materia:** Metodología I — Trabajo Práctico Integrador (TPI).
**Fecha de congelamiento:** 2026-10-09.
**Estado:** BORRADOR (Etapas 2.2 + 2.4 parcial).
**Nota de procedencia:** documento derivado de `discovery/discovery.md` (fuente viva con correcciones del usuario, fecha 2026-10-05) + `discovery/research-sistemas-2026-10-09.md` (Etapa 2.1, fecha de consulta 2026-10-09). No se editó ningún otro archivo del repositorio para producir este informe. Ante cualquier discrepancia entre este informe y dichas fuentes, prevalecen las fuentes.

---

## Resumen ejecutivo

Se investigaron **16 sistemas de gestión odontológica** (10 relevados en `discovery/discovery.md` con verificación del usuario + 6 incorporados en el research del 2026-10-09), con foco en Argentina (prioridad normativo-fiscal: AFIP/ARCA, Ley 25.326) y LATAM, más referencias globales. Por cada sistema se distinguió, cuando la evidencia lo permitió, entre funcionalidad **comprobada** (visible en producto, documentación o precios oficiales) y **afirmación comercial** (declarada por el proveedor sin demostración pública).

Hallazgos principales:

1. **Vacío fiscal argentino confirmado por ausencia.** Ninguno de los 16 sistemas evidencia emisión de factura electrónica con CAE ante AFIP/ARCA. Los sistemas que sí facturan electrónicamente lo hacen para otras jurisdicciones (España: VeriFactu/TicketBAI; México: CFDI; Colombia: DIAN/RIPS). Incluso el competidor directo argentino (DentalSoft) integra caja con Mercado Pago y gestión de obras sociales, pero no evidencia CAE. La diferenciación fiscal del TPI queda así respaldada por evidencia negativa sistemática, no por una suposición.
2. **Competidor directo argentino identificado: DentalSoft** (La Plata + Rosario, 300+ clínicas —cifra declarada por el proveedor—, precios en ARS pendientes de verificación —ver Sección A fila 16 y Verificación de fuentes—, turnos online 24/7, WhatsApp y Mercado Pago comprobados). Es el benchmark funcional más cercano y, por ello, se lo incorpora como 5.º competidor para análisis de demo.
3. **Benchmark de turnos en LATAM.** AgendaPro (Chile, opera en AR) y DentalSoft fijan el estándar regional en agenda online 24/7 y recordatorios con confirmación; el TPI debe igualarlos en turnos y superarlos en el eje clínico-fiscal (odontograma + AFIP/CAE + cuenta corriente).
4. **Barrera de costos en USD.** La mayoría de los competidores extranjeros cotiza en USD/EUR, costo prohibitivo para consultorios unipersonales argentinos por carga impositiva sobre pagos al exterior; solo DentalSoft declara precios en pesos (pendientes de verificación por riesgo de homonimia — ver Sección A fila 16 y Verificación de fuentes). Un SaaS nativo en ARS es una ventaja competitiva concreta.

**MVP recomendado (V1):** agenda multi-profesional y multi-box con prevención de solapamientos; portal de reserva online vía web y WhatsApp; historia clínica electrónica con odontograma básico/estándar; recordatorios automáticos por WhatsApp; caja diaria con cobros (efectivo, transferencia, Mercado Pago); facturación electrónica básica integrada con AFIP/ARCA. Se difieren a V1.5 (bot de WhatsApp con IA, presupuestos con firma digital) y V2 (obras sociales complejas, PACS/DICOM, app nativa). Coherente con `knowledge-base/01_vision_y_objetivos.md`.

---

## Checklist Discovery (11 puntos)

1. **Problema.** Gestión fragmentada de turnos, historias clínicas y cobros en consultorios odontológicos de Argentina y LATAM: agendas manuales (papel/WhatsApp), historias clínicas desacopladas de imágenes, cobros sin trazabilidad de caja, ausencia de facturación fiscal integrada y ausentismo del 20–30% por falta de recordatorios automatizados. Consecuencias: pérdida de ingresos, riesgo legal (Ley 25.326, incumplimiento AFIP) y fricción operativa. *(Fuente: `discovery/discovery.md`, §2; `state.json › discovery.problema`.)*
2. **Usuarios.** Odontólogo / Profesional tratante; Recepcionista / Secretario/a; Administrador / Dueño de clínica; Paciente. Roles y responsabilidades según §3 de `discovery/discovery.md`.
3. **Casos de uso.** (i) Reserva 24/7 sin fricción (web/WhatsApp); (ii) recordatorios automatizados con confirmación/cancelación que liberan el turno; (iii) historia clínica y odontograma integrados con presupuesto en un clic; (iv) control de caja con cobros mixtos y factura electrónica AFIP/ARCA; (v) liquidación de honorarios por profesional. *(Fuente: `discovery/discovery.md`, §4.)*
4. **Competidores.** Ver **Sección A** (tabla de 16 sistemas) y **Sección B** (matriz ponderada). Síntesis: mercado cubierto en agenda y odontograma básico; descubierto en integración fiscal argentina nativa.
5. **Funcionalidades necesarias (MVP V1).** Agenda multi-profesional y multi-box; reserva online vía web y WhatsApp; HCE y odontograma básico/estándar; recordatorios automáticos por WhatsApp; caja diaria y facturación AFIP/ARCA. *(Fuente: `state.json › discovery.funcionalidades_necesarias`; `discovery/discovery.md`, §8.C.)*
6. **Funcionalidades opcionales (post-MVP).** Bot de WhatsApp con IA para re-agenda; presupuestos con firma digital; app móvil nativa (la web responsiva basta en V1). *(Fuente: `state.json › discovery.funcionalidades_opcionales`.)*
7. **Reglas de negocio.** Prevención de solapamiento de turnos por profesional/box; cumplimiento de la Ley 25.326 de protección de datos de salud; trazabilidad de cobros y caja. *(Fuente: `state.json › discovery.reglas_de_negocio`.)*
8. **Integraciones.** WhatsApp Business API; Mercado Pago; AFIP/ARCA (facturación electrónica); Google Calendar. *(Fuente: `state.json › discovery.integraciones`.)*
9. **Restricciones.** Adaptación obligatoria al marco fiscal e impositivo argentino; costo accesible en pesos (ARS) para consultorios independientes. *(Fuente: `state.json › discovery.restricciones`.)*
10. **Riesgos.** Resistencia al cambio del personal acostumbrado a papel/WhatsApp manual; estabilidad y latencia de las integraciones con AFIP y WhatsApp API. *(Fuente: `state.json › discovery.riesgos`.)*
11. **Preguntas abiertas.** ¿Multi-sucursal desde la v1 o foco en consultorios unipersonales/clínicas medianas? ¿Cuál será la pasarela primaria para señas de turnos online? *(Fuente: `state.json › discovery.preguntas_abiertas`.)*

---

## Sección A — Tabla comparativa de 16 sistemas

Filas 1–10 transcriptas fielmente de `discovery/discovery.md` (§5, relevamiento verificado por el usuario el 2026-10-05). Filas 11–16 incorporadas de `discovery/research-sistemas-2026-10-09.md` (Etapa 2.1, consulta 2026-10-09). Criterio crítico aplicado en todo el informe: **toda celda sin respaldo público literal dice "No evidenciado"**; se distingue **comprobado** (producto/docs/precios oficiales) de **afirmación comercial** (dicho por el proveedor sin demostración pública).

| # | Software | Empresa / Origen | Segmento / Modalidad | Agenda & Turnos | Gestión Clínica | Facturación & OO.SS. | Integraciones | Modelo comercial | Fuente (URL + fecha) |
|---|----------|------------------|----------------------|-----------------|-----------------|----------------------|---------------|------------------|----------------------|
| 1 | Simples Dental | Simples Dental (Brasil / LATAM) | Consultorio / Clínica (Cloud SaaS) | Multiprofesional, gestión por sillones, control de solapamientos | Odontograma digital, evoluciones, historia clínica | Gestión de caja, cobros y facturación (requiere integraciones fiscales locales en Argentina) | WhatsApp, pasarelas de pago | Suscripción mensual (SaaS) | https://www.simplesdental.com — 2026-10-05 |
| 2 | Dentalink | Dentalink (Chile / LATAM) | Clínica / Red de clínicas / Independiente (Cloud SaaS) | Robusta, multi-sucursal, recordatorios automáticos por WhatsApp | Completa (odontograma, periodontograma, recetas, imágenes) | Control de caja, pagos, facturas y cobros vía pasarelas | WhatsApp API, Mercado Pago, Google Calendar | Suscripción mensual por profesional (USD) | https://www.dentalink.cl — 2026-10-05 |
| 3 | Alegra Odonto | Alegra (Colombia / LATAM) | Profesional independiente / Consultorio (Cloud SaaS) | Intuitiva, agenda integrada, recordatorios automáticos | Odontograma básico/avanzado, planes de tratamiento | Contabilidad, facturación electrónica adaptable a LATAM (AFIP en Argentina: integración, no emisión nativa evidenciada) | WhatsApp, Mercado Pago, AFIP | Suscripción mensual escalonada (USD) | https://www.alegra.com/odonto/ — 2026-10-05 |
| 4 | Dentidesk | Dentidesk (Chile / LATAM) | Consultorio / Clínica (Cloud SaaS) | Completa, enlace web público de turnos y recordatorios | Odontograma, evolución clínica, prescripciones | Control de pagos, reportes financieros y caja | WhatsApp, Google Calendar, pasarelas de pago | Suscripción mensual por usuario (USD) | https://la.dentidesk.me — 2026-10-05 |
| 5 | Sima Dental | Desarrollos locales / Sistemas médicos (Argentina) | Consultorio / Clínica mediana (Cloud / Híbrido) | Agenda por box y profesional, lista de espera | Historia clínica adaptada a normativas locales | Caja diaria, cobros y facturación local (Argentina) | WhatsApp, sistemas locales | Suscripción mensual en pesos (ARS) | No evidenciado (sin URL oficial aportada en la fuente) |
| 6 | Clinic Cloud | Clinic Cloud (España / LATAM) | Clínica multidisciplinaria (Cloud SaaS) | Multi-agenda avanzada, control de salas y equipos | Multidisciplinaria (odontología + medicina general / estética) | Facturación, contabilidad, gestión de mutuas y seguros | WhatsApp, pasarelas de pago, API propia | Suscripción mensual por clínica (EUR / USD) | https://cliniccloud.es — 2026-10-05 |
| 7 | Gesden Go | Infomed / Henry Schein One (España / LATAM) | Cadenas y grandes clínicas (Cloud SaaS) | Gestión corporativa multi-sucursal y salas | Muy avanzada, historia clínica centralizada e imágenes | Control financiero centralizado, compras y proveedores | APIs corporativas, sistemas de imagen | Suscripción corporativa (USD / moneda local) | https://www.henryscheinone.es — 2026-10-05 |
| 8 | Curve Dental | Curve Dental (EE.UU. / Global) | Clínica moderna (Cloud SaaS) | Excelente UX web, arrastrar y soltar turnos | Periodontograma avanzado, gráficos de diagnóstico en nube | Cobros, reportes gerenciales en tiempo real | APIs, integraciones de rayos X cloud | Suscripción mensual por usuario (USD) | https://www.curvedental.com — 2026-10-05 |
| 9 | Open Dental | Open Dental Software (EE.UU.) | Clínicas avanzadas (Desktop / SQL con opción Cloud por hosting) | Completa, alta customización de flujos | Robusta, código propietario sobre base SQL | Facturación robusta (mercado EE.UU. / adaptable) | SQL API, integraciones custom | Licencia de uso / Hosting dedicado | https://www.opendental.com — 2026-10-05 |
| 10 | Carestream / SoftDent | Carestream Dental (EE.UU. / Global) | Grandes clínicas (Desktop legacy / servidor local) | Multi-agenda local integrada a equipos | Historia clínica tradicional de escritorio | Facturación robusta e inventario | Equipos Carestream, DICOM, PACS | Licencia perpetua / Mantenimiento anual | https://www.carestreamdental.com — 2026-10-05 |
| 11 | AgendaPro | AgendaPro SpA (Chile; opera AR/CL/CO/MX) | Cloud SaaS multi-rubro; pymes y cadenas | Agenda 24/7, recordatorios WA/SMS/email doble confir. (compr.); app; bloqueo horarios; −90% ausencias (afirm.) | Fichas clínicas sync agenda y caja (compr.); odontograma parcial sin editor evidenciado | Caja t. real, anticipos, TPV/POS, comis. (compr.); AFIP/ARCA: No evidenciado; OO.SS. argentinas: No evidenciado | Marketplace propio, POS (afirm.); Mercado Pago: No evidenciado; Google Calendar: No evidenciado en página dental | CLP+IVA (compr.): Indiv. $15.900 a Pro $249.900; POS +$60.000+IVA; ARS ~$44.900/mes no confirmado; WA 50–200/mes | https://agendapro.com/es/dental/software-odontologico · https://agendapro.com/ar/dental/software-odontologico — 2026-10-09 |
| 12 | Medesk | Medesk Limited (Reino Unido; foco MX/CO/LATAM) | Cloud SaaS; consultorios pequeños → clínicas multi-sucursal | Agenda inteligente, reserva online, record. SMS/email, anti-doble-reserva, GCal/iCal (compr.); WA (afirm., blog MX) | Odontograma 5 caras c/ editor, periodontograma, ortodoncia, HCE+CIE-10, Rx, telemedicina (compr.) | Facturación CFDI (MX) y DIAN/RIPS (CO). AFIP/ARCA: No evidenciado. OO.SS. argentinas: No evidenciado | GCal/iCal, Stripe, Xero (compr.); Mercado Pago: No evidenciado; WA API: No evidenciado en docs core | Freemium USD (gratis 2 usuarios/50 citas; planes ~US$10–28; trial 7 días sin tarjeta) | https://www.medesk.net/es/solutiones/odontologia/ — 2026-10-09 |
| 13 | DriCloud / XDentalCloud | DriCloud (España; 14 países UE+LATAM; datos en Azure UE) | Cloud SaaS; profesional solo → grandes clínicas/hospitales | Agenda + cita online tiempo real, telemedicina, portal, kiosco; record. SMS/email (compr.); WhatsApp: No evidenciado | Odontograma + periodontograma + pptos. por pieza/fase, HCE config., firma digital (compr.); IA historia sola (afirm.) | VeriFactu ES, CFDI MX, DIAN CO; liquid./contab./arqueos; AFIP/ARCA: No evidenciado; OO.SS. argentinas: No evidenciado | 72 integraciones listadas (funcionam. afirm.); Mercado Pago, GCal/Outlook, imagen, escáner, API | Suscripción EUR/USD (Esencial 42€ → Grandes 497€; América US$49–574) | https://dricloud.com/ — 2026-10-09 |
| 14 | Nubimed | España (ciudad exacta: No evidenciada) | Cloud SaaS en navegador; clínicas pequeñas/medianas + multicentro | Agenda + cita online 24h, sala, lista espera, video, record. email/SMS, portal (compr.); WA en plan LITE (compr.) | Comprobado: odontograma interactivo, periodontograma, HCE configurable, firma digital, recetas, CIE-10 | TicketBAI/VeriFactu Premium, mutuas ES, liquid. profes.; AFIP/ARCA: No evidenciado; OO.SS. argentinas: No evidenciado | Doctoralia, VidSigner, CIE-10 (comprobadas). Mercado Pago: No evidenciado. Google Calendar: No evidenciado | EUR + IVA sin permanencia (LITE 27,40€; PREMIUM 50,10€; multicentro a consultar) | https://www.nubimed.com/ — 2026-10-09 |
| 15 | OdontoSoft Millennium! | GB Systems (Argentina + USA; ©1995–2026; "3000+ dentistas": afirmación comercial) | On-premise Windows (XP→10), monousuario o red; módulo web opcional | Agenda doctor y llamados, record. masivos email/SMS, caller-ID, CSV (compr.); Reserva online / WhatsApp: No evidenciado | Comprobado: odontogramas definibles, fichas de todas las especialidades, periodontograma, O'Leary, recetas, imágenes | Pptos., cta. cte. doble saldo, listas/plan, planes pago, stock, liquid. profes. (compr.); FE AFIP/CAE: No evidenciado | SMS/caller-ID/email masivo, CSV/Excel, eMedicalRecs opcional (+u$s120). Mercado Pago / WhatsApp / AFIP: No evidenciado | Licencia perpetua USD (mono u$s390→273; multi 5 u$s799; multi 10 u$s1199) o suscripción (u$s35/65/99 por mes) | https://gbsystems.com/os/ — 2026-10-09 |
| 16 | DentalSoft | DentalSoft (Argentina: La Plata + Rosario; "300+ clínicas": afirmación comercial) | Cloud SaaS 100% nube; consultorios y clínicas multi-profesional/multi-sucursal | Drag&drop, sobreturnos c/ antisolap., turnos 24/7 en 4 pasos, record. WA/mail, IA 24h (compr.); −82% ausencias (afirm.) | HCE + odontograma SVG (18 estados, FDI, hist./pieza), ortodoncia, pptos. c/ OS, consentim. c/ firma, recetas (compr.) | OO.SS. planes/cob., desglose OS/pac.+coseguro, liq. PDF, caja MP/multi, arqueo (compr.); FE AFIP/CAE: No evidenciado | Google Calendar, WhatsApp (Meta 0,026 USD/mensaje en Pro), Mercado Pago, PDF/Excel, web pública con SEO (comprobadas) | ARS PEND.VERIF.: 3m/50t. gratis; Gestión $30.000/mes; Pro $60.000/mes+Meta; COP $1.570.800 NO valida; dentalsoft.com.ar | https://dentalsoft.com.ar/ — 2026-10-09 |

Notas críticas de la tabla: (i) las filas 1–10 provienen de un relevamiento que no distinguía "comprobado" de "afirmación comercial"; sus celdas deben leerse como "declarado/documentado por el proveedor según la fuente citada", no como funcionalidad auditada; (ii) AFIP/CAE no evidenciado en las 16 filas —incluida la argentina DentalSoft y el incumbente OdontoSoft—; (iii) sistemas descartados con registro en Etapa 2.1 (PlanetDDS/Denticon, Eaglesoft/Patterson, Doctolib) no integran la tabla por carecer de evidencia mínima (sin AFIP/OS/WhatsApp/ARS/español, o error 429 sin posibilidad de verificación).

---

## Sección B — Matriz de puntuación ponderada

Pesos: Turnos y automatización 25% · Clínico 20% · Integraciones/WhatsApp 15% · Admin/Facturación 15% · UX paciente 10% · Seguridad/trazabilidad 10% · Precio/adopción 5%. Escala 0,0–5,0 por criterio.

| Competidor | Turnos (25%) | Clínico (20%) | Integ./WA (15%) | Admin/Fact (15%) | UX Pac. (10%) | Seguridad (10%) | Precio (5%) | Ponderado |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Dentalink | 4,8 | 4,7 | 4,5 | 4,2 | 4,8 | 4,5 | 3,8 | **4,53** |
| Simples Dental | 4,5 | 4,2 | 4,8 | 4,9 | 4,2 | 4,3 | 4,5 | **4,48** |
| Alegra Odonto | 4,2 | 4,1 | 4,3 | 4,8 | 4,5 | 4,4 | 4,6 | **4,38** |
| Dentidesk | 4,5 | 4,4 | 4,2 | 4,0 | 4,5 | 4,2 | 4,0 | **4,32** |
| Curve Dental | 4,9 | 4,8 | 3,8 | 3,8 | 4,9 | 4,6 | 3,0 | **4,31** |
| Clinic Cloud | 4,4 | 4,5 | 4,0 | 4,1 | 4,1 | 4,3 | 3,5 | **4,15** |
| Sima Dental | 4,1 | 4,0 | 4,2 | 4,2 | 3,9 | 4,0 | 4,3 | **4,11** |
| Gesden Go | No evidenciado | No evidenciado | No evidenciado | No evidenciado | No evidenciado | No evidenciado | No evidenciado | No evidenciado |
| Open Dental | No evidenciado | No evidenciado | No evidenciado | No evidenciado | No evidenciado | No evidenciado | No evidenciado | No evidenciado |
| Carestream / SoftDent | No evidenciado | No evidenciado | No evidenciado | No evidenciado | No evidenciado | No evidenciado | No evidenciado | No evidenciado |
| AgendaPro | No evidenciado | No evidenciado | No evidenciado | No evidenciado | No evidenciado | No evidenciado | No evidenciado | No evidenciado |
| Medesk | No evidenciado | No evidenciado | No evidenciado | No evidenciado | No evidenciado | No evidenciado | No evidenciado | No evidenciado |
| DriCloud / XDentalCloud | No evidenciado | No evidenciado | No evidenciado | No evidenciado | No evidenciado | No evidenciado | No evidenciado | No evidenciado |
| Nubimed | No evidenciado | No evidenciado | No evidenciado | No evidenciado | No evidenciado | No evidenciado | No evidenciado | No evidenciado |
| OdontoSoft Millennium! | No evidenciado | No evidenciado | No evidenciado | No evidenciado | No evidenciado | No evidenciado | No evidenciado | No evidenciado |
| DentalSoft (AR) | No evidenciado | No evidenciado | No evidenciado | No evidenciado | No evidenciado | No evidenciado | No evidenciado | No evidenciado |

**NOTA METODOLÓGICA (lectura obligatoria).** *Quién puntuó:* los 7 puntajes numéricos fueron producidos por el agente de Discovery y revisados por el usuario en la fuente viva (`discovery/discovery.md`, 2026-10-05); el presente informe los **transcribe sin recalcular ni alterar**. *Cuándo:* relevamiento original 2026-10-05; congelamiento del informe 2026-10-09. *Fórmula del ponderado:* `0,25·Turnos + 0,20·Clínico + 0,15·Integraciones + 0,15·Admin + 0,10·UX + 0,10·Seguridad + 0,05·Precio`. *Tratamiento de "No evidenciado":* las celdas sin respaldo no reciben número, no suman al ponderado y se declaran abiertamente; asignar puntajes a los 9 sistemas restantes (3 de la fuente viva nunca puntuados + 6 de la Etapa 2.1) exigiría aplicar la misma rúbrica con evidencia homogénea, ejercicio pendiente que corresponde a la Etapa 2.3 (verificación de fuentes) y no a este borrador. En consecuencia: **filas puntuadas: 7; filas no evidenciadas: 9**. El ranking numérico resultante ordena solo a los 7 sistemas puntuados y no debe leerse como comparación contra los 9 restantes.

---

## Sección C — Análisis competitivo y oportunidades

### Funcionalidades estándar de mercado

- Agenda interactiva por profesional con vista diaria, semanal y mensual.
- Odontograma gráfico básico (piezas sanas, caries, obturaciones, ausentes).
- Recordatorios automáticos de turnos por WhatsApp o email.
- Ficha clínica básica con datos personales y antecedentes (anamnesis).
- Control de caja diario y registro de ingresos/egresos en efectivo o transferencia.

### Funcionalidades diferenciadoras reales

- Odontograma y periodontograma interactivos avanzados con trazabilidad por sesión y firma digital del profesional.
- Facturación electrónica nativa adaptada a AFIP/ARCA (Factura C/B directa desde el cobro, sin exportaciones manuales).
- Gestión de obras sociales y prepagas con validación de padrones, copagos y control de liquidaciones.
- Asistente conversacional por WhatsApp con IA para pre-triaje, cancelación y reprogramación autónoma.

### Vacíos frecuentes en el mercado argentino

- **Integración fiscal deficiente:** los softs extranjeros requieren APIs complejas o intermediarios para facturar en Argentina, generando doble carga administrativa.
- **Complejidad con obras sociales / prepagas:** los sistemas genéricos no resuelven bonos, autorizaciones previas ni débitos prestacionales.
- **Costo en dólares:** los abonos en USD sufren cargas impositivas argentinas (impuesto PAIS, percepciones AFIP), prohibitivos para consultorios unipersonales.
- **Soporte deslocalizado:** falta de soporte en horario argentino e idiosincrasia local.

### Oportunidades de innovación para TPI Metodología

- SaaS nativo argentino en pesos (ARS), arquitectura moderna (FastAPI + React + PostgreSQL), optimizado para emisión fiscal instantánea (AFIP/ARCA) y conciliación con Mercado Pago.
- Módulo WhatsApp First: 90% de las interacciones del paciente sin apps ni portales complejos.
- UX ultra-liviana (consumer-grade): curva de aprendizaje menor a 15 minutos.

### Integración de hallazgos de la Etapa 2.1 (nuevo)

El research del 2026-10-09 confirma por ausencia el vacío fiscal: de los 6 sistemas nuevos, los tres que facturan electrónicamente lo hacen exclusivamente para España (DriCloud, Nubimed: VeriFactu/TicketBAI), México (Medesk, DriCloud: CFDI) o Colombia (Medesk, DriCloud: DIAN/RIPS); AgendaPro, OdontoSoft y —decisivamente— DentalSoft no evidencian emisión con CAE ante AFIP/ARCA pese a operar o pertenecer al mercado argentino. Que ni el competidor directo nacional ni el incumbente histórico con el circuito de obras sociales más maduro (OdontoSoft) exhiban CAE convierte la facturación fiscal nativa en el diferencial de mayor respaldo evidencial del TPI, por encima del canal WhatsApp o la agenda online, donde la competencia ya es paritaria.

En paralelo, el benchmark de turnos para LATAM queda fijado por AgendaPro (agenda 24/7 multi-sucursal con doble confirmación y app móvil, aunque con WhatsApp racionado por plan) y DentalSoft (turnos online en 4 pasos, detección de solapamientos, confirmación que actualiza la agenda y asistente IA 24h, con precios en ARS pendientes de verificación —ver Sección A fila 16 y Verificación de fuentes—). El TPI no necesita inventar el estándar de reserva: debe igualar ese nivel de fricción mínima y desplazar la competencia al eje donde ambos son débiles —trazabilidad clínico-fiscal (odontograma vinculado a presupuesto, cuenta corriente y factura con CAE en un solo flujo)— en lugar de competir solo por recordatorios o diseño de agenda.

*(Sección C basada en `discovery/discovery.md`, §7; párrafos finales integran `discovery/research-sistemas-2026-10-09.md`, §§1–6 y síntesis transversal.)*

---

## Sección D — Recomendación, demos y MVP

### A. Cinco competidores prioritarios para análisis de demo

1. **Dentalink** — Benchmark absoluto en UX y robustez en LATAM. (https://www.dentalink.cl)
2. **Simples Dental** — Referente regional en gestión ágil para consultorios de alto volumen. (https://www.simplesdental.com)
3. **Alegra Odonto** — Ejemplo de integración contable, facturación y facilidad de uso. (https://www.alegra.com/odonto/)
4. **Dentidesk** — Modelo equilibrado de precio y funcionalidades clínicas para consultorios medianos. (https://la.dentidesk.me)
5. **DentalSoft (Argentina)** — Competidor directo nacional: turnos online 24/7 con detección de solapamientos y recordatorios por WhatsApp comprobados, más caja con Mercado Pago y precios en ARS. Observar su demo permite fijar el piso funcional local que el TPI debe igualar antes de diferenciarse vía AFIP/CAE y cuenta corriente. (https://dentalsoft.com.ar/)

### B. Tres productos de referencia para UX

- **Curve Dental** — Benchmark mundial en velocidad de carga, diseño web limpio y odontograma interactivo sin fricciones. (https://www.curvedental.com)
- **Calendly** — Referencia de agendamiento autónomo sin fricción (enlaces limpios de reserva). (https://calendly.com)
- **Alegra (ecosistema)** — Simplicidad absoluta en flujos administrativos y cobros. (https://www.alegra.com)

### C. MVP sugerido para TPI Metodología

**Imprescindibles (V1 — Core MVP):**

- Agenda multi-profesional y multi-box con prevención de solapamientos y bloqueo de horarios.
- Portal de reserva online público vía enlace web y WhatsApp.
- Historia clínica electrónica (HCE) y odontograma básico/estándar (registro por cara de pieza dentaria).
- Recordatorios automáticos por WhatsApp (confirmación y cancelación interactiva).
- Caja diaria y registro de cobros (efectivo, transferencia, Mercado Pago).
- Facturación electrónica básica integrada con AFIP/ARCA.

**Diferenciadoras (V1.5):**

- Bot de WhatsApp con IA para gestión autónoma de turnos 24/7.
- Módulo de presupuestos con firma digital del paciente y seguimiento de conversión.

**Etapas posteriores (V2 / Roadmap):**

- Módulo avanzado de gestión de obras sociales complejas y auditoría de prepagas.
- Radiología PACS/DICOM nativa en la nube.
- App móvil nativa dedicada (la web responsiva basta para V1).

---

## Verificación de fuentes (Etapa 2.3 — registro personal del usuario, 2026-10-10)

| Fuente | Tipo | Qué afirmaba el informe | Qué se encontró | Corrección |
|--------|------|-------------------------|-----------------|------------|
| Medesk (https://www.medesk.net/es/blog/software-para-clinicas-dentales/) | Cloud SaaS médico | Odontograma 5 caras, HCE con CIE-10, telemedicina, Mini ~US$10, Pro ~US$28 | Sitio oficial lo ratifica textual (odontograma 5 caras, CIE precargado, telemedicina, Mini $10/mes, Pro $28/mes) | Ninguna |
| DriCloud (https://dricloud.com/precios/) | Cloud SaaS clínico | Esencial 42€ a Grandes 497€ | Tarifario confirma ESENCIAL 42€, SOLO 92€, CLÍNICA 129€, CENTRO MÉDICO 249€, GRANDES CLÍNICAS 497€/mes | Ninguna |
| Nubimed (https://www.nubimed.com/planes-precios/) | SaaS dental | LITE 27,40€, PREMIUM 50,10€, recepción/admin ilimitados gratis | Ratificado al centavo (+IVA) + usuarios recepción/admin/gestores/contables ILIMITADOS y GRATUITOS | Ninguna |
| AgendaPro (https://agendapro.com/ar/dental/software-odontologico) | Sitio localizado AR | Modelo CLP + agenda 24/7 + recordatorios WhatsApp | Funciones ratificadas + presencia localizada AR (URL /ar/) con tarifas ARS reportadas (~$44.900 ARS/mes en comparativas, NO confirmado directo) | Actualizar Modelo Comercial — existe presencia/facturación localizada AR, no asumir CLP obligatorio. NOTA: la página /ar/ por sí sola no prueba que todos los planes se facturen en ARS; moneda/precio/impuestos pendientes de confirmación directa |
| DentalSoft (dominio a analizar: https://dentalsoft.com.ar/) | Entidad argentina (a verificar) | Entidad argentina con planes ARS 30.000/60.000 | Riesgo de homonimia — las búsquedas priorizan "DentalSoftWeb" colombiana (precios COP, ej. $1.570.800 COP), que NO valida al proveedor argentino | Flag de advertencia explícito + restringir análisis a dentalsoft.com.ar + precios ARS 30.000/60.000 pasan a PENDIENTES DE VERIFICACIÓN hasta evidencia inequívoca del dominio argentino |

---

## Referencias completas

**De `discovery/discovery.md` (consulta 2026-10-05):** https://www.simplesdental.com · https://www.dentalink.cl (ayuda: https://ayuda.dentalink.cl) · https://www.alegra.com/odonto/ · https://la.dentidesk.me · https://cliniccloud.es · https://www.henryscheinone.es · https://www.curvedental.com · https://www.opendental.com · https://www.carestreamdental.com · https://www.afip.gob.ar · https://www.argentina.gob.ar/aaip. Fila Sima Dental: sin URL oficial aportada (No evidenciado).

**De `discovery/research-sistemas-2026-10-09.md` (consulta 2026-10-09):** https://agendapro.com/es/dental/software-odontologico · https://agendapro.com/cl/planes · https://www.medesk.net/es/solutiones/odontologia/ · https://www.medesk.net/es/ · https://xdentalcloud.com/ · https://dricloud.com/ (precios: https://dricloud.com/precios/) · https://www.nubimed.com/ (odontograma: https://www.nubimed.com/odontograma-digital/; precios: https://www.nubimed.com/planes-precios/) · https://gbsystems.com/os/ (producto: https://gbsystems.com/os/producto.htm; precios: https://gbsystems.com/os/precios.htm) · https://dentalsoft.com.ar/ (OO.SS.: https://dentalsoft.com.ar/funcionalidades/obras-sociales; caja: https://dentalsoft.com.ar/funcionalidades/caja-cobros).

**De coherencia MVP:** `knowledge-base/01_vision_y_objetivos.md` (única lectura, §3–§4).

*Referencias UX (§D.B):* https://calendly.com · https://www.alegra.com.
