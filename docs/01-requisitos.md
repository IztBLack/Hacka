# Especificación de Requisitos — Sistema YMS/WMS Ligero CEDIS

**Reto:** De la Orden de Compra al Embarque
**Documento:** 01 — Requisitos
**Versión:** 1.0
**Fecha:** 25 de noviembre de 2026
**Base:** `propuesta-cedis-v2.md` y `tecnologias-cedis.txt`

---

## 1. Propósito y alcance

### 1.1 Propósito

Especificar, de manera verificable, qué debe hacer el sistema YMS/WMS ligero que
ordena la operación del CEDIS desde que un proveedor pide una cita hasta que una
unidad sale con la Relación de Embarque hacia una sucursal.

El documento existe para que tres cosas puedan ocurrir sin discusión posterior:
que un desarrollador sepa qué construir, que un operador sepa qué va a usar en el
andén, y que un jurado o un comité pueda **medir** si el sistema entregado cumple
o no cumple.

### 1.2 Contexto operativo de referencia

| Dato | Valor |
|:---|:---|
| Superficie de nave | 100 m de largo × 40 m de fondo (4,000 m²) |
| Andenes de recibo | 4 fijos + 1 flex (andén 5 de embarque operando a recibo 8:00–13:00) |
| Andenes de embarque | 3 (uno de ellos es el andén 5 flex) |
| Horario de operación | 8:00 a 18:00 (10 horas) |
| Entradas | ~35 camiones de proveedores por día |
| Bultos recibidos | ~148 bultos por camión, ~5,200 bultos/día en pico |
| Sucursales surtidas | 32 |
| Salidas | ~20 embarques diarios, ~156 tarimas/día |
| Proveedores en el padrón | 35 |

### 1.3 Qué entra en el alcance

1. **Momento 1 — Agendamiento.** Portal de proveedores, captura de Orden de
   Compra y CFDI, desglose por bulto, motor de citas con duración calculada,
   detección de traslape, andén 5 flex, score de proveedor, pase de acceso en
   caseta.
2. **Momento 2 — Identificación.** Generación de etiqueta 4" × 6" con QR firmado
   por bulto, regla de un SKU por bulto, reimpresión controlada en CEDIS y
   kiosco de impresión en caseta.
3. **Momento 3 — Recepción.** Escaneo bulto por bulto en andén con handheld,
   validación contra copia local de la OC, aceptación, rechazo, cross-dock
   dirigido, acta de faltante al cierre de cita.
4. **Momento 4 — Almacenamiento y embarque.** Ubicación dirigida con zona flex,
   semáforo de consolidación por sucursal sobre posiciones de tarima, selección
   automática de clase de unidad, regla de ≥90% de llenado con su excepción
   auditable, Relación de Embarque impresa y en PDF con QR maestro, y
   alimentación de datos para el Complemento Carta Porte 3.1.
5. **Transversal.** Operación sin internet (edge-first y app offline-first),
   bitácora de auditoría, roles, tablero de KPIs e interfaz de integración con
   el ERP.

### 1.4 Qué NO entra en el alcance (explícito)

| # | Fuera de alcance | Por qué se declara |
|:--|:---|:---|
| FA-01 | **No es un TMS de ruteo.** El sistema no calcula rutas, no secuencia paradas, no optimiza kilometraje ni asigna operadores de transporte. Solo selecciona la **clase de unidad** (tortón / rabón / camioneta) y, en el caso de milk-run, propone el par de sucursales contiguas que ya trae definido el catálogo. | El reto pide consolidar y embarcar, no planear transporte. La secuencia de ruta la define el área de distribución. |
| FA-02 | **No gestiona inventario de piso de venta en sucursal.** La responsabilidad del sistema termina al confirmar la recepción del QR maestro en el andén de la sucursal. Lo que pasa después (acomodo en tienda, exhibición, venta, mermas en piso) no se modela. | El reto es de CEDIS. El inventario de tienda vive en el punto de venta y en el ERP. |
| FA-03 | **No sustituye al ERP.** El sistema no es el maestro de artículos, no es el maestro de proveedores comerciales, no genera órdenes de compra, no lleva cuentas por pagar ni contabilidad, y no emite el CFDI del proveedor. Consume y devuelve datos; no es la fuente de verdad financiera. | Duplicar el maestro de datos es la vía más rápida a inconsistencias y a un proyecto que nadie puede conciliar. |
| FA-04 | **No incluye control de temperatura ni cadena de frío.** No hay registro de temperatura, no hay alarmas termométricas, no hay segregación por rango térmico ni trazabilidad de rompimiento de cadena de frío. | No hay refrigerados en el alcance declarado del reto. Si entran, es un proyecto distinto con hardware (dataloggers, sondas) y requisitos sanitarios propios. |
| FA-05 | **No hace conteo de inventario cíclico en fase 1.** El handheld de acomodo tiene la capacidad técnica, pero el proceso de conteo cíclico, su calendario, su tolerancia de ajuste y su autorización contable quedan fuera de fase 1. | El conteo cíclico requiere política de ajuste autorizada por Contraloría. Se habilita en una fase posterior. |
| FA-06 | **No gestiona mantenimiento de montacargas ni de la flota.** Horómetros, órdenes de servicio y checklist de equipo no se modelan. | Es un dominio de mantenimiento, no de almacén. |
| FA-07 | **No emite el CFDI con Complemento Carta Porte.** El sistema **entrega los datos** que el transportista o el PAC necesitan para timbrar; el timbrado lo ejecuta el PAC. | El sistema no es un PAC autorizado por el SAT. |
| FA-08 | **No incluye picking por pieza ni surtido fraccionado.** La unidad de manejo en embarque es la tarima consolidada por sucursal, no la pieza. | El reto describe consolidación por sucursal, no surtido unitario. |
| FA-09 | **No incluye nómina, asistencia ni productividad individual del personal.** Se registra quién ejecutó cada evento para auditoría, no para medir desempeño laboral. | Evita convertir la bitácora en instrumento de evaluación de personal, que es un uso distinto con implicaciones laborales. |

---

## 2. Supuestos

Cada supuesto trae su consecuencia si resulta falso. Un supuesto sin consecuencia
declarada es una apuesta oculta.

| ID | Supuesto | Si resulta falso |
|:---|:---|:---|
| **A-01** | La descarga de un camión promedio toma 1.0 h y la maniobra entre citas (entrada, posicionamiento, retiro) toma 15 min, para un ciclo de 1.25 h por cita. | La capacidad de 36 citas/día se derrumba. Con ciclo de 1.5 h la capacidad baja a 30 citas y el andén 5 flex no alcanza: habría que ampliar su ventana a 8:00–18:00 o negociar un segundo andén flex. **Se mide en Fase 0.** |
| **A-02** | Los andenes de embarque están ociosos en la mañana y pueden ceder un andén a recibo de 8:00 a 13:00. | Si hay embarques matutinos obligados (sucursal que abre temprano), el andén 5 flex no existe y el déficit de 3 citas/día regresa. Mitigación: reprogramar 1–2 embarques a la tarde, o escalonar el inicio de citas desde 7:30. |
| **A-03** | El llenado promedio actual de las unidades es ~65%. | Es el supuesto más caro del proyecto. Por arriba del 80% el caso de negocio de flete **desaparece** y el proyecto debe justificarse por exactitud y cumplimiento fiscal. Por debajo del 55% el ahorro es mayor al proyectado. **Se mide en Fase 0 y puede cancelar el proyecto.** |
| **A-04** | La distribución de volumen entre sucursales es de tipo Pareto: 8 sucursales concentran ~60% y 24 sucursales el ~40% restante. | Si el volumen es más uniforme, la flota heterogénea pierde valor y bastaría el tortón. Si es más concentrado, aumentan las excepciones de antigüedad en la cola larga y hay que revisar el SLA de 36 h. |
| **A-05** | Los 35 proveedores pueden imprimir una etiqueta térmica o láser 4" × 6", o aceptan usar el kiosco de la caseta. | Es el riesgo principal del proyecto. Si una fracción relevante no imprime, la identificación se desplaza al CEDIS, el kiosco de caseta se vuelve cuello de botella y hay que presupuestar una tercera impresora y una posición de personal en caseta. |
| **A-06** | El servicio de consulta de CFDI del SAT está disponible con latencia aceptable al momento de agendar. | La validación de UUID pasa a modo diferido: la cita se agenda en estado *provisional* y se confirma cuando el servicio responde. Un UUID que resulte cancelado después de agendado genera cancelación de cita con aviso al proveedor. |
| **A-07** | El ERP expone (o puede exponer) una interfaz para consultar órdenes de compra y recibir confirmaciones de recepción. | Fase 2 se atrasa. Mitigación ya prevista: contingencia por archivo plano CSV/XML sobre SFTP durante los primeros 60 días. Si el ERP no puede ni eso, se requiere captura manual de OC y el beneficio de exactitud cae. |
| **A-08** | La tarima estándar es de 1.12 m × 1.15 m, soporta al menos 1,000 kg y no excede 1.85 m de altura armada. | Cambian todos los cálculos de capacidad de unidad (12 / 6 / 3 posiciones) y el umbral de ≥90% hay que recalibrar por clase de unidad. |
| **A-09** | Un tortón admite 12 posiciones de tarima, un rabón 6 y una camioneta 3.5 t admite 3. | La tabla de selección automática de unidad queda inválida y el semáforo de llenado se dispara en el momento equivocado. Se confirma con medición física de las cajas del transportista contratado. |
| **A-10** | Hay energía eléctrica estable y espacio físico en sitio para rack de comunicaciones, UPS 3 kVA y nodo edge. | Sin UPS, un apagón detiene el CEDIS completo: el modo degradado del handheld (8 h) cubre el escaneo pero no el tablero ni la impresión. Habría que agregar planta de emergencia al CAPEX. |
| **A-11** | El site survey RF confirma que 16 APs cubren la nave con los criterios de diseño declarados. | El número de APs cambia al alza o baja y con él el CAPEX de red, el cableado y las licencias. El diseño de 16 APs es **predictivo**, no medido. |
| **A-12** | Los handhelds Zebra TC27/TC53 y Honeywell EDA52 soportan WPA2-Enterprise con modo transición WPA3. | Hay que degradar la seguridad de la red a WPA2-Enterprise puro o reemplazar equipos. Se valida con una unidad de prueba antes de la compra del lote. |
| **A-13** | Un bulto contiene un solo SKU, y así lo arma el proveedor en su origen. | La regla de pureza por bulto se vuelve inaplicable y la validación de cantidad por escaneo pierde sentido: habría que escanear a nivel pieza, lo que multiplica el tiempo de andén. |
| **A-14** | El transportista proporciona permiso SICT, configuración vehicular, placas, aseguradora y número de póliza, y acepta recibirlos del sistema para su timbrado. | La Relación de Embarque no puede alimentar Carta Porte 3.1 y el cumplimiento fiscal queda en manos del transportista sin apoyo del sistema. |
| **A-15** | Las sucursales cuentan con un dispositivo capaz de escanear el QR maestro al recibir. | La conciliación en destino se hace manual (firma de la Relación de Embarque impresa) y se pierde el cierre automático del ciclo. Alternativa: escaneo con el celular del gerente de sucursal vía web. |
| **A-16** | El prototipo de la fase de concurso opera con datos sintéticos y no requiere conexión real al SAT, al ERP ni al PAC. | Si se exige integración real, el alcance del prototipo crece y requiere credenciales de prueba de los tres servicios, que hoy no se tienen. |

---

## 3. Restricciones impuestas por el reto

Estas reglas las fija el reto. No son decisiones de diseño y no se negocian: el
sistema las hace cumplir o el sistema está mal construido.

| ID | Restricción | Regla exacta | Dónde se hace cumplir |
|:---|:---|:---|:---|
| **R-01** | Duración mínima de cita | Ninguna cita puede durar menos de **60 minutos**. | Motor de citas (RF-005) |
| **R-02** | Exclusividad de andén | **Un andén atiende una sola entrega a la vez.** No hay traslape de citas en el mismo andén, ni parcial. | Motor de citas (RF-007) |
| **R-03** | Folio de factura único | El folio que identifica la entrega es **único y no repetible**. Se implementa como el **UUID del CFDI 4.0**, validado contra el SAT. | Portal de agendamiento (RF-002, RF-003) |
| **R-04** | Pureza del bulto | **Un SKU por bulto.** Un bulto no puede contener más de un SKU. | Generador de etiquetas (RF-017) |
| **R-05** | No se recibe mercancía no solicitada | Todo bulto debe corresponder a una OC vigente y a un desglose declarado. Lo que no está solicitado **no se recibe**. | Handheld, validación local (RF-027, RF-030) |
| **R-06** | Altura máxima de tarima | La tarima armada no excede **1.85 m** de altura total. | Confirmación de armado (RF-040) |
| **R-07** | Capacidad de tarima | La tarima soporta **al menos 1,000 kg** (resistencia mínima); el tope operativo de carga por tarima es **1,000 kg**. | Confirmación de armado (RF-041) |
| **R-08** | Film de seguridad | Toda tarima consolidada debe llevar **film de seguridad (emplaye)** antes de ser asignada a embarque. | Confirmación de armado (RF-042) |
| **R-09** | Llenado mínimo de salida | **Ninguna unidad sale con menos de 90% de llenado**, medido sobre posiciones de tarima. | Semáforo y liberación (RF-043, RF-045) |
| **R-10** | Relación de Embarque | Toda salida lleva **Relación de Embarque impresa y en PDF**, con **QR** que permita conciliar en destino. | Embarque (RF-048, RF-049) |
| **R-11** | Horario de operación | Las citas y los embarques ocurren dentro de la ventana **8:00–18:00**. | Motor de citas (RF-013) |

