# De la Orden de Compra al Embarque — Propuesta v2 (CEDIS)

> **Qué cambió respecto a la v1:** la v1 subestimaba el CAPEX en ~2.4x, inventaba el beneficio de flete (lo subestimaba ~2x), tenía el cuello de botella real sin diagnosticar, un diseño de Wi-Fi que deja al operador en sombra, y omitía el requisito legal que puede frenar la operación (Carta Porte 3.1). La v2 corrige todo eso y **el payback apenas se mueve de 4.2 a 5.4 meses** — porque el caso de negocio verdadero era más grande que el que la v1 presumía.

---

## PARTE A — Auditoría de la propuesta v1

### A.1 Hallazgos críticos (los que un jurado detecta en 5 minutos)

| # | Hallazgo | Severidad | Dónde |
|:--|:---|:---|:---|
| 1 | **El cuello de botella no es el software: son los andenes de recibo.** La v1 presenta "87.5% de ocupación" como dato tranquilizador. Es una alerta roja. | Crítica | §2 Momento 1 |
| 2 | **La regla del ≥90% genera inanición en las sucursales de bajo volumen.** Sin regla de excepción, una sucursal chica espera 4–7 días su mercancía. | Crítica | §2 Momento 4 |
| 3 | **No hay operación sin red.** La validación "en tiempo real" contra un servidor cloud convierte al Wi-Fi y al ISP en punto único de falla. Un CEDIS no puede parar porque se cayó internet. | Crítica | §2 Momento 3 / §3 |
| 4 | **Falta Complemento Carta Porte 3.1** (obligatorio desde jul-2024 para autotransporte). Un embarque a sucursal sin él es riesgo fiscal y de detención en carretera. | Crítica | Ausente |
| 5 | **No hay flujo de faltantes.** El reto dice literalmente que "los faltantes y excedentes se detectan tarde". La v1 resuelve excedentes (rechazo) y **deja el faltante sin tratamiento**. | Crítica | §2 Momento 3 |
| 6 | **No hay prototipo.** El entregable exige "un prototipo funcional". La v1 dice "a continuación tienes un prototipo" y no hay nada. | Crítica | §2 |

### A.2 Errores de cálculo verificables

**Capacidad de andén — el número está mal leído**

```
v1:  4 andenes x 10 h = 40 horas-andén  ->  35 citas = 87.5% ocupación  = "cómodo"

Real: la descarga toma MÍNIMO 1 h, y entre citas hay maniobra
      (entrada, posicionamiento, retiro) de ~15 min.
      Capacidad = 4 x 10 h / 1.25 h = 32 citas/día
      Demanda   = 35 citas/día
      DÉFICIT   = 3 citas/día  ->  el andén está SOBREVENDIDO, no al 87.5%
```

Y eso asumiendo que *toda* descarga dura el mínimo. Con una media realista de 1.3 h, la demanda sube a 45.5 horas-andén contra 40 disponibles.

**Capacidad del Tortón — dos cifras inventadas**

| Dato | v1 dice | Correcto | Cómo se obtiene |
|:---|:---|:---|:---|
| Peso | ~14,000 kg | **12,000 kg** | 12 tarimas x 1,000 kg |
| Volumen | ~45 m³ | **28.6 m³** | 12 x (1.12 x 1.15 x 1.85) |

Con 45 m³ en el denominador, el semáforo del 90% nunca se dispara por volumen y **la regla queda desactivada de facto**. El límite real es *posiciones de tarima* (11 de 12), no peso ni volumen.

**Lectura invertida de la regla de tarima**

El reto dice *"capacidad **mínima** 1,000 kg"* (resistencia de la tarima). La v1 lo transcribe como *"capacidad **máxima** 1,000 kg"*. Operativamente el tope de 1,000 kg está bien, pero es un dato del reto citado al revés.

**El ahorro de flete no está derivado de nada**

La v1 afirma "reducir al menos 2 fletes diarios" sin ninguna aritmética detrás. Si hoy salen 20 unidades a medio llenar y se exige ≥90%, el ahorro es mucho mayor que 2 — **o no existe en absoluto**. Depende enteramente del llenado actual, que nadie midió. Se resuelve en §B.6.

**La aritmética que sí estaba bien** (para que no se toque): 145,600 + 18,000 + 22,000 = 185,600 ✓ · 185,600 − 11,270 = 174,330 ✓ · 728,000 / 174,330 = 4.18 meses ✓ · ROI = (2,091,960 − 728,000)/728,000 = 187% ✓

### A.3 Huecos de CAPEX (por esto la cotización pierde credibilidad)

