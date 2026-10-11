# ui/panel_dashboard.py
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton
)
from PySide6.QtCore import Qt, Signal
from ui.tabla_reservas import TablaReservas
from utils.stylesheets import COLORES_ESTATUS, ESTILO_PANEL

class TarjetaKpi(QFrame):
    """Indicador numérico del tablero."""

    def __init__(self, titulo, color, parent=None):
        super().__init__(parent)
        self.setObjectName("tarjetaKpi")
        self.setFixedHeight(92)
        self.setMinimumWidth(150)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(2)

        self.lbl_titulo = QLabel(titulo)
        self.lbl_titulo.setObjectName("kpiTitulo")
        self.lbl_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_titulo)

        self.lbl_valor = QLabel("0")
        self.lbl_valor.setObjectName("kpiValor")
        self.lbl_valor.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_valor.setStyleSheet(f"color: {color};")
        layout.addWidget(self.lbl_valor)

    def set_valor(self, valor):
        self.lbl_valor.setText(str(valor))


class PanelDashboard(QWidget):
    """Tablero operativo: ocupación en tiempo real y accesos rápidos."""

    navegar_a = Signal(str)
    # Alta de huésped: la acción más frecuente de la recepción.
    registro_solicitado = Signal()
    # Abre la ventana independiente con el historial completo de huéspedes.
    historial_solicitado = Signal()
    # Un ingreso o una salida mueven la ocupación: hay que refrescar el resto.
    ocupacion_cambiada = Signal()

    def __init__(self, usuario_actual: dict = None, habitacion_service=None, reserva_service=None, parent=None):
        super().__init__(parent)
        self.usuario_actual = usuario_actual or {}
        self.habitacion_service = habitacion_service
        self.reserva_service = reserva_service

        self.setObjectName("panelRaiz")
        # Necesario para que Qt dibuje el fondo de la hoja de estilos: en un
        # QWidget propio no lo hace por defecto.
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(ESTILO_PANEL)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(16)

        # --------------------------------------------------
        # ENCABEZADO
        # --------------------------------------------------
        layout.addWidget(self._crear_encabezado())

        # --------------------------------------------------
        # INDICADORES DE OCUPACIÓN
        # --------------------------------------------------
        layout.addLayout(self._crear_fila_kpis())

        # --------------------------------------------------
        # DETALLE DE OPERACIÓN
        # --------------------------------------------------
        layout.addLayout(self._crear_fila_detalles(), stretch=1)

    def _crear_encabezado(self):
        contenedor = QWidget()
        layout = QHBoxLayout(contenedor)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        textos = QVBoxLayout()
        textos.setSpacing(2)
        lbl_titulo = QLabel("Inicio")
        lbl_titulo.setObjectName("panelTitulo")
        textos.addWidget(lbl_titulo)

        nombre = self.usuario_actual.get("nombre_completo") or self.usuario_actual.get("nombre", "")
        lbl_subtitulo = QLabel(
            f"{self._saludo()}, {nombre}.  {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        )
        lbl_subtitulo.setObjectName("panelSubtitulo")
        textos.addWidget(lbl_subtitulo)

        layout.addLayout(textos)
        layout.addStretch()

        self.btn_historial = QPushButton("Ver historial de huéspedes")
        self.btn_historial.setObjectName("accionSecundaria")
        self.btn_historial.setCursor(Qt.PointingHandCursor)
        self.btn_historial.setFixedHeight(38)
        self.btn_historial.setToolTip("Abre una ventana con todos los registros de huéspedes del hotel.")
        self.btn_historial.clicked.connect(self.historial_solicitado.emit)
        layout.addWidget(self.btn_historial)

        # Acción principal del sistema: llega un cliente y hay que registrarlo.
        self.btn_registrar = QPushButton("+  Registrar Huésped")
        self.btn_registrar.setObjectName("accionPrimaria")
        self.btn_registrar.setCursor(Qt.PointingHandCursor)
        self.btn_registrar.setFixedHeight(38)
        self.btn_registrar.setMinimumWidth(180)
        self.btn_registrar.setToolTip("Registra al cliente que acaba de llegar.")
        self.btn_registrar.clicked.connect(self.registro_solicitado.emit)
        layout.addWidget(self.btn_registrar)

        return contenedor

    def _crear_fila_kpis(self):
        layout = QHBoxLayout()
        layout.setSpacing(12)

        self.kpi_total = TarjetaKpi("HABITACIONES", "#1f2d3d")
        self.kpi_disponibles = TarjetaKpi("DISPONIBLES", COLORES_ESTATUS["Disponible"])
        self.kpi_ocupadas = TarjetaKpi("OCUPADAS HOY", COLORES_ESTATUS["Ocupado"])
        self.kpi_reservadas = TarjetaKpi("RESERVADAS HOY", COLORES_ESTATUS["Reservado"])
        self.kpi_mantenimiento = TarjetaKpi("MANTENIMIENTO", COLORES_ESTATUS["Mantenimiento"])

        for kpi in (self.kpi_total, self.kpi_disponibles, self.kpi_ocupadas,
                    self.kpi_reservadas, self.kpi_mantenimiento):
            layout.addWidget(kpi)

        return layout

    def _crear_fila_detalles(self):
        layout = QHBoxLayout()
        layout.setSpacing(12)

        # Las dos mesas operativas del día: quién está por llegar y quién está
        # alojado. Antes eran textos sueltos; ahora son tablas con su acción de
        # ingreso o salida, como pedía la operación diaria de recepción.
        self.tabla_llegadas = TablaReservas(
            usuario_actual=self.usuario_actual,
            reserva_service=self.reserva_service,
            columnas=["habitacion", "cliente", "entrada", "salida"],
            con_acciones=True,
            con_filtros=False,
            titulo="Reservas pendientes",
            alto=240,
        )
        self.tabla_alojados = TablaReservas(
            usuario_actual=self.usuario_actual,
            reserva_service=self.reserva_service,
            columnas=["habitacion", "cliente", "entrada", "salida"],
            con_acciones=True,
            con_filtros=False,
            titulo="Huéspedes alojados",
            alto=240,
        )

        self.tabla_llegadas.ocupacion_cambiada.connect(self.ocupacion_cambiada.emit)
        self.tabla_alojados.ocupacion_cambiada.connect(self.ocupacion_cambiada.emit)

        layout.addWidget(self.tabla_llegadas, stretch=1)
        layout.addWidget(self.tabla_alojados, stretch=1)
        return layout

    def refrescar(self):
        """Recarga los indicadores y las dos mesas operativas."""
        if not self.habitacion_service or not self.reserva_service:
            return

        resumen = self.habitacion_service.obtener_resumen_ocupacion()
        self.kpi_total.set_valor(resumen["total"])
        self.kpi_disponibles.set_valor(resumen["disponibles"])
        self.kpi_ocupadas.set_valor(resumen["ocupadas"])
        self.kpi_reservadas.set_valor(resumen["reservadas"])
        self.kpi_mantenimiento.set_valor(resumen["mantenimiento"])

        self.kpi_ocupadas.lbl_titulo.setText(
            f"OCUPADAS HOY ({resumen['porcentaje_ocupacion']}%)"
        )

        self.tabla_llegadas.llenar(self.reserva_service.obtener_reservas_pendientes())
        self.tabla_alojados.llenar(self.reserva_service.obtener_en_casa())

    @staticmethod
    def _saludo():
        hora = datetime.now().hour
        if hora < 12:
            return "Buenos días"
        if hora < 19:
            return "Buenas tardes"
        return "Buenas noches"
