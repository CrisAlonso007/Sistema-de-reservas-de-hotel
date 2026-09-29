# **Sistema de Reservas de Hotel — Módulo de Recepción**

Aplicación de escritorio para la gestión de catálogo de habitaciones y estancias,
destinada al **uso interno del personal del hotel** (recepcionistas y administradores).

## Modelo operativo

El sistema funciona como una terminal de recepción, no como un portal web:

- **El huésped no es un usuario.** No tiene cuenta, no se autentica y no accede a la
  aplicación. El recepcionista captura sus datos directamente como atributos de la
  transacción en la tabla `Reserva`.
- **El acceso es exclusivo del personal.** No existe autoregistro público ni selección
  de privilegios desde la interfaz. Las cuentas se dan de alta por el administrador o
  desde el script SQL inicial.
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
* Conector: mysql-connector-python

**Patrón por capas (UI → Service → DAO):**

```
main.py                  Orquestador de sesión y ciclo de vida de ventanas
DATABASE/
  conexion.py            Configuración y pooled-no: conexión única reutilizable
  usuario_dao.py         Personal del hotel (autenticación)
  habitacion_dao.py      Catálogo y ocupación calculada
  reserva_dao.py         Estancias, ingresos, salidas y cancelación
  BD_Registro.sql        Esquema y datos iniciales
services/
  autenticacion_service.py
  habitacion_service.py
  reserva_service.py
ui/
  login_window.py        Acceso del personal (sin registro público)
  main_window.py         Shell: banner superior + paneles apilados
  banner_navegacion.py   Cabecera con navegación y menú de sesión
  panel_dashboard.py     Tablero de ocupación e indicadores
  panel_catalogo.py      Listado de habitaciones
   panel_recepcion.py     Mesa de recepción: ingresos y salidas
   admin_window.py        Alta y edición de habitaciones (solo admin)
   detalle_habitacion.py  Ficha de habitación y acceso al alta de huésped
   registro_huesped.py    Formulario único de registro de huésped
   tarjetas_lista.py      Tarjeta del catálogo
utils/
  seguridad.py           Hash PBKDF2-SHA256 de contraseñas
  permisos.py            Autorización por sesión y rol (backend)
  validaciones.py        Reglas de validación de entrada
  stylesheets.py         Estilos visuales
recursos/                Imagen por defecto de las habitaciones
```

## Puesta en marcha

1. Instalar dependencias: `pip install PySide6 mysql-connector-python`
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

## Permisos

| Acción                        | Recepcionista | Administrador |
|-------------------------------|:-------------:|:-------------:|
| Iniciar sesión                | Sí            | Sí            |
| Ver ocupación en tiempo real  | Sí            | Sí            |
| Registrar estancia de huésped  | Sí            | Sí            |
| Registrar ingreso / salida    | Sí            | Sí            |
| Cancelar reservas             | Sí            | Sí            |
| Publicar / editar / eliminar habitaciones | No | Sí            |
| Marcar habitación en mantenimiento | No       | Sí            |

Las dos primeras filas incluyen **Marcar como ocupada** y **Registrar salida**,
que son las acciones que ofrece la mesa de recepción. «Marcar como ocupada»
sustituye al antiguo «Registrar ingreso» para dejar claro que solo cambia el
estado de la reserva: el huésped no se registra aquí, eso ocurre al dar de alta
la estancia.

## Registro de huésped

El alta del huésped es la operación más frecuente de la recepción, así que se
resuelve en un **formulario único** (`ui/registro_huesped.py`) alcanzable desde
tres puntos de entrada:

- el botón **+ Registrar Huésped** del panel de Recepción,
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
* Un ingreso o una salida actualizan las dos mesas de recepción, el catálogo y el
  tablero en el momento, sin esperar al refresco periódico.
* Cancelar una reserva solo es posible mientras está `Pendiente` o `Confirmada`.

## Las dos mesas de recepción

El panel de Recepción (`ui/panel_recepcion.py`) muestra dos tablas que se
complementan y no deben confundirse:

| Mesa | Qué contiene | Qué se le puede hacer |
|------|--------------|----------------------|
| **Reservas del hotel** | Todas las reservas, de cualquier fecha y estado: `Pendiente`, `Confirmada`, `Iniciada`, `Finalizada` y `Cancelada` | **Marcar como ocupada** (solo si la fecha de entrada ya llegó), **Cancelar reserva** y **Registrar salida** |
| **Huéspedes alojados** | Solo los huéspedes que están dentro del hotel ahora mismo | **Registrar salida** |

«Reservas del hotel» es el histórico completo: una reserva del mes que viene o una
estancia ya cerrada siguen apareciendo, para que recepción pueda consultar y
gestionar cualquier reserva sin tener que filtrar por fecha. Las filas cuya
fecha de entrada aún no llega no ofrecen «Marcar como ocupada», porque el
huésped no puede alojarse antes de tiempo; sí pueden cancelarse.

«Huéspedes alojados» responde a una pregunta distinta: *¿quién está dentro del
hotel?* Solo lista reservas `Iniciada` cuya fecha de entrada no sea futura, y por
construcción **cada habitación ocupada aparece una sola vez**. Es exactamente la
misma condición que marca la habitación como `Ocupado` en el catálogo, así que
las dos vistas siempre coinciden: lo que sale en «Huéspedes alojados» está
ocupado, y toda habitación ocupada tiene a su huésped en la mesa.

Las reservas `Finalizada` y `Cancelada` se muestran en el histórico pero sin
botones, porque una estancia cerrada ya no admite más movimientos.