| Omitido en la v1 | Impacto estimado | Por qué es indispensable |
|:---|---:|:---|
| Site survey RF predictivo + validación post-instalación | $55,000 | Sin esto, "12 APs" es un número inventado |
| Licenciamiento / controladora Wi-Fi | $48,000 | Cisco 9120AXI exige DNA o WLC; Aruba AP-515 exige Central. La tabla no los incluye |
| UPS y rack de comunicaciones | $34,000 | Un apagón detiene el CEDIS completo |
| Impresora térmica de etiquetas en CEDIS | $56,000 | Siempre hay etiqueta mojada, rota o ilegible. Sin reimpresión controlada, el bulto se queda sin identidad |
| Terminales montadas en montacargas (VMT) | $76,000 | El acomodo a nivel 4 (6 m) no se hace con handheld en la mano |
| Capacitación y gestión del cambio | $95,000 | 35 proveedores + 32 sucursales + cuadrilla. Es el riesgo #1 del proyecto |
| Integración CFDI/UUID + Carta Porte | $85,000 | Requisito legal |
| Servidor edge local | $42,000 | Para que la operación sobreviva sin internet |
| Contingencia (12%) | $187,000 | Ninguna cotización seria va sin ella |

También: el "lote" de $68,000 por *switch + cableado Cat6A industrial con tiradas a 9 m* es insuficiente. Solo la canalización y el cableado de 16 tiradas a esa altura en nave industrial ronda los $78,000.

### A.4 Errores de ingeniería de red

1. **El criterio de dimensionamiento es de oficina, no de nave.** "350–400 m² por AP" aplica a espacio abierto. Con racks metálicos de 6 m, los pasillos se comportan como guías de onda y el criterio correcto es **por pasillo**, no por área. 12 APs omnidireccionales son insuficientes; se requieren **16**, cuatro de ellos con antena direccional.

2. **El montaje a 7 m sobre la coronilla de los racks es exactamente el error clásico.** La v1 lo justifica como "línea de vista por encima del metal" — pero el operador está a 1.2 m del suelo *dentro* del pasillo. Un AP por encima del rack ilumina la parte superior del metal y deja el piso del pasillo en sombra. **Los APs van montados en el pasillo a 5.5–6 m, radiando hacia abajo.**

3. **40 MHz es la decisión equivocada.** Escanear un QR mueve ~2 KB; no se necesita ancho de banda, se necesita **cobertura y roaming**. A 40 MHz solo hay ~12 canales y la v1 termina reutilizando el canal 36 en el fondo de la nave mientras está activo en los andenes. **A 20 MHz hay 24 canales** y la reutilización queda holgada con mejor SNR.

4. **Los canales DFS (52–144) no van en operación crítica.** La v1 asigna DFS a 7 de los 12 APs. Un evento de radar tira el AP y con él la cuadrilla de ese pasillo. Usar **solo no-DFS**: 36, 40, 44, 48, 149, 153, 157, 161, 165.

5. **Falta el criterio de diseño medible.** No basta "−65 dBm". Falta: SNR ≥25 dB, **mínimo 2 APs audibles** en todo punto, y **deshabilitar tasas de datos bajas** (1/2/5.5/11/6/9 Mbps) — sin eso el handheld se queda pegado a un AP lejano y 802.11r/k/v no sirve de nada.

### A.5 Problemas de diseño operativo

- **El rack fijo por sucursal *es* el mal aprovechamiento del espacio.** El reto dice que "el espacio se aprovecha mal" y la v1 responde con 32 posiciones rígidas por sucursal: la sucursal grande desborda y la chica deja 28 posiciones muertas. Falta zona flex de desborde y ubicación dirigida por sistema.
- **Cross-docking aparece como título y nunca se desarrolla.** Es la optimización de mayor retorno de todo el reto y queda en una palabra entre paréntesis.
- **No hay dimensionamiento de personal ni de montacargas.** ~156 tarimas/día de acomodo + 156 de surtido = 312 movimientos en 10 h = 31/h. Un montacarguista rinde 20–25/h: se requieren **2 montacargas simultáneos**, y la v1 compró 2 handhelds para acomodo.
- **El QR no está firmado.** Un QR de texto plano se fotocopia. Sin firma criptográfica, cualquiera fabrica una etiqueta válida.
- **No hay KPIs ni línea base.** Sin baseline medido, el ROI no es defendible ante un comité.
- **La notación LaTeX (`$\text{...}$`, `$\ge$`) no renderiza** fuera de un visor con MathJax. En el PDF del jurado se verá como código roto.

---

## PARTE B — Propuesta v2

### B.1 Tesis

> El problema no es la falta de un sistema. Es que **el andén de recibo está sobrevendido en 3 citas/día** y que **la regla del 90% mata a las sucursales chicas**. Un WMS que no resuelva esas dos cosas solo digitaliza el atasco.

La v2 se sostiene en tres decisiones que la v1 no toma:

1. **Capacidad antes que software** — se recupera capacidad de andén sin comprar un ladrillo.
2. **Flota heterogénea** — el ≥90% se cumple cambiando de unidad, no haciendo esperar a la sucursal.
3. **Edge-first** — la operación no depende de internet.

### B.2 Decisión 1 — Recuperar capacidad de andén con cero inversión

Los andenes de embarque están **ociosos en la mañana**:

```
Embarque: 3 andenes x 10 h = 30 horas-andén
Demanda:  20 embarques x 1 h de carga = 20 h
HOLGURA:  10 horas-andén/día sin usar

Y la holgura está concentrada en la mañana: los embarques salen por
la tarde, cuando ya se acumuló la mercancía recibida ese día.
```

