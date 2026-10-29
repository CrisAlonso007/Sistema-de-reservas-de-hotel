# **Sistema de Reservas de Hotel — Módulo de Recepción**

Aplicación de escritorio para la gestión de catálogo de habitaciones y estancias,
destinada al **uso interno del personal del hotel** (recepcionistas y administradores).

## Modelo operativo

El sistema funciona como una terminal de recepción, no como un portal web:

- **El huésped no es un usuario.** No tiene cuenta, no se autentica y no accede a la
  aplicación. El recepcionista captura sus datos directamente como atributos de la
  transacción en la tabla `Reserva`.
- **El acceso es exclusivo del personal.** El administrador da de alta las cuentas
  desde la interfaz o con el script SQL inicial. Además, la pantalla de acceso ofrece
  **Crear cuenta**, que da de alta al momento una cuenta que siempre recibe el rol de
  **recepcionista** (desde ahí no se pueden crear administradores).
- **Trazabilidad.** Cada reserva guarda el `empleado_id` que la registró, el que
  registró el ingreso (`checkin_empleado_id`) y el que registró la salida
  (`salida_empleado_id`).
- **Ocupación en tiempo real.** El estado de cada habitación (`Disponible`, `Reservado`,
  `Ocupado`, `Mantenimiento`) se calcula con una consulta sobre `Reserva`, por lo que no
  existe una tabla de estado que pueda quedar desincronizada.
- **La habitación se libera cuando el recepcionista registra la salida, no por
  calendario.** Mientras una estancia está en estado `Iniciada` el huésped ocupa la
  habitación, y solo `Registrar salida` la devuelve a `Disponible`. Por eso un huésped
  con salida programada para hoy sigue apareciendo en «Huéspedes alojados» y su
  habitación no se ofrece para esa noche: de lo contrario se podría vender dos veces.
  Quien se pase de los días previstos también sigue bloqueando la habitación, y una
  reserva `Pendiente` nunca se libera sola, porque la habitación sí queda reservada.

## Arquitectura y tecnologías

* Lenguaje: Python 3.10+
* Interfaz gráfica: PySide6 (Qt6 para Python)
* Base de datos: MySQL 8.0 (InnoDB)
* Conectores: mysql-connector-python y PyMySQL (SQLAlchemy)
* ORM: SQLAlchemy 2.x con modelos y relaciones para usuarios, habitaciones,
  reservas, pagos y configuración
* Procesamiento en segundo plano: QThread para cargar el historial sin bloquear
  la interfaz
* Exportación de reportes: Excel con openpyxl y PDF con ReportLab

**Patrón por capas (UI → Service → DAO):**

```
main.py                  Orquestador de sesión y ciclo de vida de ventanas
DATABASE/
  conexion.py            Configuración y conexión única reutilizable
  conexion_orm.py        Motor SQLAlchemy y fábrica de sesiones
  models.py              Modelos ORM y relaciones del esquema existente
  usuario_dao.py         Personal del hotel (autenticación y gestión de cuentas)
  habitacion_dao.py      Catálogo y ocupación calculada
  reserva_dao.py         Estancias, ingresos, salidas, cancelación y reportes
  BD_Registro.sql        Esquema y datos iniciales (incluye Configuracion)
services/
  autenticacion_service.py  Gestión de cuentas del personal
  habitacion_service.py     Catálogo, ocupación y tarifas por tipo
  reserva_service.py        Reglas de estancia, cobros y reportes
  hilo_historial.py          Consulta del historial mediante QThread y señales
  exportador_excel.py        Exportación de pagos y resumen a Excel
  generador_pdf.py           Generación del reporte de pagos en PDF
ui/
  login_window.py           Acceso del personal y alta de cuenta de recepción
  main_window.py            Shell: banner + pila de paneles
  banner_navegacion.py      Cabecera: navegación, campana de avisos y menú de sesión
  panel_dashboard.py        Tablero: KPIs, resumen del día y mesas operativas
  panel_catalogo.py         Listado de habitaciones
  panel_pagos_reportes.py   Módulo único «Pagos y reportes» con pestañas por rol
  panel_pagos.py            Pestaña «Cobros»: saldos y estado de cuenta
  panel_reportes.py         Pestaña «Reportes» (solo administrador)
  panel_notificaciones.py   Popup de avisos de cobro y estadías vencidas
  tabla_reservas.py         Mesa reutilizable de reservas con acciones
  admin_window.py           Alta y edición de habitaciones (solo admin)
  ventana_administracion.py «Configuración del hotel»: parámetros y personal
  detalle_habitacion.py     Ficha de habitación y acceso al alta de huésped
  registro_huesped.py       Formulario único de registro de huésped
  components.py             Tarjetas reutilizables: catálogo y KPIs
  dialogs.py                Diálogos: edición de reserva, cobro y extensión de estadía
  historial_huespedes.py    Historial de estancias de un huésped
utils/
  seguridad.py              Hash de contraseñas y autorización por sesión y rol
  validaciones.py           Reglas de validación de entrada
  stylesheets.py            Estilos visuales
recursos/                   Imagen por defecto de las habitaciones
```

