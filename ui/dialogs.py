# ui/dialogs.py
from decimal import Decimal, InvalidOperation
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QComboBox,
    QDateEdit, QPushButton, QMessageBox, QGroupBox, QDoubleSpinBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QFileDialog,
)
from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtGui import QColor
from services.generador_pdf import generar_comprobante_pdf
from utils.stylesheets import ESTILO_PANEL, ESTILO_TABLA
from utils.validaciones import (
    es_monto_cobro_valido,
    filtrar_precio,
    aplicar_validador,
    crear_etiqueta_error,
)

class DialogoEditarReserva(QDialog):
    """Corrige las fechas y habitación de una reserva pendiente."""

    guardado = Signal()

    def __init__(self, reserva, usuario_actual, reserva_service,
                 habitacion_service, parent=None):
        super().__init__(parent)
        self.reserva = reserva
        self.usuario_actual = usuario_actual or {}
        self.reserva_service = reserva_service
        self.habitacion_service = habitacion_service

        self.setWindowTitle("Editar reserva")
        self.setModal(True)
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        lbl_aviso = QLabel(
            f"Huésped: {reserva['cliente']}  ·  Documento: {reserva['identificacion']}"
        )
        lbl_aviso.setObjectName("panelSubtitulo")
        layout.addWidget(lbl_aviso)

        formulario = QFormLayout()
        formulario.setSpacing(8)

        self.cmb_habitacion = QComboBox()
        self._cargar_habitaciones(reserva.get("habitacion_id"))
        cantidad_huespedes = int(reserva.get("numero_huespedes") or 1)
        texto_huespedes = (
            f"{cantidad_huespedes} huésped"
            if cantidad_huespedes == 1
            else f"{cantidad_huespedes} huéspedes"
        )

        self.dt_entrada = QDateEdit()
        self.dt_entrada.setCalendarPopup(True)
        self.dt_entrada.setDisplayFormat("yyyy-MM-dd")
        self.dt_entrada.setDate(self._a_qdate(reserva.get("fecha_entrada")))
        self.dt_entrada.setFixedHeight(32)

        self.dt_salida = QDateEdit()
        self.dt_salida.setCalendarPopup(True)
        self.dt_salida.setDisplayFormat("yyyy-MM-dd")
        self.dt_salida.setDate(self._a_qdate(reserva.get("fecha_salida")))
        self.dt_salida.setFixedHeight(32)

        self.lbl_noches = QLabel("")
        self.lbl_noches.setObjectName("panelSubtitulo")

        formulario.addRow("Habitación:", self.cmb_habitacion)
        formulario.addRow("Huéspedes:", QLabel(texto_huespedes))
        formulario.addRow("Entrada:", self.dt_entrada)
        formulario.addRow("Salida:", self.dt_salida)
        formulario.addRow("", self.lbl_noches)
        layout.addLayout(formulario)

        self.dt_entrada.dateChanged.connect(self._actualizar_noches)
        self.dt_salida.dateChanged.connect(self._actualizar_noches)
        self._actualizar_noches()

        botones = QHBoxLayout()
        botones.addStretch()
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setObjectName("accionSecundaria")
        btn_cancelar.clicked.connect(self.reject)
        btn_guardar = QPushButton("Guardar cambios")
        btn_guardar.setObjectName("accionPrimaria")
        btn_guardar.clicked.connect(self._guardar)
        botones.addWidget(btn_cancelar)
        botones.addWidget(btn_guardar)
        layout.addLayout(botones)

    def _cargar_habitaciones(self, actual_id):
        habitaciones = self.habitacion_service.obtener_todas()
        for habitacion in habitaciones:
            etiqueta = (
                f"{habitacion['numero']} · {habitacion['tipo']} · "
                f"capacidad {habitacion['capacidad']}"
            )
            self.cmb_habitacion.addItem(etiqueta, habitacion["id"])
            if habitacion["id"] == actual_id:
                self.cmb_habitacion.setCurrentIndex(self.cmb_habitacion.count() - 1)

    @staticmethod
    def _a_qdate(valor):
        if hasattr(valor, "year") and hasattr(valor, "month") and hasattr(valor, "day"):
            return QDate(valor.year, valor.month, valor.day)
        fecha = QDate.fromString(str(valor), "yyyy-MM-dd")
        return fecha if fecha.isValid() else QDate.currentDate()

    def _actualizar_noches(self):
        noches = self.dt_entrada.date().daysTo(self.dt_salida.date())
        if noches > 0:
            self.lbl_noches.setText(f"{noches} noche(s). El total se recalcula al guardar.")
        else:
            self.lbl_noches.setText("La salida debe ser posterior a la entrada.")

    def _guardar(self):
        habitacion_id = self.cmb_habitacion.currentData()
        exito, mensaje = self.reserva_service.editar_reserva(
            usuario_actual=self.usuario_actual,
            reserva_id=self.reserva["id"],
            fecha_entrada=self.dt_entrada.date().toString("yyyy-MM-dd"),
            fecha_salida=self.dt_salida.date().toString("yyyy-MM-dd"),
            habitacion_id=habitacion_id,
        )
        if not exito:
            QMessageBox.warning(self, "No se pudo guardar", mensaje)
            return
        QMessageBox.information(self, "Reserva actualizada", mensaje)
        self.guardado.emit()
        self.accept()