**Andén 5 flex:** un andén de embarque opera como recibo de 8:00 a 13:00.

```
Capacidad de recibo = (4 andenes x 10 h + 1 andén x 5 h) / 1.25 h
                    = 45 / 1.25 = 36 citas/día  >=  35 requeridas
```

El déficit desaparece. Costo: configurar el motor de citas. Esto es lo primero que debe señalar la propuesta, porque es el único hallazgo que **no se puede comprar**.

**Refuerzos del motor de citas:**

- **Duración calculada, no declarada.** La v1 deja que el proveedor estime. El sistema estima con su propio histórico: `t = max(60 min, 12 min + 0.9 min x n_bultos)`, y el proveedor solo puede pedir más tiempo, nunca menos.
- **Score de proveedor** (puntualidad, exactitud de etiquetado, exactitud documental). El score condiciona la **prioridad de reserva**: el proveedor con buen score elige horario primero. Palanca de cumplimiento sin costo.
- **Ventanas diferenciadas.** Proveedor con score ≥90 y carga pre-paletizada accede a cita de 45 min. Libera capacidad adicional.
- **No-show penalizado.** 15 min de tolerancia; luego el andén se libera y el score baja.

### B.3 Decisión 2 — Flota heterogénea contra la inanición del 90%

El problema que la v1 no ve:

```
Tarimas embarcadas/día: ~156  (20 unidades x 7.8 tarimas promedio)
Promedio por sucursal:  156 / 32 = 4.9 tarimas/día

Pero la distribución es Pareto, no uniforme:
  Top 8 sucursales   (60% del volumen) -> ~11.7 tarimas/día cada una
  Cola 24 sucursales (40%)             ->  ~2.6 tarimas/día cada una

Para llenar un Tortón al 90% (11 tarimas):
  Sucursal top  -> 0.9 días   OK, sale diario
  Sucursal cola -> 4.2 días   INACEPTABLE (desabasto en piso de venta)
```

**Solución: el sistema elige la unidad, no espera a la carga.**

| Clase | Capacidad | ≥90% se cumple con | Costo/viaje ref. | Sucursal objetivo |
|:---|:---:|:---:|---:|:---|
| Tortón | 12 tarimas | 11 tarimas | $2,800 | Top 8 (alto volumen) |
| Rabón | 6 tarimas | 6 tarimas (5.4 → 6) | $2,000 | Cola 24 (volumen medio-bajo) |
| Camioneta 3.5 t | 3 tarimas | 3 tarimas (2.7 → 3) | $1,250 | Urgencias y cola muy baja |

```
Con Rabón para la cola:  2.6 tarimas/día -> 6 tarimas en 2.3 días
Con regla de antigüedad: tope duro de 36 h -> sale aunque no llegue al 90%
```

**Reglas de liberación (en orden de precedencia):**

1. Ocupación ≥90% en la unidad más chica que acomode el inventario acumulado → **liberar**.
2. Antigüedad de la tarima más vieja ≥36 h → **liberar con acta de excepción** (queda registrada y se reporta a gerencia; el reto exige ≥90%, así que la excepción debe ser visible y auditable, no silenciosa).
3. Dos sucursales contiguas en ruta, ambas <90% y ambas con antigüedad >24 h → **milk-run** con QR maestro independiente por sucursal.

Esto respeta la regla del reto ("no salen hasta cubrir al menos 90%") en el 100% de los casos normales, y hace **explícita y auditable** la excepción en lugar de ignorar el conflicto.

### B.4 Decisión 3 — Arquitectura edge-first (la operación no se detiene)

```
+-- CEDIS (on-premise) ------------------------------+
|  Nodo edge: PostgreSQL operativo + API local       |  <- la operación vive AQUÍ
|  Switch PoE+ L3 · 16 APs · UPS 3 kVA online        |
|  Handhelds: SQLite local + cola de sync idempotente|
+---------------------+------------------------------+
                      | fibra 300 Mbps + failover LTE
+---------------------v------------------------------+
|  Nube: portal de proveedores · BI · respaldos      |
|  Integración ERP · timbrado CFDI · Carta Porte 3.1 |
+----------------------------------------------------+
```

- **El handheld valida contra su copia local.** La OC, el desglose de factura y las etiquetas esperadas se descargan al confirmar la cita. Escaneo, aceptación y rechazo funcionan **sin red**.
- **Idempotencia obligatoria.** Cada evento lleva `(id_bulto, estado, uuid_evento)`. Un doble escaneo del mismo QR no duplica recepción; una reconexión no reprocesa la cola.
- **Si cae internet**, el CEDIS opera normal; solo se posponen el portal de proveedores y el timbrado. Si cae el nodo edge (UPS + respaldo), los handhelds siguen 8 h en modo degradado.

**Máquina de estados del bulto** (ausente en la v1, y sin ella no hay trazabilidad auditable):

```
ETIQUETADO -> EN_TRANSITO -> ESCANEADO_ANDEN -> RECIBIDO ----> UBICADO
                                           \-> RECHAZADO        |
                                                                v
RECIBIDO_SUCURSAL <- EMBARCADO <- CARGADO <- ASIGNADO_EMBARQUE <-+
```