## Puesta en marcha

1. Instalar dependencias: `pip install -r requirements.txt`
2. Crear la base de datos ejecutando `DATABASE/BD_Registro.sql` en MySQL 8.0+.
3. Arrancar con `python main.py`.

### Credenciales iniciales

| Usuario      | Contraseña     | Rol            |
|--------------|----------------|----------------|
| `recepcion`  | `recepcion2026`| recepcionista   |
| `admin`      | `admin2026`    | administrador   |

> Cambie estas contraseñas antes de usar el sistema en producción. Para generar el
> hash de una nueva contraseña: `utils.seguridad.generar_hash("mi_clave")`.

### Configuración de la conexión

Los parámetros se leen de variables de entorno, con los valores actuales como
alternativa por defecto:

`DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`

Los modelos SQLAlchemy representan las tablas existentes y sus relaciones. El
historial de reservas y la configuración del hotel ya usan sesiones ORM. Las
operaciones críticas de registro, cambios de estado y cobros continúan con
`mysql-connector-python` y sus transacciones actuales; la migración es gradual
para conservar las reglas del sistema. No se crean tablas automáticamente:
primero se ejecuta `DATABASE/BD_Registro.sql`.

La ventana de historial usa un `QThread` con señales para actualizar el estado,
entregar resultados y reportar errores sin modificar widgets desde el hilo de
trabajo. Si se cancela una carga durante una consulta a MySQL, se descartan sus
resultados al terminar la consulta; no se interrumpe la operación de base de
datos a mitad de ejecución.

La pestaña administrativa «Reportes» permite exportar los pagos realizados
dentro del rango seleccionado a Excel (`.xlsx`) o PDF (`.pdf`). Ambos formatos
incluyen el detalle de cada pago, el total recibido, la cantidad de pagos y el
resumen diario, además del desglose de cantidad e importe por método de pago.
Se selecciona la ubicación del archivo al exportar.

## Navegación y permisos

La barra superior ofrece tres destinos comunes a ambos roles: **Inicio**,
**Catálogo** y **Pagos y reportes**. La campana de avisos y el menú de sesión
(nombre, rol, **Cerrar sesión**) también están siempre visibles; bajo «Cerrar
sesión» aparece **Configuración del hotel**, reservado al administrador.

| Acción                        | Recepcionista | Administrador |
|-------------------------------|:-------------:|:-------------:|
| Iniciar sesión                | Sí            | Sí            |
| Ver ocupación en tiempo real  | Sí            | Sí            |
| Registrar estancia de huésped | Sí            | Sí            |
| Registrar ingreso / salida    | Sí            | Sí            |
| Cancelar reservas             | Sí            | Sí            |
| Cobrar una estancia           | Sí            | Sí            |
| Publicar / editar / eliminar habitaciones | No | Sí            |
| Marcar habitación en mantenimiento | No       | Sí            |
| Editar fechas / habitación de una reserva | No | Sí        |
| Forzar salida con saldo pendiente | No       | Sí            |
| Reactivar una reserva cancelada | No          | Sí            |
| Cancelar una estancia ya iniciada | No        | Sí            |
| Editar los parámetros del hotel | No          | Sí            |
| Gestionar el personal          | No           | Sí            |
| Ver reportes de ocupación e ingresos | No     | Sí            |

