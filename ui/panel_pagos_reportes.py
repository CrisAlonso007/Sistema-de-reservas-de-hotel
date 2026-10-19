# ui/panel_pagos_reportes.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QLabel
from PySide6.QtCore import Qt, Signal
from utils.stylesheets import ESTILO_PANEL
from ui.panel_pagos import PanelPagos
from ui.panel_reportes import PanelReportes

class PanelPagosReportes(QWidget):
    """Módulo único de pagos y reportes, con pestañas según el rol.

    Ambos perfiles trabajan la pestaña «Cobros» (saldo y registro de pagos de
    las estancias). La pestaña «Reportes» solo se construye para el
    administrador: así el recepcionista nunca llega a instanciar el módulo
    financiero ni puede alcanzarlo por navegación.
    """

    # Propagamos el cobro registrado a la pestaña de Cobros para refrescar el
    # resto de la aplicación (tablero, notificaciones, etc.).
    pago_registrado = Signal()

    def __init__(self, usuario_actual: dict = None, reserva_service=None,
                 habitacion_service=None, es_admin=False, parent=None):
        super().__init__(parent)
        self.usuario_actual = usuario_actual or {}
        self.reserva_service = reserva_service
        self.habitacion_service = habitacion_service
        self.es_admin = es_admin

        self.setObjectName("panelRaiz")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(ESTILO_PANEL)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)

        encabezado = QVBoxLayout()
        encabezado.setSpacing(2)
        lbl_titulo = QLabel("Ingresos")
        lbl_titulo.setObjectName("panelTitulo")
        encabezado.addWidget(lbl_titulo)
        lbl_sub = QLabel(
            "Cuentas y cobros de las estancias · reportes de ingresos y cancelaciones"
        )
        lbl_sub.setObjectName("panelSubtitulo")
        encabezado.addWidget(lbl_sub)
        layout.addLayout(encabezado)

        self.tabs = QTabWidget()

        self.panel_pagos = PanelPagos(
            usuario_actual=self.usuario_actual,
            reserva_service=self.reserva_service,
        )
        self.panel_pagos.pago_registrado.connect(self.pago_registrado.emit)
        self.tabs.addTab(self.panel_pagos, "Cobros")

        self.panel_reportes = None
        if self.es_admin:
            self.panel_reportes = PanelReportes(
                usuario_actual=self.usuario_actual,
                reserva_service=self.reserva_service,
                habitacion_service=self.habitacion_service,
            )
            self.tabs.addTab(self.panel_reportes, "Reportes")

        self.tabs.currentChanged.connect(self._al_cambiar_pestana)
        layout.addWidget(self.tabs, stretch=1)

    # ------------------------------------------------------------------
    # PESTAÑAS
    # ------------------------------------------------------------------
    def _al_cambiar_pestana(self, indice):
        """Refresca la pestaña recién abierta; los reportes son más costosos."""
        if self.panel_reportes is not None and self.tabs.widget(indice) is self.panel_reportes:
            self.panel_reportes.refrescar()

    def refrescar(self):
        """Recarga los cobros siempre, y los reportes solo si están visibles."""
        self.panel_pagos.refrescar()
        if self.panel_reportes is not None and self.tabs.currentWidget() is self.panel_reportes:
            self.panel_reportes.refrescar()

    def ir_a_reportes(self):
        """Lleva a la pestaña de reportes si el rol puede verla."""
        if self.panel_reportes is not None:
            self.tabs.setCurrentWidget(self.panel_reportes)

    def ir_a_cobros(self):
        self.tabs.setCurrentWidget(self.panel_pagos)

    def buscar(self, texto):
        """Va a la pestaña de Cobros filtrando por el huésped indicado."""
        self.ir_a_cobros()
        self.panel_pagos.buscar(texto)
