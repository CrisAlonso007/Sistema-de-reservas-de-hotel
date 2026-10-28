# services/reserva_service.py
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from DATABASE.reserva_dao import ReservaDAO
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

    # Parámetros del hotel por defecto. Si la tabla Configuracion no los trae
    # (o trae un valor inválido), el sistema sigue funcionando con estos.
    PARAMETROS_POR_DEFECTO = {
        "dias_anticipacion_max": 90,
        "noches_minimas": 1,
        "noches_maximas": 30,
        "temporada_alta_inicio": None,
        "temporada_alta_fin": None,
        "factor_temporada_alta": 1.0,
        "descuento_porcentaje": 0.0,
        "dias_aviso_pago": 3,
    }

    def __init__(self):
        self.dao = ReservaDAO()

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
        """Parámetros del hotel ya convertidos a su tipo (int, float, fecha).

        La tabla Configuracion guarda texto; cualquier valor ilegible cae al
        valor por defecto en vez de romper el registro de estancias.
        """
        crudos = self.dao.obtener_configuracion()
        parametros = dict(self.PARAMETROS_POR_DEFECTO)

        parametros["dias_anticipacion_max"] = self._a_entero(
            crudos.get("dias_anticipacion_max"), self.PARAMETROS_POR_DEFECTO["dias_anticipacion_max"]
        )
        parametros["noches_minimas"] = self._a_entero(
            crudos.get("noches_minimas"), self.PARAMETROS_POR_DEFECTO["noches_minimas"]
        )
        parametros["noches_maximas"] = self._a_entero(
            crudos.get("noches_maximas"), self.PARAMETROS_POR_DEFECTO["noches_maximas"]
        )
        parametros["factor_temporada_alta"] = self._a_decimal(
            crudos.get("factor_temporada_alta"), self.PARAMETROS_POR_DEFECTO["factor_temporada_alta"]
        )
        parametros["descuento_porcentaje"] = self._a_decimal(
            crudos.get("descuento_porcentaje"), self.PARAMETROS_POR_DEFECTO["descuento_porcentaje"]
        )
        parametros["temporada_alta_inicio"] = self._a_fecha_opcional(crudos.get("temporada_alta_inicio"))
        parametros["temporada_alta_fin"] = self._a_fecha_opcional(crudos.get("temporada_alta_fin"))
        parametros["dias_aviso_pago"] = self._a_entero(
            crudos.get("dias_aviso_pago"), self.PARAMETROS_POR_DEFECTO["dias_aviso_pago"]
        )

        return parametros

    def actualizar_parametros(self, usuario_actual: dict, parametros: dict) -> tuple[bool, str]:
        """Guarda los parámetros del hotel. Exclusivo del administrador."""
        if not sesion_valida(usuario_actual):
            return False, "Debe iniciar sesión para modificar los parámetros."
        if not es_administrador(usuario_actual):
            return False, MENSAJE_SOLO_ADMIN

        try:
            anticipacion = int(parametros.get("dias_anticipacion_max"))
            noches_min = int(parametros.get("noches_minimas"))
            noches_max = int(parametros.get("noches_maximas"))
            dias_aviso = int(parametros.get("dias_aviso_pago", 3))
        except (TypeError, ValueError):
            return False, "La antelación y la duración de la estadía deben ser números enteros."

        if not (0 <= anticipacion <= 3650):
            return False, "La antelación máxima debe estar entre 0 y 3650 días."
        if not (1 <= noches_min <= 365):
            return False, "El mínimo de noches debe estar entre 1 y 365."
        if not (1 <= noches_max <= 365):
            return False, "El máximo de noches debe estar entre 1 y 365."
        if noches_max < noches_min:
            return False, "El máximo de noches no puede ser menor que el mínimo."
        if not (0 <= dias_aviso <= 30):
            return False, "Los días de aviso de cobro deben estar entre 0 y 30."

        try:
            factor = Decimal(str(parametros.get("factor_temporada_alta")))
            descuento = Decimal(str(parametros.get("descuento_porcentaje")))
        except (InvalidOperation, TypeError, ValueError):
            return False, "El recargo y el descuento deben ser números."

        if not factor.is_finite() or not (Decimal("1") <= factor <= Decimal("5")):
            return False, "El recargo de temporada alta debe estar entre 1.00 y 5.00."
        if not descuento.is_finite() or not (Decimal("0") <= descuento <= Decimal("100")):
            return False, "El descuento debe estar entre 0 y 100."

        inicio = self._texto_o_none(parametros.get("temporada_alta_inicio"))
        fin = self._texto_o_none(parametros.get("temporada_alta_fin"))

        if (inicio is None) != (fin is None):
            return False, "La temporada alta necesita fecha de inicio y de fin."

        if inicio is not None:
            fecha_inicio, error_inicio = self._parsear_fecha(inicio)
            fecha_fin, error_fin = self._parsear_fecha(fin)
            if error_inicio or error_fin:
                return False, "Las fechas de temporada alta no son válidas."
            if fecha_fin <= fecha_inicio:
                return False, "El fin de temporada alta debe ser posterior al inicio."
            inicio, fin = fecha_inicio.isoformat(), fecha_fin.isoformat()

        return self.dao.guardar_configuracion({
            "dias_anticipacion_max": anticipacion,
            "noches_minimas": noches_min,
            "noches_maximas": noches_max,
            "factor_temporada_alta": str(factor),
            "descuento_porcentaje": str(descuento),
            "temporada_alta_inicio": inicio or "",
            "temporada_alta_fin": fin or "",
            "dias_aviso_pago": dias_aviso,
        })

    def _factor_y_descuento(self, fecha_entrada):
        """Factor de temporada alta y descuento general aplicables a una entrada."""
        parametros = self.obtener_parametros()
        factor = 1.0
        inicio = parametros["temporada_alta_inicio"]
        fin = parametros["temporada_alta_fin"]
        if inicio and fin and inicio <= fecha_entrada <= fin:
            factor = parametros["factor_temporada_alta"]
        return factor, parametros["descuento_porcentaje"]

    @staticmethod
    def _a_entero(valor, defecto):
        try:
            return int(str(valor).strip())
        except (TypeError, ValueError):
            return defecto

    @staticmethod
    def _a_decimal(valor, defecto):
        try:
            return float(str(valor).strip())
        except (TypeError, ValueError):
            return defecto

    @staticmethod
    def _a_fecha_opcional(valor):
        if valor in (None, ""):
            return None
        try:
            return datetime.strptime(str(valor).strip(), "%Y-%m-%d").date()
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _texto_o_none(valor):
        texto = str(valor).strip() if valor is not None else ""
        return texto or None

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
    ) -> tuple[bool, str]:
        """Captura los datos del huésped y abre su estancia."""
        empleado_id = self._empleado_de_sesion(usuario_actual)
        if empleado_id is None:
            return False, "No hay una sesión de personal válida para registrar la reserva."

        if metodo_pago not in self.METODOS_PAGO:
            return False, "El método de pago seleccionado no es válido."

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

        # Parámetros del hotel: antelación máxima y duración permitida de la
        # estadía. Se leen aquí para que el recepcionista reciba el motivo exacto.
        parametros = self.obtener_parametros()
        if not ingreso_inmediato:
            dias_de_anticipacion = (entrada - datetime.today().date()).days
            if dias_de_anticipacion > parametros["dias_anticipacion_max"]:
                return False, (
                    "La reserva supera la antelación máxima permitida de "
                    f"{parametros['dias_anticipacion_max']} días."
                )
        if noches_calculadas < parametros["noches_minimas"]:
            return False, (
                f"La estadía debe ser de al menos {parametros['noches_minimas']} noche(s)."
            )
        if noches_calculadas > parametros["noches_maximas"]:
            return False, (
                f"La estadía no puede superar {parametros['noches_maximas']} noches."
            )

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
                    f"pendiente de ${self.formato_monto(saldo)}. Cobre la cuenta antes "
                    "de liberar la habitación."
                )

        return self.dao.registrar_salida(
            reserva_id=reserva_id, empleado_id=empleado_id, forzar=bool(forzar)
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

        return self.dao.cancelar_reserva(
            reserva_id=reserva_id, empleado_id=empleado_id, permitir_iniciada=bool(forzar)
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
        """Corrige las fechas y la habitación de una reserva pendiente (admin).

        Vuelve a calcular las noches y el total, y revalida el solape ignorando
        la propia reserva. No modifica el estado ni los pagos ya registrados.
        """
        empleado_id = self._empleado_de_sesion(usuario_actual)
        if empleado_id is None:
            return False, "No hay una sesión de personal válida."
        if not es_administrador(usuario_actual):
            return False, MENSAJE_SOLO_ADMIN
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
        parametros = self.obtener_parametros()
        if noches < parametros["noches_minimas"]:
            return False, f"La estadía debe ser de al menos {parametros['noches_minimas']} noche(s)."
        if noches > parametros["noches_maximas"]:
            return False, f"La estadía no puede superar {parametros['noches_maximas']} noches."

        factor, descuento = self._factor_y_descuento(entrada)

        return self.dao.actualizar_reserva(
            reserva_id=reserva_id,
            fecha_entrada=entrada,
            fecha_salida=salida,
            noches=noches,
            habitacion_id=habitacion_id,
            empleado_id=empleado_id,
            factor_temporada=factor,
            descuento_porcentaje=descuento,
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
        parametros = self.obtener_parametros()
        if noches > parametros["noches_maximas"]:
            return False, f"La estadía no puede superar {parametros['noches_maximas']} noches."

        factor, descuento = self._factor_y_descuento(entrada)

        return self.dao.extender_estadia(
            reserva_id=reserva_id,
            nueva_salida=nueva_salida,
            empleado_id=empleado_id,
            factor_temporada=factor,
            descuento_porcentaje=descuento,
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

    def obtener_reservas(self):
        """Listado completo: toda reserva, sea de la fecha que sea y esté en el
        estado que esté. Sin esto, una reserva futura no aparecía en ninguna
        parte del sistema.

        El orden jerárquico por estado lo garantiza la consulta: pendientes,
        luego iniciadas, después canceladas y al final finalizadas,
        y dentro de cada grupo la fecha de entrada más antigua primero.
        """
        return self.dao.obtener_todas()

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

        if metodo_pago not in self.METODOS_PAGO:
            return False, "El método de pago seleccionado no es válido."

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
        )

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

        datos = {
            "fecha_inicio": inicio,
            "fecha_fin": fin,
            "ingresos": Decimal(str(resumen.get("ingresos", 0) or 0)),
            "reservas": int(resumen.get("reservas", 0) or 0),
            "canceladas_total": int(resumen.get("canceladas", 0) or 0),
            "por_dia": por_dia,
            "canceladas": canceladas,
        }
        return True, datos

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
