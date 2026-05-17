---
law_id: ley-urbanismo-construccion
title: Ley de Urbanismo y Construcción
short_title: Urbanismo y Construcción
decreto: D.L. 232
fecha_emision: 1951-06-04
diario_oficial: "Nº 107, Tomo 151, 11-06-1951"
reformas_count: 5
reformas:
  - "D.L. 2190, 31-08-1956 (D.O. 170, T.172, 12-09-1956)"
  - "D.L. 142, 10-10-1972 (D.O. 195, T.237, 20-10-1972)"
  - "D.L. 708, 13-02-1991 (D.O. 36, T.310, 21-02-1991)"
  - "D.L. 294, 03-03-2016 (D.O. 60, T.411, 04-04-2016)"
  - "D.L. 98, 13-07-2021 (D.O. 138, T.432, 20-07-2021)"
ultima_reforma: "D.L. 98, 13-07-2021"
disposicion_relacionada: "Ley Especial para la Reestructuración Municipal — D.L. 762, 13-06-2023"
reglamento: "D.E. 69, 14-09-1973 (D.O. 179, T.240, 26-09-1973)"
estado: vigente
materia: Urbanismo y construcción — autorizaciones administrativas
source_url: https://www.asamblea.gob.sv/sites/default/files/documents/decretos/CDCC9678-C96C-4E1F-9F32-A832AF6ED4A7.pdf
last_verified: 2026-05-09
relevance_to_casa_segura: critical
covers:
  - autoridad de aprobación de urbanizaciones, parcelaciones y construcción (Ministerio de Vivienda + municipalidades)
  - requisitos técnicos para la aprobación de proyectos (parques, escuelas, servicios, materiales)
  - obligación de utilizar arquitectos/ingenieros colegiados
  - obligación de dar aviso al iniciar las obras
  - plazo de vigencia de las aprobaciones (1 año)
  - potestades municipales de ejecución (suspensión, demolición, multas)
  - recurso de reconsideración ante el Ministerio de Vivienda
---

# Ley de Urbanismo y Construcción

## Resumen en lenguaje sencillo

Esta es la **ley fundacional para cualquier proyecto de urbanización, parcelación o construcción en El Salvador**. De origen en 1951, con cinco reformas (la más reciente en 2021), establece que:

1. El **Ministerio de Vivienda** fija la política nacional y aprueba los proyectos cuando las municipalidades no cuentan con sus propios planes de desarrollo.
2. Todo proyecto de urbanización o construcción debe ser **aprobado antes de su ejecución** — por el Ministerio de Vivienda, la municipalidad correspondiente, o ambos.
3. Los proyectos deben ser **diseñados y construidos por arquitectos o ingenieros civiles colegiados** inscritos en el Registro Nacional de Arquitectos, Ingenieros, Proyectistas y Constructores.
4. Las aprobaciones **tienen vigencia de solo un año** — las aprobaciones viejas no se trasladan.
5. El incumplimiento detona **suspensión municipal, demolición forzosa y multas** del 25% (Art. 5) o 10% (Art. 9) del valor del terreno.

Para Casa Segura, esta es la ley a la que *se refiere el número de permiso del rótulo del proyecto*. Cada "OPAMSS-2024-XXXX" o "Aprobación Vivienda XXXX" en el rótulo de un proyecto es una instancia de una aprobación bajo esta ley (o bajo la autoridad municipal equivalente que opera bajo ella).

## Aplicación a Casa Segura

Esta es **la ley más importante para el Flow 1 de todo el corpus**. Es la base legal de cada verificación relacionada con permisos que ejecuta el flujo de legitimidad del proyecto.

Hallazgos que el motor de veredictos debe fundamentar aquí:

- **`permit_required`** (proyecto anunciando ventas sin ningún permiso visible) → arts. 1, 2, 5
- **`permit_authority_unclear`** (proyecto muestra un "permiso" de una autoridad no reconocida) → art. 1
- **`permit_format_invalid`** (la verificación regex de Casa Segura falla) → art. 1, art. 2 (el formato específico depende de si fue emitido por el Ministerio de Vivienda o por la municipalidad)
- **`permit_expired`** (permiso de más de 1 año sin construcción iniciada) → art. 6
- **`permit_pre_1951`** (imposiblemente antiguo o pre-ley) → art. 7
- **`developer_not_licensed_architect`** (proyecto no diseñado/construido por profesional colegiado) → arts. 4, 8
- **`construction_not_supervised_by_registered_professional`** → art. 8
- **`industrial_construction_no_safety_clearance`** (edificación de fábrica/taller sin aprobación de Previsión Social) → art. 8 último párrafo
- **`urbanization_without_park_reservation`** (parcelación anunciada que afirma más lotes de los que el 90% del área útil permitiría) → art. 2(e)
- **`urbanization_without_school_reservation`** → art. 2(g)
- **`urbanization_without_water_drainage_resolution`** → art. 2(h)
- **`developer_did_not_notify_start_of_works`** (no se presentó aviso dentro de los 8 días) → art. 5
- **`works_inconsistent_with_approved_plans`** (el proyecto se desvía de los planos aprobados) → art. 5
- **`accessibility_design_missing`** (sin diseño universal de accesibilidad conforme a la Convención sobre los Derechos de las Personas con Discapacidad) → art. 1 (agregado en la reforma de 2016)

## Artículos clave

### Art. 1 — Autoridad y ámbito (CRÍTICO)
El **Ministerio de Vivienda** formula y dirige la política nacional de vivienda y desarrollo urbano. También elabora los planes nacionales y regionales y las disposiciones generales que toda urbanización, parcelación y construcción debe seguir en todo el país.

Los planes locales de desarrollo urbano y rural corresponden a la respectiva **municipalidad**, enmarcados dentro de los planes nacionales/regionales. **Cuando una municipalidad no tiene plan local, se aplican las disposiciones generales del Ministerio.**

Cuando las municipalidades carezcan de sus propios planes y ordenanzas de desarrollo, **todo particular, entidad oficial o autónoma deberá solicitar la aprobación al Ministerio de Vivienda antes que a cualquier otra oficina** para ejecutar cualquier proyecto comprendido en este artículo. **Para los proyectos de interés general contratados o ejecutados por instituciones del Estado en el sistema de vivienda, el Ministerio de Vivienda emite la aprobación.**

El Ministerio y las municipalidades, al elaborar/aprobar/ejecutar planes de desarrollo urbano/rural, deben **verificar el estricto cumplimiento del diseño universal de accesibilidad** según el Art. 9 de la Convención sobre los Derechos de las Personas con Discapacidad (agregado en la reforma de 2016).

Cuando alguna institución del sistema de vivienda del Estado requiera proyectos de urbanización, parcelación o construcción de beneficio general, el Ministro de Vivienda podrá emitir una **declaración de interés social** en beneficio de las familias salvadoreñas a ser atendidas (agregado en 2021).

> **Señal Casa Segura:** si el rótulo de un proyecto no muestra una autoridad de aprobación clara — ni un permiso municipal ni una autorización del Ministerio de Vivienda — marcar como **rojo**. Ningún proyecto puede avanzar legalmente sin él. Citar art. 1.

### Art. 2 — Requisitos de aprobación (CRÍTICO)
Para que el Ministerio de Vivienda otorgue la aprobación, el interesado debe cumplir con:

(a) **Levantamiento topográfico** con curvas de nivel a equidistancia máxima de 1 metro;
(b) **Clase de urbanización** con su respectivo parcelamiento;
(c) **Proyecto de calles** (primarias y secundarias);
(d) **Resolución del problema de conexión** con el resto de la ciudad y sus alrededores;
(e) **Reservar terreno para jardines y parques públicos** equivalente al **10% mínimo del área útil** cuando se ubique dentro de ciudades; o **12.5 m² mínimo por lote** cuando se ubique fuera de centros poblados existentes. La ubicación debe ser adecuada para estos fines.
(f) **Reservar terreno suficiente para la instalación de servicios públicos**, con especificaciones y ubicación a juicio del Ministerio de Vivienda;
(g) **Reservar terreno para escuelas** equivalente a **8 m² por lote** a parcelar o urbanizar. El reglamento establece las excepciones;
(h) **Resolución de factibilidad** de la entidad correspondiente para: agua potable, drenaje completo de aguas lluvias y servidas, alumbrado eléctrico, servicio telefónico — indicando las conexiones con los servicios públicos existentes;
(i) **Especificar la clase de materiales** a emplear para agua, alcantarillado, cordones, cunetas y tratamiento de la superficie de las calles;
(j) **Planos a escalas mínimas**: topográfico y planimétrico ≥ 1:500; planos de "perfiles" ≥ 1:50 vertical y 1:500 horizontal; los complejos grandes necesitan adicionalmente un plano 1:1000.

Para los terrenos referenciados en (e) y (g), los urbanizadores están obligados a realizar las obras — pero pueden **liberarse de esas obligaciones donando irrevocablemente el terreno a la municipalidad** si las obras no se inician y terminan dentro del plazo del reglamento.

Los requisitos de (e), (f), (g) y (h) son exigibles por reglamento cuando la extensión del área y la población proyectada lo ameriten.

> **Señal Casa Segura:** para un proyecto que anuncia N lotes, se puede verificar si las matemáticas de la parcelación dejan suficiente terreno para la reserva del 10% de parque. Si un proyecto en 10,000 m² anuncia lotes que totalizan más de 9,000 m² de área vendible, algo falta. Vale la pena marcarlo.

### Art. 3 — Aprobación de materiales
Los materiales utilizados en las obras de urbanización requieren la aprobación del **laboratorio de ensayo de materiales del Ministerio de Obras Públicas**.

### Art. 4 — Urbanizaciones solo locales rechazadas; requisito profesional (CRÍTICO)
**Las urbanizaciones que consideren únicamente el estudio local** y no incluyan la superficie como parte integrada de la zona metropolitana **no serán aprobadas**. Lo mismo aplica a las urbanizaciones cuyo proyecto y construcción **no sean ejecutados por ingenieros civiles o arquitectos legalmente autorizados** para ejercer en el país.

> **Señal Casa Segura:** si un rótulo o anuncio no menciona el arquitecto o ingeniero responsable (o nombra a alguien que no está en el Registro Nacional), marcar. Citar art. 4. Combinado con el art. 8, esta es una de las señales verificables más fuertes.

### Art. 5 — Obligación de aviso y sanciones (CRÍTICO)
Las personas o instituciones que hayan obtenido aprobación bajo el art. 1 están obligadas a dar **aviso por escrito dentro de los 8 días hábiles** al Ministerio de Vivienda o a la municipalidad correspondiente, para la supervisión técnica, de las fechas en que se iniciarán las obras.

El incumplimiento del aviso: **multa del 25% del valor del terreno** (incluyendo el valor de la construcción si aplica), exigible por las municipalidades conforme a leyes y reglamentos.

Si las obras no se están realizando conforme a los planos y especificaciones aprobados, **se podrá ordenar la suspensión y corrección**, y si ya están hechas, **la demolición a costa del infractor**.

> **Señal Casa Segura:** la multa del 25% es un disuasivo que existe en el papel pero se aplica de forma desigual. El producto puede señalar la obligación, pero el usuario debe saber que la aplicación puede requerir presionar a la municipalidad.

### Art. 6 — Vigencia de un año (CRÍTICO)
La autorización para ejecutar una parcelación o urbanización con base en proyectos aprobados tiene una **vigencia de un año** a partir del día siguiente de la aprobación.

Si las obras no han iniciado en ese año, **se debe obtener una nueva aprobación de los planos correspondientes** del Ministerio de Vivienda o de la municipalidad.

> **Señal Casa Segura:** si el número de permiso del rótulo sugiere que fue emitido hace más de un año y no hay evidencia de obra continua, marcar como **amarillo** con cita del art. 6. El comprador debe pedir la renovación.