Clave única `(id_bulto, estado)`: garantiza que ningún bulto retroceda ni se duplique.

**QR firmado (anti-fotocopia):**

```
v1|B00412|OC-88213|PRV-0147|SUC-14|SKU-993201|24|18.4|0.42|K7QX4M2A
                                                           ^-- HMAC-SHA256
                                                               truncado (8 B base32)
~92 caracteres -> QR versión 7, ECC nivel M, módulo 0.5 mm
Etiqueta 4" x 6" -> lectura confiable a 30-40 cm con motor SE4710
```

Sin la firma válida, el handheld rechaza la etiqueta aunque los datos sean correctos. Mata la etiqueta fotocopiada y la etiqueta reimpresa fuera del sistema.

### B.5 Los cuatro momentos — lo que la v2 agrega

#### Momento 1 · Agendamiento
Todo lo de la v1 (portal, folio único, pase QR en caseta) **más**: andén 5 flex, duración calculada por el sistema, score de proveedor con prioridad de reserva, ventana corta para proveedor pre-paletizado, no-show penalizado.

**Cambio de fondo en el folio único:** el identificador no es el "folio de factura" sino el **UUID del CFDI 4.0**, validado contra el servicio de consulta del SAT. Resuelve de verdad lo que la v1 intentaba (unicidad) y además detecta factura cancelada o apócrifa antes de que el camión salga del patio.

#### Momento 2 · Identificación
Todo lo de la v1 (etiquetas 4x6 generadas por el portal, regla de pureza por bulto) **más**:

- **QR firmado con HMAC** (arriba).
- **Reimpresión controlada en CEDIS.** Impresora térmica Zebra ZT411 en recibo: etiqueta ilegible → se reimprime con **folio de reimpresión** ligado al bulto original y queda en bitácora. Sin esto, el bulto sin etiqueta legible paraliza la descarga.
- **Kiosco de impresión en caseta** para el proveedor pequeño sin capacidad de imprimir. Es la objeción #1 que pondrán los 35 proveedores y la v1 no la contempla.

#### Momento 3 · Recepción
Todo lo de la v1 (escaneo por bulto, bloqueo de excedente y SKU no solicitado, acta automática) **más los flujos de excepción que faltaban**:

| Excepción | Tratamiento v2 |
|:---|:---|
| **Faltante** (lo pedido > lo recibido) | Al cerrar la cita, el sistema calcula el delta, genera **Acta de Faltante**, cierra la OC parcialmente, notifica a Compras y dispara solicitud de nota de crédito. *Ausente en la v1.* |
| Bulto dañado | Recepción condicionada con evidencia fotográfica desde el handheld |
| Etiqueta ilegible | Reimpresión con folio trazable (Momento 2) |
| Bulto sin registro en el desglose | Rechazo con acta; no se recibe |
| Sucursal destino errónea en etiqueta | Se recibe y se reencamina con acta de corrección (el bulto es legítimo; el dato no) |
| QR con firma inválida | Rechazo inmediato — etiqueta no emitida por el sistema |

**Cross-dock directo (la optimización que la v1 dejó en una palabra):**

```
Al escanear el bulto en el andén de recibo:
  ¿Su sucursal tiene embarque abierto con ocupación >= 70%?
     SÍ  -> el handheld dirige el bulto al ANDÉN DE SALIDA
            (ahorra 2 movimientos de montacargas y 1 posición de rack)
     NO  -> acomodo dirigido a rack / zona flex

Meta: 25-30% de los bultos sin tocar rack.
A 312 movimientos/día, son ~80 movimientos de montacargas evitados.
```

#### Momento 4 · Almacenamiento y embarque
Todo lo de la v1 **más**:

- **Semáforo corregido:** el límite es **posiciones de tarima (11 de 12)**, con peso (12,000 kg) y volumen (28.6 m³) como restricciones secundarias. La v1 usaba 14,000 kg y 45 m³ — con esos denominadores el semáforo no se dispara nunca.
- **Zona flex de desborde.** Se respeta el rack home de cada sucursal (32 posiciones), pero el desborde va a zona flex con ubicación dirigida por sistema en lugar de quedarse en piso. KPI: ocupación de rack objetivo 35–45%, alerta >70%.
- **Relación de Embarque completa:** folio, QR maestro por sucursal, **número de sello de seguridad**, kilometraje de salida y firma del operador. La v1 omite el sello — control antirrobo básico.
- **Complemento Carta Porte 3.1.** La Relación de Embarque alimenta los datos que el transportista necesita para su CFDI con complemento (permiso SICT, configuración vehicular, placas, aseguradora, póliza). Obligatorio desde el 17-jul-2024.

### B.6 Viabilidad económica — con el supuesto que la v1 esconde

El ahorro de flete depende **por completo** del llenado actual de las unidades, que nadie midió. En lugar de inventar "2 fletes diarios", la v2 lo modela y declara el riesgo.

