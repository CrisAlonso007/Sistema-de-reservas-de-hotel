# ui/detalle_habitacion.py
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
    QLineEdit, QPushButton, QMessageBox, QScrollArea, QDateEdit, QSpinBox, QComboBox
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, QDate
from utils.validaciones import *
from utils.stylesheets import ESTILO_CAMPO_VALIDO, ESTILO_CAMPO_INVALIDO

class DetalleHabitacionWidget(QWidget):
    def __init__(self, al_volver_callback, usuario_actual=None, habitacion_service=None):
        super().__init__()
        self.al_volver_callback = al_volver_callback
        self.usuario_actual = usuario_actual or {}
        self.habitacion_service = habitacion_service
        self.habitacion = {}

        layout_base = QVBoxLayout(self)

        #barra superior 
        barra_menu_container = QWidget()
        layout_menu = QHBoxLayout(barra_menu_container)

        btn_volver = QPushButton("← Volver")
        btn_volver.setFixedWidth(90)
        btn_volver.clicked.connect(self.al_volver_callback)

        lbl_menu = QLabel("Detalles de Habitación")
        lbl_menu.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout_menu.addWidget(btn_volver)
        layout_menu.addWidget(lbl_menu, stretch=1)

        layout_base.addWidget(barra_menu_container)

        # -------------------------------------------------------------
        # ÁREA CON SCROLL
        # -------------------------------------------------------------
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        contenido_widget = QWidget()
        layout_contenido = QVBoxLayout(contenido_widget)
        layout_contenido.setContentsMargins(30, 15, 30, 20)
        layout_contenido.setSpacing(15)

        #titulo 
        self.lbl_titulo = QLabel()
        self.lbl_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_contenido.addWidget(self.lbl_titulo)

        #foto
        self.lbl_foto = QLabel()
        self.lbl_foto.setFixedHeight(220)
        self.lbl_foto.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_contenido.addWidget(self.lbl_foto)

        #info
        self.lbl_info = QLabel()
        self.lbl_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_contenido.addWidget(self.lbl_info)

        #descripcion extendida 
        self.lbl_descripcion = QLabel()
        self.lbl_descripcion.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_contenido.addWidget(self.lbl_descripcion)

        # -------------------------------------------------------------
        # CONFIRMAR RESERVA (Visible solo para clientes)
        # -------------------------------------------------------------
        self.seccion_reserva = QWidget()
        layout_reserva = QVBoxLayout(self.seccion_reserva)
        layout_reserva.setContentsMargins(0, 10, 0, 0)

        lbl_form_titulo = QLabel("<b>Completar Registro de Reserva</b>")
        lbl_form_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_reserva.addWidget(lbl_form_titulo)

        grid_formulario = QGridLayout()
        grid_formulario.setHorizontalSpacing(10)
        grid_formulario.setVerticalSpacing(8)

        self.txt_cliente = QLineEdit()
        self.txt_cliente.setPlaceholderText("Nombre completo")
        self.txt_cliente.setFixedHeight(30)
        self.txt_cliente.setReadOnly(True)
        self.txt_cliente.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.txt_cliente.textChanged.connect(self._validar_cliente)

        self.txt_identificacion = QLineEdit()
        self.txt_identificacion.setPlaceholderText("Numero de identificación")
        self.txt_identificacion.setFixedHeight(30)
        self.txt_identificacion.setReadOnly(True)
        self.txt_identificacion.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.txt_identificacion.textChanged.connect(self._validar_identificacion)

        self.txt_correo = QLineEdit()
        self.txt_correo.setPlaceholderText("Correo electrónico")
        self.txt_correo.setFixedHeight(30)
        self.txt_correo.setReadOnly(True)
        self.txt_correo.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.txt_correo.textChanged.connect(self._validar_correo)

        self.txt_contacto = QLineEdit()
        self.txt_contacto.setPlaceholderText("Número de teléfono")
        self.txt_contacto.setFixedHeight(30)
        self.txt_contacto.setReadOnly(True)
        self.txt_contacto.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.txt_contacto.textChanged.connect(self._validar_telefono)

        self.fecha_entrada = QDateEdit(QDate.currentDate())
        self.fecha_entrada.setCalendarPopup(True)
        self.fecha_entrada.setDisplayFormat("dd/MM/yyyy")
        self.fecha_entrada.setMinimumDate(QDate.currentDate())
        self.fecha_entrada.dateChanged.connect(self._actualizar_estancia)

        self.txt_noches = QSpinBox()
        self.txt_noches.setRange(1, 365)
        self.txt_noches.setValue(1)
        self.txt_noches.valueChanged.connect(self._actualizar_estancia)

        self.lbl_fecha_salida = QLabel()
        self.lbl_total = QLabel()
        self.cmb_metodo_pago = QComboBox()
        self.cmb_metodo_pago.addItems([
            "Tarjeta de Crédito / Débito",
            "Efectivo en Recepción",
            "Transferencia Bancaria",
        ])

        grid_formulario.addWidget(QLabel("Cliente:"), 0, 0)
        grid_formulario.addWidget(self.txt_cliente, 0, 1)

        grid_formulario.addWidget(QLabel("Identificación:"), 1, 0)
        grid_formulario.addWidget(self.txt_identificacion, 1, 1)

        grid_formulario.addWidget(QLabel("Correo electrónico:"), 2, 0)
        grid_formulario.addWidget(self.txt_correo, 2, 1)

        grid_formulario.addWidget(QLabel("Teléfono:"), 3, 0)
        grid_formulario.addWidget(self.txt_contacto, 3, 1)

        grid_formulario.addWidget(QLabel("Fecha de entrada:"), 4, 0)
        grid_formulario.addWidget(self.fecha_entrada, 4, 1)

        grid_formulario.addWidget(QLabel("N° Noches:"), 5, 0)
        grid_formulario.addWidget(self.txt_noches, 5, 1)

        grid_formulario.addWidget(QLabel("Fecha de salida:"), 6, 0)
        grid_formulario.addWidget(self.lbl_fecha_salida, 6, 1)
        grid_formulario.addWidget(QLabel("Método de pago:"), 7, 0)
        grid_formulario.addWidget(self.cmb_metodo_pago, 7, 1)
        grid_formulario.addWidget(QLabel("Total a pagar:"), 8, 0)
        grid_formulario.addWidget(self.lbl_total, 8, 1)

        layout_reserva.addLayout(grid_formulario)

        btn_confirmar = QPushButton("Confirmar y Procesar Reserva")
        btn_confirmar.setFixedHeight(38)
        btn_confirmar.clicked.connect(self._procesar_reserva)
        layout_reserva.addWidget(btn_confirmar)

        layout_contenido.addWidget(self.seccion_reserva)

        scroll_area.setWidget(contenido_widget)
        layout_base.addWidget(scroll_area)

        self._aplicar_estilo_campo(self.txt_cliente, True)
        self._aplicar_estilo_campo(self.txt_identificacion, True)
        self._actualizar_estancia()

    def _aplicar_estilo_campo(self, campo, valido: bool):
        campo.setStyleSheet(ESTILO_CAMPO_VALIDO if valido else ESTILO_CAMPO_INVALIDO)

    def _validar_cliente(self):
        self._aplicar_estilo_campo(self.txt_cliente, es_texto_valido(self.txt_cliente.text(), longitud_minima=2))

    def _validar_identificacion(self):
        self._aplicar_estilo_campo(self.txt_identificacion, es_identificacion_valida(self.txt_identificacion.text()))

    def _validar_telefono(self):
        self._aplicar_estilo_campo(self.txt_contacto, validar_telefono(self.txt_contacto.text()))

    def _validar_correo(self):
        self._aplicar_estilo_campo(self.txt_correo, validar_correo(self.txt_correo.text()))

    def _actualizar_estancia(self):
        salida = self.fecha_entrada.date().addDays(self.txt_noches.value())
        total = float(self.habitacion.get("precio", 0)) * self.txt_noches.value()
        self.lbl_fecha_salida.setText(salida.toString("dd/MM/yyyy"))
        self.lbl_total.setText(f"${total:.2f}")

    def _obtener_dato_usuario(self, *claves, valor_predeterminado=""):
        for clave in claves:
            valor = self.usuario_actual.get(clave)
            if valor is not None and str(valor).strip():
                return str(valor).strip()
        return valor_predeterminado

    def cargar_datos(self, habitacion):
        """Puebla los datos de la habitación seleccionada."""
        self.habitacion = habitacion
        
        self.lbl_titulo.setText(habitacion.get("nombre", "Habitación Sin Nombre"))
        
        self.lbl_info.setText(
            f"<b>Tipo:</b> {habitacion.get('tipo', 'N/A')} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>N°:</b> {habitacion.get('numero', 'N/A')} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Capacidad:</b> {habitacion.get('capacidad', 'N/A')}<br>"
            f"<b>Precio por Noche:</b> ${habitacion.get('precio', 0):.2f}"
        )
        
        desc = habitacion.get("descripcion", "Sin descripción detallada disponible.")
        self.lbl_descripcion.setText(f"<b>Descripción:</b><br>{desc}")

        ruta_img = habitacion.get("imagen", "")
        if ruta_img and os.path.exists(ruta_img):
            pixmap = QPixmap(ruta_img).scaled(
                self.lbl_foto.size(), 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            self.lbl_foto.setPixmap(pixmap)
        else:
            self.lbl_foto.setText("Sin Foto Seleccionada")

        self.txt_cliente.setText(self._obtener_dato_usuario("nombre_completo", "nombre", "cliente"))
        self.txt_identificacion.setText(self._obtener_dato_usuario("identificacion", "cedula", "dni"))
        self.txt_correo.setText(self._obtener_dato_usuario("correo", "email", "correo_electronico", "contacto"))
        self.txt_contacto.setText(self._obtener_dato_usuario("telefono", "contacto", "telefono_contacto"))
        self.fecha_entrada.setDate(QDate.currentDate())
        self.txt_noches.setValue(1)
        self._actualizar_estancia()
        self._validar_cliente()
        self._validar_identificacion()
        self._validar_correo()
        self._validar_telefono()

    def configurar_modo(self, es_cliente: bool):
        """Muestra u oculta la sección de reserva según el rol."""
        self.seccion_reserva.setVisible(es_cliente)

    def _procesar_reserva(self):
        cliente = self.txt_cliente.text().strip()
        cedula = self.txt_identificacion.text().strip()
        correo = self.txt_correo.text().strip()
        contacto = self.txt_contacto.text().strip()
        noches = self.txt_noches.value()

        if not (
            es_texto_valido(cliente, longitud_minima=2)
            and es_identificacion_valida(cedula)
            and validar_correo(correo)
            and validar_telefono(contacto)
            and noches > 0
        ):
            QMessageBox.warning(self, "Datos Incompletos", "Los datos del huésped no son válidos o están incompletos.")
            return

        if not self.habitacion_service:
            QMessageBox.critical(self, "Error", "El servicio de reservas no está disponible.")
            return

        fecha_entrada = self.fecha_entrada.date().toString("yyyy-MM-dd")
        fecha_salida = self.fecha_entrada.date().addDays(noches).toString("yyyy-MM-dd")
        total = float(self.habitacion.get("precio", 0)) * noches
        exito, mensaje = self.habitacion_service.realizar_reserva(
            cliente=cliente,
            identificacion=cedula,
            contacto=contacto,
            noches=noches,
            fecha_entrada=fecha_entrada,
            fecha_salida=fecha_salida,
            metodo_pago=self.cmb_metodo_pago.currentText(),
            total=total,
            usuario_id=self.usuario_actual.get("id"),
            habitacion_id=self.habitacion.get("id"),
        )
        if not exito:
            QMessageBox.warning(self, "Error al reservar", mensaje)
            return

        QMessageBox.information(
            self,
            "Reserva Exitosa",
            f"¡Reserva confirmada para {cliente}!\n\n"
            f"Habitación: {self.habitacion.get('nombre')}\n"
            f"Fechas: {self.fecha_entrada.date().toString('dd/MM/yyyy')} - "
            f"{self.fecha_entrada.date().addDays(noches).toString('dd/MM/yyyy')}\n"
            f"Método de pago: {self.cmb_metodo_pago.currentText()}\n"
            f"Total a pagar ({noches} noches): ${total:.2f}\n\n{mensaje}"
        )
        self.al_volver_callback()