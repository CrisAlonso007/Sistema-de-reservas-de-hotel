# services/reserva_service.py
from datetime import datetime
from decimal import Decimal, InvalidOperation
from DATABASE.reserva_dao import ReservaDAO
from utils.permisos import sesion_valida
from utils.validaciones import (
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
        )

    def registrar_checkin(self, usuario_actual: dict, reserva_id) -> tuple[bool, str]:
        """Marca el ingreso del huésped y ocupa la habitación."""
        empleado_id = self._empleado_de_sesion(usuario_actual)
        if empleado_id is None:
            return False, "No hay una sesión de personal válida para registrar el ingreso."

        return self.dao.registrar_checkin(reserva_id=reserva_id, empleado_id=empleado_id)

    def registrar_salida(self, usuario_actual: dict, reserva_id) -> tuple[bool, str]:
        """Marca el egreso del huésped y libera la habitación."""
        empleado_id = self._empleado_de_sesion(usuario_actual)
        if empleado_id is None:
            return False, "No hay una sesión de personal válida para registrar la salida."

        return self.dao.registrar_salida(reserva_id=reserva_id, empleado_id=empleado_id)

    def cancelar_reserva(self, usuario_actual: dict, reserva_id) -> tuple[bool, str]:
        """Cancela una reserva que todavía no inició la estancia."""
        empleado_id = self._empleado_de_sesion(usuario_actual)
        if empleado_id is None:
            return False, "No hay una sesión de personal válida para cancelar la reserva."

        return self.dao.cancelar_reserva(reserva_id=reserva_id, empleado_id=empleado_id)

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

    def registrar_pago(self, usuario_actual: dict, reserva_id, monto, metodo_pago) -> tuple[bool, str]:
        """Cobra total o parcialmente una reserva.

        El saldo real lo valida el DAO dentro de la transacción, porque puede
        haber cambiado entre que el cajero abrió el diálogo y confirmó el cobro.
        """
        empleado_id = self._empleado_de_sesion(usuario_actual)
        if empleado_id is None:
            return False, "No hay una sesión de personal válida para registrar el pago."

        if metodo_pago not in self.METODOS_PAGO:
            return False, "El método de pago seleccionado no es válido."

        try:
            monto_decimal = Decimal(str(monto))
        except (InvalidOperation, TypeError, ValueError):
            return False, "El monto a cobrar no es válido."

        if monto_decimal <= 0:
            return False, "El monto a cobrar debe ser mayor a cero."

        return self.dao.registrar_pago(
            reserva_id=reserva_id,
            monto=monto_decimal,
            metodo_pago=metodo_pago,
            empleado_id=empleado_id,
        )

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