**Modelo.** Las sucursales demandan `T` tarimas/día. Hoy salen 20 unidades a un llenado `f`, así que `T = 20 x 12 x f`. Con la v2, el 70% de las tarimas viaja en Tortón al ≥90% y el 30% (cola larga) en Rabón.

| Llenado actual | Tarimas/día | Costo hoy | Costo v2 | **Ahorro flete/mes** |
|:---|:---:|---:|---:|---:|
| 50% (muy ineficiente) | 120 | $56,000 | $34,732 | **$552,968** |
| **65% (caso base)** | **156** | **$56,000** | **$45,130** | **$282,620** |
| 75% (ya bastante bueno) | 180 | $56,000 | $52,060 | **$102,440** |
| 85% (casi óptimo) | 204 | $56,000 | $59,004 | **−$78,104** |

> **Punto de equilibrio: ~80% de llenado actual.** Si el CEDIS ya carga por encima de eso, **el caso de negocio del flete no existe** y el proyecto debe justificarse por exactitud, cumplimiento fiscal y escalabilidad. Medir el llenado real es el **primer entregable**, no un supuesto.

Costo/viaje de referencia: Tortón $2,800 y Rabón $2,000, consistentes con tarifas de mercado de $28–36/km (Tortón 18 t) y $20–28/km (Rabón 10 t) sobre ruta metropolitana de ~75–80 km redondos.

**Ahorros operativos (con su driver explícito, a diferencia de la v1):**

| Fuente | Cálculo | Mensual |
|:---|:---|---:|
| Horas extra de cuadrilla | 2 h/día x 4 personas x $210/h extra x 26 días | $43,680 |
| Mermas y logística inversa | 0.5% de 156 tarimas/día mal encaminadas x $1,150 x 26 días | $23,400 |
| Ahorro de flete (caso base) | tabla anterior | $282,620 |
| **Ahorro bruto mensual** | | **$349,700** |

### B.7 CAPEX v2 — Inversión inicial

Precios de referencia de mercado México, **sin IVA**, noviembre 2026. Requieren cotización formal de distribuidor autorizado antes de liberar el proyecto.

| Rubro | Especificación | Cant. | Unitario | Total |
|:---|:---|:---:|---:|---:|
| Site survey RF | Predictivo (Ekahau) + validación post-instalación con mediciones | 1 | $55,000 | $55,000 |
| Access Points | **Ruckus R650/R670** Wi-Fi 6 — antena adaptativa BeamFlex, la opción correcta en nave metálica. 4 con antena direccional para pasillos profundos | 16 | $14,500 | $232,000 |
| Controladora y licencias | Ruckus SmartZone virtual o Unleashed + soporte 5 años | 1 | $48,000 | $48,000 |
| Switching | Switch L3 PoE+ 48p (740 W) + switch de acceso + SFP+ | 1 lote | $62,000 | $62,000 |
| Cableado | Cat6A + canalización industrial, 16 tiradas a 6–7 m | 1 lote | $78,000 | $78,000 |
| Energía | UPS 3 kVA online + rack de comunicaciones + PDU | 1 | $34,000 | $34,000 |
| Handhelds andén | **Zebra TC27 / TC53** (IP65/IP67, caída 1.5 m, motor 2D SE4710) | 8 | $19,500 | $156,000 |
| Handhelds acomodo | **Honeywell ScanPal EDA52** — mismo grado de uso rudo, menor costo | 6 | $11,500 | $69,000 |
| Terminales vehiculares | **Zebra VC8300** montada en montacargas (acomodo a nivel 4) | 2 | $38,000 | $76,000 |
| Accesorios | Bases de carga 4 bahías, baterías spare, rugged boots | 5 kits | $7,200 | $36,000 |
| Impresión térmica | **Zebra ZT411** — reimpresión en CEDIS + kiosco en caseta | 2 | $28,000 | $56,000 |
| Impresión láser | Brother HL-L5210DN / HP LaserJet Pro 4003dn (Relación de Embarque) | 2 | $7,400 | $14,800 |
| Servidor edge | Nodo local on-premise, SSD en espejo, redundancia de fuente | 1 | $42,000 | $42,000 |
| Desarrollo | Portal proveedores + app Android **offline-first** + backend YMS/WMS + integración ERP | 1 | $420,000 | $420,000 |
| Fiscal | Integración CFDI 4.0 / validación UUID SAT + Carta Porte 3.1 | 1 | $85,000 | $85,000 |
| Gestión del cambio | Capacitación cuadrilla + onboarding 35 proveedores + 32 sucursales | 1 | $95,000 | $95,000 |
| | | | **Subtotal** | **$1,558,800** |
| Contingencia | 12% | | | $187,056 |
| | | | **TOTAL CAPEX** | **$1,745,856** |

**Nota de honestidad sobre precios:** la Zebra TC27 se lista hoy entre $15,990 y $27,480 MXN con IVA según configuración y distribuidor. La v1 cotizó $15,800 sin IVA — el extremo más optimista del rango. La v2 usa $19,500 sin IVA, dentro de la banda media verificable.

### B.8 OPEX v2 — Costos recurrentes

