---
law_id: ley-compras-publicas
title: Ley de Compras Públicas (LCP)
short_title: LCP
decreto: D.L. 868 (and companion decree creating DINAC)
fecha_emision: 2023-01-25
diario_oficial: Publicado 02-03-2023, vigente desde 10-03-2023
reformas_count: 0
ultima_reforma: null
estado: vigente
materia: Compras públicas / contratación administrativa
sources:
  - https://www.trade.gov/market-intelligence/el-salvador-new-public-procurement-law
  - https://imprentanacional.gob.sv/servicios/archivo-digital-del-diario-oficial/
last_verified: 2026-05-09
relevance_to_casa_segura: medium
covers:
  - government procurement and contracting (national and municipal)
  - DINAC, the new autonomous procurement regulator
  - COMPRASAL electronic procurement system
  - RUPES (Unique Registry of State Providers)
  - bidding methods and thresholds
note: |
  Este archivo es un resumen estructurado basado en el artículo de inteligencia
  de mercado de la ITA de EE. UU. y el anuncio de la Asamblea Legislativa. El
  texto completo no fue directamente accesible al momento de la recuperación
  (asamblea.gob.sv bloqueó la descarga). Cuando el decreto completo se descargue,
  expandir cada sección con citas a nivel de artículo.
---

# Ley de Compras Públicas (LCP)

## Resumen en lenguaje sencillo

La nueva Ley de Compras Públicas (LCP) aprobada por la Asamblea Legislativa el 25 de enero de 2023 y en vigencia desde el 10 de marzo de 2023 regula **todas las compras públicas** realizadas por entidades del gobierno central, entidades autónomas y municipalidades que utilicen fondos públicos. Sustituye a la Ley de Adquisiciones y Contrataciones de la Administración Pública (LACAP).

La LCP crea la **Dirección Nacional de Compras Públicas (DINAC)**, un ente regulador autónomo que es responsable de la política de contratación pública y opera **COMPRASAL** (el sistema electrónico de compras públicas). Todas las empresas — nacionales y extranjeras — que quieran venderle al gobierno salvadoreño deben inscribirse en el **RUPES** (Registro Único de Proveedores del Estado), con excepciones durante emergencias nacionales.

**Los proyectos estratégicos y las adquisiciones realizadas por la Dirección de Obras Municipales (DOM) están excluidos** de la LCP.

Los cuatro métodos de contratación son: (a) Licitación Competitiva, (b) Comparación de Precios, (c) Compra Directa, y (d) Bajo Monto. Umbral para licitación competitiva: **$87,600**.

## Aplicación a Casa Segura

Esta ley es relevante cuando:
- Un "desarrollador" afirma que su proyecto forma parte de un programa gubernamental (Ministerio de Vivienda, FSV, IVU, municipalidad)
- A un comprador se le ofrecen "precios gubernamentales preferenciales" o propiedades "con descuento DOM"
- Un vendedor presenta su inscripción en el RUPES como signo de credibilidad

Ángulos clave para la detección de fraude:

1. **Contratos gubernamentales fantasma.** Un vendedor afirma que un edificio forma parte de un proyecto gubernamental. Los registros del RUPES + COMPRASAL pueden verificar si el desarrollador es un proveedor del Estado inscrito y contratado.
2. **Uso indebido de la exclusión DOM.** Algunos vendedores explotan el hecho de que los proyectos estratégicos de la DOM están excluidos de la transparencia de la LCP para argumentar que la opacidad es normal. Casa Segura puede marcar este patrón.
3. **Cobertura bajo el Régimen de Excepción.** Las compras directas bajo el Régimen de Excepción (marzo de 2022) están exentas de licitación competitiva. Un "desarrollador" puede abusar de esto para fabricar un contrato gubernamental falso.

Hallazgos que el motor de veredictos debería anclar aquí:

- **`gov_project_claim_unverified`** → cruzar con las bases de datos de COMPRASAL y RUPES
- **`developer_not_in_rupes`** → indica que el vendedor no puede contratar legalmente con el Estado para proyectos sobre los umbrales
- **`dom_exclusion_misuse`** → marcar cuando un proyecto declara afiliación a la DOM sin base verificable

## Disposiciones clave (nivel resumen)