> **Nota sobre R-09.** La regla de ≥90% y el SLA de antigüedad de 36 h están en
> tensión real (ver §9, limitación L-05). El sistema resuelve la tensión
> cambiando de clase de unidad —no haciendo esperar a la sucursal— y, cuando ni
> la unidad más chica alcanza el 90%, libera **con acta de excepción visible y
> auditable** en lugar de romper la regla en silencio.

---

## 4. Glosario

| Término | Definición operativa |
|:---|:---|
| **Bulto** | Unidad mínima de manejo identificada con etiqueta y QR propios. Contiene **un solo SKU** (R-04). Es el objeto que se escanea en el andén y el que tiene máquina de estados. Ejemplo: una caja master, un atado, un saco. |
| **Tarima** | Plataforma (1.12 m × 1.15 m de referencia) sobre la que se consolidan bultos. Resistencia mínima 1,000 kg, altura armada máxima 1.85 m. Es la unidad de medida de llenado de la unidad de transporte: lo que cuenta no es el peso ni el volumen, sino la **posición de tarima**. |
| **OC (Orden de Compra)** | Documento emitido por Compras que autoriza al proveedor a entregar artículos y cantidades específicas. Es la referencia contra la que se valida toda recepción. El sistema la consume del ERP; no la genera. |
| **CFDI** | Comprobante Fiscal Digital por Internet, versión 4.0. Es la factura electrónica que ampara la entrega del proveedor. |
| **UUID** | Identificador único universal de 36 caracteres que el SAT asigna a cada CFDI timbrado. En este sistema **el UUID es el folio único de la entrega** (R-03): no se usa un consecutivo interno, porque un consecutivo se puede repetir o falsificar y el UUID se puede consultar contra el SAT. |
| **Cross-dock** | Práctica de llevar un bulto directamente del andén de recibo al andén de embarque, sin pasar por rack. Ahorra dos movimientos de montacargas y una posición de almacenamiento. En este sistema el cross-dock es **dirigido por el sistema**, no decidido por el operador. |
| **Put-away** | Acomodo dirigido: el sistema indica al montacarguista la ubicación exacta donde debe depositar la tarima o el bulto, en lugar de dejarlo a criterio del operador. |
| **Cita** | Reserva de un andén de recibo por una ventana de tiempo específica para una entrega concreta. Tiene duración calculada por el sistema (mínimo 60 min), andén asignado y folio ligado al UUID del CFDI. |
| **Andén flex** | Andén de embarque que opera como andén de recibo durante una ventana horaria determinada. En este diseño, el **andén 5** opera a recibo de 8:00 a 13:00 y vuelve a embarque de 13:00 a 18:00. Es lo que convierte un déficit de 3 citas/día en un superávit de 1. |
| **QR maestro** | Código QR único por embarque (una sucursal, una unidad) impreso en la Relación de Embarque. Al escanearlo en destino, la sucursal confirma la recepción de todo el embarque en un solo acto, en lugar de bulto por bulto. En un milk-run hay un QR maestro **por sucursal**, no uno por unidad. |
| **Score de proveedor** | Calificación numérica (0–100) que resume puntualidad de cita, exactitud de etiquetado y exactitud documental de un proveedor. No es decorativa: determina la **prioridad de reserva** de horario y el acceso a la ventana corta de 45 minutos. Es la palanca de cumplimiento que no cuesta dinero. |
| **Acta de faltante** | Documento que el sistema genera automáticamente al cerrar una cita cuando lo recibido es menor a lo declarado en el desglose. Registra el delta por SKU, cierra parcialmente la OC, notifica a Compras y dispara la solicitud de nota de crédito. |
| **Acta de excepción** | Documento que registra una liberación de embarque que **no cumple** el 90% de llenado, por haber alcanzado el tope de antigüedad de 36 h. Deja constancia de quién autorizó, cuándo y por qué. |
| **Tortón** | Camión de dos ejes traseros (seis ruedas atrás). En este diseño: **12 posiciones de tarima**, ~12,000 kg, ~28.6 m³. Se da por lleno al ≥90% con **11 tarimas**. Se asigna a las sucursales de alto volumen. |
| **Rabón** | Camión de un eje trasero, más chico que el tortón. En este diseño: **6 posiciones de tarima**, ~10 t. Se da por lleno al ≥90% con **6 tarimas** (5.4 redondeado al entero superior). Se asigna a sucursales de volumen medio-bajo. |
| **Camioneta 3.5 t** | Unidad ligera de **3 posiciones de tarima**. Se da por llena al ≥90% con **3 tarimas**. Se usa para urgencias y para la cola de muy bajo volumen. |
| **Nodo edge** | Servidor físico instalado en el CEDIS donde vive la base de datos operativa y la API. La nube es réplica, no dependencia. Si cae internet, el CEDIS sigue operando. |
| **HMAC** | Código de autenticación de mensaje con llave secreta (aquí HMAC-SHA256 truncado a 8 bytes en base32). Va impreso dentro del QR de cada bulto. Sin firma válida, el handheld rechaza la etiqueta aunque los datos sean correctos: mata la etiqueta fotocopiada y la reimpresa fuera del sistema. |
| **Relación de Embarque** | Documento que acompaña a cada unidad que sale: folio, sucursal destino, lista de tarimas y bultos, QR maestro, **número de sello de seguridad**, kilometraje de salida y firma del operador. Se imprime y se guarda en PDF. |
| **Carta Porte 3.1** | Complemento obligatorio del CFDI para autotransporte federal desde el 17 de julio de 2024. Requiere permiso SICT, configuración vehicular, placas, aseguradora y número de póliza. El sistema **alimenta** esos datos; el PAC los timbra. |
| **Zona flex de desborde** | Área de almacenamiento sin asignación fija por sucursal, con ubicación dirigida por sistema, usada cuando el rack *home* de una sucursal se desborda. Evita que el excedente termine en piso. |
| **Milk-run** | Embarque que atiende dos sucursales contiguas en ruta, cada una con su propio QR maestro, cuando ambas están por debajo del 90% y ambas rebasan 24 h de antigüedad. |
| **Idempotencia** | Propiedad de un evento que puede procesarse varias veces sin duplicar su efecto. Cada evento de escaneo lleva un UUID v4 generado en el handheld: un doble escaneo no duplica la recepción y una reconexión no reprocesa la cola. |

---

## 5. Actores

| Actor | Quién es | Qué necesita del sistema |
|:---|:---|:---|
| **Proveedor** | Una de las 35 empresas que entregan mercancía al CEDIS. Capacidad técnica muy heterogénea: algunos agendan desde un ERP, otros desde el celular. | Agendar una cita sin llamar por teléfono; conocer de inmediato qué horarios hay disponibles; capturar OC, UUID del CFDI y desglose por bulto; descargar o imprimir las etiquetas 4" × 6" con QR; ver su score y entender qué lo baja; recibir confirmación, recordatorio y aviso de cancelación; consultar las actas de faltante y rechazo que le afectan. |
| **Vigilancia / caseta** | Personal de acceso en la puerta del CEDIS. No es personal de almacén y su capacitación debe ser mínima. | Validar en un solo escaneo si el camión que llega tiene cita vigente y para qué andén; ver placas, transportista y hora de cita contra lo que trae el conductor; registrar hora real de arribo (para puntualidad y tolerancia de 15 min); imprimir en el kiosco las etiquetas del proveedor que no pudo imprimirlas; dirigir al conductor al andén correcto sin preguntar por radio. |
| **Operador de recibo** | Trabajador en el andén con handheld en la mano, guantes puestos, bajo luz de nave y a veces bajo el sol que entra por la cortina. | Escanear bulto por bulto y recibir una respuesta inequívoca en menos de un segundo: aceptado, rechazado y por qué; saber en todo momento cuántos bultos faltan de ese camión; poder rechazar con causa sin salir de la pantalla; tomar foto de un bulto dañado; que todo funcione **sin red**; ver a dónde va el bulto (cross-dock o rack) sin consultar a nadie; cerrar la cita y que el sistema genere el acta de faltante solo. |
| **Montacarguista** | Operador de montacargas con terminal montada en cabina (VMT) y escáner tethered de largo alcance, trabajando hasta 6 m de altura. | Recibir la instrucción de acomodo o de surtido en pantalla grande y legible, operable sin soltar los controles; escanear etiquetas del nivel 4 sin bajarse; confirmar la ubicación destino; ver la cola de movimientos pendientes priorizada; que el sistema no le pida nada que lo obligue a usar las dos manos fuera de los mandos. |
| **Jefe de embarques** | Responsable de decidir qué sale, en qué unidad y cuándo. Consulta el tablero de pie y de lejos, en un monitor de 27" montado en pared. | Ver el semáforo de las 32 sucursales en tiempo real sobre posiciones de tarima; ver qué clase de unidad propone el sistema y por qué; ver la antigüedad de la tarima más vieja de cada sucursal; recibir alerta antes de llegar a 36 h, no después; liberar un embarque y, si va por debajo del 90%, firmar el acta de excepción; generar la Relación de Embarque con QR maestro y capturar el número de sello; ver qué embarques llevan excepción este mes. |
| **Sucursal receptora** | Gerente o encargado de recibo en una de las 32 sucursales. | Saber qué viene en camino y cuándo; confirmar la recepción completa con **un solo escaneo** del QR maestro; reportar diferencia o daño contra la Relación de Embarque; ver el historial de lo recibido; cuando es milk-run, confirmar solo su parte. |
| **Comprador** | Área de Compras, dueña de la OC. | Enterarse el mismo día (no a fin de mes) de un faltante, un excedente o un rechazo; ver el acta de faltante con el delta por SKU; saber qué OC quedó cerrada parcialmente; disparar la solicitud de nota de crédito; ver el score de cada proveedor para negociar con dato, no con percepción. |
| **Gerencia** | Dirección de operaciones o de logística. | Tablero de los KPIs de la propuesta contra línea base y meta; número de embarques liberados con excepción de antigüedad; costo por tarima embarcada; cumplimiento de cita; exactitud de recibo; ocupación de rack; porcentaje de bultos en cross-dock; evidencia auditable para sustentar el ROI ante un comité. |
| **Administrador del sistema** | Perfil técnico responsable de operación y configuración del sistema. | Alta, baja y roles de usuarios; parametrizar reglas de negocio (umbral de 90%, umbral de cross-dock de 70%, SLA de 36 h, fórmula de duración de cita) sin cambiar código; rotar la llave HMAC de firma de etiquetas; administrar el catálogo de sucursales, andenes y clases de unidad; consultar la bitácora inmutable; monitorear salud de APs, cola de sincronización y réplica a nube; ejecutar y verificar respaldos; gestionar el enrolamiento MDM de los 16 dispositivos. |

---

## 6. Requisitos funcionales

**Convención de prioridad**

| Prioridad | Significado |
|:---|:---|
| **Debe** | Sin esto el sistema no cumple el reto. Es condición de entrega. |
| **Debería** | Aporta valor material; se entrega si el calendario lo permite, y se documenta su ausencia. |
| **Podría** | Deseable. Candidato a fase posterior. |

### 6.1 Momento 1 — Agendamiento