| Concepto | Detalle | Mensual | Anual |
|:---|:---|---:|---:|
| Nube | Réplica, BI, respaldos, SSL | $4,800 | $57,600 |
| Conectividad | Fibra 300 Mbps + failover LTE | $3,900 | $46,800 |
| Soporte software | Póliza 18%/año sobre desarrollo | $8,500 | $102,000 |
| Soporte hardware y red | Ruckus support + refacciones handheld | $4,200 | $50,400 |
| Papel y tóner | 1,500 hojas/mes + prorrateo de cartucho | $970 | $11,640 |
| Etiquetas térmicas y ribbon | Reimpresión ~5% de bultos | $1,400 | $16,800 |
| Timbrado fiscal | ~650 CFDI+Carta Porte/mes | $780 | $9,360 |
| **TOTAL OPEX** | | **$24,550** | **$294,600** |

### B.9 Indicadores financieros

```
Ahorro bruto mensual (caso base) ......  $349,700
OPEX mensual ..........................  -$24,550
FLUJO NETO MENSUAL ....................  $325,150

Inversión inicial .....................  $1,745,856
PAYBACK ............................... 5.4 meses
VPN (36 meses, costo de capital 14% anual) ....  $7.88 M MXN
TIR mensual ........................... ~18.4%
```

**Análisis de escenarios** — esto es lo que un comité de inversión exige y la v1 no tiene:

| Escenario | Supuesto de llenado | Flujo neto/mes | Payback | VPN 36 m |
|:---|:---|---:|:---|---:|
| Optimista | 50% | $595,100 | 2.9 meses | $15.9 M |
| **Base** | **65%** | **$325,150** | **5.4 meses** | **$7.88 M** |
| Conservador | 75% | $144,970 | 12.0 meses | $2.54 M |
| Adverso | 85% | −$35,574 | no se recupera | negativo |

**En el escenario adverso el proyecto no se paga con ahorro de flete.** Se sostendría por cumplimiento de Carta Porte, exactitud de recibo y capacidad de crecer sin contratar — beneficios reales pero no monetizables con la misma firmeza. Decirlo es lo que hace creíble al resto del documento.

> Comparación directa: la v1 reporta payback de 4.2 meses sobre $728,000. La v2 reporta 5.4 meses sobre $1,745,856. **El CAPEX subió 2.4x y el payback solo 1.3x**, porque el ahorro real de flete era casi el doble del que la v1 presumía. La v1 era optimista en costo *y* pesimista en beneficio al mismo tiempo.

### B.10 Ingeniería de red v2 — 16 APs

**Criterios de diseño (medibles y verificables en la validación):**

| Parámetro | Valor objetivo |
|:---|:---|
| RSSI primario | ≥ −65 dBm en todo punto operativo a 1.2 m del suelo |
| RSSI secundario | ≥ −72 dBm (mínimo **2 APs audibles** para roaming) |
| SNR | ≥ 25 dB |
| Ancho de canal | **20 MHz** (no 40) — más canales, mejor SNR |
| Banda | 5 GHz **solo no-DFS**: 36, 40, 44, 48, 149, 153, 157, 161, 165 |
| 2.4 GHz | Activo solo en 4 APs (canales 1/6/11) para equipo legacy |
| Potencia Tx | 11–15 dBm (celdas chicas, roaming ágil) |
| Tasas de datos | Deshabilitar 1/2/5.5/11/6/9 Mbps · mínima habilitada 12 Mbps |
| Roaming | 802.11r (FT) + 802.11k + 802.11v, band steering activo |
| Seguridad | WPA2-Enterprise con RADIUS (modo transición WPA3; los handhelds de generación anterior fallan con WPA3 puro) |
| Reutilización de canal | Separación mínima 40 m entre APs del mismo canal |

**Montaje — la corrección más importante respecto a la v1:**

| Zona | Altura Z | Posición | Antena |
|:---|:---:|:---|:---|
| Pasillos de racks | **5.5–6.0 m** | **Dentro del pasillo**, sobre el eje, radiando hacia abajo | Omni (R650) |
| Pasillos profundos (4 puntos) | 5.5 m | Cabecera de pasillo | Direccional / patch |
| Andenes | 5.0 m | Sobre el dintel de cortina (4.5 m) | Omni, orientada a proyectar dentro de la caja seca |
| Oficinas y mesa de incidencias | 3.0 m | Plafón | Omni |

> **Nunca sobre la coronilla del rack.** La v1 monta a 7 m "para tener línea de vista por encima del metal". Eso ilumina la parte superior del rack y deja al operador —que está a 1.2 m, dentro del pasillo— en sombra. El AP va **en** el pasillo.

**Distribución (origen en esquina suroeste, X = largo 0–100 m, Y = fondo 0–40 m):**

