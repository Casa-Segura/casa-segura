---
law_id: ley-fsv
title: Ley del Fondo Social para la Vivienda
short_title: FSV
decreto: D.L. 328
fecha_emision: 1973-05-17
diario_oficial: "Nº 104, Tomo 239, 06-06-1973"
reformas_count: 12
ultima_reforma: "D.L. 46, 03-06-2021 (D.O. 107, T.431, 05-06-2021)"
estado: vigente
materia: Vivienda — seguridad social
source_url: https://www.jurisprudencia.gob.sv/DocumentosBoveda/D/2/1970-1979/1973/06/889B6.PDF
last_verified: 2026-05-09
relevance_to_casa_segura: high
covers:
  - creación y estructura del Fondo Social para la Vivienda (FSV)
  - aportaciones obligatorias de empleador/trabajador
  - operaciones de crédito financiadas por el FSV para vivienda del trabajador
  - reglas procesales y registrales especiales para contratos del FSV
  - exenciones tributarias para compras financiadas por el FSV
---

# Ley del Fondo Social para la Vivienda

## Resumen en lenguaje sencillo

Crea el **Fondo Social para la Vivienda (FSV)** como una institución autónoma de crédito de derecho público cuyo propósito es ayudar a los trabajadores a obtener una vivienda cómoda, higiénica y segura. Se financia con aportaciones obligatorias del empleador (5%) y del trabajador (0.5%) sobre la planilla, más subsidios estatales y operaciones.

El FSV no construye vivienda directamente en el caso típico — **financia** la compra, construcción, reparación o refinanciamiento de vivienda para trabajadores, ya sea directamente o a través de instituciones intermediarias calificadas por el Ministerio de Vivienda. También tiene facultades especiales: las certificaciones del Director Ejecutivo son títulos ejecutivos para el cobro, sus créditos gozan de privilegio de primera clase, y las compraventas financiadas por el FSV bajo cierto umbral están exentas del impuesto de transferencia de bienes raíces.

## Aplicación a Casa Segura

Esta ley importa para proyectos que:
- Aleguen estar financiados o afiliados al FSV
- Ofrezcan vivienda "elegible para FSV" como argumento de venta
- Usen al FSV como intermediario o garante

Ángulos clave para detección de fraude:

1. **Afiliación fantasma al FSV.** Un desarrollador afirma tener financiamiento del FSV que en realidad no tiene. Verificable: el FSV publica los proyectos que apoya.
2. **Fraude de exención tributaria.** Alguien alega que su venta es financiada por el FSV (y por tanto exenta del impuesto de transferencia bajo el art. 68) cuando no lo es.
3. **Fraude en aportaciones del trabajador.** Un empleador cobra a los trabajadores pero no deposita efectivamente las aportaciones al FSV.
4. **Manipulación de la anotación preventiva de la hipoteca.** La anotación preventiva del FSV (art. 55) crea prioridad retroactiva — los esquemas de fraude intentan colar transacciones entre la adjudicación y la inscripción.

Findings que el motor de veredicto debería fundamentar aquí:

- **`fsv_affiliation_claim_unverified`** → arts. 5, 7
- **`fsv_intermediary_required_for_third_party`** → art. 7 párrafo final
- **`fsv_tax_exemption_misapplied`** → art. 68
- **`fsv_first_class_privilege_misrepresented`** → art. 71(b)
- **`fsv_anotacion_preventiva_required`** → arts. 55–57

## Capítulo I — Creación, objeto, naturaleza

### Art. 1 — Creación
Se crea el FSV como un programa de desarrollo de la seguridad social.

### Art. 2 — Personalidad jurídica, domicilio
El FSV es una **institución autónoma de crédito de derecho público** con personalidad jurídica, sin más limitaciones que las de esta ley, con sede en San Salvador y sucursales en todo el país.

### Art. 3 — Objeto
Contribuir a la solución del problema habitacional de los trabajadores, proporcionando los medios adecuados para adquirir viviendas cómodas, higiénicas y seguras.