| ID | Requisito | Prioridad | Actor | Criterio de aceptación |
|:---|:---|:---|:---|:---|
| **RF-001** | El sistema debe permitir al proveedor registrar una solicitud de cita asociada a una Orden de Compra vigente. | Debe | Proveedor | Dada una OC vigente en el catálogo, el proveedor completa la solicitud y el sistema devuelve folio de solicitud. Con una OC inexistente, cerrada o cancelada, el sistema rechaza con mensaje que nombra la causa. Verificación: 3 casos (vigente, inexistente, cerrada). |
| **RF-002** | El sistema debe exigir el UUID del CFDI 4.0 como folio único de la entrega y rechazar cualquier UUID ya registrado en el sistema. | Debe | Proveedor | Al capturar un UUID ya usado en otra cita o recepción, el sistema rechaza con el texto de la causa y el folio de la cita previa. La unicidad está garantizada por restricción de base de datos, no solo por validación de aplicación: una inserción directa duplicada falla. |
| **RF-003** | El sistema debe validar el UUID contra el servicio de consulta del SAT y rechazar la cita si el CFDI está cancelado, no existe o no corresponde al RFC del proveedor y al RFC receptor. | Debe | Proveedor, Comprador | Con UUID vigente la cita queda confirmada. Con UUID cancelado o inexistente la cita se rechaza y se registra el motivo en bitácora. Si el servicio del SAT no responde en 10 s, la cita queda en estado *provisional* y se reintenta; una cita provisional no genera pase de caseta. Verificación: 4 casos (vigente, cancelado, inexistente, servicio caído). |
| **RF-004** | El sistema debe permitir cargar el desglose de la entrega a nivel bulto, con SKU, cantidad, peso y sucursal destino por bulto. | Debe | Proveedor | Se acepta carga por archivo (CSV/XLSX) y por captura manual. El sistema valida que la suma de cantidades por SKU del desglose coincida con las cantidades del CFDI y de la OC; si no coincide, bloquea la carga indicando el SKU y el delta. |
| **RF-005** | El sistema debe calcular la duración de la cita con la fórmula `t = max(60, 12 + 0.9 × n_bultos)` minutos, donde `n_bultos` es el número de bultos del desglose. | Debe | Proveedor | El resultado se redondea hacia arriba al **bloque de 30 min**, porque la malla de citas del andén opera en medias horas. Con 50 bultos: 12 + 45 = 57 → mínimo 60 → **60 min**. Con 148 bultos: 12 + 133.2 = 145.2 → 146 → **150 min**. Con 200 bultos: 192 → **210 min**. La duración mostrada al proveedor y la reservada en el andén son el mismo valor. Verificación: tabla de 5 valores de `n_bultos` incluyendo el punto donde el mínimo deja de aplicar (n = 54) y uno que caiga justo sobre un múltiplo de 30. |
| **RF-006** | El sistema debe permitir al proveedor solicitar una duración mayor a la calculada, y debe impedir que solicite una menor. | Debe | Proveedor | El campo de duración acepta valores ≥ al calculado y rechaza valores menores con mensaje explícito. Un intento por interfaz de programación con duración menor se rechaza con error de validación. |
| **RF-007** | El sistema debe impedir que dos citas se traslapen, total o parcialmente, en el mismo andén (R-02). | Debe | Proveedor, Jefe de embarques | Dada una cita en andén 2 de 10:00 a 11:30, el sistema rechaza una segunda cita en andén 2 que inicie en cualquier instante del intervalo [10:00, 11:30) y también una que inicie antes y termine dentro de él. La detección contempla los 15 min de maniobra: la siguiente cita en el mismo andén no puede iniciar antes de 11:45. Verificación: 6 casos de traslape (antes-dentro, dentro-dentro, dentro-después, exacto, adyacente sin maniobra, adyacente con maniobra). |
| **RF-008** | El sistema debe operar el andén 5 como andén de recibo de 8:00 a 13:00 y como andén de embarque de 13:00 a 18:00. | Debe | Jefe de embarques, Proveedor | El andén 5 aparece como disponible para citas de recibo solo en la ventana 8:00–13:00; una cita de recibo cuya duración termine después de las 13:00 se rechaza. A partir de las 13:00 el andén 5 solo acepta embarques. La capacidad total de recibo publicada por el sistema es de **36 citas/día**: (4 × 10 h + 1 × 5 h) / 1.25 h. |
| **RF-009** | El sistema debería ofrecer ventana de cita de 45 minutos al proveedor con score ≥90 y carga declarada como pre-paletizada. | Debería | Proveedor | Un proveedor con score 92 y carga pre-paletizada puede reservar una ventana de 45 min aunque la fórmula de RF-005 arroje 60. Un proveedor con score 88, o con carga no pre-paletizada, no ve esa opción. Esta ventana es la única excepción permitida al mínimo de 60 min de R-01 y queda registrada como tal. |
| **RF-010** | El sistema debe calcular un score de proveedor (0–100) a partir de puntualidad de cita, exactitud de etiquetado y exactitud documental, y debe usarlo para determinar la prioridad de reserva de horario. | Debe | Proveedor, Comprador | El score se recalcula al cierre de cada cita. Los proveedores con score más alto pueden reservar horarios en una ventana de apertura anticipada (parámetro configurable, por omisión 48 h antes que el resto). El desglose de los tres componentes y su ponderación es visible para el proveedor. Ponderación inicial: puntualidad 40%, etiquetado 35%, documental 25%. |
| **RF-011** | El sistema debe aplicar una tolerancia de 15 minutos al arribo y, al vencerla, liberar el andén y registrar no-show con impacto en el score. | Debe | Vigilancia, Jefe de embarques | Con cita a las 10:00 y arribo registrado a las 10:12, la cita procede. Con arribo a las 10:16 o sin arribo, el sistema marca no-show, libera el andén para reasignación y baja el score del proveedor. El evento queda en bitácora con sello de tiempo del servidor, no del dispositivo. |
| **RF-012** | El sistema debe emitir un pase de acceso con QR al confirmar la cita, y la caseta debe poder validarlo en un solo escaneo. | Debe | Vigilancia, Proveedor | Al escanear el pase, la caseta ve en una pantalla: proveedor, folio, UUID, andén asignado, hora de cita, placas y número de bultos esperados. Un pase de una cita cancelada, ya usada o de otro día se rechaza con la causa en pantalla. Verificación: 4 casos (vigente, cancelada, ya usada, otro día). |
| **RF-013** | El sistema debe restringir la programación de citas y de embarques a la ventana 8:00–18:00 (R-11). | Debe | Proveedor, Jefe de embarques | Una cita cuyo inicio sea anterior a 8:00 o cuyo fin sea posterior a 18:00 se rechaza. Los días no hábiles del calendario configurado no aparecen como disponibles. |
| **RF-014** | El sistema debe preparar y entregar a los handhelds el paquete de datos de la cita (OC, desglose por bulto, etiquetas esperadas, firmas HMAC válidas) al confirmarse la cita, para que la recepción opere sin red. | Debe | Operador de recibo | Al confirmar una cita, el paquete queda disponible para descarga. Un handheld que sincronizó el paquete y luego se desconecta de la red completa una recepción de 148 bultos sin ninguna llamada remota. Verificación: prueba con la interfaz de red del dispositivo deshabilitada de principio a fin. |
| **RF-015** | El sistema debería permitir al proveedor cancelar o reprogramar su cita con una antelación mínima configurable, sin penalización de score. | Debería | Proveedor | Con antelación ≥ al parámetro (por omisión 4 h), la cancelación libera el andén y no afecta el score. Con antelación menor, se registra como cancelación tardía y afecta el score con un peso menor al de un no-show. |

### 6.2 Momento 2 — Identificación

| ID | Requisito | Prioridad | Actor | Criterio de aceptación |
|:---|:---|:---|:---|:---|
| **RF-016** | El sistema debe generar una etiqueta por bulto en formato 4" × 6" con código QR, lista para imprimir en PDF y en ZPL II. | Debe | Proveedor | El PDF generado mide exactamente 4" × 6" por etiqueta, con QR versión 7 y corrección de errores nivel M, módulo ≥0.5 mm. La etiqueta incluye en texto legible: identificador de bulto, SKU, cantidad, sucursal destino, proveedor y folio de OC. El ZPL lo genera el backend, no el controlador de impresión. Verificación: impresión en Zebra ZT411 a 203 dpi y lectura con motor SE4710 a 30–40 cm. |
| **RF-017** | El sistema debe firmar el contenido del QR con HMAC-SHA256 truncado a 8 bytes en base32 e incluir la firma dentro del QR. | Debe | Operador de recibo, Administrador | El contenido del QR responde al formato `v1\|id_bulto\|OC\|proveedor\|sucursal\|SKU\|cantidad\|peso\|volumen\|firma`. Un QR cuyo cuerpo haya sido alterado en un solo carácter produce firma inválida y es rechazado por el handheld. Una etiqueta fotocopiada de otro bulto tiene firma válida pero identificador ya recibido, y se detecta por RF-032. Verificación: 3 casos (firma válida, cuerpo alterado, firma truncada). |
| **RF-018** | El sistema debe impedir la generación de la etiqueta de un bulto que declare más de un SKU (R-04). | Debe | Proveedor | Al intentar declarar dos SKUs en un mismo bulto, el sistema bloquea la carga del desglose y señala el renglón y el identificador de bulto en conflicto. El bloqueo ocurre en la validación del desglose, antes de generar cualquier etiqueta: no existe la posibilidad de una etiqueta impresa con dos SKUs. Verificación: carga de archivo con un bulto de 2 SKUs → carga rechazada, cero etiquetas generadas. |
| **RF-019** | El sistema debe permitir la reimpresión de la etiqueta de un bulto existente generando un folio de reimpresión trazable ligado al bulto original y al usuario que la solicitó. | Debe | Operador de recibo, Administrador | La etiqueta reimpresa conserva el identificador del bulto original y agrega folio de reimpresión visible. La bitácora registra: bulto, folio de reimpresión, usuario, motivo (catálogo: mojada, rota, ilegible, no llegó), sello de tiempo e impresora. La reimpresión no crea un bulto nuevo ni altera la cantidad esperada. |
| **RF-020** | El sistema debe ofrecer en la caseta un kiosco de impresión que permita al proveedor sin capacidad de impresión obtener las etiquetas de su cita. | Debe | Vigilancia, Proveedor | Autenticado con el folio del pase de acceso, el kiosco imprime el juego completo de etiquetas de esa cita. La impresión queda registrada y es reimprimible por el mismo mecanismo de RF-019. El tiempo de impresión de 148 etiquetas no excede 6 minutos en la ZT411. |
| **RF-021** | El sistema debe asignar a cada bulto un identificador único e inmutable al generarse su etiqueta. | Debe | Proveedor, Operador de recibo | El identificador es único en todo el sistema y no se reutiliza ni al cancelar la cita. Una inserción duplicada falla por restricción de base de datos. |
| **RF-022** | El sistema debería permitir al proveedor descargar las etiquetas de su cita en un solo archivo PDF paginado, listo para impresión por lotes. | Debería | Proveedor | Un desglose de 148 bultos produce un PDF de 148 páginas de 4" × 6", en el orden declarado del desglose, generado en menos de 30 s. |

### 6.3 Momento 3 — Recepción

