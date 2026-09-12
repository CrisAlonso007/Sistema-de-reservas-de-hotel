# ui/detalle_habitacion.py
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
    QLineEdit, QPushButton, QMessageBox, QScrollArea
)
<<<<<<< HEAD
from PySide6.QtGui import QPixmap, QIntValidator
from PySide6.QtCore import Qt
from utils.validaciones import es_texto_valido, es_identificacion_valida, es_noches_valida
from utils.stylesheets import ESTILO_CAMPO_VALIDO, ESTILO_CAMPO_INVALIDO
=======
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt
from utils.validaciones import es_texto_valido
>>>>>>> 4f407e8c6312a48d30092630981c73c4460f90fa

class DetalleHabitacionWidget(QWidget):
    def __init__(self, al_volver_callback):
        super().__init__()
        self.al_volver_callback = al_volver_callback
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
        self.txt_cliente.textChanged.connect(self._validar_cliente)
        self.txt_cliente.setFixedHeight(30)  

        self.txt_identificacion = QLineEdit()
        self.txt_identificacion.setPlaceholderText("N° Cédula o Pasaporte")
        self.txt_identificacion.setFixedHeight(30)
        self.txt_identificacion.textChanged.connect(self._validar_identificacion)

        self.txt_noches = QLineEdit()
        self.txt_noches.setPlaceholderText("Cantidad de noches")
        self.txt_noches.setFixedHeight(30)
        self.txt_noches.setValidator(QIntValidator(1, 365))
        self.txt_noches.textChanged.connect(self._validar_noches)

        grid_formulario.addWidget(QLabel("Cliente:"), 0, 0)
        grid_formulario.addWidget(self.txt_cliente, 0, 1)

        grid_formulario.addWidget(QLabel("Identificación:"), 1, 0)
        grid_formulario.addWidget(self.txt_identificacion, 1, 1)

        grid_formulario.addWidget(QLabel("N° Noches:"), 2, 0)
        grid_formulario.addWidget(self.txt_noches, 2, 1)

        layout_reserva.addLayout(grid_formulario)

        btn_confirmar = QPushButton("Confirmar Reserva")
        btn_confirmar.setFixedHeight(38)
        btn_confirmar.clicked.connect(self._procesar_reserva)
        layout_reserva.addWidget(btn_confirmar)

        layout_contenido.addWidget(self.seccion_reserva)

        scroll_area.setWidget(contenido_widget)
        layout_base.addWidget(scroll_area)

        self._aplicar_estilo_campo(self.txt_cliente, True)
        self._aplicar_estilo_campo(self.txt_identificacion, True)
        self._aplicar_estilo_campo(self.txt_noches, True)

    def _aplicar_estilo_campo(self, campo, valido: bool):
        campo.setStyleSheet(ESTILO_CAMPO_VALIDO if valido else ESTILO_CAMPO_INVALIDO)

    def _validar_cliente(self):
        self._aplicar_estilo_campo(self.txt_cliente, es_texto_valido(self.txt_cliente.text(), longitud_minima=2))

    def _validar_identificacion(self):
        self._aplicar_estilo_campo(self.txt_identificacion, es_identificacion_valida(self.txt_identificacion.text()))

    def _validar_noches(self):
        self._aplicar_estilo_campo(self.txt_noches, es_noches_valida(self.txt_noches.text()))

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

        # Limpiar campos de texto
        self.txt_cliente.clear()
        self.txt_identificacion.clear()
        self.txt_noches.clear()
        self._validar_cliente()
        self._validar_identificacion()
        self._validar_noches()

    def configurar_modo(self, es_cliente: bool):
        """Muestra u oculta la sección de reserva según el rol."""
        self.seccion_reserva.setVisible(es_cliente)

    def _procesar_reserva(self):
        cliente = self.txt_cliente.text().strip()
        cedula = self.txt_identificacion.text().strip()
        noches = self.txt_noches.text().strip()

        if not (
            es_texto_valido(cliente, longitud_minima=2)
            and es_identificacion_valida(cedula)
            and es_noches_valida(noches)
        ):
            cliente = self.txt_cliente.text()
            cedula = self.txt_identificacion.text()
            noches = self.txt_noches.text()

        if not (es_texto_valido(cliente) and es_texto_valido(cedula) and noches.isdigit() and int(noches) > 0):
            QMessageBox.warning(self, "Datos Incompletos", "Por favor ingresa un nombre, cédula y número de noches válido.")
            return

        total = float(self.habitacion.get("precio", 0)) * int(noches)
        QMessageBox.information(
            self,
            "Reserva Exitosa",
            self, 
            "Reserva Exitosa", 
            f"¡Reserva confirmada para {cliente}!\n\n"
            f"Habitación: {self.habitacion.get('nombre')}\n"
            f"Total a pagar ({noches} noches): ${total:.2f}"
        )
        self.al_volver_callback()