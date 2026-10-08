# 10. Preguntas Abiertas — TPI Metodologia

1. **[P-01] Pasarela de Pagos Secundaria:** ¿Se integrará otra pasarela además de Mercado Pago (ej. Todo Pago, MODO) para el cobro de señas online en la V1?
   - *Estado:* Cerrada como D-4: Mercado Pago único en MVP; pasarela secundaria → V2.
2. **[P-02] Gestión de Obras Sociales:** ¿Cuál es el nivel de complejidad requerido para las validaciones de padrones de obras sociales en la primera iteración de facturación?
   - *Estado:* Movido a V2 (fuera de alcance MVP).
3. **[P-03] Hosting y Despliegue:** ¿Se utilizará infraestructura propia dockerizada en un VPS (ej. DigitalOcean / Hetzner) o plataformas PaaS (Railway / Render) para el lanzamiento inicial?
   - *Estado:* Cerrada como D-4: dev con Docker Compose local; staging en Railway/Render; prod VPS diferido.
4. **[P-04] Multi-sucursal:** ¿V1 es clínica única o multi-sucursal (se requiere `branch_id`)?
   - *Estado:* Cerrada como D-3: v1 clínica única, solo `clinic_id` (sin `branch_id`); multi-sucursal → V2.
