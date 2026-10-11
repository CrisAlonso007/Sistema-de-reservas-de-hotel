# ui/historial_huespedes.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
)
from PySide6.QtCore import Qt
from ui.tabla_reservas import TablaReservas
from utils.stylesheets import ESTILO_PANEL

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

        self.tabla = TablaReservas(
            usuario_actual=self.usuario_actual,
            reserva_service=self.reserva_service,
            columnas=["habitacion", "cliente", "documento", "entrada", "salida", "total", "saldo", "estado"],
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

        btn_actualizar = QPushButton("Actualizar")
        btn_actualizar.setObjectName("accionSecundaria")
        btn_actualizar.setCursor(Qt.PointingHandCursor)
        btn_actualizar.setFixedHeight(38)
        btn_actualizar.clicked.connect(self.refrescar)
        layout.addWidget(btn_actualizar)

        return contenedor

    def refrescar(self):
        if not self.reserva_service:
            return
        self.tabla.llenar(self.reserva_service.obtener_reservas())