| ID | Requisito | Prioridad | Actor | Criterio de aceptación |
|:---|:---|:---|:---|:---|
| **RF-023** | El sistema debe validar cada escaneo de bulto contra la copia local de la OC y el desglose en el handheld, sin requerir conexión de red. | Debe | Operador de recibo | Con la interfaz de red deshabilitada, el handheld acepta un bulto válido y rechaza uno inválido, en ambos casos con respuesta visible al operador. Ninguna de las dos decisiones requiere llamada remota. Verificación: recepción completa de 148 bultos en modo avión, 100% de decisiones resueltas localmente. |
| **RF-024** | El sistema debe rechazar todo bulto cuyo QR presente firma HMAC inválida, aun cuando los datos del QR sean correctos. | Debe | Operador de recibo | Un QR con firma alterada se rechaza con la causa "firma inválida — etiqueta no emitida por el sistema". El evento queda en bitácora con el contenido del QR leído para investigación. El bulto no puede recibirse por ninguna vía desde el handheld; requiere acta y autorización en la mesa de incidencias. |
| **RF-025** | El sistema debe rechazar todo bulto cuyo SKU no esté solicitado en la OC de esa cita (R-05). | Debe | Operador de recibo, Comprador | Un bulto con SKU ausente de la OC se rechaza con la causa "SKU no solicitado" y el SKU leído en pantalla. El sistema genera renglón de acta de rechazo y notifica a Compras al sincronizar. |
| **RF-026** | El sistema debe rechazar todo bulto que exceda la cantidad declarada para su SKU en el desglose de esa cita. | Debe | Operador de recibo, Comprador | Con 24 piezas de un SKU declaradas y 24 ya recibidas, el escaneo del bulto 25 se rechaza con la causa "excedente" y muestra declarado contra recibido. El excedente nunca se recibe parcialmente: el bulto se rechaza completo, porque un bulto es un SKU puro con cantidad fija. |
| **RF-027** | El sistema debe rechazar todo bulto cuyo identificador no exista en el desglose de la cita en curso. | Debe | Operador de recibo | Un bulto con identificador válido en el sistema pero perteneciente a otra cita se rechaza con la causa "bulto no corresponde a esta cita". Un identificador inexistente se rechaza con la causa "bulto sin registro". |
| **RF-028** | El sistema debe impedir el inicio de una recepción sin cita confirmada, UUID validado y desglose cargado (R-05). | Debe | Operador de recibo, Vigilancia | Un camión sin cita no genera pase de caseta (RF-012) y el handheld no ofrece recepción para él. Un intento de abrir recepción contra una cita provisional se bloquea indicando el estado del UUID. |
| **RF-029** | El sistema debe mantener, por cada escaneo, un evento idempotente identificado con UUID v4 generado en el dispositivo, de modo que un doble escaneo o una resincronización no dupliquen la recepción. | Debe | Operador de recibo, Administrador | El mismo bulto escaneado dos veces consecutivas produce un solo registro de recepción y un aviso "ya recibido" en el segundo escaneo. Reenviar la cola completa después de reconectar no cambia el conteo recibido. Verificación: cola de 148 eventos enviada tres veces → 148 recepciones. |
| **RF-030** | El sistema debe mantener la máquina de estados del bulto con clave única `(id_bulto, estado)`, de modo que ningún bulto retroceda de estado ni duplique un estado. | Debe | Administrador, Gerencia | Los estados son: ETIQUETADO, EN_TRANSITO, ESCANEADO_ANDEN, RECIBIDO, RECHAZADO, UBICADO, ASIGNADO_EMBARQUE, CARGADO, EMBARCADO, RECIBIDO_SUCURSAL. Una transición no permitida se rechaza con error. Un segundo registro del mismo estado para el mismo bulto falla por restricción de base de datos. |
| **RF-031** | El sistema debe dirigir el bulto a cross-dock (andén de salida) cuando el embarque abierto de su sucursal destino tenga una ocupación ≥70% de posiciones de tarima; en caso contrario debe dirigirlo a acomodo. | Debe | Operador de recibo, Montacarguista | Al aceptar un bulto, el handheld muestra el destino inmediato: "ANDÉN DE SALIDA — embarque SUC-14" o "ACOMODO — ubicación X". Con un embarque de tortón al 58% (7 de 12) el bulto va a acomodo; al 75% (9 de 12) va a cross-dock. El umbral de 70% es parámetro configurable (RF-063). Meta operativa: 25–30% de bultos en cross-dock (KPI). |
| **RF-032** | El sistema debe indicar al montacarguista la ubicación exacta de acomodo, considerando el rack *home* de la sucursal y la zona flex de desborde cuando el rack esté lleno. | Debe | Montacarguista | Con rack *home* disponible, el sistema asigna posición en ese rack. Con rack *home* lleno, asigna posición en zona flex y lo marca como desborde. En ningún caso la respuesta es "piso" o "donde quepa". La confirmación de acomodo requiere escanear la etiqueta de ubicación destino. |
| **RF-033** | El sistema debe permitir registrar un bulto dañado como recepción condicionada, con al menos una evidencia fotográfica capturada desde el dispositivo. | Debe | Operador de recibo, Comprador | No se puede guardar una recepción condicionada sin al menos una fotografía adjunta. La foto queda ligada al identificador del bulto y se sincroniza con el evento. El bulto queda en estado RECIBIDO con marca de condicionado y Compras recibe el aviso. |
| **RF-034** | El sistema debe calcular el delta de faltantes al cerrar la cita y generar automáticamente el Acta de Faltante. | Debe | Operador de recibo, Comprador | Con 148 bultos declarados y 142 recibidos, al cerrar la cita el sistema genera acta con los 6 bultos faltantes desglosados por SKU y cantidad, folio de acta, cita, proveedor, UUID y sello de tiempo. El acta se genera **sin intervención manual**: el operador no puede cerrar la cita y omitir el acta. |
| **RF-035** | El sistema debe cerrar parcialmente la OC cuando exista faltante, notificar a Compras y registrar la solicitud de nota de crédito. | Debe | Comprador | Al generarse el Acta de Faltante, la OC queda en estado "cerrada parcial" con las cantidades efectivamente recibidas, Compras recibe notificación con el folio del acta, y el sistema registra la solicitud de nota de crédito por el monto faltante. La notificación llega el mismo día del cierre de cita. |
| **RF-036** | El sistema debe permitir recibir un bulto cuya sucursal destino en la etiqueta sea incorrecta, reencaminándolo a la sucursal correcta con acta de corrección. | Debe | Operador de recibo, Comprador | El bulto es legítimo (firma válida, SKU solicitado, dentro de cantidad) pero su sucursal no corresponde a lo que indica la OC. El sistema lo recibe, registra la sucursal corregida, genera acta de corrección con el valor original y el corregido, y afecta el componente de exactitud de etiquetado del score del proveedor. |
| **RF-037** | El sistema debe mostrar al operador, durante toda la recepción, el avance de la cita: bultos declarados, recibidos, rechazados y pendientes. | Debe | Operador de recibo | El contador se actualiza con cada escaneo y es legible sin salir de la pantalla de escaneo. Funciona en modo sin red con los datos locales. |
| **RF-038** | El sistema debería registrar el sello de tiempo de inicio y fin real de ocupación del andén para alimentar el KPI de tiempo medio de andén. | Debería | Gerencia, Jefe de embarques | El primer y el último escaneo de la cita, más el cierre, producen sellos de tiempo del servidor. El KPI de tiempo medio de andén se calcula a partir de ellos sin captura manual. |

### 6.4 Momento 4 — Almacenamiento y embarque

| ID | Requisito | Prioridad | Actor | Criterio de aceptación |
|:---|:---|:---|:---|:---|
| **RF-039** | El sistema debe impedir la confirmación de armado de una tarima cuya altura declarada exceda 1.85 m (R-06). | Debe | Montacarguista | Con altura declarada de 1.90 m el sistema bloquea la confirmación y exige redistribuir. Con 1.85 m exactos, la acepta. La altura se declara en la confirmación de armado; el sistema no la mide por sí mismo. |
| **RF-040** | El sistema debe impedir la confirmación de armado de una tarima cuyo peso acumulado exceda 1,000 kg (R-07). | Debe | Montacarguista | El peso acumulado se calcula sumando el peso declarado de los bultos asignados a la tarima. A 1,001 kg el sistema bloquea y señala el bulto que provoca el exceso. A 1,000 kg exactos, acepta. |
| **RF-041** | El sistema debe exigir la confirmación de aplicación de film de seguridad antes de permitir que una tarima se asigne a un embarque (R-08). | Debe | Montacarguista, Jefe de embarques | Una tarima sin confirmación de emplaye no aparece como disponible para asignación a embarque. La confirmación registra usuario y sello de tiempo. No existe forma de asignar una tarima no emplayada sin acta de excepción autorizada. |
| **RF-042** | El sistema debe mostrar un semáforo de consolidación por sucursal calculado sobre **posiciones de tarima** ocupadas de la clase de unidad propuesta, con peso y volumen como restricciones secundarias. | Debe | Jefe de embarques | Para un tortón, el semáforo se calcula como `tarimas_acumuladas / 12`. A 11 de 12 marca verde (≥90%); a 8 de 12 marca amarillo; a 3 de 12 marca rojo. Si el peso acumulado llega a 12,000 kg o el volumen a 28.6 m³ antes de las 11 tarimas, el semáforo marca verde por restricción secundaria e indica cuál se activó. Verificación: el cálculo nunca usa 14,000 kg ni 45 m³. |
| **RF-043** | El sistema debe seleccionar automáticamente la clase de unidad más chica que acomode el inventario acumulado de la sucursal, entre tortón (12 posiciones), rabón (6) y camioneta 3.5 t (3). | Debe | Jefe de embarques | Con 3 tarimas acumuladas propone camioneta (3/3 = 100%). Con 6 propone rabón (6/6 = 100%). Con 11 propone tortón (11/12 = 91.7%). Con 7 propone tortón y lo marca al 58%, por debajo del umbral: el tortón es la unidad más chica que acomoda 7, y el embarque no se libera por regla de llenado hasta llegar a 11. El sistema muestra la unidad propuesta y el porcentaje resultante. |
| **RF-044** | El sistema debe considerar cumplido el umbral de ≥90% con 11 posiciones en tortón, 6 en rabón y 3 en camioneta. | Debe | Jefe de embarques | 11/12 = 91.7% ✓ · 6/6 = 100% ✓ (5.4 redondeado al entero superior) · 3/3 = 100% ✓ (2.7 redondeado al entero superior). La tabla de umbrales es parte de la configuración y se muestra en el tablero. |
| **RF-045** | El sistema debe impedir la liberación de un embarque con llenado inferior al 90% salvo por las excepciones expresamente previstas (R-09). | Debe | Jefe de embarques | Con un tortón a 8 de 12 posiciones, el botón de liberación está deshabilitado y el sistema indica cuántas tarimas faltan. Las únicas vías de liberación por debajo del 90% son RF-046 (antigüedad ≥36 h) y RF-047 (milk-run), ambas con acta. |
| **RF-046** | El sistema debe permitir liberar un embarque por debajo del 90% cuando la tarima más antigua de esa sucursal alcance 36 horas de antigüedad, generando Acta de Excepción. | Debe | Jefe de embarques, Gerencia | A las 36 h de la tarima más vieja, el sistema habilita la liberación y exige el acta. El acta registra: sucursal, folio de embarque, llenado alcanzado, antigüedad de la tarima más vieja, usuario que autorizó, motivo y sello de tiempo. El embarque no se libera sin acta. El acta se reporta a gerencia y alimenta el KPI "embarques con excepción de antigüedad" (meta ≤8%). |
| **RF-047** | El sistema debería proponer un milk-run cuando dos sucursales contiguas en ruta estén ambas por debajo del 90% y ambas rebasen 24 h de antigüedad, generando un QR maestro independiente por sucursal. | Debería | Jefe de embarques | El sistema propone el par, muestra el llenado combinado y, al liberar, genera dos Relaciones de Embarque con QR maestro independiente, una por sucursal. Cada sucursal confirma solo su parte al escanear su QR. La contigüidad en ruta proviene del catálogo de sucursales [POR DEFINIR CON EL CLIENTE: agrupación de sucursales contiguas en ruta]. |
| **RF-048** | El sistema debe generar la Relación de Embarque con folio, sucursal destino, lista de tarimas y bultos, **QR maestro**, **número de sello de seguridad**, kilometraje de salida y espacio de firma del operador. | Debe | Jefe de embarques, Sucursal receptora | El documento generado contiene los ocho elementos. La captura del número de sello es obligatoria: sin ella no se genera el documento. El QR maestro es único por embarque y por sucursal. |
| **RF-049** | El sistema debe entregar la Relación de Embarque impresa y en PDF archivado (R-10). | Debe | Jefe de embarques | La liberación produce impresión en la láser de la oficina de embarques y archiva el PDF ligado al folio de embarque, recuperable por folio, sucursal o fecha. Si la impresora falla, el PDF se genera igual y el sistema registra la falla de impresión sin bloquear la salida. |
| **RF-050** | El sistema debe permitir a la sucursal receptora confirmar la recepción de todo el embarque escaneando el QR maestro. | Debe | Sucursal receptora | Un escaneo del QR maestro cambia el estado de todos los bultos del embarque a RECIBIDO_SUCURSAL y registra sello de tiempo y usuario. Un QR maestro ya conciliado se rechaza como "embarque ya recibido". La sucursal puede además registrar diferencia o daño contra la lista. |
| **RF-051** | El sistema debe entregar los datos que alimentan el Complemento Carta Porte 3.1: permiso SICT, configuración vehicular, placas, aseguradora y número de póliza del transportista. | Debe | Jefe de embarques | Al liberar el embarque, el sistema produce el conjunto de datos completo para el timbrado, en formato consumible por el PAC. Si falta cualquiera de los cinco datos del transportista, el sistema advierte antes de liberar e identifica el faltante. El timbrado lo ejecuta el PAC, no el sistema (FA-07). |
| **RF-052** | El sistema debe mantener y mostrar la antigüedad de la tarima más vieja por sucursal, con alerta anticipada antes de alcanzar las 36 h. | Debe | Jefe de embarques, Gerencia | El tablero muestra la antigüedad por sucursal en horas. El sistema emite alerta a las 30 h (parámetro configurable) y la escala a las 36 h. La alerta llega al jefe de embarques, no solo al tablero. |
| **RF-053** | El sistema debe registrar la ocupación de rack por sucursal y alertar cuando rebase el umbral configurado. | Debería | Jefe de embarques, Gerencia | El tablero muestra ocupación por rack *home* y por zona flex. Objetivo 35–45%; alerta por arriba de 70%. El dato alimenta el KPI de ocupación de rack. |
| **RF-054** | El sistema debe registrar la carga de cada tarima a la unidad mediante escaneo, de modo que el contenido de la Relación de Embarque corresponda a lo efectivamente cargado. | Debe | Montacarguista, Jefe de embarques | Una tarima asignada al embarque pero no escaneada al cargar impide generar la Relación de Embarque hasta resolverse (cargarla o desasignarla). El documento nunca lista una tarima que no se escaneó al cargar. |

