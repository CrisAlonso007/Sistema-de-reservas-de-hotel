# ui/admin_window.py
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLineEdit, 
    QTextEdit, QPushButton, QMessageBox, QLabel, QFileDialog, QComboBox, QDoubleSpinBox
)
from PySide6.QtGui import QPixmap, QRegularExpressionValidator
from PySide6.QtCore import Qt, QRegularExpression
from utils.validaciones import es_texto_valido, es_precio_valido, es_numero_habitacion_valido, es_capacidad_valida
from utils.stylesheets import (
    ESTILO_SELECTOR_IMAGEN,
    ESTILO_CAMPO_VALIDO,
    ESTILO_CAMPO_INVALIDO,
    ESTILO_PRECIO_VALIDO,
    ESTILO_PRECIO_INVALIDO,
)

class AdminWindow(QWidget):
    def __init__(self, habitacion_service, al_actualizar_callback=None, habitacion_a_editar: dict = None):
        super().__init__()
        self.service = habitacion_service
        self.al_actualizar_callback = al_actualizar_callback
        self.habitacion_a_editar = habitacion_a_editar
        
        modo_texto = "Editar Habitación" if self.habitacion_a_editar else "Publicar Nueva Habitación"
        self.setWindowTitle(f"{modo_texto}")
        self.resize(650, 480)

        self.ruta_imagen = ""

        layout_principal = QVBoxLayout(self)
        layout_principal.setSpacing(15)

        layout_grid = QGridLayout()
        layout_grid.setHorizontalSpacing(15)
        layout_grid.setVerticalSpacing(10)

        #Selector de Imagen
        self.lbl_imagen = QLabel("seleccionar\nimagen")
        self.lbl_imagen.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_imagen.setFixedSize(220, 180)
        self.lbl_imagen.setCursor(Qt.PointingHandCursor)
        self.lbl_imagen.setStyleSheet(ESTILO_SELECTOR_IMAGEN)
        self.lbl_imagen.mousePressEvent = lambda event: self._seleccionar_imagen()
        
        layout_grid.addWidget(self.lbl_imagen, 0, 0, 5, 1)

        #Campos de Entrada
        self.txt_nombre = QLineEdit()
        self.txt_nombre.setPlaceholderText("Nombre de la habitación")
        self.txt_nombre.textChanged.connect(self._validar_nombre)

        self.txt_numero = QLineEdit()
        self.txt_numero.setPlaceholderText("Ej: 101, 202, 303...")
        self.txt_numero.setValidator(QRegularExpressionValidator(QRegularExpression(r"\d{0,6}")))
        self.txt_numero.textChanged.connect(self._validar_numero)

        #Combobox para Tipo de Habitación
        self.cmb_tipo = QComboBox()
        self.cmb_tipo.addItems(["Simple", "Doble", "Matrimonial", "Suite", "Deluxe", "Presidencial"])

        #Spinbox para Precio 
        self.txt_precio = QDoubleSpinBox()
        self.txt_precio.setRange(0.00, 10000.00)
        self.txt_precio.setDecimals(2)
        self.txt_precio.setSingleStep(5.00)
        self.txt_precio.setPrefix("$ ")
        self.txt_precio.setFixedHeight(30)
        self.txt_precio.valueChanged.connect(self._validar_precio)

        self.txt_capacidad = QLineEdit()
        self.txt_capacidad.setPlaceholderText("Ej: 1 Persona, 2 Personas...")
        self.txt_capacidad.setValidator(QRegularExpressionValidator(QRegularExpression(r"[0-9A-Za-zÁÉÍÓÚáéíóúÑñ\s]{0,30}")))
        self.txt_capacidad.textChanged.connect(self._validar_capacidad)

        layout_grid.addWidget(QLabel("Nombre:"), 0, 1)
        layout_grid.addWidget(self.txt_nombre, 0, 2)

        layout_grid.addWidget(QLabel("N° Habitación:"), 1, 1)
        layout_grid.addWidget(self.txt_numero, 1, 2)

        layout_grid.addWidget(QLabel("Tipo:"), 2, 1)
        layout_grid.addWidget(self.cmb_tipo, 2, 2)

        layout_grid.addWidget(QLabel("Precio ($):"), 3, 1)
        layout_grid.addWidget(self.txt_precio, 3, 2)

        layout_grid.addWidget(QLabel("Capacidad:"), 4, 1)
        layout_grid.addWidget(self.txt_capacidad, 4, 2)

        layout_principal.addLayout(layout_grid)

        self.txt_descripcion = QTextEdit()
        self.txt_descripcion.setPlaceholderText("Descripción de la habitación, servicios incluidos, etc...")
        self.txt_descripcion.setFixedHeight(110)
        self.txt_descripcion.textChanged.connect(self._validar_descripcion)
        layout_principal.addWidget(self.txt_descripcion)

        layout_bot = QHBoxLayout()
        btn_texto = "Guardar Cambios" if self.habitacion_a_editar else "Publicar Habitación"
        btn_guardar = QPushButton(btn_texto)
        btn_guardar.setFixedWidth(180)
        btn_guardar.setFixedHeight(35)
        btn_guardar.clicked.connect(self._guardar_habitacion)

        layout_bot.addStretch()
        layout_bot.addWidget(btn_guardar)
        layout_bot.addStretch()

        layout_principal.addLayout(layout_bot)

        self._aplicar_estilo_campo(self.txt_nombre, True)
        self._aplicar_estilo_campo(self.txt_numero, True)
        self._aplicar_estilo_campo(self.txt_capacidad, True)
        self._aplicar_estilo_campo(self.txt_descripcion, True)
        self._aplicar_estilo_precio(True)

        if self.habitacion_a_editar:
            self._cargar_datos_existentes()

    def _aplicar_estilo_campo(self, campo, valido: bool):
        if hasattr(campo, "setStyleSheet"):
            campo.setStyleSheet(ESTILO_CAMPO_VALIDO if valido else ESTILO_CAMPO_INVALIDO)

    def _aplicar_estilo_precio(self, valido: bool):
        self.txt_precio.setStyleSheet(ESTILO_PRECIO_VALIDO if valido else ESTILO_PRECIO_INVALIDO)

    def _validar_nombre(self):
        self._aplicar_estilo_campo(self.txt_nombre, es_texto_valido(self.txt_nombre.text().strip(), longitud_minima=2))

    def _validar_numero(self):
        self._aplicar_estilo_campo(self.txt_numero, es_numero_habitacion_valido(self.txt_numero.text()))

    def _validar_precio(self):
        self._aplicar_estilo_precio(es_precio_valido(self.txt_precio.value()))

    def _validar_capacidad(self):
        self._aplicar_estilo_campo(self.txt_capacidad, es_capacidad_valida(self.txt_capacidad.text()))

    def _validar_descripcion(self):
        self._aplicar_estilo_campo(self.txt_descripcion, es_texto_valido(self.txt_descripcion.toPlainText(), longitud_minima=10))

    def _cargar_datos_existentes(self):
        hab = self.habitacion_a_editar
        self.txt_nombre.setText(hab.get("nombre", ""))
        self.txt_numero.setText(str(hab.get("numero", "")))
        
        # Seleccionar valor en el ComboBox
        tipo_hab = hab.get("tipo", "Simple")
        index = self.cmb_tipo.findText(tipo_hab)
        if index >= 0:
            self.cmb_tipo.setCurrentIndex(index)

        try:
            precio_float = float(hab.get("precio", 0.0))
            self.txt_precio.setValue(precio_float)
        except (ValueError, TypeError):
            self.txt_precio.setValue(0.0)

        self.txt_capacidad.setText(str(hab.get("capacidad", "")))
        self.txt_descripcion.setPlainText(hab.get("descripcion", ""))
        self._validar_nombre()
        self._validar_numero()
        self._validar_precio()
        self._validar_capacidad()
        self._validar_descripcion()

        #Carga la imagen si existe 
        ruta = hab.get("imagen", "")
        if ruta and os.path.exists(ruta):
            self.ruta_imagen = ruta
            pixmap = QPixmap(ruta).scaled(
                self.lbl_imagen.size(), 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            self.lbl_imagen.setPixmap(pixmap)

    def _seleccionar_imagen(self):
        filtros = "Imágenes (*.png *.jpg *.jpeg *.bmp *.gif)"
        archivo, _ = QFileDialog.getOpenFileName(self, "Buscar Imagen", "", filtros)
        
        if archivo:
            self.ruta_imagen = archivo
            pixmap = QPixmap(archivo)
            pixmap_escalado = pixmap.scaled(
                self.lbl_imagen.size(), 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            self.lbl_imagen.setPixmap(pixmap_escalado)

    def _guardar_habitacion(self):
        nombre = self.txt_nombre.text().strip()
        num = self.txt_numero.text().strip()
        tipo = self.cmb_tipo.currentText()
        precio_val = self.txt_precio.value()
        capacidad = self.txt_capacidad.text().strip()
        descripcion = self.txt_descripcion.toPlainText().strip()

        if not (
            es_texto_valido(nombre, longitud_minima=2)
            and es_numero_habitacion_valido(num)
            and es_precio_valido(precio_val)
            and es_capacidad_valida(capacidad)
            and es_texto_valido(descripcion, longitud_minima=10)
        ):
            QMessageBox.warning(
                self,
                "Error",
                "Completa los campos obligatorios: nombre, número, capacidad, descripción y un precio válido."
            )
            return

        if self.habitacion_a_editar:
            self.habitacion_a_editar.update({
                "nombre": nombre,
                "numero": num,
                "tipo": tipo,
                "precio": precio_val,
                "capacidad": capacidad,
                "descripcion": descripcion,
                "imagen": self.ruta_imagen
            })
            QMessageBox.information(self, "Éxito", "Habitación actualizada correctamente.")
        else:
            self.service.agregar_habitacion(
                nombre=nombre,
                numero=num,
                tipo=tipo,
                precio=precio_val,
                capacidad=capacidad,
                descripcion=descripcion,
                imagen=self.ruta_imagen
            )
            QMessageBox.information(self, "Éxito", "Habitación publicada correctamente.")

        if self.al_actualizar_callback:
            self.al_actualizar_callback()

        self.close()