### Ámbito y sustitución de la LACAP
- Se aplica a: entidades gubernamentales, entidades autónomas, municipalidades — cuando se utilicen fondos públicos.
- Sustituye a: Ley de Adquisiciones y Contrataciones de la Administración Pública (LACAP).
- Excluidos: proyectos estratégicos y adquisiciones gestionadas por la DOM.

### DINAC — Dirección Nacional de Compras Públicas
Un nuevo regulador autónomo creado por un decreto complementario (Ley de Creación de la Dirección Nacional de Compras Públicas). Responsabilidades:
- Establecer la política y regulación de las compras públicas
- Administrar COMPRASAL
- Mantener el RUPES

### COMPRASAL — Sistema Electrónico de Compras Públicas
La plataforma electrónica obligatoria a través de la cual se canalizan todas las compras públicas (con excepciones por emergencia). Todos los proveedores inscritos deben realizar sus operaciones a través de COMPRASAL.

### RUPES — Registro Único de Proveedores del Estado
Registro único de proveedores del Estado. **Todas las empresas que quieran venderle al gobierno deben inscribirse** (nacionales o extranjeras), salvo durante emergencia o urgencia nacional según lo defina la ley.

> **Señal Casa Segura:** si un desarrollador afirma que "construye para el gobierno" pero no puede mostrar su inscripción en el RUPES, es una alerta. Los registros públicos del RUPES (cuando son accesibles vía COMPRASAL) hacen esto verificable.

### Métodos de contratación
- **(a) Licitación Competitiva** — umbral por encima de $87,600
- **(b) Comparación de Precios** — bajo $87,600, requiere cotizaciones de al menos 3 proveedores
- **(c) Compra Directa** — permitida durante emergencia o urgencia nacional (p. ej. Régimen de Excepción)
- **(d) Bajo Monto** — para compras pequeñas

La ley exige **el uso de alta tecnología** y la consideración de **criterios de sostenibilidad e innovación**.

### Interacción con el Régimen de Excepción
Las compras vinculadas al Régimen de Excepción declarado en marzo de 2022 operan bajo las exenciones de emergencia señaladas arriba. Un desarrollador que invoque cobertura bajo el Régimen de Excepción para un proyecto inmobiliario privado debería ser una alerta — esa exención es para contratación de emergencia, no para desarrollo residencial.

## Patrones de fraude prácticos a vigilar

| Patrón | Verificación |
|---|---|
| El desarrollador afirma ser un "proveedor del Estado" — verificar inscripción en RUPES | RUPES (vía DINAC/COMPRASAL) |
| El proyecto afirma ser un proyecto gubernamental de vivienda social | Verificar con el Ministerio de Vivienda + portal del FSV |
| Afirmación de "construido por DOM" sin registros públicos | La DOM publica sus proyectos estratégicos |
| Licitación bajo Régimen de Excepción invocada para una venta de vivienda residencial | El Régimen de Excepción de la LCP es para contratación de emergencia |
| Precio de venta "subsidiado por licitación competitiva bajo $87,600" | Revisión del umbral |

## Referencias cruzadas

- **Vivienda obrera financiada por el FSV**: ver `03-ley-fsv.md` (el FSV es en sí una institución de derecho público con su propio régimen).
- **Contratos del IVU**: ver `02-ley-ivu.md` (vivienda institucional bajo una ley especial distinta).
- **Impuesto sobre transferencia de bienes raíces**: Ley del Impuesto sobre Transferencia de Bienes Raíces.

## Pendiente: desglose completo a nivel de artículo

Cuando los decretos completos de la LCP y la DINAC se descarguen del archivo del Diario Oficial, expandir este archivo con:
- Ámbito y definiciones artículo por artículo
- Artículos detallados sobre métodos de contratación (Título II)
- Artículos sobre gobernanza de la DINAC
- Artículos sobre sanciones e inhabilitaciones
- Reglas de inscripción en el RUPES

Recuperación sugerida: https://imprentanacional.gob.sv/servicios/archivo-digital-del-diario-oficial/, buscar D.O. del 2 de marzo de 2023.

## Formato de cita para hallazgos

```json
{
  "law_id": "ley-compras-publicas",
  "section": "RUPES registration",
  "url": "/laws/04-ley-compras-publicas.md#rupes--registro-unico-de-proveedores-del-estado",
  "official_source": "Ley de Compras Públicas, D.O. 02-03-2023, vigente 10-03-2023"
}
```