### Art. 4 — Ámbito de aplicación
Se aplica a todos los empleadores y trabajadores sin importar el tipo de relación o la forma de remuneración. El reglamento especifica el tiempo y la forma de incorporación. La cobertura puede extenderse a trabajadores sin empleador.

### Art. 5 — Relación con el gobierno
El Fondo se relaciona con el gobierno a través del **Ministerio de Vivienda**.

## Capítulo II — Recursos y operaciones

### Art. 6 — Recursos
- (a) Subsidio estatal inicial de ¢25,000,000 pagados en 5 cuotas anuales;
- (b) Aportaciones del **5% (empleador) y 0.5% (trabajador)** sobre la planilla, dentro de los límites que fije el reglamento;
- (c) Subsidios estatales adicionales;
- (d) Utilidades netas de las operaciones;
- (e) Otros ingresos.

### Art. 7 — Uso de los recursos (CRÍTICO)
Los recursos del FSV se destinan a:
- (a) Créditos a **trabajadores** para: (I) adquisición de vivienda; (II) construcción, reparación, ampliación, mejora; (III) refinanciamiento de deudas anteriores de estos tipos;
- (b) Créditos a **empleadores** para construir vivienda para trabajadores;
- (c) Créditos a **cooperativas** para financiamiento de muebles/enseres del hogar;
- (d) Adquisición de bienes muebles/inmuebles necesarios para los fines del FSV;
- (e) Financiamiento de empresas de materiales de construcción;
- (f) Construcción o financiamiento de complejos habitacionales;
- (g) Gastos de operación.

Los créditos se otorgan **directamente o a través de instituciones intermediarias** calificadas por el Ministerio de Vivienda.

> **Señal Casa Segura:** si un desarrollador alega financiamiento del FSV pero no es una institución calificada por el FSV ni un tipo de beneficiario trabajador/empleador listado en (a)–(c), esa afirmación es sospechosa. Citar art. 7.

### Art. 8 — Operaciones que el FSV puede realizar
- (a) Comprar, mantener y vender títulos de crédito y valores de fácil realización;
- (b) Comprar y vender acciones, valores de fácil realización, inmuebles y otros activos compatibles;
- (c) Emitir y colocar bonos y valores conforme a la ley;
- (d) Negociar por cuenta de terceros valores emitidos por el Estado, organismos autónomos o empresas del sector construcción;
- (e) Otorgar garantías;
- (f) Descontar documentos y obtener financiamiento del BCR y otras instituciones;
- (g) Obtener financiamiento interno/externo;
- (h) Administrar (sin fines de lucro) fondos que el Estado o terceros le entreguen para construir vivienda de reemplazo para tugurios;
- (i) Otras operaciones compatibles.

### Art. 8-A — Transferencia de títulos de crédito
Los títulos de crédito son transferibles por entrega + endoso escrito firmado ante notario, registrado en el Registro de Hipotecas al margen de la inscripción hipotecaria correspondiente.

## Capítulo III — Organización y administración

### Arts. 9–40 (resumen)
**Órganos:** Asamblea de Gobernadores, Junta Directiva, Dirección Ejecutiva, Gerencia, Consejo de Vigilancia.

**Asamblea de Gobernadores** (art. 10): Máxima autoridad. Compuesta por los titulares de Vivienda, Obras Públicas/Transporte, Trabajo, Hacienda, Economía, más 2 gobernadores del sector empleador y 2 del sector laboral (última reforma 2021).

**Junta Directiva** (arts. 17–26): 5 miembros — 1 nominado por el Presidente de la República (quien es Presidente de la Junta y Director Ejecutivo), 4 nominados por la Asamblea (1 empleador, 1 laboral, 2 del sector público).

**Director Ejecutivo** (arts. 27–30): Ejecuta las resoluciones de la Junta, tiene la representación legal, firma los contratos operativos.

