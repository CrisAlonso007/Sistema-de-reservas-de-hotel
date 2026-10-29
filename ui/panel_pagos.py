# ui/panel_pagos.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QLineEdit, QComboBox,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from services.reserva_service import ReservaService
from ui.dialogs import DialogoCobro
from utils.stylesheets import COLORES_ESTADO_PAGO, ESTILO_PANEL, ESTILO_TABLA

class PanelPagos(QWidget):
    """Gestión de cobros y saldos de las estancias.

    Es la pestaña que antes compartía las mesas de recepción. Ahora está
    dedicada exclusivamente al pago: muestra el saldo y el estado de cuenta de
    cada reserva vigente y abre el diálogo de cobro.
    """

    # Un cobro cambia el saldo que muestra este panel y el historial.
    pago_registrado = Signal()

    ANCHO_COLUMNA_ACCIONES = 130

    def __init__(self, usuario_actual: dict = None, reserva_service=None, parent=None):
        super().__init__(parent)
        self.usuario_actual = usuario_actual or {}
        self.reserva_service = reserva_service

        self.setObjectName("panelRaiz")
        # Necesario para que Qt dibuje el fondo de la hoja de estilos.
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(ESTILO_PANEL)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)

        layout.addWidget(self._crear_encabezado())
        layout.addLayout(self._crear_tabla(), stretch=1)

    def _crear_encabezado(self):
        contenedor = QWidget()
        layout = QHBoxLayout(contenedor)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        textos = QVBoxLayout()
        textos.setSpacing(2)

        lbl_titulo = QLabel("Pagos")
        lbl_titulo.setObjectName("panelTitulo")
        textos.addWidget(lbl_titulo)

        lbl_subtitulo = QLabel("Consulta pagos realizados y revisa saldos pendientes.")
        lbl_subtitulo.setObjectName("panelSubtitulo")
        textos.addWidget(lbl_subtitulo)

        layout.addLayout(textos)
        layout.addStretch()

        btn_actualizar = QPushButton("Actualizar")
        btn_actualizar.setObjectName("accionSecundaria")
        btn_actualizar.setCursor(Qt.PointingHandCursor)
        btn_actualizar.setFixedHeight(38)
        btn_actualizar.setToolTip("Vuelve a consultar los pagos y saldos pendientes.")
        btn_actualizar.clicked.connect(self.refrescar)
        layout.addWidget(btn_actualizar)

        return contenedor

    def _crear_tabla(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)

        grupo = QGroupBox("Estado de pagos")
        grupo.setObjectName("seccion")
        layout_grupo = QVBoxLayout(grupo)
        layout_grupo.setContentsMargins(14, 18, 14, 14)
        layout_grupo.setSpacing(10)

        layout_grupo.addWidget(self._crear_barra())

        self.tabla = QTableWidget(0, 7)
        self.tabla.setHorizontalHeaderLabels(
            ["Hab.", "Huésped", "Total", "Pagado", "Saldo", "Estado de pago", ""]
        )
        self.tabla.setStyleSheet(ESTILO_TABLA)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tabla.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.tabla.setColumnWidth(6, self.ANCHO_COLUMNA_ACCIONES)
        layout_grupo.addWidget(self.tabla)

        layout.addWidget(grupo)
        return layout

    def _crear_barra(self):
        barra = QWidget()
        layout = QHBoxLayout(barra)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.txt_buscar = QLineEdit()
        self.txt_buscar.setObjectName("campoFiltro")
        self.txt_buscar.setPlaceholderText("Buscar por huésped, habitación o documento...")
        self.txt_buscar.setClearButtonEnabled(True)
        self.txt_buscar.setFixedHeight(30)
        self.txt_buscar.setToolTip("Filtra los pagos por huésped, habitación o documento.")
        self.txt_buscar.textChanged.connect(self._filtrar)
        layout.addWidget(self.txt_buscar, stretch=1)

        self.cmb_estado_pago = QComboBox()
        self.cmb_estado_pago.setObjectName("campoFiltro")
        self.cmb_estado_pago.addItem("Todos los estados de pago", "")
        for estado in ReservaService.ESTADOS_PAGO:
            self.cmb_estado_pago.addItem(ReservaService.etiqueta_estado_pago(estado), estado)
        self.cmb_estado_pago.setFixedHeight(30)
        self.cmb_estado_pago.setToolTip("Muestra solo los pagos del estado elegido.")
        self.cmb_estado_pago.currentIndexChanged.connect(self._filtrar)
        layout.addWidget(self.cmb_estado_pago)

        self.lbl_conteo = QLabel("")
        self.lbl_conteo.setObjectName("panelSubtitulo")
        self.lbl_conteo.setMinimumWidth(160)
        self.lbl_conteo.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.lbl_conteo)

        return barra

    # ------------------------------------------------------------------
    # DATOS
    # ------------------------------------------------------------------
    def refrescar(self):
        """Recarga los pagos y saldos de las reservas vigentes."""
        if not self.reserva_service:
            return

        self.tabla.setRowCount(0)
        self.tabla.clearSpans()
        cuentas = self.reserva_service.obtener_cuentas()

        if not cuentas:
            item = QTableWidgetItem("No hay reservas vigentes para mostrar.")
            item.setForeground(QColor("#8a97a6"))
            self.tabla.setRowCount(1)
            self.tabla.setItem(0, 0, item)
            self.tabla.setSpan(0, 0, 1, self.tabla.columnCount())
            self.lbl_conteo.setText("")
            return

        for cuenta in cuentas:
            fila = self.tabla.rowCount()
            self.tabla.insertRow(fila)

            celdas = [
                str(cuenta["habitacion_numero"]),
                cuenta["cliente"],
                f"${self.reserva_service.formato_monto(cuenta['total'])}",
                f"${self.reserva_service.formato_monto(cuenta['monto_pagado'])}",
                f"${self.reserva_service.formato_monto(cuenta['saldo'])}",
            ]
            for columna, texto in enumerate(celdas):
                item = QTableWidgetItem(str(texto))
                if columna == 0:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    fuente = item.font()
                    fuente.setBold(True)
                    item.setFont(fuente)
                    item.setData(Qt.ItemDataRole.UserRole, {
                        "estado_pago": cuenta["estado_pago"],
                        "texto": self._texto_buscable(cuenta),
                    })
                if columna == 4:
                    item.setForeground(QColor(
                        COLORES_ESTADO_PAGO["Pagado"]
                        if float(cuenta["saldo"] or 0) <= 0
                        else COLORES_ESTADO_PAGO["Pendiente"]
                    ))
                    fuente = item.font()
                    fuente.setBold(True)
                    item.setFont(fuente)
                self.tabla.setItem(fila, columna, item)

            estado_item = QTableWidgetItem(
                ReservaService.etiqueta_estado_pago(cuenta["estado_pago"])
            )
            estado_item.setForeground(QColor(
                COLORES_ESTADO_PAGO.get(cuenta["estado_pago"], "#1f2d3d")
            ))
            estado_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tabla.setItem(fila, 5, estado_item)

            self.tabla.setCellWidget(fila, 6, self._crear_boton_cobrar(cuenta))

        self._filtrar()

    def _crear_boton_cobrar(self, cuenta):
        contenedor = QWidget()
        layout = QVBoxLayout(contenedor)
        layout.setContentsMargins(2, 3, 2, 3)

        saldada = float(cuenta["saldo"] or 0) <= 0
        btn = QPushButton("Saldada" if saldada else "Cobrar")
        btn.setObjectName("accionTablaPrimaria")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(28)
        btn.setEnabled(not saldada)
        if saldada:
            btn.setToolTip("Esta reserva ya está pagada por completo.")
        else:
            btn.setToolTip("Abrir el detalle y registrar un pago.")
            btn.clicked.connect(lambda _=False, c=cuenta: self._abrir_cobro(c))
        layout.addWidget(btn)
        return contenedor

    @staticmethod
    def _texto_buscable(cuenta) -> str:
        partes = [
            str(cuenta.get("habitacion_numero", "")),
            cuenta.get("cliente", ""),
            cuenta.get("identificacion", ""),
            cuenta.get("contacto", ""),
            cuenta.get("estado_pago", ""),
        ]
        return " ".join(partes).lower()

    def _filtrar(self, *_):
        texto = self.txt_buscar.text().strip().lower()
        estado = self.cmb_estado_pago.currentData()

        total = 0
        visibles = 0
        for fila in range(self.tabla.rowCount()):
            celda = self.tabla.item(fila, 0)
            if celda is None:
                continue
            datos = celda.data(Qt.ItemDataRole.UserRole)
            if not isinstance(datos, dict):
                continue

            total += 1
            coincide = (
                (not texto or texto in datos["texto"])
                and (not estado or datos["estado_pago"] == estado)
            )
            self.tabla.setRowHidden(fila, not coincide)
            if coincide:
                visibles += 1

        self.lbl_conteo.setText(f"{visibles} de {total} reservas" if total else "")

    # ------------------------------------------------------------------
    # COBRO
    # ------------------------------------------------------------------
    def buscar(self, texto):
        """Filtra las reservas por el huésped indicado desde el tablero."""
        self.txt_buscar.setText(str(texto or ""))
        self._filtrar()

    def _abrir_cobro(self, cuenta):
        dialogo = DialogoCobro(
            usuario_actual=self.usuario_actual,
            reserva_service=self.reserva_service,
            reserva=cuenta,
            parent=self,
        )
        dialogo.pago_registrado.connect(self._al_registrar_pago)
        dialogo.exec()

    def _al_registrar_pago(self):
        self.refrescar()
        self.pago_registrado.emit()
