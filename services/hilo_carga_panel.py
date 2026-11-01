from datetime import date

from mysql.connector import Error
from PySide6.QtCore import QThread, Signal
from sqlalchemy.exc import SQLAlchemyError

from services.habitacion_service import HabitacionService
from services.reserva_service import ReservaService


class HiloCargaPanel(QThread):
    """Carga los datos del panel solicitado sin bloquear el hilo visual."""

    datos_cargados = Signal(str, object)
    error_carga = Signal(str, str)

    def __init__(
        self, clave_panel, usuario_actual=None, parametros=None, parent=None
    ):
        super().__init__(parent)
        self.clave_panel = clave_panel
        self.usuario_actual = usuario_actual or {}
        self.parametros = parametros or {}

    def run(self):
        habitacion_service = HabitacionService()
        reserva_service = ReservaService()

        try:
            if self.clave_panel == "dashboard":
                datos = {
                    "resumen": habitacion_service.obtener_resumen_ocupacion(),
                    "cuentas": reserva_service.obtener_cuentas(),
                    "pendientes": reserva_service.obtener_reservas_pendientes(),
                    "alojados": reserva_service.obtener_en_casa(),
                }
            elif self.clave_panel == "catalogo":
                datos = habitacion_service.obtener_todas()
            elif self.clave_panel == "servicios":
                datos = habitacion_service.obtener_tareas_habitacion(date.today())
            elif self.clave_panel == "pagos_reportes":
                datos = reserva_service.obtener_cuentas()
            elif self.clave_panel == "reportes":
                exito, resultado = reserva_service.obtener_reporte(
                    self.usuario_actual,
                    self.parametros["fecha_inicio"],
                    self.parametros["fecha_fin"],
                )
                if not exito:
                    self.error_carga.emit(self.clave_panel, str(resultado))
                    return
                datos = {
                    "reporte": resultado,
                    "ocupacion": habitacion_service.obtener_resumen_ocupacion(),
                }
            else:
                return
        except (ConnectionError, Error, SQLAlchemyError, ValueError) as err:
            self.error_carga.emit(
                self.clave_panel,
                f"No se pudieron cargar los datos del panel: {err}",
            )
            return

        self.datos_cargados.emit(self.clave_panel, datos)