**Consejo de Vigilancia** (arts. 34–40): 4 miembros — 1 empleador, 1 laboral, 2 del Ejecutivo (Vivienda, Trabajo). Supervisa la correcta aplicación de la ley, tiene acceso pleno a la documentación.

### Art. 16-A — Causales de remoción (añadido en 2021)
Los gobernadores solo pueden ser removidos por su autoridad nominadora, con causa motivada, por: (a) violación de los requisitos de nominación; (b) incumplimiento legal en funciones; (c) condena por delito doloso; (d) pérdida de los derechos de ciudadanía; (e) conducta contraria a la moral; (f) conflicto de intereses; (g) tráfico de influencias; (h) pérdida de la representatividad sectorial.

## Capítulo IV — Registro, afiliación, aportaciones

### Art. 41 — Obligación de registro
El FSV mantiene un registro de empleadores y trabajadores cotizantes. El empleador debe inscribirse a sí mismo y a sus trabajadores conforme al reglamento.

### Art. 42 — Prohibición de deducción
Las aportaciones del empleador no pueden ser deducidas del salario del trabajador. Violación: multa según el art. 54 y restitución.

> **Señal Casa Segura:** si un trabajador alega que su empleador le está deduciendo la porción *del empleador* (5%) de su salario, eso es una violación clara. Citar art. 42.

### Art. 43 — Retención y entrega
El empleador retiene la aportación del trabajador y cualquier cuota del crédito del FSV del salario y es **personalmente responsable** de entregarlo al FSV. Los pagos tardíos generan un recargo del 1% mensual.

### Art. 44 — Inspección
El FSV puede realizar inspecciones en los lugares de trabajo directamente o a través del Ministerio de Trabajo. Los informes y actas del inspector se presumen exactos salvo prueba en contrario.

## Capítulo V — Depósitos y devoluciones

### Art. 45 — Depósitos y exención tributaria
Las aportaciones del trabajador y el empleador son recibidas por el FSV como **depósitos a favor del trabajador**, exentos de todo impuesto.

### Art. 46 — Devoluciones
Procedimientos de devolución conforme al reglamento, tras el período actuarial de espera o en casos de jubilación, muerte, incapacidad permanente total.

### Art. 47 — Derecho a la devolución
Los trabajadores en jubilación o incapacidad permanente total tienen derecho a devolución. En caso de muerte, la devolución va a los beneficiarios o herederos.

### Art. 48 — Compensación
En cualquier devolución, la deuda previa con el FSV se salda primero (aunque no esté aún vencida) contra el depósito.

## Capítulo VI — Conflictos y sanciones

### Art. 49 — Competencia
Los conflictos entre cotizantes/FSV/beneficiarios son conocidos por el Director Ejecutivo, quien designa un delegado que actúa como arbitrador.

### Art. 50 — Recurso de revisión
Dentro de los 3 días de notificada, las partes pueden solicitar revisión.

### Art. 51 — Comisión de revisión
La Junta Directiva nombra una comisión de 3 miembros de su seno para conocer las revisiones.

### Art. 52 — Plazo de resolución
La comisión tiene 15 días para resolver. Su decisión es definitiva.

### Art. 53 — Otras acciones preservadas
No obstante lo anterior, las partes conservan el derecho a la acción judicial ordinaria.

### Art. 54 — Sanciones
Las sanciones son **multas** de ¢50–5,000, fijadas por el Director Ejecutivo según gravedad y capacidad económica.

## Capítulo VII — Formalidades del crédito (añadido por la reforma 3)

### Art. 55 — Anotación preventiva (CRÍTICO)
Una vez que la Junta autoriza un crédito con garantía hipotecaria, se emite una certificación con extracto. Contiene: fecha del acto, nombre del beneficiario, monto del crédito, plazo y referencias a las inscripciones vigentes en el Registro de la Propiedad de los inmuebles ofrecidos — sin necesidad de descripción de los inmuebles.

La certificación, firmada por el Director Ejecutivo o el Gerente, se **anota preventivamente** en el Registro de la Propiedad Raíz e Hipotecas. **No se cobra derecho alguno por la anotación.**