class DialogoDetalleReserva(QDialog):
    """Muestra la información completa disponible de una reserva."""

    def __init__(self, reserva, reserva_service, parent=None):
        super().__init__(parent)
        self.reserva = reserva
        self.reserva_service = reserva_service

        habitacion = reserva.get("habitacion_numero", "—")
        self.setWindowTitle(f"Reserva · Habitación {habitacion}")
        self.setModal(True)
        self.setMinimumWidth(440)
        self.setObjectName("panelRaiz")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(ESTILO_PANEL)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(12)

        titulo = QLabel(str(reserva.get("cliente") or "Detalle de reserva"))
        titulo.setObjectName("panelTitulo")
        titulo.setWordWrap(True)
        layout.addWidget(titulo)

        subtitulo = QLabel(
            f"Reserva #{reserva.get('id', '—')}  ·  Habitación {habitacion}"
        )
        subtitulo.setObjectName("panelSubtitulo")
        layout.addWidget(subtitulo)

        formulario = QFormLayout()
        formulario.setSpacing(9)
        formulario.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        formulario.setFormAlignment(Qt.AlignmentFlag.AlignTop)

        self._agregar_dato(formulario, "Estado:", self._estado_reserva())
        self._agregar_dato(
            formulario, "Documento:", reserva.get("identificacion")
        )
        self._agregar_dato(formulario, "Contacto:", reserva.get("contacto"))
        self._agregar_dato(
            formulario,
            "Huéspedes:",
            reserva.get("numero_huespedes"),
        )
        self._agregar_dato(
            formulario,
            "Entrada:",
            self.reserva_service.formato_fecha(reserva.get("fecha_entrada")),
        )
        self._agregar_dato(
            formulario,
            "Salida:",
            self.reserva_service.formato_fecha(reserva.get("fecha_salida")),
        )
        self._agregar_dato(formulario, "Noches:", reserva.get("noches"))
        self._agregar_dato(
            formulario,
            "Método de pago:",
            reserva.get("metodo_pago"),
        )
        self._agregar_dato(
            formulario,
            "Total:",
            self.reserva_service.formato_dinero(reserva.get("total") or 0),
        )
        self._agregar_dato(
            formulario,
            "Abonado:",
            self.reserva_service.formato_dinero(reserva.get("monto_pagado") or 0),
        )
        self._agregar_dato(
            formulario,
            "Saldo pendiente:",
            self.reserva_service.formato_dinero(reserva.get("saldo") or 0),
        )
        if reserva.get("empleado_nombre"):
            self._agregar_dato(
                formulario, "Registró:", reserva.get("empleado_nombre")
            )
        if reserva.get("checkin_empleado"):
            self._agregar_dato(
                formulario, "Registró ingreso:", reserva.get("checkin_empleado")
            )
        if reserva.get("salida_empleado"):
            self._agregar_dato(
                formulario, "Registró salida:", reserva.get("salida_empleado")
            )
        layout.addLayout(formulario)

        botones = QHBoxLayout()
        botones.addStretch()
        cerrar = QPushButton("Cerrar")
        cerrar.setObjectName("accionPrimaria")
        cerrar.setCursor(Qt.PointingHandCursor)
        cerrar.setFixedHeight(36)
        cerrar.clicked.connect(self.accept)
        botones.addWidget(cerrar)
        layout.addLayout(botones)

    @staticmethod
    def _agregar_dato(formulario, etiqueta, valor):
        texto = "—" if valor is None or str(valor).strip() == "" else str(valor)
        contenido = QLabel(texto)
        contenido.setWordWrap(True)
        formulario.addRow(etiqueta, contenido)

    def _estado_reserva(self):
        estado = self.reserva.get("estado")
        if estado:
            return self.reserva_service.etiqueta_estado(estado)
        return "—"


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

        self.setWindowTitle("Cobro de estancia")
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
        cantidad_huespedes = int(self.reserva.get("numero_huespedes") or 1)
        texto_huespedes = (
            f"{cantidad_huespedes} huésped"
            if cantidad_huespedes == 1
            else f"{cantidad_huespedes} huéspedes"
        )
        form.addRow("Huéspedes:", QLabel(texto_huespedes))
        form.addRow("Noches:", QLabel(str(noches)))
        form.addRow("Precio por noche:", QLabel(self.reserva_service.formato_dinero(precio_noche)))
        form.addRow("Total de la cuenta:", self._valor_fuerte(self.reserva_service.formato_dinero(total)))
        form.addRow("Abonado:", self._valor(self.reserva_service.formato_dinero(pagado)))
        form.addRow("Saldo pendiente:", self._valor_fuerte(
            self.reserva_service.formato_dinero(self.saldo),
            "#c0392b" if self.saldo > 0 else "#2e9e5b",
        ))

        return grupo

    def _crear_historial(self):
        grupo = QGroupBox("Pagos registrados")
        grupo.setObjectName("seccion")
        layout = QVBoxLayout(grupo)
        layout.setContentsMargins(16, 18, 16, 14)

        pagos = self.reserva_service.obtener_pagos_reserva(self.reserva["id"])

        self.tabla_pagos = QTableWidget(0, 5)
        self.tabla_pagos.setHorizontalHeaderLabels(
            ["Fecha", "Monto", "Método", "Registró", "Comprobante"]
        )
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
                    self.reserva_service.formato_dinero(pago["monto"]),
                    pago["metodo_pago"],
                    pago["empleado"],
                ]
                for columna, texto in enumerate(celdas):
                    self.tabla_pagos.setItem(fila, columna, QTableWidgetItem(str(texto)))
                if int(pago["id"]) > 0 and pago["metodo_pago"] != "Devolución":
                    btn_comprobante = QPushButton("Generar")
                    btn_comprobante.setObjectName("accionSecundaria")
                    btn_comprobante.clicked.connect(
                        lambda _=False, pago_id=pago["id"]: self._generar_comprobante(pago_id)
                    )
                    self.tabla_pagos.setCellWidget(fila, 4, btn_comprobante)
        else:
            self.tabla_pagos.setRowCount(1)
            item = QTableWidgetItem("Todavía no se registró ningún pago.")
            item.setForeground(QColor("#8a97a6"))
            self.tabla_pagos.setItem(0, 0, item)
            self.tabla_pagos.setSpan(0, 0, 1, 5)

        layout.addWidget(self.tabla_pagos)
        return grupo

    def _generar_comprobante(self, pago_id):
        ruta, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar comprobante",
            f"comprobante_pago_{pago_id}.pdf",
            "Documento PDF (*.pdf)",
        )
        if not ruta:
            return
        if not ruta.lower().endswith(".pdf"):
            ruta += ".pdf"
        exito, resultado = self.reserva_service.generar_comprobante_pago(
            self.usuario_actual, pago_id
        )
        if not exito:
            QMessageBox.warning(self, "No se pudo generar", resultado)
            return
        try:
            generar_comprobante_pdf(ruta, resultado)
        except (OSError, ValueError) as err:
            QMessageBox.warning(
                self, "No se pudo guardar", f"No se pudo escribir el archivo PDF: {err}"
            )
            return
        QMessageBox.information(
            self,
            "Comprobante generado",
            f"Se guardó el comprobante {resultado['numero']} en:\n{ruta}",
        )

    def _crear_seccion_cobro(self):
        grupo = QGroupBox("Registrar cobro")
        grupo.setObjectName("seccion")
        form = QFormLayout(grupo)
        form.setContentsMargins(16, 18, 16, 14)
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        self.spn_monto = QDoubleSpinBox()
        self.spn_monto.setDecimals(2)
        self.spn_monto.setPrefix(
            "C$ " if self.reserva_service.obtener_configuracion_hotel()["moneda"] == "NIO" else "$ "
        )
        self.spn_monto.setMinimum(0.01)
        self.spn_monto.setMaximum(float(self.saldo if self.saldo > 0 else Decimal("0.01")))
        self.spn_monto.setValue(float(self.saldo if self.saldo > 0 else Decimal("0.01")))
        self.spn_monto.setFixedHeight(32)
        self.spn_monto.setEnabled(self.saldo > 0)
        self.spn_monto.setToolTip(
            "Importe a abonar. No puede superar el saldo pendiente de la cuenta."
        )
        form.addRow("Monto a cobrar:", self.spn_monto)

        self.cmb_metodo = QComboBox()
        metodos = self.reserva_service.metodos_pago_disponibles()
        self.cmb_metodo.addItems(metodos)
        metodo_actual = self.reserva.get("metodo_pago")
        if metodo_actual in metodos:
            self.cmb_metodo.setCurrentText(metodo_actual)
        self.cmb_metodo.setFixedHeight(32)
        self.cmb_metodo.setEnabled(self.saldo > 0)
        self.cmb_metodo.setToolTip("Forma de pago del cobro que se va a registrar.")
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
        btn_cancelar.setToolTip("Cierra la ventana sin registrar ningún cobro.")
        btn_cancelar.clicked.connect(self.reject)
        layout.addWidget(btn_cancelar)

        self.btn_cobrar = QPushButton("Registrar pago")
        self.btn_cobrar.setObjectName("accionPrimaria")
        self.btn_cobrar.setFixedHeight(38)
        self.btn_cobrar.setMinimumWidth(150)
        self.btn_cobrar.setCursor(Qt.PointingHandCursor)
        self.btn_cobrar.setEnabled(self.saldo > 0)
        self.btn_cobrar.setToolTip(
            "Registra el cobro y abona el importe a la cuenta de la reserva."
        )
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


