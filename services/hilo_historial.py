from threading import Event

from mysql.connector import Error
from PySide6.QtCore import QThread, Signal, Slot
from sqlalchemy.exc import SQLAlchemyError

from services.reserva_service import ReservaService


class HiloHistorial(QThread):
    """Consulta las reservas del historial fuera del hilo de la interfaz."""

    historial_cargado = Signal(list)
    error_carga = Signal(str)
    progreso_carga = Signal(str)
    carga_cancelada = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cancelacion_solicitada = Event()

    @Slot()
    def cancelar(self):
        self._cancelacion_solicitada.set()

    def run(self):
        self.progreso_carga.emit("Consultando el historial...")
        try:
            reservas = ReservaService().obtener_reservas(estricto=True)
        except (ConnectionError, Error, SQLAlchemyError):
            self.error_carga.emit(
                "No se pudo cargar el historial. Verifique la conexión con MySQL "
                "e inténtelo de nuevo."
            )
            return

        if self._cancelacion_solicitada.is_set():
            self.carga_cancelada.emit()
            return

        self.progreso_carga.emit("Mostrando resultados...")
        self.historial_cargado.emit(reservas)
