# services/reserva_service.py
from datetime import datetime
from decimal import Decimal
from DATABASE.reserva_dao import ReservaDAO
from utils.permisos import sesion_valida
from utils.validaciones import (
    es_identificacion_valida,
    es_noches_valida,
    validar_correo,
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

    def __init__(self):
        self.dao = ReservaDAO()

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
        correo,
        noches,
        fecha_entrada,
        fecha_salida,
        metodo_pago,
        habitacion_id,
        ingreso_inmediato=False,
    ) -> tuple[bool, str]:
        """Captura los datos del huésped y abre su estancia.

        Con `ingreso_inmediato` el huésped se aloja en el acto: la habitación
        queda ocupada de inmediato. Sin él, la estancia queda como reserva para
        las fechas elegidas. El total lo calcula el servidor.
        """
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

        if not validar_correo(correo):
            return False, "El correo electrónico no es válido."

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

        return self.dao.registrar_reserva(
            cliente=str(cliente).strip(),
            identificacion=str(identificacion).strip(),
            contacto=str(contacto).strip(),
            correo=str(correo).strip(),
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

    def obtener_llegadas_hoy(self):
        """Reservas que esperan su ingreso hoy o de días anteriores."""
        return self.dao.obtener_llegadas(datetime.today().date())

    def obtener_salidas_hoy(self):
        """Huéspedes que deben registrar su salida hoy."""
        return self.dao.obtener_salidas(datetime.today().date())

    def obtener_en_casa(self):
        """Huéspedes con estancia iniciada que siguen en el hotel.

        Coincide con las habitaciones que el catálogo marca como «Ocupado»: si
        un huésped figura aquí, su habitación está tomada de verdad.
        """
        return self.dao.obtener_en_casa(datetime.today().date())

    def obtener_reservas(self):
        """Listado completo: toda reserva, sea de la fecha que sea y esté en el
        estado que esté. Sin esto, una reserva futura no aparecía en ninguna
        parte del sistema."""
        return self.dao.obtener_todas()

    def obtener_reservas_habitacion(self, habitacion_id):
        """Reservas vigentes de una habitación, para no duplicar fechas."""
        return self.dao.obtener_por_habitacion(habitacion_id)

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
