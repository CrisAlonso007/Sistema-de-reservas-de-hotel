# ui/panel_notificaciones.py
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QScrollArea, QWidget
from PySide6.QtCore import Qt
from services.reserva_service import ReservaService
from utils.stylesheets import ESTILO_NOTIFICACIONES

class PanelNotificaciones(QFrame):
    """Popup con los avisos operativos de recepción.

    Hoy avisa las estadías vencidas: huéspedes que siguen en la habitación
    pese a tener el egreso cumplido. Como el sistema no libera la habitación
    por calendario, es el único sitio donde se hace visible ese retraso.

    Es un `Qt.Popup`: se cierra solo cuando se hace clic fuera.
    """

    ANCHO = 380
    ALTO_MAX = 460

    def __init__(self, reserva_service=None, parent=None):
        super().__init__(parent)
        self.reserva_service = reserva_service or ReservaService()

        self.setObjectName("popupNotificaciones")
        # QFrame no pinta el fondo por defecto: se lo pedimos explícitamente.
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(ESTILO_NOTIFICACIONES)
        self.setWindowFlags(Qt.WindowType.Popup)
        self.setFixedWidth(self.ANCHO)
        self.setMaximumHeight(self.ALTO_MAX)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        lbl_titulo = QLabel("Notificaciones")
        lbl_titulo.setObjectName("popupTitulo")
        layout.addWidget(lbl_titulo)

        self.lbl_subtitulo = QLabel("Estadías que superaron su fecha de salida")
        self.lbl_subtitulo.setObjectName("popupSubtitulo")
        layout.addWidget(self.lbl_subtitulo)

        self.area = QScrollArea()
        self.area.setWidgetResizable(True)
        self.area.setFrameShape(QFrame.Shape.NoFrame)
        self.area.setWidgetResizable(True)

        self.contenido = QWidget()
        self.layout_contenido = QVBoxLayout(self.contenido)
        self.layout_contenido.setContentsMargins(0, 0, 0, 0)
        self.layout_contenido.setSpacing(8)
        self.area.setWidget(self.contenido)
        layout.addWidget(self.area, stretch=1)

    # ------------------------------------------------------------------
    # DATOS
    # ------------------------------------------------------------------
    def recargar(self):
        """Lee las estadías vencidas y pinta un aviso por cada una."""
        avisos = self.reserva_service.obtener_estadias_vencidas()
        self.pintar(avisos)

    def pintar(self, avisos):
        """Dibuja la lista de avisos (separamos leer de pintar para poder
        reutilizar el panel con datos de prueba)."""
        # Se vacía el contenedor antes de volver a llenarlo.
        while self.layout_contenido.count():
            item = self.layout_contenido.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        if not avisos:
            vacio = QLabel("No hay estadías vencidas. Todo al día.")
            vacio.setObjectName("avisoVacio")
            vacio.setWordWrap(True)
            self.layout_contenido.addWidget(vacio)
        else:
            for aviso in avisos:
                self.layout_contenido.addWidget(self._crear_item(aviso))

        self.layout_contenido.addStretch()

    def _crear_item(self, aviso):
        item = QFrame()
        item.setObjectName("avisoItem")
        layout = QVBoxLayout(item)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(2)

        dias = aviso.get("dias_excedidos") or 0
        titulo = QLabel(
            f"Habitación {aviso.get('habitacion_numero')} · {aviso.get('cliente')}"
        )
        titulo.setObjectName("avisoTitulo")
        titulo.setWordWrap(True)
        layout.addWidget(titulo)

        detalle = (
            f"Debió salir el {self.reserva_service.formato_fecha(aviso.get('fecha_salida'))} "
            f"· lleva {dias} día(s) de exceso"
        )
        saldo = float(aviso.get("saldo") or 0)
        if saldo > 0:
            detalle += f" · debe ${self.reserva_service.formato_monto(saldo)}"

        texto = QLabel(detalle)
        texto.setObjectName("avisoTexto")
        texto.setWordWrap(True)
        layout.addWidget(texto)

        return item

    # ------------------------------------------------------------------
    # POSICIÓN
    # ------------------------------------------------------------------
    def mostrar_bajo(self, widget):
        """Abre el popup justo debajo del botón que lo invoca."""
        self.recargar()
        posicion = widget.mapToGlobal(widget.rect().bottomLeft())
        self.move(posicion)
        self.show()
        self.raise_()