Los efectos de la hipoteca, una vez inscrito el contrato, **se retrotraen a la fecha de la anotación preventiva**.

> **Señal Casa Segura:** esta prioridad retroactiva es crítica. Si una venta ocurre entre la anotación preventiva del FSV y la inscripción definitiva, el título del comprador queda subordinado al gravamen del FSV. Verificar en el Registro las anotaciones del FSV es una verificación clave. Citar art. 55.

### Art. 56 — Contrato subsiguiente
Tras la anotación, el contrato se firma en forma legal salvo que una circunstancia desfavorable lleve a la Junta a revocar.

### Art. 57 — Cesación de la anotación
La anotación cesa por:
1. Inscripción definitiva del crédito;
2. Notificación escrita del FSV al Registro para cancelarla;
3. Transcurso de 90 días desde la presentación conforme al art. 55.

### Art. 58 — Restricciones de gravamen
Sin el consentimiento del FSV, no podrá inscribirse ninguna escritura que venda, enajene o grave cualquier inmueble hipotecado al FSV.

### Art. 59 — Inembargabilidad
Una vez que el FSV otorga el préstamo, los bienes gravados no son embargables por créditos personales anteriores o posteriores a la constitución del gravamen. La protección corre desde la fecha de la anotación preventiva para la hipoteca, y desde la fecha de la inscripción para la prenda.

### Art. 60 — Terminación de derechos inferiores por embargo
Si el embargo del FSV se da por incumplimiento de la deuda, el embargo termina con cualquier arrendamiento, usufructo, anticresis u otro derecho posterior a la hipoteca, salvo que se haya otorgado con consentimiento del FSV.

### Art. 61 — Caducidad (aceleración)
El plazo convenido caduca (es decir, el crédito se vuelve inmediatamente exigible) cuando:
- (a) El deudor no notifica dentro del mes los deterioros que afecten el valor, la posesión o el título del inmueble;
- (b) El deudor ocultó cualquier causa de resolución, rescisión o gravamen oculto;
- (c) El deudor omite cualquier cuota;
- (d) El deudor enajena los bienes gravados o constituye hipotecas, usufructos, etc., sin consentimiento del FSV (excepto crédito refaccionario);
- (e) El deudor incumple cualquier otra deuda con el FSV;
- (f) Los bienes se deterioran de manera que ya no cubren la garantía (el FSV debe aceptar una garantía alternativa suficiente);
- (g) Los fondos se desvían a fines distintos de los acordados;
- (h) Otros casos conforme a las leyes o contratos aplicables.

## Capítulo VIII — Disposiciones generales

### Art. 62 — Prescripción de saldos inactivos
Los saldos inactivos a cargo del FSV prescriben conforme al art. 204 de la Ley de Instituciones de Crédito y Organizaciones Auxiliares — pero al cumplirse, el saldo revierte al FSV (no al Estado).

### Art. 65 — Leyes inaplicables
La Ley de Tesorería, la Ley Orgánica de Presupuestos, la Ley de Suministros y demás disposiciones sobre fondos públicos y personal **no se aplican** a la gestión del FSV. Esta ley prevalece sobre cualquier otra.

### Art. 66 — Fiscalización de la Corte de Cuentas
La Corte de Cuentas fiscaliza la ejecución presupuestaria a través de un delegado-auditor. La auditoría es *a posteriori*, enfocada en la legalidad.

### Art. 68 — Exención tributaria en compraventas financiadas por el FSV (CRÍTICO)
Las compraventas de inmuebles **financiadas por el FSV** y los préstamos otorgados por el FSV, **cuando la operación no exceda de ¢100,000**, no generan ningún impuesto fiscal. Las escrituras públicas para estos actos se extienden en papel simple, y la inscripción registral está exenta de todo impuesto o derecho.