### Art. 7 — Las aprobaciones anteriores a 1951 caducan
Las aprobaciones otorgadas **antes de la entrada en vigencia de esta ley** (junio de 1951) para urbanizaciones aún no iniciadas **son nulas y carecen de efecto**.

> **Señal Casa Segura:** si un rótulo cita una aprobación anterior a 1951 como legitimidad, eso es una bandera roja. Casi con seguridad es una fabricación o un documento profundamente desactualizado.

### Art. 8 — La construcción debe estar a cargo de profesionales colegiados (CRÍTICO)
Todo proyecto de construcción de edificios, **ya sea por particulares o por entidades oficiales, edilicias o autónomas**, debe ser:

- **Elaborado por un arquitecto o ingeniero civil legalmente autorizado**, inscrito en el **Registro Nacional de Arquitectos, Ingenieros, Proyectistas y Constructores**;
- **Firmado y sellado** por ellos en los planos presentados;
- **Ejecutado y supervisado** por un arquitecto o ingeniero civil legalmente autorizado e inscrito.

**Excepciones** (sin profesional requerido):
- Construcciones de bahareque, adobe
- Construcciones de ladrillo y de sistema mixto de un solo piso con techo de estructura de madera
- Construcciones de madera de un solo piso

Estas excepciones pueden ser diseñadas y construidas por **proyectistas y constructores de reconocida capacidad**, también inscritos en el Registro, siguiendo las normas del Ministerio de Vivienda.

En todos los casos, al construir fábricas, talleres u otras instalaciones industriales/comerciales, **no se otorgará la aprobación sin el dictamen favorable previo del Departamento Nacional de Previsión Social** sobre seguridad e higiene del trabajo.

> **Señal Casa Segura:** verificar al arquitecto/ingeniero responsable es una de las verificaciones más concretas que el producto puede hacer. El Registro Nacional debería poder consultarse. Citar art. 8.

### Art. 9 — Potestad municipal de ejecución y demolición
**Las alcaldías municipales y las autoridades del Ministerio de Obras Públicas están obligadas a hacer cumplir esta ley**. Deben, según corresponda, **suspender o demoler** las obras que se realicen en contravención a las leyes y reglamentos sobre la materia, **a costa del infractor** — sin perjuicio de que las alcaldías municipales impongan **multas equivalentes al 10% del valor del terreno** por las infracciones.

Cuando el Ministerio de Vivienda o las municipalidades soliciten la ayuda de la fuerza pública para hacer cumplir resoluciones o prevenir infracciones, dichas fuerzas deben proporcionarla de inmediato. Otras instituciones gubernamentales, edilicias o autónomas involucradas en el desarrollo urbano también deben colaborar.

> **Señal Casa Segura:** estas potestades de ejecución existen. El comprador debe saber que la municipalidad tiene autoridad para demoler construcciones no autorizadas a costa del urbanizador — una protección concreta si el urbanizador opera sin permisos.

### Art. 10 — Recurso de reconsideración
Si se deniega la aprobación de un proyecto de urbanización, parcelación o construcción, los interesados pueden interponer un **recurso de reconsideración** dentro de los **10 días** siguientes a la notificación, ante el **Ministerio de Vivienda**, el cual debe resolver y notificar dentro de **un mes** (agregado en la reforma de 2021).

### Art. 10 Bis — Reglamento
El Presidente de la República emite los reglamentos para facilitar la aplicación de esta ley (agregado en la reforma de 1991). El reglamento de aplicación vigente es el D.E. 69 del 14 de septiembre de 1973.

### Art. 11 — Cláusula derogatoria
Quedan derogadas todas las disposiciones que se opongan a esta ley.

### Art. 12 — Vigencia
El decreto entró en vigencia 8 días después de su publicación en el Diario Oficial (junio de 1951).

## Cronología de reformas

