# ui/panel_dashboard.py
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGroupBox, QPushButton
)
from PySide6.QtCore import Qt, Signal
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
        layout.addLayout(self._crear_fila_detalles())

        layout.addStretch()

    def _crear_encabezado(self):
        contenedor = QWidget()
        layout = QHBoxLayout(contenedor)
        layout.setContentsMargins(0, 0, 0, 0)

        textos = QVBoxLayout()
        textos.setSpacing(2)

        lbl_titulo = QLabel("Panel de Control")
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

        # Acción principal del sistema: llega un cliente y hay que registrarlo.
        self.btn_registrar = QPushButton("+  Registrar Huésped")
        self.btn_registrar.setObjectName("accionPrimaria")
        self.btn_registrar.setCursor(Qt.PointingHandCursor)
        self.btn_registrar.setFixedHeight(38)
        self.btn_registrar.setMinimumWidth(180)
        self.btn_registrar.setToolTip("Registra al cliente que acaba de llegar.")
        self.btn_registrar.clicked.connect(self.registro_solicitado.emit)
        layout.addWidget(self.btn_registrar)

        btn_recepcion = QPushButton("Ir a Recepción")
        btn_recepcion.setObjectName("accionSecundaria")
        btn_recepcion.setCursor(Qt.PointingHandCursor)
        btn_recepcion.clicked.connect(lambda: self.navegar_a.emit("recepcion"))
        layout.addWidget(btn_recepcion)

        if self.usuario_actual.get("rol") == "administrador":
            btn_catalogo = QPushButton("Gestionar Catálogo")
            btn_catalogo.setObjectName("accionSecundaria")
            btn_catalogo.setCursor(Qt.PointingHandCursor)
            btn_catalogo.clicked.connect(lambda: self.navegar_a.emit("catalogo"))
            layout.addWidget(btn_catalogo)

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

        # --------------------------------------------------
        # LLEGADAS PENDIENTES
        # --------------------------------------------------
        grupo_llegadas = QGroupBox("Llegadas pendientes de ingreso")
        grupo_llegadas.setObjectName("seccion")
        layout_llegadas = QVBoxLayout(grupo_llegadas)
        layout_llegadas.setContentsMargins(16, 18, 16, 14)

        self.lbl_llegadas = QLabel("—")
        self.lbl_llegadas.setWordWrap(True)
        self.lbl_llegadas.setTextFormat(Qt.TextFormat.PlainText)
        self.lbl_llegadas.setStyleSheet("font-size: 12px; color: #1f2d3d; font-weight: normal;")
        layout_llegadas.addWidget(self.lbl_llegadas)
        layout_llegadas.addStretch()

        # --------------------------------------------------
        # HUÉSPEDES ALOJADOS
        # --------------------------------------------------
        grupo_casa = QGroupBox("Huéspedes alojados")
        grupo_casa.setObjectName("seccion")
        layout_casa = QVBoxLayout(grupo_casa)
        layout_casa.setContentsMargins(16, 18, 16, 14)

        self.lbl_en_casa = QLabel("—")
        self.lbl_en_casa.setWordWrap(True)
        self.lbl_en_casa.setTextFormat(Qt.TextFormat.PlainText)
        self.lbl_en_casa.setStyleSheet("font-size: 12px; color: #1f2d3d; font-weight: normal;")
        layout_casa.addWidget(self.lbl_en_casa)
        layout_casa.addStretch()

        layout.addWidget(grupo_llegadas)
        layout.addWidget(grupo_casa)
        return layout

    def refrescar(self):
        """Recarga los indicadores con el estado actual del hotel."""
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

        llegadas = self.reserva_service.obtener_llegadas_hoy()
        if llegadas:
            self.lbl_llegadas.setText("\n".join(
                f"· Hab. {res['habitacion_numero']} — {res['cliente']} (al {self._fechas(res)})"
                for res in llegadas[:5]
            ))
        else:
            self.lbl_llegadas.setText("No hay llegadas pendientes para hoy.")

        en_casa = self.reserva_service.obtener_en_casa()
        if en_casa:
            self.lbl_en_casa.setText("\n".join(
                f"· Hab. {res['habitacion_numero']} — {res['cliente']} (sale {self._fechas(res)})"
                for res in en_casa[:5]
            ))
        else:
            self.lbl_en_casa.setText("No hay huéspedes alojados en este momento.")

    def _fechas(self, reserva):
        return (
            f"{self.reserva_service.formato_fecha(reserva['fecha_entrada'])} a "
            f"{self.reserva_service.formato_fecha(reserva['fecha_salida'])}"
        )

    @staticmethod
    def _saludo():
        hora = datetime.now().hour
        if hora < 12:
            return "Buenos días"
        if hora < 19:
            return "Buenas tardes"
        return "Buenas noches"