Las acciones de ingreso y salida («Marcar como ocupada» y «Registrar salida»)
aparecen en las mesas del tablero. «Marcar como ocupada» deja claro que solo
cambia el estado de la reserva: el huésped no se registra ahí, eso ocurre al dar
de alta la estancia.

## Registro de huésped

El alta del huésped es la operación más frecuente de la recepción, así que se
resuelve en un **formulario único** (`ui/registro_huesped.py`) alcanzable desde
tres puntos de entrada:

- el botón **+ Registrar Huésped** del tablero,
- el botón de la ficha de una habitación, que abre el formulario con esa
  habitación ya seleccionada.

El formulario:

- lista solo las habitaciones libres para el tramo de fechas elegido y vuelve a
  consultarlo al cambiar la fecha o el número de noches, avisa si la habitación
  seleccionada deja de estar libre y deshabilita el registro si no queda ninguna;
- calcula la fecha de salida y el total, y muestra el desglose por noche;
- valida los datos del huésped antes de enviar, marcando en rojo los campos
  incorrectos y enfocando el primero pendiente;
- ofrece un selector **Tipo de estancia** con dos opciones: **Hospedaje inmediato**
  (el huésped entra hoy, la habitación queda ocupada y aparece en «Huéspedes
  alojados») o **Reserva** (la habitación queda apartada para la fecha elegida y
  el huésped se aloja al registrar su ingreso el día de llegada). El hospedaje
  inmediato solo se ofrece con entrada hoy, y fija la fecha al día en curso.

El total nunca se envía desde la interfaz: lo calcula el servidor a partir del
precio del catálogo, dentro de la misma transacción que valida el solapamiento
de fechas.

## Ciclo de una estancia

```
        Registrar Huésped                 Marcar como ocupada
   (Hospedaje inmediato) ─────────────▶ estado = Iniciada ──┐
   (Reserva) ──▶ Pendiente ─────────────────────────────────┤
                                                               ▼
                                     habitacion = Ocupado  ◀── el recepcionista
                                                               │   lo ve en
                                                               │   «Huéspedes alojados»
                                                               ▼
                                                     Registrar salida
                                                               │
                                                               ▼
                                                   estado = Finalizada
                                                   habitacion = Disponible
```

* El **hospedaje inmediato** nace ya en `Iniciada`: el huésped ya está dentro, así que
  la habitación queda ocupada desde el primer momento.
* Una **reserva** nace en `Pendiente`: la habitación queda reservada, no ocupada, y no
  aparece en «Huéspedes alojados» hasta que se marque como ocupada.
* Un ingreso o una salida actualizan las mesas del tablero, el catálogo y los
  cobros en el momento, sin esperar al refresco periódico.
* Cancelar una reserva solo es posible mientras está `Pendiente` (el administrador
  además puede anular una estancia ya iniciada y reactivar una cancelada).

## Tablero (Inicio)

El tablero (`ui/panel_dashboard.py`) reúne, en este orden:

1. **KPIs de ocupación**: total de habitaciones, disponibles, ocupadas hoy,
   reservadas y en mantenimiento.
2. **Cuentas por cobrar · huéspedes alojados**: total adeudado por los huéspedes
   que están dentro y el desglose por habitación y saldo. **El nombre de cada
   huésped es un enlace**: al pulsarlo se salta a la ventana de **Pagos y
   reportes**, en la pestaña Cobros, con la tabla ya filtrada por ese huésped y
   su botón **Cobrar** a mano.
3. **Reservas pendientes** y **Huéspedes alojados**: dos mesas con sus acciones
   de ingreso y salida. Las mesas comparten `ui/tabla_reservas.py`.

## Pagos y reportes

`ui/panel_pagos_reportes.py` es un módulo único con pestañas según el rol:

- **Cobros** (`ui/panel_pagos.py`): para ambos roles. Lista las reservas vigentes
  con su total, pagado, saldo y estado de cuenta, con buscador por huésped,
  habitación o documento, y un botón que abre el diálogo de cobro
  (`ui/dialogs.py`). Registrar un cobro actualiza el saldo al instante.
- **Reportes** (`ui/panel_reportes.py`): **solo administrador**. Resume un rango
  de fechas con los ingresos, la ocupación actual, el número de reservas y las
  canceladas, y desglosa los ingresos por día y las reservas canceladas en dos
  tablas.