| # | Decreto | Fecha | Qué cambió |
|---|---|---|---|
| 1 | D.L. 2190 | 31-08-1956 | Actualizó el Art. 8 (requisitos profesionales) |
| 2 | D.L. 142 | 10-10-1972 | Actualizó el Art. 9 (ejecución) |
| 3 | D.L. 708 | 13-02-1991 | Reforma mayor: la mayoría de artículos modernizados; agregó el Art. 10 Bis (reglamentos) |
| 4 | D.L. 294 | 03-03-2016 | Agregó el requisito de accesibilidad universal al Art. 1 |
| 5 | D.L. 98 | 13-07-2021 | Actualizó el Art. 1 con la declaración de interés social; actualizó el Art. 10 (reconsideración) |

La reforma de 1991 es la más importante — modernizó la mayoría de los requisitos técnicos y le dio al Ministerio de Vivienda el rol central que tiene hoy.

## Patrones prácticos de fraude a vigilar

| Patrón | Artículo |
|---|---|
| El rótulo no muestra ningún número de permiso | art. 1, 2 |
| El número de permiso no coincide con el formato del Ministerio de Vivienda o municipal | art. 1 |
| El proyecto anuncia construcción pero no se ve el nombre del arquitecto/ingeniero | art. 4, 8 |
| El arquitecto/ingeniero nombrado no está en el Registro Nacional | art. 8 |
| Las fechas del permiso sugieren más de 1 año de antigüedad sin historial de obra | art. 6 |
| La parcelación anuncia un conteo de lotes incompatible con la reserva del 10% de parque | art. 2(e) |
| Proyecto industrial/comercial sin referencia a aval de Previsión Social | art. 8 final |
| El proyecto se desvía visiblemente de los planos anunciados | art. 5 |
| Se cita una aprobación anterior a 1951 | art. 7 |

## Qué es realmente el número de permiso en un rótulo

Los números de permiso que el modelo de visión de Casa Segura extrae de los rótulos suelen ser uno de:

- **OPAMSS-YYYY-XXXX** — emitido por la Oficina de Planificación del Área Metropolitana de San Salvador (la oficina metropolitana de planificación), bajo autoridad municipal para la zona metropolitana del AMSS, operando bajo el marco de esta ley.
- **Permisos municipales** — formatos variables según la municipalidad (p. ej. Santa Tecla, Antiguo Cuscatlán) para proyectos en sus jurisdicciones.
- **Aprobaciones del Ministerio de Vivienda** — para proyectos en municipalidades sin sus propios planes, o para proyectos de interés general.

La verificación regex del formato de permiso de Casa Segura se fundamenta en la estructura de este artículo. Para cada autoridad conocida, el producto puede validar el formato y (cuando el registro esté expuesto) cruzar la emisión.

## Referencias cruzadas

- **Lotificaciones**: cuando se complete, la Ley Especial para la Regularización de Lotificaciones y Parcelaciones para Uso Habitacional (actualmente el archivo aún pendiente `06-pendiente-...`) rige el régimen de regularización para parcelaciones que no cumplieron con los requisitos de esta ley antes de septiembre de 2012. La mayoría del fraude relacionado con lotificaciones se ubica en la intersección de esta ley (¿alguna vez se emitió un permiso?) y aquella (¿se está regularizando el proyecto?).
- **FSV**: los proyectos financiados por el gobierno también pasan por las puertas de permisos de esta ley.
- **Contratos IVU**: ver `02-ley-ivu.md`.
- **Compras Públicas (LCP)**: cuando el proyecto es una urbanización financiada por el Estado, el proceso de adquisición se rige por `04-ley-compras-publicas.md`, pero la aprobación técnica sigue bajo esta ley.
- **Reglamento de aplicación**: D.E. 69 de 1973 (Reglamento a la Ley de Urbanismo y Construcción) — define los umbrales técnicos, excepciones y procedimientos referenciados abstractamente en esta ley.

## Formato de cita para hallazgos

```json
{
  "law_id": "ley-urbanismo-construccion",
  "article": "Art. 8",
  "anchor": "art-8",
  "url": "/laws/07-ley-urbanismo-construccion.md#art-8",
  "official_source": "D.L. 232 de 04-06-1951, D.O. Nº 107, T.151, 11-06-1951"
}
```
