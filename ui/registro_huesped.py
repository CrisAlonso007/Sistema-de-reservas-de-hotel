# ui/registro_huesped.py
from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtWidgets import (QApplication, QComboBox, QDateEdit, QDialog, QFormLayout, 
                            QFrame, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, 
                            QScrollArea, QSpinBox, QVBoxLayout, QWidget,
                            )

from services.reserva_service import ReservaService
from utils.stylesheets import (ESTILO_CAMPO_INVALIDO, ESTILO_CAMPO_VALIDO, ESTILO_PANEL,
)
from utils.validaciones import (es_identificacion_valida, es_texto_valido, validar_correo, 
                                validar_nombre_completo, validar_telefono,
                                )


class RegistroHuespedDialog(QDialog):
    """Captura el huésped que llega y abre su reserva."""
    reserva_registrada = Signal(dict, str)
    ANCHO_ETIQUETA = 22
    ANCHO = 540
    ALTO_MAXIMO = 720
    ALTO_MINIMO = 420

    def __init__(self, usuario_actual: dict, habitacion_service, reserva_service, habitacion_preseleccionada: dict = None, parent=None):
        super().__init__(parent)
        self.usuario_actual = usuario_actual or {}
        self.habitacion_service = habitacion_service
        self.reserva_service = reserva_service

        self.setWindowTitle("Registrar Huésped")
        self.setStyleSheet(ESTILO_PANEL)
        self.setObjectName("panelRaiz")
        self._acotar_tamano()

        self._construir_formulario()
        self._conectar_senales()
        self._cambiar_tipo_estancia()
        self._cargar_habitaciones(habitacion_preseleccionada)

    # ------------------------------------------------------------------
    # CONSTRUCCIÓN
    # ------------------------------------------------------------------
    def _acotar_tamano(self):
        """Fija el ancho y limita el alto a lo que cabe en la pantalla."""
        self.setFixedWidth(self.ANCHO)

        alto = self.ALTO_MAXIMO
        pantalla = QApplication.primaryScreen()
        if pantalla is not None:
            alto = min(alto, int(pantalla.availableGeometry().height() * 0.88))

        self.resize(self.ANCHO, max(self.ALTO_MINIMO, alto))

    def _con_fondo_de_panel(self, widget):
        """Repite el fondo del panel en las piezas internas del diálogo.

        Sin esto el área con scroll y la botonera quedarían con el gris por
        defecto de Qt en vez del fondo de la aplicación.
        """
        widget.setObjectName("panelRaiz")
        widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        return widget

    def _construir_formulario(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.area_desplazable = QScrollArea()
        self.area_desplazable.setWidgetResizable(True)
        self.area_desplazable.setFrameShape(QScrollArea.Shape.NoFrame)
        self.area_desplazable.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        contenido = self._con_fondo_de_panel(QWidget())
        layout_contenido = QVBoxLayout(contenido)
        layout_contenido.setContentsMargins(24, 20, 24, 16)
        layout_contenido.setSpacing(12)

        lbl_titulo = QLabel("Registro de huésped")
        lbl_titulo.setObjectName("panelTitulo")
        layout_contenido.addWidget(lbl_titulo)

        lbl_subtitulo = QLabel(
            "Indique si el huésped se aloja ahora o si desea reservar para otra fecha. "
            "El huésped no necesita cuenta ni contraseña."
        )
        lbl_subtitulo.setObjectName("panelSubtitulo")
        # Este rótulo, sin ajuste de línea, era lo que ensanchaba el diálogo
        lbl_subtitulo.setWordWrap(True)
        layout_contenido.addWidget(lbl_subtitulo)

        layout_contenido.addWidget(self._crear_seccion_habitacion())
        layout_contenido.addWidget(self._crear_seccion_huesped())
        layout_contenido.addWidget(self._crear_seccion_estancia())
        layout_contenido.addStretch()

        self.area_desplazable.setWidget(contenido)
        layout.addWidget(self.area_desplazable, stretch=1)

        marco_botones = self._con_fondo_de_panel(QWidget())
        layout_marco = QVBoxLayout(marco_botones)
        layout_marco.setContentsMargins(24, 10, 24, 18)
        layout_marco.addLayout(self._crear_botones())
        layout.addWidget(marco_botones)

    def _crear_seccion_habitacion(self):
        marco = QFrame()
        marco.setObjectName("seccion")
        layout = QFormLayout(marco)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        self.cmb_habitacion = QComboBox()
        self.cmb_habitacion.setFixedHeight(34)
        self.cmb_habitacion.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.cmb_habitacion.setMinimumContentsLength(20)
        layout.addRow(self._etiqueta("Habitación:"), self.cmb_habitacion)

        self.lbl_info_habitacion = QLabel("—")
        self.lbl_info_habitacion.setWordWrap(True)
        self.lbl_info_habitacion.setStyleSheet("font-size: 12px; color: #5d6d7e;")
        layout.addRow("", self.lbl_info_habitacion)

        self.lbl_sin_habitaciones = QLabel("")
        self.lbl_sin_habitaciones.setWordWrap(True)
        self.lbl_sin_habitaciones.setStyleSheet(
            "font-size: 12px; color: #c0392b; font-weight: bold;"
        )
        self.lbl_sin_habitaciones.hide()
        layout.addRow("", self.lbl_sin_habitaciones)

        return marco

    def _crear_seccion_huesped(self):
        marco = QFrame()
        marco.setObjectName("seccion")
        layout = QFormLayout(marco)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        self.txt_cliente = self._crear_campo("Nombre completo del huésped *", 100)
        self.txt_identificacion = self._crear_campo("Documento de identidad *", 30)
        self.txt_contacto = self._crear_campo("Teléfono *", 30)
        self.txt_correo = self._crear_campo("Correo electrónico *", 120)

        layout.addRow(self._etiqueta("Huésped:"), self.txt_cliente)
        layout.addRow(self._etiqueta("Identificación:"), self.txt_identificacion)
        layout.addRow(self._etiqueta("Teléfono:"), self.txt_contacto)
        layout.addRow(self._etiqueta("Correo:"), self.txt_correo)

        nota = QLabel("Los campos con * son obligatorios.")
        nota.setStyleSheet("font-size: 11px; color: #7f8c8d;")
        layout.addRow("", nota)

        return marco

    def _crear_seccion_estancia(self):
        marco = QFrame()
        marco.setObjectName("seccion")
        layout = QFormLayout(marco)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        self.cmb_tipo_estancia = QComboBox()
        self.cmb_tipo_estancia.addItem(
            "Hospedaje inmediato (el huésped se aloja hoy)", "inmediata"
        )
        self.cmb_tipo_estancia.addItem(
            "Reserva para una fecha futura", "reserva"
        )
        self.cmb_tipo_estancia.setFixedHeight(32)
        layout.addRow(self._etiqueta("Tipo de estancia:"), self.cmb_tipo_estancia)

        self.lbl_efecto_tipo = QLabel("")
        self.lbl_efecto_tipo.setWordWrap(True)
        self.lbl_efecto_tipo.setStyleSheet("font-size: 11px; color: #5d6d7e;")
        layout.addRow("", self.lbl_efecto_tipo)

        self.fecha_entrada = QDateEdit(QDate.currentDate())
        self.fecha_entrada.setCalendarPopup(True)
        self.fecha_entrada.setDisplayFormat("dd/MM/yyyy")
        self.fecha_entrada.setMinimumDate(QDate.currentDate())
        self.fecha_entrada.setFixedHeight(32)
        layout.addRow(self._etiqueta("Fecha de entrada:"), self.fecha_entrada)

        self.txt_noches = QSpinBox()
        self.txt_noches.setRange(1, 365)
        self.txt_noches.setValue(1)
        self.txt_noches.setFixedHeight(32)
        layout.addRow(self._etiqueta("Noches:"), self.txt_noches)

        self.lbl_fecha_salida = QLabel("—")
        self.lbl_fecha_salida.setStyleSheet("font-size: 13px; font-weight: bold; color: #1f2d3d;")
        layout.addRow(self._etiqueta("Fecha de salida:"), self.lbl_fecha_salida)

        self.cmb_metodo_pago = QComboBox()
        self.cmb_metodo_pago.addItems(ReservaService.METODOS_PAGO)
        self.cmb_metodo_pago.setFixedHeight(32)
        layout.addRow(self._etiqueta("Método de pago:"), self.cmb_metodo_pago)

        fila_total = QHBoxLayout()
        self.lbl_total = QLabel("$0.00")
        self.lbl_total.setStyleSheet("font-size: 18px; font-weight: bold; color: #2f6fb0;")
        self.lbl_noches = QLabel("")
        self.lbl_noches.setStyleSheet("font-size: 12px; color: #5d6d7e;")
        fila_total.addWidget(self.lbl_total)
        fila_total.addWidget(self.lbl_noches)
        fila_total.addStretch()
        layout.addRow(self._etiqueta("Total a cobrar:"), fila_total)

        return marco

    def _crear_botones(self):
        layout = QHBoxLayout()
        layout.setSpacing(10)

        layout.addStretch()

        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setObjectName("accionSecundaria")
        btn_cancelar.setFixedHeight(40)
        btn_cancelar.setCursor(Qt.PointingHandCursor)
        btn_cancelar.clicked.connect(self.reject)
        layout.addWidget(btn_cancelar)

        self.btn_registrar = QPushButton("Registrar Huésped")
        self.btn_registrar.setObjectName("accionPrimaria")
        self.btn_registrar.setFixedHeight(40)
        self.btn_registrar.setMinimumWidth(190)
        self.btn_registrar.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.btn_registrar)

        return layout

    def _crear_campo(self, placeholder, maxlen):
        campo = QLineEdit()
        campo.setPlaceholderText(placeholder)
        campo.setMaxLength(maxlen)
        campo.setFixedHeight(32)
        return campo

    def _pintar_campos(self, valido: bool):
        """Resalta los campos del huésped para que se vea qué falta."""
        self.txt_cliente.setStyleSheet(ESTILO_CAMPO_VALIDO if valido else ESTILO_CAMPO_INVALIDO)
        self.txt_identificacion.setStyleSheet(ESTILO_CAMPO_VALIDO if valido else ESTILO_CAMPO_INVALIDO)
        self.txt_contacto.setStyleSheet(ESTILO_CAMPO_VALIDO if valido else ESTILO_CAMPO_INVALIDO)
        self.txt_correo.setStyleSheet(ESTILO_CAMPO_VALIDO if valido else ESTILO_CAMPO_INVALIDO)

    def _etiqueta(self, texto):
        etiqueta = QLabel(texto)
        etiqueta.setMinimumWidth(self.ANCHO_ETIQUETA)
        etiqueta.setStyleSheet("font-size: 12px; color: #1f2d3d; font-weight: bold;")
        return etiqueta

    def _conectar_senales(self):
        self.btn_registrar.clicked.connect(self._registrar)
        self.cmb_habitacion.currentIndexChanged.connect(self._actualizar_resumen)
        self.cmb_tipo_estancia.currentIndexChanged.connect(self._cambiar_tipo_estancia)
        self.fecha_entrada.dateChanged.connect(self._cambiar_tramo)
        self.txt_noches.valueChanged.connect(self._cambiar_tramo)

    def _cambiar_tramo(self, *_):
        """Recarga las habitaciones libres conservando la selección actual."""
        self._cargar_habitaciones(self._habitacion_seleccionada())

    def _es_hospedaje_inmediato(self):
        """True si el huésped se aloja ahora; False si es una reserva futura."""
        return self.cmb_tipo_estancia.currentData() == "inmediata"

    def _cambiar_tipo_estancia(self, *_):
        """Ajusta el formulario según se aloje ahora o se reserve a futuro."""
        inmediata = self._es_hospedaje_inmediato()

        if inmediata:
            self.fecha_entrada.blockSignals(True)
            self.fecha_entrada.setDate(QDate.currentDate())
            self.fecha_entrada.blockSignals(False)
            self.lbl_efecto_tipo.setText(
                "La habitación quedará ocupada de inmediato y el huésped aparecerá "
                "en «Huéspedes alojados»."
            )
            self.fecha_entrada.setToolTip(
                "El hospedaje inmediato siempre empieza el día de hoy."
            )
        else:
            self.lbl_efecto_tipo.setText(
                "La habitación quedará reservada para las fechas elegidas, sin "
                "ocuparse todavía."
            )
            self.fecha_entrada.setToolTip("Día en que llegará el huésped.")

        self.fecha_entrada.setEnabled(not inmediata)
        self._cambiar_tramo()

    # ------------------------------------------------------------------
    # DISPONIBILIDAD
    # ------------------------------------------------------------------
    def _tramo_actual(self):
        entrada = self.fecha_entrada.date()
        noches = self.txt_noches.value()
        return entrada, entrada.addDays(noches)

    def _cargar_habitaciones(self, habitacion_preseleccionada=None):
        """Releee las habitaciones libres para el tramo de fechas elegido."""
        entrada, salida = self._tramo_actual()
        self.cmb_habitacion.blockSignals(True)
        self.cmb_habitacion.clear()

        disponibles = self.habitacion_service.obtener_disponibles(
            entrada.toString("yyyy-MM-dd"), salida.toString("yyyy-MM-dd")
        )

        indice_preseleccionado = -1
        for i, hab in enumerate(disponibles):
            self.cmb_habitacion.addItem(
                f"Hab. {hab['numero']:03d} · {hab['tipo']} · "
                f"${hab['precio']:,.2f} / noche · {hab['capacidad_texto']}",
                hab,
            )
            if habitacion_preseleccionada and hab["id"] == habitacion_preseleccionada.get("id"):
                indice_preseleccionado = i

        perdida = (
            habitacion_preseleccionada
            and indice_preseleccionado < 0
            and disponibles
        )

        if indice_preseleccionado >= 0:
            self.cmb_habitacion.setCurrentIndex(indice_preseleccionado)
        self.cmb_habitacion.blockSignals(False)

        if not disponibles:
            self.lbl_sin_habitaciones.setText(
                "No hay habitaciones libres para esas fechas. "
                "Cambie la fecha de entrada o la cantidad de noches."
            )
            self.lbl_sin_habitaciones.show()
        elif perdida:
            self.lbl_sin_habitaciones.setText(
                f"La habitación {habitacion_preseleccionada.get('numero')} no está libre "
                "para el tramo completo. Se ha seleccionado otra habitación disponible."
            )
            self.lbl_sin_habitaciones.show()
        else:
            self.lbl_sin_habitaciones.hide()

        self._actualizar_resumen()

    def _habitacion_seleccionada(self):
        return self.cmb_habitacion.currentData()

    def _actualizar_resumen(self):
        entrada, salida = self._tramo_actual()
        self.lbl_fecha_salida.setText(salida.toString("dd/MM/yyyy"))

        hab = self._habitacion_seleccionada()
        if not hab:
            self.lbl_info_habitacion.setText("—")
            self.lbl_total.setText("$0.00")
            self.lbl_noches.setText("")
            self.btn_registrar.setEnabled(False)
            return

        noches = self.txt_noches.value()
        total = float(hab["precio"]) * noches
        self.lbl_info_habitacion.setText(
            f"{hab['nombre']} · {hab['tipo']} · capacidad {hab['capacidad_texto']}"
        )
        self.lbl_total.setText(f"${total:,.2f}")
        self.lbl_noches.setText(
            f"({noches} noche{'s' if noches != 1 else ''} × ${hab['precio']:,.2f})"
        )
        self.btn_registrar.setEnabled(True)

    # ------------------------------------------------------------------
    # REGISTRO
    # ------------------------------------------------------------------
    def _registrar(self):
        hab = self._habitacion_seleccionada()
        if not hab:
            QMessageBox.warning(
                self, "Sin habitación", "Seleccione una habitación libre para continuar."
            )
            return
        
        cliente = self.txt_cliente.text().strip()
        identificacion = self.txt_identificacion.text().strip()
        contacto = self.txt_contacto.text().strip()
        correo = self.txt_correo.text().strip()

        if not (validar_nombre_completo(cliente)
                and es_identificacion_valida(identificacion)
                and validar_telefono(contacto)
                and validar_correo(correo)):
            self._pintar_campos(False)
            faltantes = []
            if not es_texto_valido(cliente, longitud_minima=2):
                faltantes.append("el nombre completo")
            if not es_identificacion_valida(identificacion):
                faltantes.append("un documento de identidad válido")
            if not validar_telefono(contacto):
                faltantes.append("un teléfono válido")
            if not validar_correo(correo):
                faltantes.append("un correo válido")

            QMessageBox.warning(
                self,
                "Datos incompletos",
                "Revise los datos marcados en rojo. Se necesita:\n\n"
                f"• {', '.join(faltantes)}.",
            )
            if not es_texto_valido(cliente, longitud_minima=2):
                self.txt_cliente.setFocus()
            elif not es_identificacion_valida(identificacion):
                self.txt_identificacion.setFocus()
            elif not validar_telefono(contacto):
                self.txt_contacto.setFocus()
            else:
                self.txt_correo.setFocus()
            return

        self._pintar_campos(True)
        inmediata = self._es_hospedaje_inmediato()
        entrada, salida = self._tramo_actual()
        exito, resultado = self.reserva_service.registrar_estancia(
            usuario_actual=self.usuario_actual,
            cliente=cliente,
            identificacion=identificacion,
            contacto=contacto,
            correo=correo,
            noches=self.txt_noches.value(),
            fecha_entrada=entrada.toString("yyyy-MM-dd"),
            fecha_salida=salida.toString("yyyy-MM-dd"),
            metodo_pago=self.cmb_metodo_pago.currentText(),
            habitacion_id=hab["id"],
            ingreso_inmediato=inmediata,
        )

        if not exito:
            QMessageBox.warning(self, "No se pudo registrar", str(resultado))
            self._cargar_habitaciones()
            return

        reserva = resultado
        if inmediata:
            mensaje = (
                f"Hospedaje registrado para {self.txt_cliente.text().strip()}.\n\n"
                f"Habitación: {hab['numero']:03d}\n"
                f"Estadía: {entrada.toString('dd/MM/yyyy')} - {salida.toString('dd/MM/yyyy')}\n"
                f"Total a cobrar: ${float(reserva['total']):,.2f}\n\n"
                "La habitación figura como ocupada."
            )
        else:
            mensaje = (
                f"Reserva #{reserva['id']} registrada para {self.txt_cliente.text().strip()}.\n\n"
                f"Habitación: {hab['numero']:03d}\n"
                f"Estadía: {entrada.toString('dd/MM/yyyy')} - {salida.toString('dd/MM/yyyy')}\n"
                f"Total a cobrar: ${float(reserva['total']):,.2f}\n\n"
                "La habitación quedó reservada. Registre el ingreso el día de llegada."
            )

        self.reserva_registrada.emit(reserva, mensaje)
        self.accept()