La interpretación auténtica de 1976 (D.L. 180) aclara: esta exención cubre:
- Ventas entre particulares y trabajadores cotizantes, financiadas por el FSV;
- Ventas entre particulares y el FSV destinadas a la adjudicación a trabajadores cotizantes;
- Ventas entre particulares y el FSV destinadas a la construcción por el FSV para adjudicación a trabajadores cotizantes.

> **Señal Casa Segura:** un vendedor fraudulento puede alegar que la "exención del FSV" aplica para evadir el impuesto de transferencia de bienes raíces (3% sobre transacciones mayores a $28,571.43 conforme a la Ley del Impuesto sobre Transferencia de Bienes Raíces). Verificar la cadena de financiamiento del FSV. Citar art. 68.

### Art. 69 — Exención tributaria general para el FSV
El FSV está exento de todos los impuestos fiscales cuando los adeude, y de los impuestos de sucesiones/donaciones sobre las recepciones al FSV.

### Art. 70 — Exención de bonos
Los bonos emitidos por el FSV y sus intereses están exentos de todos los impuestos fiscales, incluyendo renta, vialidad, papel sellado, sucesiones y donaciones.

### Art. 71 — Procedimientos ejecutivos especiales (CRÍTICO)
Los juicios ejecutivos del FSV (o sus intermediarios) siguen el derecho común con estas modificaciones:
- (a) Las certificaciones del Director Ejecutivo de los montos adeudados son **títulos ejecutivos**;
- (b) Los créditos del FSV son de **primera clase** con preferencia absoluta excepto frente a los créditos laborales/sociales del deudor;
- (c) Las notificaciones pueden hacerse directamente al deudor o al apoderado que el deudor debe constituir en la escritura fundacional;
- (d) Período probatorio: 3 días. Únicas excepciones admisibles: pago efectivo, error en la liquidación;
- (e) **No hay apelación** contra el decreto de embargo, la sentencia de remate u otras resoluciones;
- (f) El acreedor (FSV) es depositario de los bienes embargados sin fianza;
- (g) Las tercerías solo son admisibles si se basan en un título anterior a la hipoteca del FSV;
- (h) No puede acumularse ningún otro juicio a la ejecución.

Tras el pago total con el remate, se notifica a los demás acreedores para perseguir cualquier remanente.

### Art. 72 — Valor auténtico de las certificaciones del FSV
Las transcripciones, extractos y certificaciones de los libros y registros del FSV, firmados por el Director Ejecutivo o el Gerente con el sello del FSV, tienen valor de documentos auténticos.

## Patrones prácticos de fraude a vigilar

| Patrón | Artículo |
|---|---|
| Desarrollador alega financiamiento del FSV sin ser una institución calificada ni tener un beneficiario trabajador/empleador | art. 7 |
| Venta alega exención tributaria del FSV sin cadena de crédito FSV verificable | art. 68 |
| Inmueble tiene anotación preventiva del FSV pero el vendedor no la divulga | art. 55, 58 |
| Vendedor alega "la hipoteca del FSV se cancelará al firmar" sin consentimiento escrito del FSV | art. 58, 61(d) |
| El empleador cobra al trabajador el 5% de la aportación patronal | art. 42 |
| Precio de venta dentro del rango elegible para FSV pero el vendedor se niega al proceso del FSV | indicio de fraude |

## Referencias cruzadas

- **Impuesto de transferencia de bienes raíces**: Ley del Impuesto sobre Transferencia de Bienes Raíces (3% sobre $28,571.43 salvo exención del FSV).
- **Vivienda construida por el gobierno**: Ley sobre Contratos del IVU (`02-ley-ivu.md`) para contratos específicos del IVU.
- **Sistema bancario público**: Ley de Bancos y supervisión de la SSF.
- **Ejecución hipotecaria**: derecho procesal común + este régimen especial.

## Formato de citación para findings

```json
{
  "law_id": "ley-fsv",
  "article": "Art. 55",
  "anchor": "art-55",
  "url": "/laws/03-ley-fsv.md#art-55",
  "official_source": "D.L. 328 de 17-05-1973, D.O. Nº 104, T.239, 06-06-1973"
}
```