### 6.5 Excepciones

| ID | Requisito | Prioridad | Actor | Criterio de aceptación |
|:---|:---|:---|:---|:---|
| **RF-055** | El sistema debe permitir que los handhelds continúen operando en modo degradado por al menos 8 horas si el nodo edge no está disponible. | Debe | Operador de recibo, Administrador | Con el nodo edge apagado, un handheld sincronizado previamente completa recepciones y encola eventos durante 8 h continuas sin pérdida de datos. Al restablecerse el nodo, la cola se vacía sin duplicar (RF-029). Verificación: prueba de 8 h con nodo edge apagado y 500 eventos encolados. |
| **RF-056** | El sistema debe ofrecer una bandeja de excepciones (mesa de incidencias) donde un usuario con rol autorizado resuelva los casos que el handheld no puede cerrar. | Debe | Jefe de embarques, Administrador | Todo rechazo, recepción condicionada, corrección de sucursal, firma inválida y faltante aparece en la bandeja con su causa. Cada caso se cierra con resolución tipificada, usuario y sello de tiempo. Ningún caso se cierra sin resolución registrada. |
| **RF-057** | El sistema debe permitir revertir una recepción registrada por error, con autorización de un rol distinto al que la registró y acta de reversión. | Debe | Jefe de embarques, Administrador | La reversión exige rol autorizado, motivo de catálogo y queda en bitácora con el evento original y el de reversión. El operador que recibió no puede revertir su propio registro. El bulto vuelve al estado anterior según la máquina de estados, sin borrar el historial. |
| **RF-058** | El sistema debe generar acta de rechazo consolidada al cierre de cita, con todos los bultos rechazados y sus causas. | Debe | Operador de recibo, Comprador, Proveedor | El acta lista cada bulto rechazado con su causa tipificada (firma inválida, SKU no solicitado, excedente, sin registro). Se notifica a Compras y al proveedor al sincronizar. El proveedor puede consultarla en el portal. |
| **RF-059** | El sistema debe alertar al administrador cuando la cola de sincronización de un dispositivo rebase 200 eventos pendientes. | Debe | Administrador | Con 201 eventos pendientes se emite alerta identificando el dispositivo, el usuario y la antigüedad del evento más viejo. La alerta llega por el canal configurado, no solo al tablero. |
| **RF-060** | El sistema debería permitir reabrir una cita cerrada por error dentro de una ventana limitada, con autorización y acta. | Debería | Jefe de embarques | La reapertura es posible dentro de una ventana configurable (por omisión 2 h desde el cierre), exige rol autorizado y motivo, e invalida el acta de faltante previa generando una nueva al segundo cierre. Ambas actas quedan en bitácora. |
| **RF-061** | El sistema debe permitir la asignación manual de andén por parte del jefe de embarques cuando exista una contingencia física (andén bloqueado, cortina averiada), registrando el motivo. | Debe | Jefe de embarques | El jefe de embarques puede marcar un andén como no disponible por rango horario; el sistema reprograma o reasigna las citas afectadas y notifica a los proveedores. El motivo queda registrado y los andenes bloqueados no se ofrecen para nuevas citas. |
| **RF-062** | El sistema debería permitir operar una recepción en contingencia total (sin handheld disponible) mediante captura posterior con marca de origen manual. | Podría | Operador de recibo, Administrador | La captura manual exige rol autorizado, queda marcada como "origen manual", no afecta el score de etiquetado del proveedor y se reporta aparte en los KPIs de exactitud, para no mezclar datos escaneados con datos capturados. |

### 6.6 Administración

| ID | Requisito | Prioridad | Actor | Criterio de aceptación |
|:---|:---|:---|:---|:---|
| **RF-063** | El sistema debe permitir configurar, sin modificar código, los parámetros de negocio: umbral de llenado (90%), umbral de cross-dock (70%), SLA de antigüedad (36 h), coeficientes de la fórmula de duración de cita, tolerancia de no-show (15 min), maniobra entre citas (15 min), ventana del andén flex y umbrales de alerta. | Debe | Administrador | Cada parámetro se modifica desde la interfaz de administración, toma efecto sin reinicio y su cambio queda en bitácora con valor anterior, valor nuevo, usuario y sello de tiempo. Verificación: cambiar el umbral de cross-dock de 70% a 60% y comprobar que el siguiente escaneo aplica el nuevo valor. |
| **RF-064** | El sistema debe implementar control de acceso basado en roles, con al menos los perfiles: proveedor, vigilancia, operador de recibo, montacarguista, jefe de embarques, sucursal, comprador, gerencia y administrador. | Debe | Administrador | Cada rol solo accede a las funciones de su perfil. Un operador de recibo no puede liberar embarques ni revertir recepciones; una sucursal solo ve sus propios embarques; un proveedor solo ve sus propias citas y actas. Verificación: matriz rol × función probada en los nueve roles. |
| **RF-065** | El sistema debe registrar en una bitácora inmutable todo evento de negocio relevante, con usuario, dispositivo, sello de tiempo del servidor y datos antes/después del cambio. | Debe | Administrador, Gerencia | La bitácora es de solo inserción: no existe operación de actualización ni de borrado para ningún rol, incluido el administrador. Un intento de modificación falla y queda registrado. Los eventos cubren como mínimo: citas, escaneos, rechazos, actas, liberaciones, cambios de parámetro, cambios de rol y rotaciones de llave. |
| **RF-066** | El sistema debe permitir rotar la llave HMAC de firma de etiquetas conservando la capacidad de validar etiquetas emitidas con llaves anteriores durante un periodo de gracia configurable. | Debe | Administrador | Después de rotar la llave, las etiquetas nuevas se firman con la llave vigente y las emitidas con la anterior siguen siendo válidas durante el periodo de gracia (por omisión 30 días). La rotación queda en bitácora. La llave nunca se almacena en el dispositivo en claro ni se transmite en la etiqueta. |
| **RF-067** | El sistema debe mantener el catálogo de sucursales con su rack *home*, número de posiciones, clase de unidad preferente y agrupación de contigüidad en ruta. | Debe | Administrador | Alta, baja y cambio de sucursal con sus atributos, sin afectar embarques en curso. [POR DEFINIR CON EL CLIENTE: listado de las 32 sucursales, su volumen histórico y su agrupación por contigüidad en ruta]. |
| **RF-068** | El sistema debe mantener el catálogo de proveedores con alta autoservicio supervisada y asignación de credenciales. | Debe | Administrador, Proveedor | Un proveedor se registra, queda en estado pendiente y un administrador lo activa. Solo un proveedor activo agenda citas. La autenticación usa OAuth2/OIDC con autoservicio de recuperación de acceso. |
| **RF-069** | El sistema debe mantener el catálogo de andenes con su tipo (recibo, embarque, flex), su ventana horaria y su estado de disponibilidad. | Debe | Administrador | Cambiar el tipo o la ventana de un andén se refleja de inmediato en la disponibilidad de citas y no invalida citas ya confirmadas sin aviso explícito al proveedor. |
| **RF-070** | El sistema debe mantener el catálogo de clases de unidad con posiciones de tarima, peso máximo, volumen máximo y umbral de llenado. | Debe | Administrador | Las tres clases iniciales son tortón (12 posiciones, 12,000 kg, 28.6 m³, umbral 11), rabón (6, [POR DEFINIR CON EL CLIENTE: peso y volumen], umbral 6) y camioneta 3.5 t (3, [POR DEFINIR CON EL CLIENTE: peso y volumen], umbral 3). Agregar una cuarta clase no requiere cambio de código. |
| **RF-071** | El sistema debe publicar un tablero de KPIs con los nueve indicadores de la propuesta, cada uno con línea base, valor actual y meta. | Debe | Gerencia | El tablero muestra cumplimiento de cita, tiempo medio de andén, llenado promedio por unidad, exactitud de recibo, antigüedad máxima en rack, porcentaje de bultos en cross-dock, ocupación de rack, costo por tarima embarcada y porcentaje de embarques con excepción de antigüedad. Los valores se calculan de los datos operativos, sin captura manual. La columna de línea base se carga con la medición de Fase 0. |
| **RF-072** | El sistema debe exponer una interfaz de integración con el ERP para consultar órdenes de compra y entregar confirmaciones de recepción, con contingencia por archivo plano. | Debe | Administrador, Comprador | La interfaz se publica como contrato versionado (OpenAPI 3.1) que es la única fuente de verdad del intercambio: los tipos del consumidor y las respuestas del proveedor se verifican contra ese mismo archivo. Debe existir además un canal de contingencia por CSV/XML sobre SFTP operable durante al menos 60 días. [POR DEFINIR CON EL CLIENTE: ERP objetivo, su modelo de datos de OC y su mecanismo de autenticación]. |
| **RF-073** | El sistema debe permitir al administrador consultar el estado de salud de la infraestructura: APs, cola de sincronización por dispositivo, estado de la réplica a nube y último respaldo exitoso. | Debe | Administrador | Una sola vista muestra los cuatro indicadores con su sello de tiempo de última actualización. La caída de un AP genera alerta en menos de 2 minutos. |
| **RF-074** | El sistema debería permitir la gestión del enrolamiento de dispositivos en modo dispositivo dedicado (kiosco) y el despliegue remoto de actualizaciones de la app. | Debería | Administrador | Un dispositivo nuevo se enrola y queda bloqueado a la app de operación. Una actualización se despliega a los 16 dispositivos sin recogerlos físicamente. Se implementa con la herramienta de MDM, no con desarrollo propio. |
| **RF-075** | El sistema debería generar un reporte mensual de actas (faltante, rechazo, excepción de antigüedad, corrección, reversión) por proveedor y por sucursal. | Debería | Gerencia, Comprador | El reporte se genera por rango de fechas, es exportable y los totales cuadran con el conteo de actas en bitácora. |

**Resumen de requisitos funcionales**

| Grupo | Rango | Cantidad |
|:---|:---|---:|
| Momento 1 — Agendamiento | RF-001 a RF-015 | 15 |
| Momento 2 — Identificación | RF-016 a RF-022 | 7 |
| Momento 3 — Recepción | RF-023 a RF-038 | 16 |
| Momento 4 — Almacenamiento y embarque | RF-039 a RF-054 | 16 |
| Excepciones | RF-055 a RF-062 | 8 |
| Administración | RF-063 a RF-075 | 13 |
| **Total** | | **75** |

---

## 7. Requisitos no funcionales

Cada requisito trae **métrica** y **método de verificación**. Un requisito no
funcional sin número no se puede aprobar ni rechazar.

### 7.1 Desempeño

| ID | Requisito | Métrica | Cómo se verifica |
|:---|:---|:---|:---|
| **RNF-001** | La validación local de un escaneo en el handheld debe resolverse de forma imperceptible para el operador. | **≤300 ms** desde el intent de DataWedge hasta el aviso visible en pantalla, en el percentil 95, con el dispositivo sin red. | Instrumentación en la app que registre el delta de ambos sellos de tiempo; muestra de 1,000 escaneos en un TC27 con la base local cargada con 5,200 bultos. Se reporta p50, p95 y p99. |
| **RNF-002** | La generación del juego completo de etiquetas de una cita debe permitir que el proveedor imprima sin esperar. | **≤30 s** para 148 etiquetas en un PDF paginado; ≤6 min de impresión física en ZT411. | Medición cronometrada de 10 corridas de 148 etiquetas; se reporta el promedio y el máximo. |
| **RNF-003** | El tablero de consolidación debe reflejar el efecto de un escaneo en el acumulado de la sucursal casi de inmediato. | **≤2 s** desde la confirmación del evento en el nodo edge hasta la actualización visible en el tablero, en el percentil 95. | Prueba con reloj compartido: escaneo instrumentado y captura de video del tablero; 50 repeticiones. |
| **RNF-004** | La validación de unicidad y vigencia del UUID del CFDI al agendar no debe bloquear la operación del portal. | **≤10 s** de espera máxima al servicio del SAT; al vencer, la cita pasa a estado provisional y el reintento es asíncrono. | Prueba con servicio simulado a 1 s, 9 s, 11 s y sin respuesta; se verifica el estado resultante de la cita en los cuatro casos. |
| **RNF-005** | La generación de la Relación de Embarque debe no retrasar la salida de la unidad. | **≤10 s** para generar el PDF con QR maestro; **≤30 s** hasta tener el documento impreso. | Medición cronometrada de 10 liberaciones de embarque de 12 tarimas. |
| **RNF-006** | La sincronización de la cola pendiente al reconectar no debe saturar el dispositivo ni el nodo edge. | **≥50 eventos/s** de drenado de cola, con la app respondiendo a escaneos durante el drenado. | Encolar 1,000 eventos sin red, reconectar y medir tiempo total de drenado mientras se escanean 20 bultos adicionales. |

