# ui/panel_pagos_reportes.py
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Qt, Signal
from utils.stylesheets import ESTILO_PANEL
from ui.panel_pagos import PanelPagos

class PanelPagosReportes(QWidget):
    """Contenedor del panel de pagos, conservado para la navegación existente."""

    # Propagamos el cobro registrado a la pestaña de Cobros para refrescar el
    # resto de la aplicación (tablero, notificaciones, etc.).
    pago_registrado = Signal()

    def __init__(self, usuario_actual: dict = None, reserva_service=None,
                 habitacion_service=None, es_admin=False, parent=None):
        super().__init__(parent)
        self.usuario_actual = usuario_actual or {}
        self.reserva_service = reserva_service

        self.setObjectName("panelRaiz")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(ESTILO_PANEL)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.panel_pagos = PanelPagos(
            usuario_actual=self.usuario_actual,
            reserva_service=self.reserva_service,
        )
        self.panel_pagos.pago_registrado.connect(self.pago_registrado.emit)
        layout.addWidget(self.panel_pagos, stretch=1)

    def refrescar(self):
        """Recarga las cuentas y cobros."""
        self.panel_pagos.refrescar()

    def aplicar_cuentas(self, cuentas):
        self.panel_pagos.aplicar_cuentas(cuentas)

    def buscar(self, texto):
        """Filtra las cuentas por el huésped indicado."""
        self.panel_pagos.buscar(texto)