El estado de cuenta se deriva de `monto_pagado` frente al `total` de la reserva
(`Pendiente`, `Parcial`, `Pagado`), sin depender de la columna `estado`, que solo
describe la estancia.

## Notificaciones

La campana de la cabecera (`ui/panel_notificaciones.py`) agrupa los avisos de
cobro y de estadía en tres momentos, como se hace en un hotel real:

* **Vencidas**: llegada sin pago, deuda que quedó tras la salida o estadía que se
  pasó de la fecha de salida. La estadía vencida se avisa aunque la cuenta esté
  pagada, porque el problema es operativo: la habitación sigue ocupada.
* **Para hoy**: la llegada o la salida es hoy y la cuenta tiene saldo.
* **Próximas**: la llegada o la salida cae dentro de los `dias_aviso_pago`
  configurados y la cuenta tiene saldo.

El número del botón refleja cuántos avisos hay pendientes. La fecha límite de
pago se toma en dos pasos: se avisa antes de la llegada y se exige liquidar al
registrar la salida (el recepcionista) o al forzarla (el administrador).

## Configuración del hotel (solo administradores)

Se abre desde el menú de sesión y agrupa dos pestañas en
`ui/ventana_administracion.py`.

### Parámetros

Guarda en la tabla `Configuracion` (clave-valor) las reglas que aplica
`ReservaService.registrar_estancia`:

| Parámetro | Significado |
|-----------|-------------|
| `dias_anticipacion_max` | Cuántos días por adelantado se puede reservar |
| `noches_minimas` / `noches_maximas` | Duración mínima y máxima de una estadía |
| `temporada_alta_inicio` / `temporada_alta_fin` | Ventana de temporada alta |
| `factor_temporada_alta` | Multiplicador de precio en temporada alta |
| `descuento_porcentaje` | Descuento aplicado al total |
| `dias_aviso_pago` | Días de antelación con que se avisa un cobro pendiente |

El total lo sigue calculando el servidor: aplica el factor de temporada si la
fecha de entrada cae dentro de la ventana y luego el descuento, redondeando a
dos decimales. La interfaz nunca envía el precio.

### Gestión de personal

Alta, edición y deshabilitación de empleados, y restablecimiento de sus
contraseñas (`DialogoEmpleado` en `ui/ventana_administracion.py`,
`AutenticacionService`). Un empleado deshabilitado conserva su historial (no se
borra) pero no puede iniciar sesión. El administrador no puede deshabilitar su
propia cuenta.

El enlace **Crear cuenta** de la pantalla de acceso (en `ui/login_window.py`,
`DialogoRegistro`) es la vía de autorregistro: crea una cuenta activa con rol
`recepcionista` a partir de los mismos datos validados que el alta de personal
(`AutenticacionService.registrar_cuenta`). El rol no es elegible para que nadie
pueda otorgarse privilegios de administrador.

### Extender una estadía

Cuando un huésped se pasa de la fecha de salida, la mesa de alojados ofrece
**Extender estadía** (`DialogoExtenderEstadia` en `ui/dialogs.py`). El
recepcionista elige la nueva salida y el servidor:

* revalida que la habitación no tenga otra reserva en el tramo que se agrega,
* recalcula las noches y el total con la tarifa vigente,
* deja el saldo pendiente actualizado sin exigir el pago de la extensión.

Si la habitación ya está comprometida, el sistema rechaza la extensión y explica
el motivo; la salida normal sigue exigiendo la cuenta pagada. Así se cubren las
dos respuestas reales del hotel: **extender** (cobrando las noches extra) o
**registrar la salida**.

### Acciones de reserva reservadas al administrador

En las mesas del tablero, el administrador ve acciones adicionales según el
estado de cada fila:

* **Editar reserva** (solo `Pendiente`): cambia fechas y/o habitación y recalcula
  noches y total, revalidando el solapamiento contra las demás reservas
  (`ui/dialogs.py`).
* **Forzar salida** (estancia `Iniciada` con saldo): libera la habitación aunque
  la cuenta quede pendiente. El recepcionista solo puede registrar la salida si
  la cuenta está pagada.
* **Anular estancia** (estancia `Iniciada`): cancela una reserva ya comenzada.
* **Reactivar reserva** (reserva `Cancelada`): la devuelve a `Pendiente`,
  revalidando que la habitación siga libre.