### 7.2 Disponibilidad y operación degradada

| ID | Requisito | Métrica | Cómo se verifica |
|:---|:---|:---|:---|
| **RNF-007** | La recepción en andén debe continuar funcionando sin internet. | **100%** de las decisiones de aceptación y rechazo resueltas localmente, con **0** pérdidas de evento durante un corte de internet de 8 h. | Desconectar la WAN durante una jornada completa simulada de 35 citas; contar decisiones locales y eventos conciliados al reconectar. |
| **RNF-008** | El handheld debe operar de forma autónoma al menos una jornada si el nodo edge no está disponible. | **≥8 h** de autonomía funcional con cola local; capacidad de cola **≥1,000 eventos** por dispositivo. | Apagar el nodo edge y operar 8 h continuas con 2 dispositivos, encolando ≥500 eventos cada uno; verificar conciliación íntegra al restablecer. |
| **RNF-009** | El nodo edge debe estar disponible durante el horario de operación. | **≥99.5%** de disponibilidad medida en la ventana 8:00–18:00 (equivale a ≤1.3 h de caída al mes). | Monitoreo de latido cada 30 s con Prometheus; reporte mensual de disponibilidad en la ventana operativa. |
| **RNF-010** | La operación debe sobrevivir a un corte eléctrico sin detenerse de inmediato. | **≥30 min** de autonomía del nodo edge, switch y APs con la UPS de 3 kVA; los handhelds mantienen su autonomía de batería. | Prueba de corte real con la UPS en línea, midiendo el tiempo hasta el apagado ordenado. |
| **RNF-011** | La caída de un solo punto de acceso no debe dejar sin cobertura a un pasillo. | **≥2 APs audibles** a ≥−72 dBm en todo punto operativo a 1.2 m del suelo; con un AP apagado, el punto conserva ≥−72 dBm. | Validación post-instalación con medición en sitio (mapa de calor), repetida apagando cada AP de pasillo de uno en uno. |
| **RNF-012** | La pérdida de conexión durante un roaming no debe cortar un escaneo en curso. | **≤50 ms** de interrupción en el traspaso entre APs, con 802.11r/k/v activos. | Medición de roaming caminando el recorrido completo de la nave con herramienta de análisis Wi-Fi; 20 traspasos. |

### 7.3 Capacidad

| ID | Requisito | Métrica | Cómo se verifica |
|:---|:---|:---|:---|
| **RNF-013** | El sistema debe soportar la demanda diaria de citas con el andén flex habilitado. | **36 citas/día** de recibo: (4 andenes × 10 h + 1 andén × 5 h) / 1.25 h, contra 35 requeridas. | Prueba de carga del motor de citas con una agenda sintética de 36 citas que ocupa toda la capacidad; se verifica que la 37ª se rechace por falta de andén y no por error del sistema. |
| **RNF-014** | El sistema debe procesar el volumen de bultos del día pico sin degradación. | **~5,200 bultos/día** (35 camiones × ~148 bultos). Pico por hora: **≥700 eventos de escaneo/h** sostenidos. | Prueba de carga de 5,200 eventos distribuidos en 10 h, con un pico de 700 en una hora; se verifica que p95 de validación local siga ≤300 ms y que ningún evento se pierda. |
| **RNF-015** | El sistema debe soportar la operación de embarque diaria. | **20 embarques/día**, **~156 tarimas/día**, **32 sucursales** con semáforo activo simultáneo. | Prueba con 32 sucursales acumulando tarimas y 20 liberaciones en una jornada simulada; se verifica el tiempo de actualización del tablero (RNF-003). |
| **RNF-016** | El sistema debe soportar la concurrencia de dispositivos y usuarios prevista. | **16 dispositivos** (8 handhelds de andén, 6 de acomodo, 2 VMT) sincronizando a la vez; **35 proveedores** y **10 usuarios internos** concurrentes en el portal y el tablero. | Prueba de concurrencia con 16 clientes sincronizando y 45 sesiones web activas; se verifica que ninguna petición exceda el objetivo de desempeño correspondiente. |
| **RNF-017** | El almacenamiento debe alcanzar para la retención requerida sin intervención. | Volumen estimado: **~1.9 millones de bultos/año** más eventos de estado y fotografías de evidencia. Retención en línea **≥24 meses**; el crecimiento proyectado no debe exceder 60% de la capacidad del SSD en espejo al cierre del año 2. | Cálculo de dimensionamiento documentado y medición del crecimiento real durante el primer trimestre de operación, con proyección actualizada. |

### 7.4 Seguridad

| ID | Requisito | Métrica | Cómo se verifica |
|:---|:---|:---|:---|
| **RNF-018** | La red inalámbrica debe autenticar a cada dispositivo contra un directorio corporativo. | **WPA2-Enterprise con RADIUS**, en modo transición WPA3. **0** redes de operación con clave compartida (PSK). | Auditoría de configuración de la controladora: ninguna SSID de operación con PSK; intento de conexión de un dispositivo no enrolado debe fallar. [POR DEFINIR CON EL CLIENTE: servidor RADIUS y directorio de identidades existentes]. |
| **RNF-019** | La etiqueta de bulto debe ser infalsificable sin la llave del sistema. | **HMAC-SHA256** truncado a 8 bytes en base32 en el 100% de las etiquetas. Tasa de aceptación de una etiqueta con firma alterada: **0%**. | Generar 100 etiquetas con firma alterada aleatoriamente y verificar 100 rechazos en el handheld, en modo sin red. |
| **RNF-020** | La llave HMAC debe estar protegida y ser rotable. | La llave reside **solo** en el nodo edge y en el almacén de llaves del dispositivo (Android Keystore); **0** apariciones de la llave en código fuente, repositorio, archivos de configuración en claro o registros. Rotación con periodo de gracia configurable (por omisión 30 días). | Búsqueda automatizada de secretos en el repositorio y en los registros; prueba de rotación con validación de etiquetas de la llave anterior. |
| **RNF-021** | El acceso debe estar segmentado por rol con el menor privilegio necesario. | Matriz de **9 roles × funciones** cumplida al 100%; **0** funciones accesibles a un rol no autorizado. | Prueba automatizada de autorización que intente cada función con cada rol y verifique el resultado esperado. |
| **RNF-022** | La bitácora debe ser inmutable. | **0** operaciones de actualización o borrado disponibles sobre la bitácora para cualquier rol, incluido el administrador. Encadenamiento por resumen criptográfico de cada registro con el anterior. | Intento de modificación directa en base de datos con el usuario de aplicación: debe fallar. Verificación de la cadena de resúmenes sobre un mes de registros: debe cerrar sin ruptura. |
| **RNF-023** | El tráfico entre dispositivos, nodo edge y nube debe estar cifrado. | **TLS 1.2 o superior** en el 100% de las comunicaciones; **0** endpoints en texto claro. Réplica a nube sobre canal cifrado. | Barrido de puertos y análisis de tráfico; verificación de la configuración de la réplica lógica de PostgreSQL. |
| **RNF-024** | Los dispositivos deben estar bloqueados a la aplicación de operación. | **100%** de los 16 dispositivos en modo dispositivo dedicado (kiosco) bajo MDM; sin acceso a navegador, tienda de aplicaciones ni ajustes del sistema para el usuario operativo. | Inspección de los 16 dispositivos y de la consola de MDM; intento de salir de la app y de instalar otra. |
| **RNF-025** | El sistema no debe exponer datos de un proveedor a otro ni de una sucursal a otra. | **0** fugas entre inquilinos en las pruebas de autorización por identificador: un proveedor que solicite el folio de otro recibe "no encontrado", no "no autorizado". | Pruebas de acceso horizontal con identificadores ajenos sobre todos los recursos de proveedor y de sucursal. |

### 7.5 Usabilidad en andén

| ID | Requisito | Métrica | Cómo se verifica |
|:---|:---|:---|:---|
| **RNF-026** | La aplicación debe ser operable con guantes de trabajo puestos. | **100%** de las acciones del flujo de recepción ejecutables con guante de carnaza o nitrilo, sin gestos de precisión (sin pinza, sin arrastre fino, sin pulsación larga). | Prueba con 3 operadores usando los guantes reales de la operación, ejecutando el flujo completo 10 veces cada uno; se registra cada fallo de toque. |
| **RNF-027** | Los objetivos táctiles deben ser grandes. | **≥44 px** (≥9 mm) de lado para todo control táctil en handheld; **≥72 px** en la terminal de montacargas. | Inspección automatizada del árbol de la interfaz midiendo cada objetivo táctil; ningún control por debajo del mínimo. |
| **RNF-028** | La pantalla debe ser legible bajo luz directa en el andén. | Contraste **≥4.5:1** para texto normal y **≥3:1** para texto grande (WCAG 2.2 AA); tema de alto contraste disponible; tamaño mínimo de texto de dato operativo **≥18 sp**. | Medición de contraste con herramienta de análisis sobre todas las pantallas; prueba de lectura en el andén a mediodía con cortina abierta, con 3 operadores. |
| **RNF-029** | El flujo de recepción de un bulto debe resolverse en pocos toques. | **≤3 toques** desde el escaneo hasta el siguiente bulto en el caso normal (aceptación); **≤5 toques** para un rechazo con causa. | Conteo de toques en el flujo instrumentado, para los cuatro desenlaces (aceptación, rechazo por excedente, rechazo por SKU, rechazo por firma). |
| **RNF-030** | El resultado de un escaneo debe ser inequívoco sin leer texto. | Señal **redundante**: color, icono y vibración o sonido distintos para aceptado y rechazado. El sistema no depende solo del color (accesible para daltonismo). | Inspección de las cuatro combinaciones de desenlace; prueba con simulación de deuteranopía sobre capturas de pantalla. |
| **RNF-031** | Un operador nuevo debe poder operar la recepción con capacitación breve. | **≤2 h** de capacitación para ejecutar el flujo completo sin asistencia; **≤3 pantallas** en el perfil de recepción. | Prueba con 3 operadores sin experiencia previa en el sistema: capacitación de 2 h y luego recepción de 50 bultos con ≤2 consultas al instructor. |
| **RNF-032** | La terminal de montacargas debe operarse sin comprometer la seguridad del operador. | **100%** de las acciones ejecutables con una sola mano y en **≤2 toques**; escaneo del nivel 4 con escáner tethered a **hasta 10 m** sin que el operador descienda. | Prueba en montacargas con 2 operadores ejecutando 20 acomodos a nivel 4; se registra toda acción que obligue a soltar los mandos o a descender. |

### 7.6 Cumplimiento fiscal y legal

| ID | Requisito | Métrica | Cómo se verifica |
|:---|:---|:---|:---|
| **RNF-033** | Todo embarque por autotransporte federal debe poder timbrarse con Complemento Carta Porte 3.1. | **100%** de las Relaciones de Embarque con los cinco datos de transporte completos (permiso SICT, configuración vehicular, placas, aseguradora, póliza) o con advertencia explícita antes de liberar. | Auditoría de un mes de embarques: ninguno liberado sin los cinco datos o sin su advertencia registrada. Prueba de timbrado con el PAC en ambiente de pruebas. |
| **RNF-034** | Todo CFDI de entrada debe quedar validado contra el SAT. | **100%** de los UUID registrados con resultado de consulta al SAT (vigente, cancelado o no encontrado) asentado en bitácora; **0** recepciones iniciadas con UUID en estado desconocido. | Conciliación mensual: cada recepción debe tener su UUID con resultado de consulta y sello de tiempo. |
| **RNF-035** | La evidencia documental debe conservarse por el plazo legal aplicable. | Retención de actas, Relaciones de Embarque y bitácora: **≥5 años** (conservación de documentación fiscal y comprobatoria); **≥24 meses** en línea y el resto en archivo recuperable. | Verificación de la política de retención y prueba de recuperación de un documento del archivo frío. [POR DEFINIR CON EL CLIENTE: plazo de retención que fije el área legal o Contraloría]. |
| **RNF-036** | Los datos personales que el sistema trate deben limitarse a lo necesario y estar protegidos. | **0** datos personales sensibles almacenados. De los operadores de transporte se guarda solo nombre y firma; de los usuarios, identificador y rol. Aviso de privacidad disponible para el proveedor al registrarse. | Inventario de datos personales del sistema revisado contra el principio de minimización; verificación de la existencia del aviso de privacidad. [POR DEFINIR CON EL CLIENTE: aviso de privacidad vigente de la empresa]. |

### 7.7 Mantenibilidad y observabilidad

