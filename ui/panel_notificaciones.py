# ui/panel_notificaciones.py
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QScrollArea, QWidget
from PySide6.QtCore import Qt
from services.reserva_service import ReservaService
from utils.stylesheets import ESTILO_NOTIFICACIONES

class PanelNotificaciones(QFrame):
    """Popup con los avisos de cobro y de estadía de recepción.

    Agrupa los avisos en tres momentos, como se hace en un hotel real:
    vencidos (llegada sin pago, deuda pendiente o estadía que se pasó de la
    fecha de salida), para hoy (llegada o salida con saldo) y próximos (cobros
    que vencen dentro de los días de aviso configurados).

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

        self.lbl_subtitulo = QLabel("Cobros vencidos, de hoy y próximos")
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
        """Lee los avisos de cobro y estadía y los pinta agrupados."""
        avisos = self.reserva_service.obtener_alertas_cobro()
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
            vacio = QLabel("No hay cobros pendientes. Todo al día.")
            vacio.setObjectName("avisoVacio")
            vacio.setWordWrap(True)
            self.layout_contenido.addWidget(vacio)
        else:
            secciones = {
                "vencida": "Vencidas",
                "hoy": "Para hoy",
                "proxima": "Próximas",
            }
            tipo_actual = None
            for aviso in avisos:
                if aviso["tipo"] != tipo_actual:
                    tipo_actual = aviso["tipo"]
                    encabezado = QLabel(secciones[tipo_actual])
                    encabezado.setObjectName("avisoSeccion")
                    self.layout_contenido.addWidget(encabezado)
                self.layout_contenido.addWidget(self._crear_item(aviso))

        self.layout_contenido.addStretch()

    def _crear_item(self, aviso):
        item = QFrame()
        # El nombre del objeto cambia el borde izquierdo según la gravedad.
        item.setObjectName(f"avisoItem{aviso['tipo'].capitalize()}")
        layout = QVBoxLayout(item)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(2)

        titulo = QLabel(aviso.get("titulo", ""))
        titulo.setObjectName("avisoTitulo")
        titulo.setWordWrap(True)
        layout.addWidget(titulo)

        detalle = f"{aviso.get('categoria')}. {aviso.get('detalle')}"
        saldo = float(aviso.get("saldo") or 0)
        if saldo > 0:
            detalle += (
                f" Saldo: ${self.reserva_service.formato_monto(saldo)}."
            )

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