| AP | Zona | X | Y | Z | Canal | Tx |
|:---|:---|:---:|:---:|:---:|:---:|:---:|
| AP-01 | Andenes recibo 1–2 | 12 | 3 | 5.0 | 36 | 11 dBm |
| AP-02 | Andenes recibo 3–4 | 34 | 3 | 5.0 | 40 | 11 dBm |
| AP-03 | Andenes embarque 1–3 | 62 | 3 | 5.0 | 44 | 11 dBm |
| AP-04 | Andén 5 flex + mesa incidencias | 84 | 3 | 5.0 | 48 | 11 dBm |
| AP-05 | Pasillo A · frente | 12 | 14 | 5.5 | 149 | 14 dBm |
| AP-06 | Pasillo B · frente | 32 | 14 | 5.5 | 153 | 14 dBm |
| AP-07 | Pasillo C · frente | 52 | 14 | 5.5 | 157 | 14 dBm |
| AP-08 | Pasillo D · frente | 72 | 14 | 5.5 | 161 | 14 dBm |
| AP-09 | Pasillo E · frente (direccional) | 90 | 14 | 5.5 | 165 | 15 dBm |
| AP-10 | Pasillo A · fondo | 12 | 30 | 5.5 | 36 | 14 dBm |
| AP-11 | Pasillo B · fondo | 32 | 30 | 5.5 | 40 | 14 dBm |
| AP-12 | Pasillo C · fondo | 52 | 30 | 5.5 | 44 | 14 dBm |
| AP-13 | Pasillo D · fondo (direccional) | 72 | 30 | 5.5 | 48 | 15 dBm |
| AP-14 | Pasillo E · fondo (direccional) | 90 | 30 | 5.5 | 149 | 15 dBm |
| AP-15 | Zona flex de desborde (direccional) | 50 | 38 | 5.5 | 153 | 15 dBm |
| AP-16 | Emplayado y zona de consolidación | 26 | 8 | 5.5 | 157 | 14 dBm |

Separación entre APs del mismo canal: AP-01/AP-10 están a 27 m en Y, pero con dos hileras de rack metálico de 6 m en medio (atenuación >25 dB), suficiente para reutilizar. La validación post-instalación confirma o corrige.

### B.11 Roadmap por fases (la v1 propone un big-bang de $1.7 M)

| Fase | Duración | Alcance | Inversión | Puerta de decisión |
|:---|:---:|:---|---:|:---|
| **0** | 2 sem | **Medición de línea base** (llenado real, tiempo de andén, exactitud) + site survey RF | $55,000 | Si el llenado ya es >80%, **se replantea el caso de negocio antes de gastar** |
| **1** | 6 sem | Agendamiento + Identificación: portal de proveedores, etiquetas QR firmadas, pase de caseta, andén 5 flex | $560,000 | No requiere red industrial. **Ordena las citas desde la semana 8** |
| **2** | 8 sem | Red (16 APs, switching, UPS, edge) + handhelds + Recepción offline-first con todos los flujos de excepción | $760,000 | Exactitud de recibo ≥99% en 2 semanas de operación |
| **3** | 6 sem | Consolidación, flota heterogénea, cross-dock, Relación de Embarque, Carta Porte 3.1 | $425,856 | Llenado promedio ≥90% sostenido |

La Fase 0 cuesta 3% del proyecto y **puede cancelarlo** antes de comprometer el 97% restante. Eso es lo que distingue una propuesta de inversión de una lista de compras.

### B.12 KPIs y línea base

| KPI | Línea base | Meta 6 meses | Fuente |
|:---|:---|:---|:---|
| Cumplimiento de cita | *a medir en Fase 0* | ≥92% | Motor de citas |
| Tiempo medio de andén | *a medir* | ≤70 min | Timestamps de escaneo |
| Llenado promedio por unidad | *a medir* | ≥90% | Cierre de embarque |
| Exactitud de recibo | *a medir* | ≥99.5% | Actas vs. bultos |
| Antigüedad máxima en rack | *a medir* | ≤36 h | Inventario |
| % bultos en cross-dock | 0% | ≥25% | Dirección de put-away |
| Ocupación de rack | *a medir* | 35–45% | Inventario |
| Costo por tarima embarcada | *a medir* | −35% | Flete / tarimas |
| Embarques con excepción de antigüedad | — | ≤8% | Actas de excepción |

Sin la columna "línea base" llena, **ningún número de ROI de este documento es defendible**. Por eso la Fase 0 existe.

### B.13 Riesgos y mitigación

| Riesgo | Prob. | Impacto | Mitigación |
|:---|:---:|:---:|:---|
| **Proveedores no adoptan el etiquetado** | Alta | Crítico | Kiosco de impresión en caseta · 3 meses de convivencia con proceso manual · score con prioridad de cita como incentivo · onboarding presencial a los 10 proveedores de mayor volumen (que concentran ~60% del flujo) |
| Caída de red o internet | Media | Crítico | **App offline-first** + nodo edge + UPS + failover LTE. El riesgo está diseñado fuera del sistema. |
| Integración con el ERP se atrasa | Alta | Alto | Contrato con el proveedor del ERP **cerrado antes de iniciar Fase 2** · API de contingencia por archivo plano para los primeros 60 días |
| El llenado actual ya es alto (caso adverso) | Media | Alto | **Fase 0 lo mide antes de invertir el 97%** |
| Rotación de cuadrilla | Alta | Medio | Perfil de app de 3 pantallas · capacitación grabada · certificación interna de 2 h |
| Eventos DFS tirando APs | Media | Medio | **Solo canales no-DFS** |
| Robo en tránsito | Media | Alto | Sello de seguridad folizado en Relación de Embarque + conciliación por QR maestro en destino |
| Sobrecosto de equipo vs. referencia | Media | Medio | Contingencia 12% + cotización formal en Fase 0 |