| ID | Requisito | Métrica | Cómo se verifica |
|:---|:---|:---|:---|
| **RNF-037** | Las reglas de negocio deben ser configurables sin desplegar código. | **≥8 parámetros** de negocio (RF-063) modificables desde la interfaz de administración, con efecto sin reinicio. | Modificar cada parámetro y comprobar su efecto en la siguiente operación, sin desplegar ni reiniciar. |
| **RNF-038** | El código debe tener cobertura de prueba automatizada suficiente para cambiar sin miedo. | **≥80%** de cobertura de línea en la lógica de dominio (motor de citas, validación de escaneo, semáforo de consolidación, selección de unidad, firma HMAC). Las reglas R-01 a R-11 deben tener **al menos una prueba automatizada cada una**. | Reporte de cobertura en la canalización de integración continua; tabla de trazabilidad de restricción a prueba. |
| **RNF-039** | El sistema debe exponer métricas operativas y de infraestructura. | Métricas en Prometheus con visualización en Grafana; **≥15 métricas** incluyendo latencia de validación, profundidad de cola por dispositivo, escaneos por hora, retraso de réplica y estado de AP. Retención de métricas **≥90 días**. | Inspección del tablero de Grafana y de la configuración de retención. |
| **RNF-040** | El sistema debe centralizar registros y errores de forma consultable. | Registros en Loki con retención **≥30 días**; errores de aplicación en Sentry con **100%** de las excepciones no controladas capturadas y agrupadas. | Provocar una excepción controlada en pruebas y verificar que aparece en Sentry en menos de 1 minuto y en Loki con su contexto. |
| **RNF-041** | El sistema debe alertar sobre las condiciones que detienen la operación. | **≥5 alertas** configuradas: caída de AP (≤2 min), cola de sincronización >200 eventos, tarima con antigüedad >36 h, retraso de réplica >15 min, respaldo fallido. Cada alerta con destinatario y canal definidos. | Provocar cada condición en ambiente de pruebas y verificar la recepción de la alerta en el canal configurado. |
| **RNF-042** | El despliegue de una nueva versión no debe detener la operación. | Actualización del nodo edge en **≤15 min** dentro de ventana fuera de horario (18:00–8:00); actualización de la app en los 16 dispositivos de forma remota en **≤1 h** sin recogerlos. | Ensayo de despliegue completo cronometrado, incluido el procedimiento de reversión. |
| **RNF-043** | Debe existir un procedimiento de reversión probado para cada componente. | Reversión de la versión del nodo edge en **≤10 min**; reversión de la app en los dispositivos en **≤30 min**. | Ensayo de reversión cronometrado, ejecutado al menos una vez antes de la puesta en producción. |

### 7.8 Respaldo y recuperación

| ID | Requisito | Métrica | Cómo se verifica |
|:---|:---|:---|:---|
| **RNF-044** | La pérdida de datos tolerable ante una falla del nodo edge debe ser mínima. | **RPO ≤5 minutos** para los datos operativos, logrado con archivado continuo de WAL más réplica lógica a la nube. | Simular pérdida del nodo edge y medir la ventana de datos no replicados sobre una jornada con carga. |
| **RNF-045** | El tiempo de restablecimiento del servicio tras una falla mayor debe permitir no perder la jornada. | **RTO ≤2 horas** para restablecer la operación completa (nodo edge restaurado o conmutado a la nube). Mientras tanto, los handhelds operan en modo degradado (RNF-008), por lo que la **recepción no se detiene**. | Ensayo de recuperación completo: destruir el nodo de pruebas, restaurar desde respaldo y cronometrar hasta la primera recepción válida. |
| **RNF-046** | Los respaldos deben ejecutarse, verificarse y almacenarse fuera de sitio. | Respaldo completo **diario** más WAL continuo con pgBackRest a almacenamiento de objetos; retención **≥30 días** de respaldos diarios y **≥12 meses** de respaldos mensuales. **100%** de los respaldos con verificación de integridad automatizada. | Revisión del registro de respaldos del último mes: ninguno fallido sin alerta y sin reproceso; verificación de integridad asentada. |
| **RNF-047** | La capacidad de restaurar debe probarse periódicamente, no suponerse. | **≥1 ensayo de restauración por trimestre**, con acta de resultado y tiempo medido. | Acta del ensayo trimestral con el tiempo real de restauración y las diferencias encontradas. |
| **RNF-048** | La pérdida o robo de un handheld no debe causar pérdida de datos operativos. | **≤1 jornada** de eventos en riesgo (los que estén en cola local). Borrado remoto disponible vía MDM; la base local cifrada en reposo. | Prueba de borrado remoto en un dispositivo de prueba con cola pendiente; verificación del cifrado en reposo de la base SQLite. |

### 7.9 Interoperabilidad con el ERP

| ID | Requisito | Métrica | Cómo se verifica |
|:---|:---|:---|:---|
| **RNF-049** | El intercambio con el ERP debe regirse por un contrato único, versionado y verificable por ambos lados. | **Un solo** artefacto autoritativo (OpenAPI 3.1) en control de versiones por cada frontera. **0** copias independientes del mismo esquema en wiki, simulaciones o código escrito a mano. Los tipos del consumidor se **generan** del contrato. | Revisión del repositorio: existe el artefacto, los tipos son generados y la canalización de integración continua valida contra él. Las respuestas reales del proveedor se validan contra el mismo archivo, no solo los tipos de compilación. |
| **RNF-050** | La indisponibilidad del ERP no debe detener la recepción. | **≥60 días** de operación posible con el canal de contingencia por archivo plano (CSV/XML sobre SFTP). Una caída del ERP de hasta 24 h no impide agendar ni recibir contra las OC ya descargadas. | Prueba con el ERP simulado apagado 24 h: se agenda y se recibe contra OC previamente sincronizadas; al restablecer, las confirmaciones se entregan sin duplicar. |
| **RNF-051** | Las confirmaciones de recepción entregadas al ERP deben ser idempotentes. | Reenviar la misma confirmación **N veces** produce **un solo** efecto en el ERP, por llave de idempotencia. | Enviar la misma confirmación 5 veces contra el ERP simulado y verificar un solo registro. |
| **RNF-052** | La latencia de intercambio con el ERP debe permitir que Compras se entere el mismo día. | Confirmación de recepción y actas entregadas al ERP en **≤15 min** desde el cierre de cita, con el enlace disponible. | Medición sobre 20 cierres de cita del tiempo entre el cierre y la confirmación aceptada por el ERP. |
| **RNF-053** | Todo cambio en el contrato con el ERP debe pasar por revisión de ambos lados antes de integrarse. | **0** cambios de implementación que precedan al cambio del contrato. Un cambio que rompa compatibilidad debe traer plan de versión o migración. | Revisión del historial del repositorio: cada cambio de forma de carga útil tiene primero el cambio del contrato, con aprobación de los responsables de ambos lados. [POR DEFINIR CON EL CLIENTE: responsable del lado del ERP]. |

**Resumen de requisitos no funcionales**

| Categoría | Rango | Cantidad |
|:---|:---|---:|
| Desempeño | RNF-001 a RNF-006 | 6 |
| Disponibilidad y operación degradada | RNF-007 a RNF-012 | 6 |
| Capacidad | RNF-013 a RNF-017 | 5 |
| Seguridad | RNF-018 a RNF-025 | 8 |
| Usabilidad en andén | RNF-026 a RNF-032 | 7 |
| Cumplimiento fiscal y legal | RNF-033 a RNF-036 | 4 |
| Mantenibilidad y observabilidad | RNF-037 a RNF-043 | 7 |
| Respaldo y recuperación | RNF-044 a RNF-048 | 5 |
| Interoperabilidad con el ERP | RNF-049 a RNF-053 | 5 |
| **Total** | | **53** |

---

## 8. Criterios de aceptación del sistema

El proyecto se da por entregado cuando **todas** estas condiciones se cumplen y
están documentadas con evidencia. Son pocas a propósito: cada una resume un
conjunto de requisitos y se liga a un KPI de la propuesta.

| ID | Condición de entrega | Evidencia requerida | KPI ligado |
|:---|:---|:---|:---|
| **CA-01** | **La línea base está medida.** Los nueve KPIs tienen valor de línea base documentado de la Fase 0, incluido el llenado real actual de las unidades. | Acta de medición de Fase 0 con metodología y muestra. | Todos |
| **CA-02** | **El motor de citas absorbe la demanda.** El sistema programa 36 citas/día con andén 5 flex, sin traslape en ningún andén y con duración calculada por fórmula. | Agenda de 2 semanas de operación real sin traslapes; prueba de capacidad de RNF-013. | Cumplimiento de cita ≥92% |
| **CA-03** | **Ninguna entrega entra con folio repetido ni CFDI inválido.** 100% de las citas confirmadas tienen UUID único y con resultado de consulta al SAT. | Conciliación de un mes: cero UUID duplicados, cero recepciones con UUID en estado desconocido. | Exactitud de recibo |
| **CA-04** | **La recepción opera sin internet.** Una jornada completa de recepción se ejecuta con la WAN desconectada, sin perder un solo evento. | Acta de prueba de corte de 8 h con conteo de eventos conciliados (RNF-007, RNF-008). | Tiempo medio de andén ≤70 min |
| **CA-05** | **La etiqueta es infalsificable y el bulto es puro.** Cero etiquetas con firma alterada aceptadas; cero etiquetas generadas con más de un SKU. | Prueba de 100 firmas alteradas con 100 rechazos; prueba de bloqueo de bulto multi-SKU. | Exactitud de recibo ≥99.5% |
| **CA-06** | **Los cuatro desenlaces de rechazo funcionan en el andén.** Excedente, SKU no solicitado, firma inválida y bulto sin registro se rechazan con causa y generan acta. | Guion de prueba ejecutado con los cuatro casos y sus actas generadas. | Exactitud de recibo ≥99.5% |
| **CA-07** | **El faltante se detecta el mismo día.** Toda cita con faltante genera Acta de Faltante automática, cierre parcial de OC y notificación a Compras dentro de la jornada. | Un mes de cierres de cita: 100% de los faltantes con acta y notificación en ≤15 min (RNF-052). | Exactitud de recibo ≥99.5% |
| **CA-08** | **El cross-dock está operando.** Al menos 25% de los bultos recibidos se dirigen a andén de salida sin tocar rack, por decisión del sistema. | Reporte de dirección de acomodo de un mes de operación. | % bultos en cross-dock ≥25% |
| **CA-09** | **Ninguna unidad sale por debajo del 90% sin acta.** 100% de las salidas con llenado ≥90% medido sobre posiciones de tarima, o con Acta de Excepción de antigüedad registrada y reportada. | Reporte de embarques del mes contra actas de excepción; cero salidas sin una de las dos condiciones. | Llenado promedio ≥90% · Excepciones ≤8% |
| **CA-10** | **Ninguna tarima pasa de 36 h sin atención.** La antigüedad máxima en rack no excede 36 h, o la excepción está documentada. | Reporte de antigüedad diaria del mes. | Antigüedad máxima ≤36 h |
| **CA-11** | **Toda salida lleva Relación de Embarque completa.** 100% de los embarques con documento impreso y en PDF, con QR maestro, número de sello, kilometraje y firma, y con los cinco datos de Carta Porte 3.1 completos o advertidos. | Auditoría de un mes de Relaciones de Embarque. | Costo por tarima −35% |
| **CA-12** | **La sucursal confirma con un escaneo.** 100% de los embarques conciliados en destino por escaneo del QR maestro, salvo los casos documentados de contingencia. | Reporte de conciliación en destino del mes. | Exactitud de recibo |
| **CA-13** | **El andén es usable con guantes y bajo luz directa.** Prueba de usabilidad aprobada por 3 operadores reales: flujo de 3 toques, objetivos ≥44 px, contraste ≥4.5:1. | Acta de prueba de usabilidad con los hallazgos y su resolución (RNF-026 a RNF-031). | Tiempo medio de andén ≤70 min |
| **CA-14** | **La operación es auditable.** Bitácora inmutable con cadena de resúmenes verificable sobre un mes completo, y matriz de 9 roles probada sin accesos indebidos. | Verificación de la cadena de bitácora y reporte de pruebas de autorización. | — |
| **CA-15** | **La recuperación está probada, no supuesta.** Ensayo de restauración completo ejecutado con RPO ≤5 min y RTO ≤2 h medidos. | Acta del ensayo de recuperación con tiempos reales. | — |
| **CA-16** | **La integración con el ERP está verificada contra un contrato único.** Tipos generados del contrato, respuestas reales validadas contra el mismo artefacto, y contingencia por archivo plano probada. | Reporte de la canalización de integración continua y acta de prueba de contingencia de 24 h. | — |
| **CA-17** | **La red cumple los criterios de diseño medidos en sitio.** Validación post-instalación con ≥−65 dBm primario, ≥−72 dBm secundario, SNR ≥25 dB y ≥2 APs audibles en todo punto operativo a 1.2 m. | Reporte de site survey de validación con mapa de calor. | — |

