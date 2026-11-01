# services/reserva_service.py
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
import json
import re
from DATABASE.reserva_dao import ReservaDAO
from mysql.connector import Error
from utils.seguridad import (
    MENSAJE_SOLO_ADMIN,
    es_administrador,
    sesion_valida,
)
from utils.validaciones import (
    es_id_valido,
    es_identificacion_valida,
    es_noches_valida,
    validar_nombre_completo,
    validar_telefono,
)

class ReservaService:
    """Reglas de negocio de las estancias capturadas por el personal de recepción.

    Toda operación escribe el empleado responsable, por lo que exige una sesión
    válida: sin ella no habría trazabilidad de quién capturó o cerró la estancia.
    """

    METODOS_PAGO = [
        "Tarjeta de Crédito / Débito",
        "Efectivo en Recepción",
        "Transferencia Bancaria",
    ]

    # Estados posibles de una reserva, ya en el orden en que la mesa de trabajo
    # los presenta: primero las reservas que esperan al huésped, luego las cerradas.
    # La interfaz usa esta lista para armar el filtro de estado, así que el
    # orden y los nombres nunca se escriben a mano en dos lugares distintos.
    ESTADOS_RESERVA = [
        "Pendiente",
        "Iniciada",
        "No presentada",
        "Cancelada",
        "Finalizada",
    ]

    # Único lugar donde se traduce el estado técnico de la BD al nombre que usa
    # el personal. «Pendiente» y «Reservada» son la misma cosa: la reserva existe
    # pero el huésped todavía no llegó, así que se muestra siempre como
    # «Reservada» sin tener que renombrar el valor guardado en MySQL.
    ETIQUETAS_ESTADO = {
        "Pendiente": "Reservada",
        "Iniciada": "Alojado",
        "Finalizada": "Finalizada",
        "Cancelada": "Cancelada",
        "No presentada": "No presentada",
    }

    # Estados de la cuenta de una reserva. Se calculan a partir de monto_pagado
    # (no se almacenan) para que nunca queden desincronizados con lo cobrado.
    ESTADOS_PAGO = [
        "Pendiente",
        "Parcial",
        "Pagado",
    ]

    # Nombres visibles del estado de cuenta. El valor técnico sigue siendo
    # Pendiente/Parcial/Pagado, pero se muestra distinto para no chocar con el
    # estado «Pendiente» de la estancia (que se ve como «Reservada»).
    ETIQUETAS_ESTADO_PAGO = {
        "Pendiente": "Sin pagar",
        "Parcial": "Abonado",
        "Pagado": "Pagado",
    }

    # Los avisos operativos siguen usando un plazo fijo; no es una política
    # configurable del hotel.
    PARAMETROS_POR_DEFECTO = {
        "dias_aviso_pago": 3,
    }
    CONFIGURACION_HOTEL_POR_DEFECTO = {
        "hotel_nombre": "Allogi Hotel",
        "hotel_direccion": "",
        "hotel_telefono": "",
        "hotel_correo": "",
        "hora_checkin": "14:00",
        "hora_checkout": "12:00",
        "horario_recepcion": "24 horas",
        "confirmacion_horas": 0,
        "cancelacion_horas_limite": 48,
        "cancelacion_penalizacion_pct": 20,
        "no_show_penalizacion_pct": 30,
        "late_checkout_hora": "14:00",
        "late_checkout_cargo": "0.00",
        "moneda": "NIO",
        "metodos_pago": METODOS_PAGO,
        "comprobante_mensaje": "Gracias por su preferencia.",
        "comprobante_prefijo": "COMP",
    }

    def __init__(self):
        self.dao = ReservaDAO()
        self._configuracion_hotel_cache = None

    @staticmethod
    def etiqueta_estado(estado: str) -> str:
        """Nombre visible del estado de una reserva (unifica Pendiente/Reservada).

        Toda la interfaz debe pasar por aquí para no repetir el diccionario ni
        mostrar dos nombres distintos para el mismo estado.
        """
        return ReservaService.ETIQUETAS_ESTADO.get(estado, estado)

    @staticmethod
    def etiqueta_estado_pago(estado: str) -> str:
        """Nombre visible del estado de cuenta (Sin pagar / Abonado / Pagado)."""
        return ReservaService.ETIQUETAS_ESTADO_PAGO.get(estado, estado)

    @staticmethod
    def _empleado_de_sesion(usuario_actual):
        """Devuelve el identificador del empleado en sesión, o None si no es válida.

        Se acepta el diccionario de sesión completo para poder validar el rol, no
        solo un identificador suelto que cualquier llamante podría inventar.
        """
        if not sesion_valida(usuario_actual):
            return None
        return usuario_actual.get("id")

    # ------------------------------------------------------------------
    # PARAMETROS DEL HOTEL Y TARIFAS
    # ------------------------------------------------------------------
    def obtener_parametros(self) -> dict:
        """Ajustes internos de avisos de pago, no editables desde Configuración."""
        return dict(self.PARAMETROS_POR_DEFECTO)

    def obtener_configuracion_hotel(self, refrescar=False) -> dict:
        """Carga los ajustes visibles del hotel y aplica valores seguros por defecto."""
        if self._configuracion_hotel_cache is None or refrescar:
            crudos = self.dao.obtener_configuracion()
            configuracion = dict(self.CONFIGURACION_HOTEL_POR_DEFECTO)
            for clave in configuracion:
                valor = crudos.get(clave)
                if valor is not None:
                    configuracion[clave] = valor
            try:
                metodos = json.loads(crudos.get("metodos_pago", ""))
                if isinstance(metodos, list):
                    metodos_validos = [
                        metodo for metodo in metodos if metodo in self.METODOS_PAGO
                    ]
                    if metodos_validos:
                        configuracion["metodos_pago"] = metodos_validos
            except (TypeError, ValueError):
                pass
            if configuracion["moneda"] not in ("NIO", "USD"):
                configuracion["moneda"] = "NIO"
            if not re.fullmatch(
                r"[A-Z0-9]{2,10}", str(configuracion["comprobante_prefijo"]).upper()
            ):
                configuracion["comprobante_prefijo"] = "COMP"
            else:
                configuracion["comprobante_prefijo"] = str(
                    configuracion["comprobante_prefijo"]
                ).upper()
            configuracion["confirmacion_horas"] = self._a_entero(
                crudos.get("confirmacion_horas"), 0
            )
            configuracion["cancelacion_horas_limite"] = self._a_entero(
                crudos.get("cancelacion_horas_limite"), 48
            )
            configuracion["cancelacion_penalizacion_pct"] = self._a_entero(
                crudos.get("cancelacion_penalizacion_pct"), 20
            )
            configuracion["no_show_penalizacion_pct"] = self._a_entero(
                crudos.get("no_show_penalizacion_pct"), 30
            )
            self._configuracion_hotel_cache = configuracion
        return dict(self._configuracion_hotel_cache)

    def actualizar_configuracion_hotel(
        self, usuario_actual: dict, configuracion: dict
    ) -> tuple[bool, str]:
        """Valida y guarda la configuración del hotel. Exclusivo del administrador."""
        if not sesion_valida(usuario_actual):
            return False, "Debe iniciar sesión para modificar la configuración."
        if not es_administrador(usuario_actual):
            return False, MENSAJE_SOLO_ADMIN

        try:
            confirmacion = int(configuracion.get("confirmacion_horas", 0))
            horas_cancelacion = int(configuracion.get("cancelacion_horas_limite", 48))
            penalizacion_cancelacion = int(configuracion.get("cancelacion_penalizacion_pct", 20))
            penalizacion_no_show = int(configuracion.get("no_show_penalizacion_pct", 30))
            cargo_salida = Decimal(str(configuracion.get("late_checkout_cargo", 0)))
        except (InvalidOperation, TypeError, ValueError):
            return False, "Revise los valores numéricos de las políticas de reserva."
        if not 0 <= confirmacion <= 720:
            return False, "El tiempo para confirmar debe estar entre 0 y 720 horas."
        if not 0 <= horas_cancelacion <= 720:
            return False, "El límite de cancelación debe estar entre 0 y 720 horas."
        if not 0 <= penalizacion_cancelacion <= 100 or not 0 <= penalizacion_no_show <= 100:
            return False, "Las penalizaciones deben estar entre 0 y 100 por ciento."
        if not cargo_salida.is_finite() or cargo_salida < 0:
            return False, "El cargo por salida tardía debe ser un monto válido y no negativo."

        nombre = str(configuracion.get("hotel_nombre", "")).strip()
        if not nombre:
            return False, "El nombre del hotel es obligatorio."
        for campo in ("hora_checkin", "hora_checkout", "late_checkout_hora"):
            try:
                datetime.strptime(str(configuracion.get(campo, "")), "%H:%M")
            except ValueError:
                return False, "Las horas deben tener el formato HH:MM."

        moneda = str(configuracion.get("moneda", "NIO"))
        if moneda not in ("NIO", "USD"):
            return False, "La moneda seleccionada no es válida."
        prefijo = str(configuracion.get("comprobante_prefijo", "COMP")).strip().upper()
        if not re.fullmatch(r"[A-Z0-9]{2,10}", prefijo):
            return False, "El prefijo del comprobante debe tener de 2 a 10 letras o números."
        metodos = [
            metodo for metodo in configuracion.get("metodos_pago", [])
            if metodo in self.METODOS_PAGO
        ]
        if not metodos:
            return False, "Seleccione al menos un método de pago."

        pares = {
            "hotel_nombre": nombre,
            "hotel_direccion": str(configuracion.get("hotel_direccion", "")).strip(),
            "hotel_telefono": str(configuracion.get("hotel_telefono", "")).strip(),
            "hotel_correo": str(configuracion.get("hotel_correo", "")).strip(),
            "hora_checkin": str(configuracion["hora_checkin"]),
            "hora_checkout": str(configuracion["hora_checkout"]),
            "horario_recepcion": str(configuracion.get("horario_recepcion", "")).strip(),
            "confirmacion_horas": confirmacion,
            "cancelacion_horas_limite": horas_cancelacion,
            "cancelacion_penalizacion_pct": penalizacion_cancelacion,
            "no_show_penalizacion_pct": penalizacion_no_show,
            "late_checkout_hora": str(configuracion["late_checkout_hora"]),
            "late_checkout_cargo": str(cargo_salida.quantize(Decimal("0.01"))),
            "moneda": moneda,
            "metodos_pago": json.dumps(metodos, ensure_ascii=False),
            "comprobante_mensaje": str(configuracion.get("comprobante_mensaje", "")).strip(),
            "comprobante_prefijo": prefijo,
        }
        exito, mensaje = self.dao.guardar_configuracion(pares)
        if exito:
            self._configuracion_hotel_cache = dict(pares)
            self._configuracion_hotel_cache["metodos_pago"] = metodos
            for clave in ("confirmacion_horas", "cancelacion_horas_limite",
                          "cancelacion_penalizacion_pct", "no_show_penalizacion_pct"):
                self._configuracion_hotel_cache[clave] = int(pares[clave])
        return exito, mensaje

    def _factor_y_descuento(self, fecha_entrada):
        """La tarifa configurada por habitación se aplica sin recargos de temporada."""
        return 1.0, 0.0

    def metodos_pago_disponibles(self):
        return self.obtener_configuracion_hotel()["metodos_pago"]

    def formato_dinero(self, monto) -> str:
        moneda = self.obtener_configuracion_hotel()["moneda"]
        simbolo = "C$" if moneda == "NIO" else "$"
        return f"{simbolo} {self.formato_monto(monto)}"

    @staticmethod
    def _a_entero(valor, defecto):
        try:
            return int(str(valor).strip())
        except (TypeError, ValueError):
            return defecto

    def registrar_estancia(
        self,
        usuario_actual: dict,
        cliente,
        identificacion,
        contacto,
        noches,
        fecha_entrada,
        fecha_salida,
        metodo_pago,
        habitacion_id,
        ingreso_inmediato=False,
        numero_huespedes=1,
    ) -> tuple[bool, str]:
        """Captura los datos del huésped y abre su estancia."""
        empleado_id = self._empleado_de_sesion(usuario_actual)
        if empleado_id is None:
            return False, "No hay una sesión de personal válida para registrar la reserva."

        if metodo_pago not in self.metodos_pago_disponibles():
            return False, "El método de pago seleccionado no está habilitado por el hotel."

        if not es_noches_valida(noches):
            return False, "La cantidad de noches debe ser un número mayor a cero."

        if not validar_nombre_completo(cliente):
            return False, "El nombre del huésped no es válido."

        if not es_identificacion_valida(identificacion):
            return False, "El número de identificación no es válido."

        if not validar_telefono(contacto):
            return False, "El número de contacto no es válido."

        if not es_id_valido(habitacion_id):
            return False, "La habitación seleccionada no es válida."

        try:
            huespedes = int(str(numero_huespedes).strip())
        except (TypeError, ValueError):
            return False, "La cantidad de huéspedes debe ser un número entero válido."
        if huespedes < 1:
            return False, "Debe registrarse al menos un huésped."

        entrada, error_entrada = self._parsear_fecha(fecha_entrada)
        if error_entrada:
            return False, error_entrada

        salida, error_salida = self._parsear_fecha(fecha_salida)
        if error_salida:
            return False, error_salida

        if salida <= entrada:
            return False, "La fecha de salida debe ser posterior a la fecha de entrada."

        if entrada < datetime.today().date():
            return False, "La fecha de entrada no puede ser anterior a hoy."

        if ingreso_inmediato and entrada != datetime.today().date():
            return False, "El hospedaje inmediato solo puede registrarse con la fecha de hoy."

        noches_calculadas = (salida - entrada).days
        if noches_calculadas != int(noches):
            return False, "La cantidad de noches no coincide con el rango de fechas."

        # Validación previa del choque de cuentas: si otra reserva o estancia ya
        # pisa estas fechas, se avisa de inmediato. El registro vuelve a validar
        # con la fila bloqueada, así que aunque el tramo cambiara en el mientras
        # tanto, nunca se guardaría una reserva superpuesta.
        if self.dao.existe_choque(habitacion_id, entrada, salida):
            return False, (
                "La habitación ya tiene una reserva o estancia que se solapa "
                "con esas fechas."
            )

        factor, descuento = self._factor_y_descuento(entrada)

        return self.dao.registrar_reserva(
            cliente=str(cliente).strip(),
            identificacion=str(identificacion).strip(),
            contacto=str(contacto).strip(),
            noches=noches_calculadas,
            fecha_entrada=entrada,
            fecha_salida=salida,
            metodo_pago=metodo_pago,
            empleado_id=empleado_id,
            habitacion_id=habitacion_id,
            numero_huespedes=huespedes,
            ingreso_inmediato=bool(ingreso_inmediato),
            factor_temporada=factor,
            descuento_porcentaje=descuento,
        )

    def registrar_checkin(self, usuario_actual: dict, reserva_id) -> tuple[bool, str]:
        """Marca el ingreso del huésped y ocupa la habitación."""
        empleado_id = self._empleado_de_sesion(usuario_actual)
        if empleado_id is None:
            return False, "No hay una sesión de personal válida para registrar el ingreso."
        if not es_id_valido(reserva_id):
            return False, "La reserva indicada no es válida."

        return self.dao.registrar_checkin(reserva_id=reserva_id, empleado_id=empleado_id)

    def registrar_salida(self, usuario_actual: dict, reserva_id, forzar=False) -> tuple[bool, str]:
        """Marca el egreso del huésped y libera la habitación.

        La habitación no se libera mientras la cuenta tenga saldo pendiente: el
        pago puede registrarse con la reserva pendiente o alojada, pero la salida
        exige la cuenta saldada. La comprobación se repite con la fila bloqueada
        dentro del DAO, así que un cobro concurrente tampoco cuela una liberación
        con deuda.

        `forzar` (liberar con deuda) es exclusivo del administrador.
        """
        empleado_id = self._empleado_de_sesion(usuario_actual)
        if empleado_id is None:
            return False, "No hay una sesión de personal válida para registrar la salida."

        if not es_id_valido(reserva_id):
            return False, "La reserva indicada no es válida."

        if forzar and not es_administrador(usuario_actual):
            return False, MENSAJE_SOLO_ADMIN

        if not forzar:
            cuenta = self.dao.obtener_cuenta(reserva_id)
            if cuenta is None:
                return False, "La reserva no existe."

            saldo = Decimal(str(cuenta.get("saldo", 0) or 0))
            if saldo > 0:
                return False, (
                    "No se puede registrar la salida: la cuenta tiene un saldo "
                    f"pendiente de {self.formato_dinero(saldo)}. Cobre la cuenta antes "
                    "de liberar la habitación."
                )

        return self.dao.registrar_salida(
            reserva_id=reserva_id,
            empleado_id=empleado_id,
            forzar=bool(forzar),
            moneda=self.obtener_configuracion_hotel()["moneda"],
        )

    def cancelar_reserva(self, usuario_actual: dict, reserva_id, forzar=False) -> tuple[bool, str]:
        """Cancela una reserva que todavía no inició la estancia.

        `forzar` permite al administrador anular también una estancia ya
        iniciada (huésped que se retira antes de tiempo).
        """
        empleado_id = self._empleado_de_sesion(usuario_actual)
        if empleado_id is None:
            return False, "No hay una sesión de personal válida para cancelar la reserva."
        if not es_id_valido(reserva_id):
            return False, "La reserva indicada no es válida."
        if forzar and not es_administrador(usuario_actual):
            return False, MENSAJE_SOLO_ADMIN

        config = self.obtener_configuracion_hotel()
        return self.dao.cancelar_reserva(
            reserva_id=reserva_id,
            empleado_id=empleado_id,
            permitir_iniciada=bool(forzar),
            horas_limite=config["cancelacion_horas_limite"],
            penalizacion_pct=config["cancelacion_penalizacion_pct"],
            hora_checkin=config["hora_checkin"],
            moneda=config["moneda"],
        )

    def marcar_no_show(self, usuario_actual: dict, reserva_id) -> tuple[bool, str]:
        empleado_id = self._empleado_de_sesion(usuario_actual)
        if empleado_id is None:
            return False, "No hay una sesión de personal válida."
        if not es_administrador(usuario_actual):
            return False, MENSAJE_SOLO_ADMIN
        if not es_id_valido(reserva_id):
            return False, "La reserva indicada no es válida."
        config = self.obtener_configuracion_hotel()
        return self.dao.marcar_no_show(
            reserva_id=reserva_id,
            empleado_id=empleado_id,
            penalizacion_pct=config["no_show_penalizacion_pct"],
            moneda=config["moneda"],
        )

    def reactivar_reserva(self, usuario_actual: dict, reserva_id) -> tuple[bool, str]:
        """Devuelve al estado Pendiente una reserva cancelada por error (admin)."""
        empleado_id = self._empleado_de_sesion(usuario_actual)
        if empleado_id is None:
            return False, "No hay una sesión de personal válida."
        if not es_administrador(usuario_actual):
            return False, MENSAJE_SOLO_ADMIN
        if not es_id_valido(reserva_id):
            return False, "La reserva indicada no es válida."

        return self.dao.reactivar_reserva(reserva_id=reserva_id, empleado_id=empleado_id)

    def editar_reserva(self, usuario_actual: dict, reserva_id, fecha_entrada,
                       fecha_salida, habitacion_id) -> tuple[bool, str]:
        """Corrige las fechas y la habitación de una reserva pendiente.

        Vuelve a calcular las noches y el total, y revalida el solape ignorando
        la propia reserva. Solo admite reservas aún pendientes y no modifica los
        pagos ya registrados.
        """
        empleado_id = self._empleado_de_sesion(usuario_actual)
        if empleado_id is None:
            return False, "No hay una sesión de personal válida."
        if not es_id_valido(reserva_id):
            return False, "La reserva indicada no es válida."
        if not es_id_valido(habitacion_id):
            return False, "La habitación seleccionada no es válida."

        entrada, error_entrada = self._parsear_fecha(fecha_entrada)
        if error_entrada:
            return False, error_entrada
        salida, error_salida = self._parsear_fecha(fecha_salida)
        if error_salida:
            return False, error_salida
        if salida <= entrada:
            return False, "La fecha de salida debe ser posterior a la fecha de entrada."
        if entrada < datetime.today().date():
            return False, "La fecha de entrada no puede ser anterior a hoy."

        noches = (salida - entrada).days
        factor, descuento = self._factor_y_descuento(entrada)
        moneda = self.obtener_configuracion_hotel()["moneda"]

        return self.dao.actualizar_reserva(
            reserva_id=reserva_id,
            fecha_entrada=entrada,
            fecha_salida=salida,
            noches=noches,
            habitacion_id=habitacion_id,
            empleado_id=empleado_id,
            factor_temporada=factor,
            descuento_porcentaje=descuento,
            moneda=moneda,
        )

    def extender_estadia(self, usuario_actual: dict, reserva_id, fecha_salida) -> tuple[bool, str]:
        """Alarga la estadía de un huésped que sigue alojado.

        La nueva salida debe ser futura y posterior a la actual. El total se
        recalcula con la tarifa de la habitación, así que el saldo pendiente
        sube si corresponde. No se exige tener la cuenta pagada para autorizar
        la extensión: el sistema lo deja registrado y avisa del saldo.
        """
        empleado_id = self._empleado_de_sesion(usuario_actual)
        if empleado_id is None:
            return False, "No hay una sesión de personal válida."
        if not es_id_valido(reserva_id):
            return False, "La reserva indicada no es válida."

        nueva_salida, error = self._parsear_fecha(fecha_salida)
        if error:
            return False, error
        if nueva_salida <= datetime.today().date():
            return False, "La nueva fecha de salida debe ser posterior a hoy."

        reserva = self.dao.obtener_reserva(reserva_id)
        if not reserva:
            return False, "La reserva no existe."
        if reserva["estado"] != "Iniciada":
            return False, "Solo se puede extender una estadía que esté en curso."

        entrada = self._a_date(reserva["fecha_entrada"])
        salida_actual = self._a_date(reserva["fecha_salida"])
        if nueva_salida <= salida_actual:
            return False, "La nueva salida debe ser posterior a la actual."

        noches = (nueva_salida - entrada).days
        factor, descuento = self._factor_y_descuento(entrada)

        return self.dao.extender_estadia(
            reserva_id=reserva_id,
            nueva_salida=nueva_salida,
            empleado_id=empleado_id,
            factor_temporada=factor,
            descuento_porcentaje=descuento,
            moneda=self.obtener_configuracion_hotel()["moneda"],
        )

    def obtener_reservas_pendientes(self):
        """Todas las reservas en estado Pendiente, sin importar su fecha.

        Es la mesa de «Reservas pendientes»: el personal ve de una vez todo lo
        reservado y todavía sin ingresar, no solo lo que entra hoy.
        """
        return self.dao.obtener_pendientes()

    def obtener_en_casa(self):
        """Huéspedes con estancia iniciada que siguen en el hotel.

        Coincide con las habitaciones que el catálogo marca como «Ocupado»: si
        un huésped figura aquí, su habitación está tomada de verdad.
        """
        return self.dao.obtener_en_casa(datetime.today().date())

    def obtener_reservas(self, estricto=False):
        """Listado completo: toda reserva, sea de la fecha que sea y esté en el
        estado que esté. Sin esto, una reserva futura no aparecía en ninguna
        parte del sistema.

        El orden jerárquico por estado lo garantiza la consulta: pendientes,
        luego iniciadas, después canceladas y al final finalizadas,
        y dentro de cada grupo la fecha de entrada más antigua primero.
        """
        return self.dao.obtener_todas(estricto=estricto)

    # ------------------------------------------------------------------
    # PAGOS
    # ------------------------------------------------------------------
    def obtener_cuentas(self):
        """Cuentas de todas las reservas vigentes, con su saldo y estado de pago."""
        return self.dao.obtener_cuentas()

    def obtener_pagos_reserva(self, reserva_id):
        """Historial de cobros de una reserva."""
        return self.dao.obtener_pagos(reserva_id)

    # ------------------------------------------------------------------
    # AVISOS Y TABLERO (campana de notificaciones y tarjetas de inicio)
    # ------------------------------------------------------------------
    def obtener_estadias_vencidas(self):
        """Huéspedes alojados cuya fecha de salida ya pasó.

        Alimenta la campana de notificaciones: el sistema no libera la
        habitación por calendario, así que hay que avisar a recepción de quién
        sigue adentro pese a tener el egreso cumplido.
        """
        return self.dao.obtener_estadias_vencidas(datetime.today().date())

    def obtener_cuentas_por_cobrar(self):
        """Cuentas con saldo pendiente de los huéspedes que siguen alojados.

        Alimenta la tarjeta de «cuentas por cobrar» del tablero: solo quien
        ocupa la habitación ahora mismo y todavía debe dinero.
        """
        return self.dao.obtener_cuentas_alojados()

    def obtener_alertas_cobro(self):
        """Avisos de cobro y de estadía, ordenados en tres momentos.

        Cada aviso llega como un diccionario con ``tipo`` (``vencida``, ``hoy``
        o ``proxima``), una categoría para mostrar y el saldo pendiente.

        La fecha límite se toma así, igual que en un hotel real:
          - Antes de la llegada: se avisa cuando faltan ``dias_aviso_pago``.
          - El día de la llegada o de la salida: aviso del día.
          - Después: llegada sin pago, deuda tras la salida o estadía vencida.

        La estadía vencida se informa aunque la cuenta esté pagada: es un
        problema operativo (la habitación sigue ocupada), no solo de dinero.
        """
        hoy = datetime.today().date()
        dias_aviso = self.obtener_parametros()["dias_aviso_pago"]
        alertas = []

        for cuenta in self.dao.obtener_cuentas():
            estado = cuenta.get("estado")
            saldo = Decimal(str(cuenta.get("saldo") or 0))
            entrada = self._a_date(cuenta.get("fecha_entrada"))
            salida = self._a_date(cuenta.get("fecha_salida"))

            # 1) El huésped sigue alojado y su fecha de salida ya pasó.
            if estado == "Iniciada" and salida < hoy:
                dias = (hoy - salida).days
                alertas.append(self._alerta(
                    "vencida", "Estadía vencida", cuenta, salida, saldo,
                    f"Debió salir el {self.formato_fecha(salida)}; "
                    f"lleva {dias} día(s) de exceso.",
                ))
                continue

            # 2) Cuentas sin saldo: no hay nada que cobrar.
            if saldo <= 0:
                continue

            if estado in ("Pendiente", "Confirmada"):
                dias = (entrada - hoy).days
                if dias < 0:
                    alertas.append(self._alerta(
                        "vencida", "Llegada sin pago", cuenta, entrada, saldo,
                        f"La entrada fue el {self.formato_fecha(entrada)} "
                        "y la reserva sigue sin pagar.",
                    ))
                elif dias == 0:
                    alertas.append(self._alerta(
                        "hoy", "Cobro en la llegada", cuenta, entrada, saldo,
                        "Llega hoy y la cuenta tiene saldo pendiente.",
                    ))
                elif dias <= dias_aviso:
                    alertas.append(self._alerta(
                        "proxima", "Cobro próximo", cuenta, entrada, saldo,
                        f"Llega en {dias} día(s) y la cuenta tiene saldo pendiente.",
                    ))
            elif estado == "Iniciada":
                dias = (salida - hoy).days
                if dias == 0:
                    alertas.append(self._alerta(
                        "hoy", "Cobro en la salida", cuenta, salida, saldo,
                        "Sale hoy y la cuenta tiene saldo pendiente.",
                    ))
                elif dias <= dias_aviso:
                    alertas.append(self._alerta(
                        "proxima", "Cuenta por cobrar", cuenta, salida, saldo,
                        f"Sale en {dias} día(s) y la cuenta tiene saldo pendiente.",
                    ))
            elif estado == "Finalizada":
                alertas.append(self._alerta(
                    "vencida", "Deuda pendiente", cuenta, salida, saldo,
                    f"La estadía terminó el {self.formato_fecha(salida)} "
                    "y quedó saldo pendiente.",
                ))

        orden = {"vencida": 0, "hoy": 1, "proxima": 2}
        alertas.sort(key=lambda aviso: (orden[aviso["tipo"]], aviso["fecha"]))
        return alertas

    @staticmethod
    def _alerta(tipo, categoria, cuenta, fecha, saldo, detalle):
        """Arma el diccionario que consume la campana de notificaciones."""
        return {
            "tipo": tipo,
            "categoria": categoria,
            "titulo": (
                f"Habitación {cuenta.get('habitacion_numero')} · "
                f"{cuenta.get('cliente')}"
            ),
            "detalle": detalle,
            "fecha": fecha,
            "saldo": saldo,
        }

    def serie_ingresos(self, dias=7):
        """Serie continua de ingresos diarios de los últimos N días.

        `ingresos_por_dia` solo devuelve los días con cobros, lo que dejaría
        huecos en una gráfica. Aquí se rellenan los días sin movimientos con
        cero, de modo que el eje de fechas sea contiguo.
        """
        hoy = datetime.today().date()
        inicio = hoy - timedelta(days=max(dias, 1) - 1)

        acumulado = {}
        for fila in self.dao.ingresos_por_dia(inicio, hoy):
            acumulado[self._a_date(fila.get("fecha"))] = Decimal(
                str(fila.get("total") or 0)
            )

        serie = []
        for paso in range(max(dias, 1)):
            fecha = inicio + timedelta(days=paso)
            serie.append({"fecha": fecha, "total": acumulado.get(fecha, Decimal("0"))})
        return serie

    def total_ingresos_recientes(self, dias=7):
        """Suma de los ingresos de la serie reciente, para el KPI del tablero."""
        return sum((dia["total"] for dia in self.serie_ingresos(dias)), Decimal("0"))

    @staticmethod
    def _a_date(valor):
        """Convierte una fecha de MySQL a `datetime.date` sin romper si ya lo es."""
        if isinstance(valor, datetime):
            return valor.date()
        if hasattr(valor, "year") and hasattr(valor, "month") and hasattr(valor, "day"):
            return valor
        return datetime.strptime(str(valor).strip(), "%Y-%m-%d").date()

    def registrar_pago(self, usuario_actual: dict, reserva_id, monto, metodo_pago) -> tuple[bool, str]:
        """Cobra total o parcialmente una reserva.

        El saldo real lo valida el DAO dentro de la transacción, porque puede
        haber cambiado entre que el cajero abrió el diálogo y confirmó el cobro.
        """
        empleado_id = self._empleado_de_sesion(usuario_actual)
        if empleado_id is None:
            return False, "No hay una sesión de personal válida para registrar el pago."

        if not es_id_valido(reserva_id):
            return False, "La reserva indicada no es válida."

        if metodo_pago not in self.metodos_pago_disponibles():
            return False, "El método de pago seleccionado no está habilitado por el hotel."

        try:
            monto_decimal = Decimal(str(monto))
        except (InvalidOperation, TypeError, ValueError):
            return False, "El monto a cobrar no es válido."

        if not monto_decimal.is_finite():
            return False, "El monto a cobrar no es válido."

        if monto_decimal <= 0:
            return False, "El monto a cobrar debe ser mayor a cero."

        return self.dao.registrar_pago(
            reserva_id=reserva_id,
            monto=monto_decimal,
            metodo_pago=metodo_pago,
            empleado_id=empleado_id,
            moneda=self.obtener_configuracion_hotel()["moneda"],
        )

    def generar_comprobante_pago(self, usuario_actual: dict, pago_id):
        if self._empleado_de_sesion(usuario_actual) is None:
            return False, "Debe iniciar sesión para generar un comprobante."
        if not es_id_valido(pago_id):
            return False, "El pago indicado no es válido."
        prefijo = self.obtener_configuracion_hotel()["comprobante_prefijo"]
        return self.dao.crear_comprobante_pago(pago_id, prefijo)

    # ------------------------------------------------------------------
    # REPORTES (solo administradores)
    # ------------------------------------------------------------------
    def obtener_reporte(self, usuario_actual: dict, fecha_inicio, fecha_fin) -> tuple[bool, dict | str]:
        """Reúne los indicadores de ocupación e ingresos de un período.

        Devuelve ``(False, mensaje)`` si el rango es inválido o la sesión no es
        de administrador; en caso contrario ``(True, datos)``.
        """
        if not sesion_valida(usuario_actual):
            return False, "Debe iniciar sesión para consultar los reportes."
        if not es_administrador(usuario_actual):
            return False, MENSAJE_SOLO_ADMIN

        inicio, error_inicio = self._parsear_fecha(fecha_inicio)
        if error_inicio:
            return False, error_inicio
        fin, error_fin = self._parsear_fecha(fecha_fin)
        if error_fin:
            return False, error_fin
        if fin < inicio:
            return False, "La fecha final del reporte no puede ser anterior a la inicial."

        resumen = self.dao.resumen_periodo(inicio, fin)
        por_dia = self.dao.ingresos_por_dia(inicio, fin)
        canceladas = self.dao.reservas_canceladas(inicio, fin)
        try:
            por_metodo = self._completar_resumen_metodos(
                self.dao.ingresos_por_metodo(inicio, fin)
            )
        except (ConnectionError, Error) as err:
            print(f"Error al consultar ingresos por método: {err}")
            return False, "No se pudieron consultar los ingresos por método de pago."

        datos = {
            "fecha_inicio": inicio,
            "fecha_fin": fin,
            "ingresos": Decimal(str(resumen.get("ingresos", 0) or 0)),
            "reservas": int(resumen.get("reservas", 0) or 0),
            "canceladas_total": int(resumen.get("canceladas", 0) or 0),
            "no_presentadas_total": int(resumen.get("no_presentadas", 0) or 0),
            "por_dia": por_dia,
            "por_metodo": por_metodo,
            "canceladas": canceladas,
        }
        return True, datos

    def obtener_reporte_pagos(
        self, usuario_actual: dict, fecha_inicio, fecha_fin
    ) -> tuple[bool, dict | str]:
        """Obtiene el detalle de pagos y sus totales para exportar."""
        if not sesion_valida(usuario_actual):
            return False, "Debe iniciar sesión para generar reportes."
        if not es_administrador(usuario_actual):
            return False, MENSAJE_SOLO_ADMIN

        inicio, error_inicio = self._parsear_fecha(fecha_inicio)
        if error_inicio:
            return False, error_inicio
        fin, error_fin = self._parsear_fecha(fecha_fin)
        if error_fin:
            return False, error_fin
        if fin < inicio:
            return False, "La fecha final no puede ser anterior a la inicial."

        try:
            pagos = self.dao.pagos_en_periodo(inicio, fin)
        except (ConnectionError, Error) as err:
            print(f"Error al preparar el reporte de pagos: {err}")
            return False, "No se pudieron consultar los pagos. Revise la conexión con MySQL."

        totales_por_dia = {}
        totales_por_metodo = {}
        total = Decimal("0.00")
        for pago in pagos:
            monto = Decimal(str(pago["monto"] or 0))
            fecha = pago["creado_en"]
            fecha = fecha.date() if isinstance(fecha, datetime) else fecha
            resumen = totales_por_dia.setdefault(
                fecha, {"fecha": fecha, "cantidad": 0, "total": Decimal("0.00")}
            )
            if pago["metodo_pago"] != "Devolución":
                resumen["cantidad"] += 1
            resumen["total"] += monto
            metodo = pago["metodo_pago"]
            resumen_metodo = totales_por_metodo.setdefault(
                metodo,
                {"metodo_pago": metodo, "cantidad": 0, "total": Decimal("0.00")},
            )
            resumen_metodo["cantidad"] += 1
            resumen_metodo["total"] += monto
            total += monto

        return True, {
            "fecha_inicio": inicio,
            "fecha_fin": fin,
            "pagos": pagos,
            "por_dia": sorted(totales_por_dia.values(), key=lambda fila: fila["fecha"]),
            "por_metodo": self._completar_resumen_metodos(
                list(totales_por_metodo.values())
            ),
            "cantidad_pagos": sum(
                1 for pago in pagos if pago["metodo_pago"] != "Devolución"
            ),
            "total": total,
            "moneda": self.obtener_configuracion_hotel()["moneda"],
        }

    def _completar_resumen_metodos(self, filas):
        """Incluye todos los métodos configurados, incluso si suman cero."""
        resumen = {
            fila["metodo_pago"]: {
                "metodo_pago": fila["metodo_pago"],
                "cantidad": int(fila["cantidad"] or 0),
                "total": Decimal(str(fila["total"] or 0)),
            }
            for fila in filas
        }
        return [
            resumen.get(
                metodo,
                {"metodo_pago": metodo, "cantidad": 0, "total": Decimal("0.00")},
            )
            for metodo in (*self.METODOS_PAGO, "Devolución")
        ]

    @staticmethod
    def _parsear_fecha(fecha):
        if isinstance(fecha, datetime):
            return fecha.date(), None
        if hasattr(fecha, "year") and hasattr(fecha, "month"):
            return fecha, None

        try:
            return datetime.strptime(str(fecha).strip(), "%Y-%m-%d").date(), None
        except (TypeError, ValueError):
            return None, "Las fechas de la estancia no son válidas."

    @staticmethod
    def formato_fecha(fecha) -> str:
        """Formatea una fecha de MySQL o datetime a dd/MM/yyyy."""
        if isinstance(fecha, (datetime,)):
            return fecha.strftime("%d/%m/%Y")
        if hasattr(fecha, "strftime"):
            return fecha.strftime("%d/%m/%Y")
        try:
            return datetime.strptime(str(fecha), "%Y-%m-%d").strftime("%d/%m/%Y")
        except (TypeError, ValueError):
            return str(fecha)

    @staticmethod
    def formato_monto(monto) -> str:
        """Formatea un importe DECIMAL o float como texto monetario."""
        try:
            return f"{Decimal(str(monto)):,.2f}"
        except (TypeError, ValueError, ArithmeticError):
            return "0.00"