class DialogoExtenderEstadia(QDialog):
    """Alarga la salida de un huésped que sigue alojado.

    Solo pide la nueva fecha: el servicio recalcula las noches y el total con la
    tarifa de la habitación. Si la extensión choca con otra reserva, muestra el
    motivo y deja corregir la fecha sin cerrar el diálogo.
    """

    guardado = Signal()

    def __init__(self, reserva, usuario_actual, reserva_service, parent=None):
        super().__init__(parent)
        self.reserva = reserva
        self.usuario_actual = usuario_actual or {}
        self.reserva_service = reserva_service

        self.setWindowTitle("Extender estadía")
        self.setMinimumWidth(400)
        self.setStyleSheet(ESTILO_PANEL)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        cabecera = QLabel(
            f"{reserva.get('cliente')} · Habitación {reserva.get('habitacion_numero')}"
        )
        cabecera.setObjectName("panelTitulo")
        cabecera.setWordWrap(True)
        layout.addWidget(cabecera)

        detalle = QLabel(
            f"Entrada: {self.reserva_service.formato_fecha(reserva.get('fecha_entrada'))}\n"
            f"Salida actual: {self.reserva_service.formato_fecha(reserva.get('fecha_salida'))}\n"
            f"Saldo actual: {self.reserva_service.formato_dinero(reserva.get('saldo') or 0)}"
        )
        detalle.setObjectName("panelSubtitulo")
        layout.addWidget(detalle)

        formulario = QFormLayout()
        self.dt_nueva_salida = QDateEdit()
        self.dt_nueva_salida.setCalendarPopup(True)
        self.dt_nueva_salida.setDisplayFormat("dd/MM/yyyy")
        minimo = self._a_date(reserva.get("fecha_salida")).addDays(1)
        manana = QDate.currentDate().addDays(1)
        if minimo < manana:
            minimo = manana
        self.dt_nueva_salida.setMinimumDate(minimo)
        self.dt_nueva_salida.setDate(minimo)
        formulario.addRow("Nueva fecha de salida:", self.dt_nueva_salida)
        layout.addLayout(formulario)

        aviso = QLabel(
            "El total se recalcula con la tarifa de la habitación. No es "
            "necesario tener la cuenta pagada para extender la estadía."
        )
        aviso.setObjectName("panelSubtitulo")
        aviso.setWordWrap(True)
        layout.addWidget(aviso)

        fila = QHBoxLayout()
        fila.addStretch()
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setObjectName("accionSecundaria")
        btn_cancelar.setCursor(Qt.PointingHandCursor)
        btn_cancelar.setFixedHeight(34)
        btn_cancelar.clicked.connect(self.reject)
        fila.addWidget(btn_cancelar)

        btn_guardar = QPushButton("Guardar")
        btn_guardar.setObjectName("accionPrimaria")
        btn_guardar.setCursor(Qt.PointingHandCursor)
        btn_guardar.setFixedHeight(34)
        btn_guardar.clicked.connect(self._guardar)
        fila.addWidget(btn_guardar)
        layout.addLayout(fila)

    def _guardar(self):
        fecha = self.dt_nueva_salida.date().toString("yyyy-MM-dd")
        exito, mensaje = self.reserva_service.extender_estadia(
            self.usuario_actual, self.reserva["id"], fecha
        )
        if not exito:
            QMessageBox.warning(self, "No se pudo extender", mensaje)
            return
        QMessageBox.information(self, "Estadía extendida", mensaje)
        self.guardado.emit()
        self.accept()

    @staticmethod
    def _a_date(valor):
        """Convierte la fecha que llega de la base de datos a un `QDate`."""
        if hasattr(valor, "year"):
            return QDate(valor.year, valor.month, valor.day)
        return QDate.fromString(str(valor), "yyyy-MM-dd")
