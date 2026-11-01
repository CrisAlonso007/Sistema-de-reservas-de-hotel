# ui/historial_huespedes.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox,
    QProgressBar,
)
from PySide6.QtCore import Qt, Slot
from ui.tabla_reservas import TablaReservas
from utils.stylesheets import ESTILO_PANEL
from services.hilo_historial import HiloHistorial

class HistorialHuespedesWindow(QWidget):
    """Ventana independiente con el historial completo de huéspedes.

    Reúne todas las reservas del hotel (de cualquier fecha y estado) con su
    buscador y filtro de estado. Es de solo consulta: las acciones de ingreso y
    salida viven en las mesas del tablero.
    """

    def __init__(self, usuario_actual: dict = None, reserva_service=None, parent=None):
        super().__init__(parent)
        self.usuario_actual = usuario_actual or {}
        self.reserva_service = reserva_service
        self._worker = None
        self._cerrando = False

        self.setWindowTitle("Historial de huéspedes")
        self.setWindowFlags(Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setStyleSheet(ESTILO_PANEL)
        self.resize(920, 620)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)

        layout.addWidget(self._crear_encabezado())
        self.lbl_estado_carga = QLabel()
        self.lbl_estado_carga.setObjectName("panelSubtitulo")
        self.lbl_estado_carga.hide()
        layout.addWidget(self.lbl_estado_carga)

        self.progreso_carga = QProgressBar()
        self.progreso_carga.setRange(0, 0)
        self.progreso_carga.setFixedHeight(6)
        self.progreso_carga.hide()
        layout.addWidget(self.progreso_carga)

        self.tabla = TablaReservas(
            usuario_actual=self.usuario_actual,
            reserva_service=self.reserva_service,
            columnas=["habitacion", "huespedes", "cliente", "documento", "entrada", "salida", "total", "saldo", "estado"],
            con_acciones=False,
            con_filtros=True,
            alto=380,
        )
        layout.addWidget(self.tabla, stretch=1)

        self.refrescar()

    def _crear_encabezado(self):
        contenedor = QWidget()
        layout = QHBoxLayout(contenedor)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        textos = QVBoxLayout()
        textos.setSpacing(2)

        lbl_titulo = QLabel("Historial de huéspedes")
        lbl_titulo.setObjectName("panelTitulo")
        textos.addWidget(lbl_titulo)

        lbl_subtitulo = QLabel("Todos los registros del hotel: reservas, estancias en curso y cerradas")
        lbl_subtitulo.setObjectName("panelSubtitulo")
        textos.addWidget(lbl_subtitulo)

        layout.addLayout(textos)
        layout.addStretch()

        self.btn_actualizar = QPushButton("Actualizar")
        self.btn_actualizar.setObjectName("accionSecundaria")
        self.btn_actualizar.setCursor(Qt.PointingHandCursor)
        self.btn_actualizar.setFixedHeight(38)
        self.btn_actualizar.clicked.connect(self.refrescar)
        layout.addWidget(self.btn_actualizar)

        self.btn_cancelar_carga = QPushButton("Cancelar carga")
        self.btn_cancelar_carga.setObjectName("accionSecundaria")
        self.btn_cancelar_carga.setCursor(Qt.PointingHandCursor)
        self.btn_cancelar_carga.setFixedHeight(38)
        self.btn_cancelar_carga.setToolTip(
            "Descarta los resultados cuando termine la consulta actual."
        )
        self.btn_cancelar_carga.clicked.connect(self.cancelar_carga)
        self.btn_cancelar_carga.hide()
        layout.addWidget(self.btn_cancelar_carga)

        return contenedor

    def refrescar(self):
        if self._worker is not None or not self.reserva_service:
            return

        self.btn_actualizar.setEnabled(False)
        self.btn_actualizar.setText("Cargando...")
        self.btn_cancelar_carga.show()
        self.progreso_carga.show()
        self.lbl_estado_carga.setText("Iniciando consulta...")
        self.lbl_estado_carga.show()

        self._worker = HiloHistorial(self)
        self._worker.historial_cargado.connect(self._mostrar_reservas)
        self._worker.error_carga.connect(self._mostrar_error)
        self._worker.progreso_carga.connect(self.lbl_estado_carga.setText)
        self._worker.carga_cancelada.connect(self._carga_cancelada)
        self._worker.finished.connect(self._al_finalizar_carga)
        self._worker.start()

    @Slot()
    def cancelar_carga(self):
        if self._worker is not None:
            self._worker.cancelar()
            self.btn_cancelar_carga.setEnabled(False)
            self.lbl_estado_carga.setText("Cancelando carga...")

    @Slot(list)
    def _mostrar_reservas(self, reservas):
        self.tabla.llenar(reservas)
        self.lbl_estado_carga.setText("Historial actualizado.")

    @Slot(str)
    def _mostrar_error(self, mensaje):
        QMessageBox.warning(self, "No se pudo cargar el historial", mensaje)

    @Slot()
    def _carga_cancelada(self):
        self.lbl_estado_carga.setText("Carga cancelada.")

    @Slot()
    def _al_finalizar_carga(self):
        worker = self._worker
        self._worker = None
        self.btn_actualizar.setEnabled(True)
        self.btn_actualizar.setText("Actualizar")
        self.btn_cancelar_carga.hide()
        self.btn_cancelar_carga.setEnabled(True)
        self.progreso_carga.hide()
        if worker is not None:
            worker.deleteLater()
        if self._cerrando:
            self.close()

    def closeEvent(self, event):
        if self._worker is not None and self._worker.isRunning():
            self._cerrando = True
            self.setEnabled(False)
            event.ignore()
            return
        super().closeEvent(event)
