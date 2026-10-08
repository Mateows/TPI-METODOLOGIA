# 09. Decisiones y Supuestos — TPI Metodologia

## 1. Decisiones Clave (ADRs)
- **ADR-01: Uso de FastAPI en lugar de Django:** Elegido por su velocidad de ejecución nativa, soporte asincrónico y validación automática con Pydantic, ideal para APIs escalables de salud.
- **ADR-02: Arquitectura Multi-Tenant Lógica:** Uso de `clinic_id` en todas las tablas relacionales en lugar de bases de datos separadas por cliente, optimizando costos de infraestructura y simplificando migraciones.
- **ADR-03: Facturación AFIP mediante servicio modular:** Abstracción del conector AFIP en un servicio independiente para aislar los cambios normativos impositivos de la lógica central del negocio.

## 2. Supuestos Principales
- Los consultorios disponen de conexión a internet estable durante el horario de atención para interactuar con la nube y la API de AFIP.
- Los pacientes cuentan con WhatsApp activo para recibir confirmaciones y recordatorios.
- El modelo comercial inicial estará enfocado en suscripción mensual en pesos (ARS) ajustada al mercado argentino.