### B.14 Prototipo funcional — alcance mínimo demostrable

El reto pide un prototipo funcional y la v1 no lo entrega. Alcance mínimo para que el prototipo demuestre lo que importa:

1. **Portal de agendamiento** — captura de OC, UUID de CFDI con validación de unicidad, carga de desglose por bulto, motor de citas con cálculo de duración, detección de traslape y andén 5 flex.
2. **Generador de etiquetas** — PDF 4x6 con QR firmado HMAC y bloqueo de la regla de pureza (un SKU por bulto).
3. **Simulador de handheld** — escaneo con los tres desenlaces: aceptación, **rechazo por excedente/SKU no solicitado**, y **rechazo por firma inválida**. Modo offline con cola de sincronización visible.
4. **Tablero de consolidación** — semáforo por sucursal sobre **posiciones de tarima**, selección automática de clase de unidad, alerta de antigüedad >36 h y botón de liberación con acta de excepción.
5. **Relación de Embarque** — PDF con QR maestro, folio de sello y recepción en destino con un escaneo.
6. **Cierre de recepción con faltante** — generación de Acta de Faltante (el flujo que la v1 no tiene).

Los puntos **3, 4 y 6** son los que distinguen un prototipo que demuestra entendimiento del problema de uno que solo tiene pantallas bonitas.

---

## Resumen de cambios v1 → v2

| | v1 | v2 |
|:---|:---|:---|
| Diagnóstico del cuello de botella | "87.5% de ocupación, cómodo" | Déficit de 3 citas/día, resuelto con andén 5 flex a costo cero |
| Regla del 90% | Rígida, sin excepción → inanición de 4.2 días | Flota heterogénea + SLA de antigüedad 36 h + milk-run |
| Capacidad del Tortón | 14,000 kg / 45 m³ (mal) | 12,000 kg / 28.6 m³ · límite real = 11 de 12 posiciones |
| Arquitectura | Cloud puro, validación en línea | Edge-first, app offline-first, idempotente |
| QR | Texto plano (fotocopiable) | Firmado con HMAC-SHA256 |
| Faltantes | Sin flujo | Acta de Faltante + cierre parcial de OC + nota de crédito |
| Cross-dock | Mencionado | Regla operativa con meta de 25–30% |
| Cumplimiento fiscal | Ausente | UUID CFDI validado + Carta Porte 3.1 |
| Wi-Fi | 12 APs, 40 MHz, DFS, montados sobre racks a 7 m | 16 APs, 20 MHz, solo no-DFS, montados en pasillo a 5.5 m |
| CAPEX | $728,000 (9 rubros omitidos) | $1,745,856 (completo, con contingencia) |
| Ahorro de flete | "2 fletes/día" sin derivación | Modelado con 4 escenarios y punto de equilibrio declarado |
| Evaluación financiera | Payback y ROI | Payback, VPN, TIR, escenarios y **escenario adverso donde no se justifica** |
| Implementación | Big-bang | 4 fases con puerta de decisión en la Fase 0 (3% del CAPEX) |
| KPIs | Ninguno | 9 KPIs con línea base obligatoria |
| Riesgos | Ninguno | 8 riesgos con mitigación |
| Prototipo | Prometido, ausente | Alcance mínimo definido en 6 módulos |

---

### Fuentes de referencia de mercado

- Precios Zebra TC27 México: [Codebar](https://www.codebar.mx/producto/zebra-terminal-portatil-tc27-se4710/) · [MBCEStore](https://www.mbcestore.com.mx/zebra/tc27.htm) · [Mercado Libre](https://listado.mercadolibre.com.mx/zebra-tc27)
- Ruckus R650 (desempeño en entornos RF difíciles): [Ruckus Networks](https://www.ruckusnetworks.com/products/wireless-access-points/r650/) · [comparativo Cisco/Aruba/Ruckus](https://baidengroup.ca/cisco-vs-aruba-vs-ruckus-enterprise-wifi/)
- Tarifas de flete por km y por viaje: [Cotizadora Online](https://www.cotizadoraonline.com/cotizacion-transporte-fletes) · [Habitissimo CDMX](https://www.habitissimo.com.mx/presupuesto/flete-local/ciudad-de-mexico) · [Cargoflex Monterrey](https://cargoflex.mx/blog/cuanto-cuesta-un-flete-en-monterrey)
- Complemento Carta Porte 3.1 (obligatorio desde 17-jul-2024): [guía Facturopolis](https://www.facturopolis.com/guias/complemento-carta-porte.html) · [guía Kold](https://kold.gold/blog/complemento-carta-porte-2026-guia)

> Todos los precios son referenciales sin IVA a noviembre de 2026 y requieren cotización formal de distribuidor autorizado antes de liberar el proyecto.
