# ui/dialogo_cobro.py
from decimal import Decimal, InvalidOperation
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QFormLayout,
    QDoubleSpinBox, QComboBox, QPushButton, QMessageBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from services.reserva_service import ReservaService
from utils.stylesheets import ESTILO_PANEL, ESTILO_TABLA

class DialogoCobro(QDialog):
    """Desglose de la cuenta de una reserva y registro del cobro.

    Es la ventana flotante de recepción: muestra en detalle qué se cobra
    (noches, precio por noche, total, abonos) y permite elegir el método de
    pago antes de registrar el monto.
    """

    pago_registrado = Signal()

    def __init__(self, usuario_actual: dict, reserva_service, reserva, parent=None):
        super().__init__(parent)
        self.usuario_actual = usuario_actual or {}
        self.reserva_service = reserva_service
        self.reserva = reserva
        self.saldo = self._dec(reserva.get("saldo", 0))

        self.setWindowTitle("Cobrar cuenta")
        self.setModal(True)
        self.setObjectName("panelRaiz")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(ESTILO_PANEL)
        self.setFixedWidth(480)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(12)

        lbl_titulo = QLabel("Cobro de estancia")
        lbl_titulo.setObjectName("panelTitulo")
        layout.addWidget(lbl_titulo)

        lbl_subtitulo = QLabel(
            f"{reserva['cliente']} · Habitación {reserva['habitacion_numero']}"
        )
        lbl_subtitulo.setObjectName("panelSubtitulo")
        layout.addWidget(lbl_subtitulo)

        layout.addWidget(self._crear_desglose())
        layout.addWidget(self._crear_historial())
        layout.addWidget(self._crear_seccion_cobro())
        layout.addLayout(self._crear_botones())

    # ------------------------------------------------------------------
    # CONSTRUCCIÓN
    # ------------------------------------------------------------------
    def _crear_desglose(self):
        grupo = QGroupBox("Desglose de la cuenta")
        grupo.setObjectName("seccion")
        form = QFormLayout(grupo)
        form.setContentsMargins(16, 18, 16, 14)
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        noches = int(self.reserva.get("noches", 0) or 0)
        total = self._dec(self.reserva.get("total", 0))
        pagado = self._dec(self.reserva.get("monto_pagado", 0))
        precio_noche = (total / noches) if noches else Decimal("0")

        form.addRow("Estadía:", QLabel(self._texto_estadia()))
        form.addRow("Noches:", QLabel(str(noches)))
        form.addRow("Precio por noche:", QLabel(f"${self.reserva_service.formato_monto(precio_noche)}"))
        form.addRow("Total de la cuenta:", self._valor_fuerte(f"${self.reserva_service.formato_monto(total)}"))
        form.addRow("Abonado:", self._valor(f"${self.reserva_service.formato_monto(pagado)}"))
        form.addRow("Saldo pendiente:", self._valor_fuerte(
            f"${self.reserva_service.formato_monto(self.saldo)}",
            "#c0392b" if self.saldo > 0 else "#2e9e5b",
        ))

        return grupo

    def _crear_historial(self):
        grupo = QGroupBox("Pagos registrados")
        grupo.setObjectName("seccion")
        layout = QVBoxLayout(grupo)
        layout.setContentsMargins(16, 18, 16, 14)

        pagos = self.reserva_service.obtener_pagos_reserva(self.reserva["id"])

        self.tabla_pagos = QTableWidget(0, 4)
        self.tabla_pagos.setHorizontalHeaderLabels(["Fecha", "Monto", "Método", "Registró"])
        self.tabla_pagos.setStyleSheet(ESTILO_TABLA)
        self.tabla_pagos.verticalHeader().setVisible(False)
        self.tabla_pagos.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla_pagos.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.tabla_pagos.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.tabla_pagos.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla_pagos.setFixedHeight(110)

        if pagos:
            for pago in pagos:
                fila = self.tabla_pagos.rowCount()
                self.tabla_pagos.insertRow(fila)
                celdas = [
                    self._texto_fecha(pago["creado_en"]),
                    f"${self.reserva_service.formato_monto(pago['monto'])}",
                    pago["metodo_pago"],
                    pago["empleado"],
                ]
                for columna, texto in enumerate(celdas):
                    self.tabla_pagos.setItem(fila, columna, QTableWidgetItem(str(texto)))
        else:
            self.tabla_pagos.setRowCount(1)
            item = QTableWidgetItem("Todavía no se registró ningún pago.")
            item.setForeground(QColor("#8a97a6"))
            self.tabla_pagos.setItem(0, 0, item)
            self.tabla_pagos.setSpan(0, 0, 1, 4)

        layout.addWidget(self.tabla_pagos)
        return grupo

    def _crear_seccion_cobro(self):
        grupo = QGroupBox("Registrar cobro")
        grupo.setObjectName("seccion")
        form = QFormLayout(grupo)
        form.setContentsMargins(16, 18, 16, 14)
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        self.spn_monto = QDoubleSpinBox()
        self.spn_monto.setDecimals(2)
        self.spn_monto.setPrefix("$")
        self.spn_monto.setMinimum(0.01)
        self.spn_monto.setMaximum(float(self.saldo if self.saldo > 0 else Decimal("0.01")))
        self.spn_monto.setValue(float(self.saldo if self.saldo > 0 else Decimal("0.01")))
        self.spn_monto.setFixedHeight(32)
        self.spn_monto.setEnabled(self.saldo > 0)
        form.addRow("Monto a cobrar:", self.spn_monto)

        self.cmb_metodo = QComboBox()
        self.cmb_metodo.addItems(ReservaService.METODOS_PAGO)
        metodo_actual = self.reserva.get("metodo_pago")
        if metodo_actual in ReservaService.METODOS_PAGO:
            self.cmb_metodo.setCurrentText(metodo_actual)
        self.cmb_metodo.setFixedHeight(32)
        self.cmb_metodo.setEnabled(self.saldo > 0)
        form.addRow("Método de pago:", self.cmb_metodo)

        if self.saldo <= 0:
            aviso = QLabel("Esta cuenta ya está saldada.")
            aviso.setStyleSheet("color: #2e9e5b; font-size: 12px; font-weight: bold;")
            form.addRow("", aviso)

        return grupo

    def _crear_botones(self):
        layout = QHBoxLayout()
        layout.setSpacing(10)
        layout.addStretch()

        btn_cancelar = QPushButton("Cerrar")
        btn_cancelar.setObjectName("accionSecundaria")
        btn_cancelar.setFixedHeight(38)
        btn_cancelar.setCursor(Qt.PointingHandCursor)
        btn_cancelar.clicked.connect(self.reject)
        layout.addWidget(btn_cancelar)

        self.btn_cobrar = QPushButton("Registrar pago")
        self.btn_cobrar.setObjectName("accionPrimaria")
        self.btn_cobrar.setFixedHeight(38)
        self.btn_cobrar.setMinimumWidth(150)
        self.btn_cobrar.setCursor(Qt.PointingHandCursor)
        self.btn_cobrar.setEnabled(self.saldo > 0)
        self.btn_cobrar.clicked.connect(self._registrar)
        layout.addWidget(self.btn_cobrar)

        return layout

    # ------------------------------------------------------------------
    # REGISTRO
    # ------------------------------------------------------------------
    def _registrar(self):
        monto = Decimal(str(self.spn_monto.value())).quantize(Decimal("0.01"))
        metodo = self.cmb_metodo.currentText()

        exito, mensaje = self.reserva_service.registrar_pago(
            usuario_actual=self.usuario_actual,
            reserva_id=self.reserva["id"],
            monto=monto,
            metodo_pago=metodo,
        )

        if exito:
            QMessageBox.information(self, "Pago registrado", mensaje)
            self.pago_registrado.emit()
            self.accept()
        else:
            QMessageBox.warning(self, "No se pudo cobrar", mensaje)

    # ------------------------------------------------------------------
    # UTILIDADES
    # ------------------------------------------------------------------
    def _texto_estadia(self):
        return (
            f"{self.reserva_service.formato_fecha(self.reserva['fecha_entrada'])} a "
            f"{self.reserva_service.formato_fecha(self.reserva['fecha_salida'])}"
        )

    @staticmethod
    def _dec(valor):
        try:
            return Decimal(str(valor or 0))
        except (InvalidOperation, TypeError, ValueError):
            return Decimal("0")

    @staticmethod
    def _texto_fecha(valor):
        if hasattr(valor, "strftime"):
            return valor.strftime("%d/%m/%Y %H:%M")
        return str(valor)

    @staticmethod
    def _valor(texto):
        etiqueta = QLabel(texto)
        etiqueta.setStyleSheet("font-size: 13px; color: #1f2d3d;")
        return etiqueta

    @staticmethod
    def _valor_fuerte(texto, color="#1f2d3d"):
        etiqueta = QLabel(texto)
        etiqueta.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {color};")
        return etiqueta
