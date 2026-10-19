from ui.components import TarjetaKpi
# ui/panel_dashboard.py
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from ui.tabla_reservas import TablaReservas
from utils.stylesheets import COLORES_ESTATUS, COLORES_ESTADO_PAGO, ESTILO_PANEL, ESTILO_TABLA

class PanelDashboard(QWidget):
    """Tablero operativo: ocupación en tiempo real y accesos rápidos."""

    navegar_a = Signal(str)
    # Alta de huésped: la acción más frecuente de la recepción.
    registro_solicitado = Signal()
    # Abre la ventana independiente con el historial completo de huéspedes.
    historial_solicitado = Signal()
    # Un ingreso o una salida mueven la ocupación: hay que refrescar el resto.
    ocupacion_cambiada = Signal()
    # El administrador pidió editar una reserva desde una de las mesas.
    editar_reserva_solicitada = Signal(dict)
    # Clic en una cuenta del tablero: abrir la ventana de pagos de ese huésped.
    cobro_solicitado = Signal(str)

    FILAS_DEUDA = 5

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
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        # --------------------------------------------------
        # ENCABEZADO
        # --------------------------------------------------
        layout.addWidget(self._crear_encabezado())

        # --------------------------------------------------
        # INDICADORES DE OCUPACIÓN
        # --------------------------------------------------
        layout.addLayout(self._crear_fila_kpis())

        # --------------------------------------------------
        # CUENTAS POR COBRAR
        # --------------------------------------------------
        layout.addWidget(self._crear_tarjeta_deudas())

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

    # ------------------------------------------------------------------
    # CUENTAS POR COBRAR
    # ------------------------------------------------------------------
    def _crear_tarjeta_deudas(self):
        grupo = QGroupBox("Cuentas por cobrar · huéspedes alojados")
        grupo.setObjectName("seccion")
        contenedor = QVBoxLayout(grupo)
        contenedor.setContentsMargins(14, 18, 14, 12)
        contenedor.setSpacing(6)

        self.lbl_deuda_total = QLabel("Total por cobrar: $0.00")
        self.lbl_deuda_total.setObjectName("deudaMonto")
        contenedor.addWidget(self.lbl_deuda_total)

        self.tabla_deudas = QTableWidget(0, 3)
        self.tabla_deudas.setHorizontalHeaderLabels(["Hab.", "Huésped", "Saldo"])
        self.tabla_deudas.setStyleSheet(ESTILO_TABLA)
        self.tabla_deudas.verticalHeader().setVisible(False)
        self.tabla_deudas.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla_deudas.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tabla_deudas.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla_deudas.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla_deudas.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        # Al pulsar una fila (sobre todo el nombre del huésped) se abre su
        # cuenta en la ventana de pagos, que es donde está el botón «Cobrar».
        self.tabla_deudas.cellClicked.connect(self._al_elegir_cuenta)
        contenedor.addWidget(self.tabla_deudas)

        grupo.setFixedHeight(190)
        return grupo

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
            alto=200,
        )
        self.tabla_alojados = TablaReservas(
            usuario_actual=self.usuario_actual,
            reserva_service=self.reserva_service,
            columnas=["habitacion", "cliente", "entrada", "salida"],
            con_acciones=True,
            con_filtros=False,
            titulo="Huéspedes alojados",
            alto=200,
        )

        self.tabla_llegadas.ocupacion_cambiada.connect(self.ocupacion_cambiada.emit)
        self.tabla_alojados.ocupacion_cambiada.connect(self.ocupacion_cambiada.emit)
        self.tabla_llegadas.editar_reserva_solicitada.connect(self.editar_reserva_solicitada.emit)
        self.tabla_alojados.editar_reserva_solicitada.connect(self.editar_reserva_solicitada.emit)

        layout.addWidget(self.tabla_llegadas, stretch=1)
        layout.addWidget(self.tabla_alojados, stretch=1)
        return layout

    # ------------------------------------------------------------------
    # DATOS
    # ------------------------------------------------------------------
    def refrescar(self):
        """Recarga los indicadores, las cuentas por cobrar y las dos mesas."""
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

        self._refrescar_deudas()
        self.tabla_llegadas.llenar(self.reserva_service.obtener_reservas_pendientes())
        self.tabla_alojados.llenar(self.reserva_service.obtener_en_casa())

    def _al_elegir_cuenta(self, fila, columna):
        """Abre la cuenta del huésped en la ventana de pagos."""
        # Solo el nombre abre la cuenta: el resto de la fila no es un enlace.
        if columna != 1:
            return
        nombre = (self.tabla_deudas.item(fila, 1).text() or "").strip()
        if nombre:
            self.cobro_solicitado.emit(nombre)

    def _refrescar_deudas(self):
        cuentas = self.reserva_service.obtener_cuentas_por_cobrar()
        self.tabla_deudas.setRowCount(0)

        total = sum((float(cuenta.get("saldo") or 0) for cuenta in cuentas), 0.0)
        self.lbl_deuda_total.setText(
            f"Total por cobrar: ${self.reserva_service.formato_monto(total)}"
        )

        for cuenta in cuentas[: self.FILAS_DEUDA]:
            fila = self.tabla_deudas.rowCount()
            self.tabla_deudas.insertRow(fila)

            valores = [
                str(cuenta.get("habitacion_numero", "")),
                cuenta.get("cliente", ""),
                f"${self.reserva_service.formato_monto(cuenta.get('saldo') or 0)}",
            ]
            for columna, valor in enumerate(valores):
                item = QTableWidgetItem(str(valor))
                if columna == 0:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    fuente = item.font()
                    fuente.setBold(True)
                    item.setFont(fuente)
                if columna == 1:
                    # El nombre es un enlace: al pulsarlo se abre su cuenta en
                    # la ventana de pagos, donde está el botón «Cobrar».
                    item.setForeground(QColor("#2f6fb0"))
                    fuente = item.font()
                    fuente.setBold(True)
                    fuente.setUnderline(True)
                    item.setFont(fuente)
                    item.setToolTip(f"Ver la cuenta de {valor} en Pagos y cobrar.")
                if columna == 2:
                    item.setForeground(QColor(COLORES_ESTADO_PAGO.get("Pendiente", "#c0392b")))
                    fuente = item.font()
                    fuente.setBold(True)
                    item.setFont(fuente)
                self.tabla_deudas.setItem(fila, columna, item)

    @staticmethod
    def _saludo():
        hora = datetime.now().hour
        if hora < 12:
            return "Buenos días"
        if hora < 19:
            return "Buenas tardes"
        return "Buenas noches"