---

## 9. Limitaciones conocidas

Estas limitaciones son reales y se declaran antes de que alguien las descubra.
Ninguna invalida el proyecto; todas cambian lo que se puede prometer.

| ID | Limitación | Alcance del problema | Qué se hace al respecto |
|:---|:---|:---|:---|
| **L-01** | **El ROI depende de un llenado actual que nadie ha medido.** Todo el caso de negocio de flete —$282,620 al mes en el caso base— se sostiene en el supuesto A-03 de que hoy se carga al 65%. El punto de equilibrio está en ~80%: por arriba de eso, **el ahorro de flete no existe** y el escenario adverso (85%) da flujo neto negativo. | Es la limitación más grave del documento. No es un detalle de estimación: es la diferencia entre un payback de 5.4 meses y un proyecto que no se paga. | La Fase 0 mide el llenado real antes de comprometer el 97% del CAPEX, y es una puerta de decisión que **puede cancelar el proyecto**. Si el llenado ya es alto, el proyecto se justifica por exactitud, cumplimiento de Carta Porte y capacidad de crecer sin contratar — beneficios reales pero mucho más difíciles de monetizar ante un comité. |
| **L-02** | **El número y la posición de los 16 APs son predictivos.** El diseño está hecho por criterio de pasillo, no por medición en sitio. Las coordenadas, canales y potencias de la propuesta son una hipótesis razonada, no un resultado. | El CAPEX de red ($420,000 entre APs, controladora, switching y cableado) puede moverse al alza o a la baja. También puede cambiar el cableado, que es lo más caro de corregir después. | El site survey predictivo con validación post-instalación está presupuestado en Fase 0 ($55,000). Hasta que no exista su reporte, cualquier cifra de red de este documento debe leerse como estimación. CA-17 exige la validación medida como condición de entrega. |
| **L-03** | **La adopción de los 35 proveedores es el riesgo principal del proyecto.** El sistema puede estar perfecto y fracasar si los proveedores no etiquetan. No es un riesgo técnico; es de gestión del cambio, y está fuera del control del equipo de desarrollo. | Si una fracción relevante no etiqueta, la identificación se desplaza al CEDIS: el kiosco de caseta se vuelve cuello de botella, hay que agregar una impresora y personal, y el tiempo de andén se dispara en lugar de bajar. | Kiosco de impresión en caseta, tres meses de convivencia con proceso manual, score con prioridad de cita como incentivo, y onboarding presencial a los 10 proveedores que concentran ~60% del flujo. Aun así, **el riesgo no se elimina**: se administra. |
| **L-04** | **La integración con el ERP no está especificada porque no se conoce el ERP.** No hay nombre de producto, versión, modelo de datos de OC, mecanismo de autenticación ni responsable del lado del ERP. Los requisitos RF-072 y RNF-049 a RNF-053 describen *cómo debe comportarse* la integración, no *cómo se implementa*. | Es el riesgo de calendario más probable del proyecto. Un ERP cerrado, sin interfaz de programación o sin proveedor disponible puede atrasar la Fase 2 por meses. | Se exige cerrar el contrato con el proveedor del ERP **antes de iniciar la Fase 2**, y se diseña una contingencia por archivo plano (CSV/XML sobre SFTP) para 60 días. En este documento, todo lo específico del ERP queda marcado como **[POR DEFINIR CON EL CLIENTE]**. |
| **L-05** | **La regla del ≥90% y el SLA de 36 h están en tensión y el sistema no la elimina: la hace visible.** Una sucursal de la cola larga acumula ~2.6 tarimas/día; para llenar un tortón al 90% necesitaría 4.2 días. La flota heterogénea baja ese tiempo a ~2.3 días con rabón, pero no a cero. | Cuando ni la unidad más chica alcanza el 90% dentro de 36 h, el sistema **libera por debajo del 90%** con Acta de Excepción. Eso significa que el reto se cumple en el 100% de los casos normales, pero existe una categoría de salidas que no cumple la regla y queda registrada. | La excepción es explícita, requiere autorización, genera acta, se reporta a gerencia y tiene un KPI con meta (≤8% de los embarques). La alternativa —cumplir el 90% sin excepción— significa desabasto en piso de venta de las sucursales chicas, que es un costo mayor y no auditable. Se eligió hacer el conflicto visible en lugar de ocultarlo. |
| **L-06** | **El prototipo usa datos sintéticos.** No hay conexión real al servicio del SAT, al ERP ni al PAC de timbrado. Las órdenes de compra, el padrón de proveedores, el catálogo de sucursales y el histórico de volumen son generados. | Lo que el prototipo demuestra es **comportamiento de reglas**: cálculo de duración de cita, detección de traslape, validación de firma, los cuatro desenlaces de rechazo, el semáforo sobre posiciones de tarima, la selección de unidad y el acta de faltante. Lo que **no** demuestra es latencia real contra el SAT, forma real de los datos del ERP ni timbrado real. | Se declara el alcance del prototipo por adelantado (supuesto A-16) y se separan en los criterios de aceptación las condiciones verificables con datos sintéticos de las que exigen ambiente real (CA-03, CA-11, CA-16). |
| **L-07** | **Los precios son referenciales de mercado, no cotizaciones.** Todo el CAPEX de $1,745,856 está a precios de referencia de noviembre de 2026, sin IVA, y requiere cotización formal de distribuidor autorizado. | El rango real del hardware es amplio: la Zebra TC27 se lista entre $15,990 y $27,480 con IVA según configuración y distribuidor. La contingencia de 12% cubre variaciones moderadas, no un cambio de banda. | Cotización formal en Fase 0, antes de liberar el proyecto. La contingencia del 12% está presupuestada precisamente por esto. |
| **L-08** | **Los umbrales de usabilidad son estándares, no están validados con los operadores reales de este CEDIS.** Los 44 px, el contraste de 4.5:1 y el flujo de 3 toques provienen de WCAG 2.2 y de buena práctica de dispositivos industriales, no de una prueba con la cuadrilla que va a usar el sistema. | Un guante más grueso de lo previsto, una condición de luz específica del andén 3 o una talla de mano distinta pueden invalidar un umbral que en papel se ve correcto. | CA-13 exige prueba de usabilidad con 3 operadores reales, con guantes reales, en el andén real, como condición de entrega. Los hallazgos se resuelven antes de la aceptación. |
| **L-09** | **El dimensionamiento de personal y de montacargas queda fuera de este documento.** El cálculo de la propuesta (~312 movimientos/día, 31/h, rendimiento de 20–25/h por montacarguista, 2 montacargas simultáneos) es un insumo de diseño, no un requisito del sistema. | Si el CEDIS no dispone de 2 montacargas simultáneos, el sistema dirigirá movimientos que la operación no puede ejecutar y la cola de acomodo crecerá sin importar qué tan bueno sea el software. | Se declara como dependencia operativa. El KPI de antigüedad en rack lo delatará en operación, pero más vale resolverlo antes. [POR DEFINIR CON EL CLIENTE: número de montacargas y de operadores disponibles por turno]. |

---

## 10. Trazabilidad

Cada momento de la operación, con los requisitos funcionales que lo realizan, el
KPI que lo mide y el criterio de aceptación que lo cierra.

| Momento de la operación | Requisitos funcionales | KPI que lo mide | Meta | Criterio de aceptación |
|:---|:---|:---|:---|:---|
| **1 · Agendamiento** — reservar andén con folio único y duración calculada | RF-001 a RF-015 | Cumplimiento de cita | ≥92% | CA-02, CA-03 |
| **1 · Agendamiento** — capacidad de andén | RF-007, RF-008, RF-011, RF-013, RF-061 | Citas atendidas / citas requeridas | 36 / 35 por día | CA-02 |
| **2 · Identificación** — un bulto, un SKU, una etiqueta firmada | RF-016 a RF-022 | Exactitud de etiquetado (componente del score de proveedor) | ≥98% | CA-05 |
| **3 · Recepción** — validar en andén, sin red, con los cuatro rechazos | RF-023 a RF-030, RF-037 | Exactitud de recibo | ≥99.5% | CA-04, CA-05, CA-06 |
| **3 · Recepción** — tiempo de ocupación del andén | RF-023, RF-029, RF-037, RF-038 | Tiempo medio de andén | ≤70 min | CA-04, CA-13 |
| **3 · Recepción** — faltantes y excedentes detectados a tiempo | RF-026, RF-034, RF-035, RF-058 | Exactitud de recibo · actas del mismo día | ≥99.5% · ≤15 min | CA-07 |
| **3 · Recepción** — cross-dock dirigido | RF-031 | % bultos en cross-dock | ≥25% | CA-08 |
| **4 · Almacenamiento** — ubicación dirigida y zona flex | RF-032, RF-039 a RF-041, RF-053 | Ocupación de rack | 35–45% (alerta >70%) | CA-10 |
| **4 · Embarque** — consolidación y llenado | RF-042 a RF-045, RF-054 | Llenado promedio por unidad | ≥90% | CA-09 |
| **4 · Embarque** — antigüedad y excepción | RF-046, RF-047, RF-052 | Antigüedad máxima en rack · embarques con excepción | ≤36 h · ≤8% | CA-09, CA-10 |
| **4 · Embarque** — documento, sello y conciliación | RF-048 a RF-051 | Costo por tarima embarcada | −35% | CA-11, CA-12 |
| **Excepciones** — operación degradada y mesa de incidencias | RF-055 a RF-062 | Eventos perdidos por corte de red | 0 | CA-04, CA-15 |
| **Administración** — auditoría, roles y parámetros | RF-063 a RF-070, RF-073 a RF-075 | Integridad de bitácora · accesos indebidos | cadena sin ruptura · 0 | CA-14 |
| **Administración** — medición y tablero | RF-071 | Los nueve KPIs con línea base | 9 / 9 cargados | CA-01 |
| **Administración** — integración con el ERP | RF-072 | Latencia de confirmación al ERP | ≤15 min | CA-16 |

### Trazabilidad inversa: restricción del reto → requisito → prueba

| Restricción | Requisito que la hace cumplir | Prueba que la verifica |
|:---|:---|:---|
| R-01 · Cita mínima 1 h | RF-005, RF-009 | Tabla de 5 valores de `n_bultos` incluido n = 54 |
| R-02 · Un andén, una entrega | RF-007 | 6 casos de traslape |
| R-03 · Folio único | RF-002, RF-003 | Unicidad por restricción de base de datos + 4 casos de consulta al SAT |
| R-04 · Un SKU por bulto | RF-018 | Carga con bulto multi-SKU → rechazada, 0 etiquetas |
| R-05 · No se recibe lo no solicitado | RF-025, RF-027, RF-028 | 3 casos de rechazo en handheld sin red |
| R-06 · Altura ≤1.85 m | RF-039 | Casos 1.85 m (acepta) y 1.90 m (bloquea) |
| R-07 · Tarima 1,000 kg | RF-040 | Casos 1,000 kg (acepta) y 1,001 kg (bloquea) |
| R-08 · Film de seguridad | RF-041 | Tarima sin emplaye no asignable a embarque |
| R-09 · ≥90% de llenado | RF-042 a RF-046 | Casos 8/12 (bloquea), 11/12 (libera), 8/12 con 36 h (libera con acta) |
| R-10 · Relación de Embarque impresa y en PDF con QR | RF-048, RF-049, RF-050 | Auditoría de un mes de documentos + conciliación en destino |
| R-11 · Horario 8:00–18:00 | RF-013, RF-008 | Citas fuera de ventana rechazadas; andén flex solo 8:00–13:00 |

---

## Anexo — Marcadores pendientes de definición

Todo lo que este documento no sabe, en un solo lugar.

| Marcador | Dónde aparece | Quién lo resuelve |
|:---|:---|:---|
| Agrupación de las 32 sucursales por contigüidad en ruta | RF-047, RF-067 | Distribución |
| Listado de las 32 sucursales con volumen histórico | RF-067 | Operaciones / ERP |
| Peso y volumen máximos de rabón y camioneta 3.5 t | RF-070 | Transporte (medición física de cajas) |
| ERP objetivo, modelo de datos de OC y autenticación | RF-072, RNF-049 | Sistemas |
| Responsable del lado del ERP para revisión de contrato | RNF-053 | Sistemas |
| Servidor RADIUS y directorio de identidades existentes | RNF-018 | Sistemas / Redes |
| Plazo de retención documental que fije Legal o Contraloría | RNF-035 | Legal / Contraloría |
| Aviso de privacidad vigente de la empresa | RNF-036 | Legal |
| Número de montacargas y operadores disponibles por turno | L-09 | Operaciones |
| Línea base de los nueve KPIs | CA-01, RF-071 | Fase 0 |
