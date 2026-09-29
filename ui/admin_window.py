# ui/admin_window.py
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLineEdit,
    QTextEdit, QPushButton, QMessageBox, QLabel, QFileDialog, QComboBox,
    QDoubleSpinBox, QSpinBox
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, Signal
from utils.stylesheets import (
    ESTILO_CAMPO_INVALIDO,
    ESTILO_CAMPO_VALIDO,
    ESTILO_PANEL,
    ESTILO_PRECIO_INVALIDO,
    ESTILO_PRECIO_VALIDO,
    ESTILO_SELECTOR_IMAGEN,
)
from utils.validaciones import (
    MAX_DESCRIPCION_HABITACION,
    MAX_NOMBRE_HABITACION,
    es_precio_valido,
    es_texto_valido,
)

class SpinBoxNumeroHabitacion(QSpinBox):
    def textFromValue(self, value: int) -> str:
        return f"{value:03d}"

class AdminWindow(QWidget):
    """Alta y edición de habitaciones del catálogo. Solo administradores."""

    guardado = Signal()

    def __init__(self, habitacion_service, usuario_actual: dict = None,
                 habitacion_a_editar: dict = None, parent=None):
        super().__init__(parent)
        self.service = habitacion_service
        self.usuario_actual = usuario_actual or {}
        self.habitacion_a_editar = habitacion_a_editar

        modo_texto = "Editar Habitación" if self.habitacion_a_editar else "Publicar Nueva Habitación"
        self.setWindowTitle(modo_texto)
        self.setWindowFlags(Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(ESTILO_PANEL)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.resize(660, 500)

        self.ruta_imagen = ""

        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(20, 20, 20, 20)
        layout_principal.setSpacing(14)

        layout_grid = QGridLayout()
        layout_grid.setHorizontalSpacing(14)
        layout_grid.setVerticalSpacing(10)

        self._crear_selector_imagen(layout_grid)
        self._crear_campos(layout_grid)

        layout_principal.addLayout(layout_grid)

        self.txt_descripcion = QTextEdit()
        self.txt_descripcion.setPlaceholderText(
            f"Descripción de la habitación, servicios incluidos, etc. (máximo {MAX_DESCRIPCION_HABITACION} caracteres)"
        )
        self.txt_descripcion.setFixedHeight(110)
        self.txt_descripcion.textChanged.connect(self._validar_descripcion)
        layout_principal.addWidget(self.txt_descripcion)

        layout_principal.addLayout(self._crear_botones())

        for campo in (self.txt_nombre, self.txt_numero, self.txt_capacidad, self.txt_descripcion):
            self._aplicar_estilo_campo(campo, True)
        self._aplicar_estilo_precio(True)

        if self.habitacion_a_editar:
            self._cargar_datos_existentes()

    # ------------------------------------------------------------------
    # CONSTRUCCIÓN DE LA INTERFAZ
    # ------------------------------------------------------------------
    def _crear_selector_imagen(self, layout_grid):
        self.lbl_imagen = QLabel("Seleccionar\nimagen")
        self.lbl_imagen.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_imagen.setFixedSize(230, 190)
        self.lbl_imagen.setCursor(Qt.PointingHandCursor)
        self.lbl_imagen.setStyleSheet(ESTILO_SELECTOR_IMAGEN)
        self.lbl_imagen.mousePressEvent = lambda event: self._seleccionar_imagen()
        layout_grid.addWidget(self.lbl_imagen, 0, 0, 5, 1)

    def _crear_campos(self, layout_grid):
        self.txt_nombre = QLineEdit()
        self.txt_nombre.setPlaceholderText(f"Ej. Suite Deluxe (máximo {MAX_NOMBRE_HABITACION} caracteres)")
        self.txt_nombre.setFixedHeight(32)
        self.txt_nombre.textChanged.connect(self._validar_nombre)

        self.txt_numero = SpinBoxNumeroHabitacion()
        self.txt_numero.setRange(1, 999)
        self.txt_numero.setValue(1)
        self.txt_numero.setFixedHeight(32)
        self.txt_numero.setButtonSymbols(QSpinBox.ButtonSymbols.UpDownArrows)

        self.cmb_tipo = QComboBox()
        self.cmb_tipo.addItems(["Simple", "Doble", "Matrimonial", "Suite", "Deluxe", "Presidencial"])
        self.cmb_tipo.setFixedHeight(32)

        self.txt_precio = QDoubleSpinBox()
        self.txt_precio.setRange(0.01, 10000.00)
        self.txt_precio.setDecimals(2)
        self.txt_precio.setSingleStep(5.00)
        self.txt_precio.setPrefix("$ ")
        self.txt_precio.setFixedHeight(32)
        self.txt_precio.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.UpDownArrows)
        self.txt_precio.valueChanged.connect(self._validar_precio)

        self.txt_capacidad = QSpinBox()
        self.txt_capacidad.setRange(1, 20)
        self.txt_capacidad.setValue(2)
        self.txt_capacidad.setSuffix(" huéspedes")
        self.txt_capacidad.setFixedHeight(32)
        self.txt_capacidad.setButtonSymbols(QSpinBox.ButtonSymbols.UpDownArrows)

        campos = [
            ("Nombre:", self.txt_nombre, 0),
            ("N° Habitación:", self.txt_numero, 1),
            ("Tipo:", self.cmb_tipo, 2),
            ("Precio por noche ($):", self.txt_precio, 3),
            ("Capacidad:", self.txt_capacidad, 4),
        ]
        for etiqueta, campo, fila in campos:
            layout_grid.addWidget(QLabel(etiqueta), fila, 1)
            layout_grid.addWidget(campo, fila, 2)

    def _crear_botones(self):
        layout_bot = QHBoxLayout()
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setObjectName("accionSecundaria")
        btn_cancelar.setCursor(Qt.PointingHandCursor)
        btn_cancelar.setFixedHeight(36)
        btn_cancelar.clicked.connect(self.close)

        btn_guardar = QPushButton("Guardar Cambios" if self.habitacion_a_editar else "Publicar Habitación")
        btn_guardar.setObjectName("accionPrimaria")
        btn_guardar.setCursor(Qt.PointingHandCursor)
        btn_guardar.setFixedHeight(36)
        # Sin ancho fijo: 200px recortaba el texto de "Guardar Cambios" y
        # "Publicar Habitación". El ancho lo calcula Qt segun su contenido.
        btn_guardar.setMinimumWidth(0)
        btn_guardar.clicked.connect(self._guardar_habitacion)

        layout_bot.addStretch()
        layout_bot.addWidget(btn_cancelar)
        layout_bot.addWidget(btn_guardar)
        layout_bot.addStretch()
        return layout_bot

    # ------------------------------------------------------------------
    # VALIDACIÓN VISUAL
    # ------------------------------------------------------------------
    def _aplicar_estilo_campo(self, campo, valido: bool):
        campo.setStyleSheet(ESTILO_CAMPO_VALIDO if valido else ESTILO_CAMPO_INVALIDO)

    def _aplicar_estilo_precio(self, valido: bool):
        self.txt_precio.setStyleSheet(ESTILO_PRECIO_VALIDO if valido else ESTILO_PRECIO_INVALIDO)

    def _validar_nombre(self):
        self._aplicar_estilo_campo(
            self.txt_nombre,
            es_texto_valido(self.txt_nombre.text(), longitud_minima=3, longitud_maxima=MAX_NOMBRE_HABITACION),
        )

    def _validar_precio(self):
        self._aplicar_estilo_precio(es_precio_valido(self.txt_precio.value()))

    def _validar_descripcion(self):
        self._aplicar_estilo_campo(
            self.txt_descripcion,
            es_texto_valido(
                self.txt_descripcion.toPlainText(),
                longitud_minima=10,
                longitud_maxima=MAX_DESCRIPCION_HABITACION,
            ),
        )

    # ------------------------------------------------------------------
    # DATOS
    # ------------------------------------------------------------------
    def _cargar_datos_existentes(self):
        hab = self.habitacion_a_editar
        self.txt_nombre.setText(hab.get("nombre", ""))
        self.txt_numero.setValue(int(hab.get("numero", 1)))

        index = self.cmb_tipo.findText(hab.get("tipo", "Simple"))
        if index >= 0:
            self.cmb_tipo.setCurrentIndex(index)

        self.txt_precio.setValue(float(hab.get("precio") or 0))
        self.txt_capacidad.setValue(int(hab.get("capacidad") or 1))
        self.txt_descripcion.setPlainText(hab.get("descripcion", ""))

        self.ruta_imagen = hab.get("imagen", "") or ""
        if self.ruta_imagen and os.path.exists(self.ruta_imagen):
            self.lbl_imagen.setPixmap(self._escalar(self.ruta_imagen))

        self._validar_nombre()
        self._validar_precio()
        self._validar_descripcion()

    def _seleccionar_imagen(self):
        filtros = "Imágenes (*.png *.jpg *.jpeg *.bmp *.gif)"
        archivo, _ = QFileDialog.getOpenFileName(self, "Buscar Imagen", "", filtros)
        if archivo:
            self.ruta_imagen = archivo
            self.lbl_imagen.setPixmap(self._escalar(archivo))

    def _escalar(self, ruta):
        return QPixmap(ruta).scaled(
            self.lbl_imagen.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

    def _guardar_habitacion(self):
        nombre = self.txt_nombre.text().strip()
        numero = self.txt_numero.value()
        tipo = self.cmb_tipo.currentText()
        precio = self.txt_precio.value()
        capacidad = self.txt_capacidad.value()
        descripcion = self.txt_descripcion.toPlainText().strip()

        if not (
            es_texto_valido(nombre, longitud_minima=3, longitud_maxima=MAX_NOMBRE_HABITACION)
            and es_precio_valido(precio)
            and es_texto_valido(descripcion, longitud_minima=10, longitud_maxima=MAX_DESCRIPCION_HABITACION)
        ):
            QMessageBox.warning(
                self,
                "Datos incompletos",
                f"Revise el formulario: el nombre necesita al menos 3 caracteres, "
                f"la descripción entre 10 y {MAX_DESCRIPCION_HABITACION}, y el precio debe ser mayor a cero.",
            )
            return

        if self.habitacion_a_editar:
            exito, mensaje = self.service.editar_habitacion(
                usuario_actual=self.usuario_actual,
                habitacion_id=self.habitacion_a_editar.get("id"),
                nombre=nombre,
                numero=numero,
                tipo=tipo,
                precio=precio,
                capacidad=capacidad,
                descripcion=descripcion,
                imagen=self.ruta_imagen,
            )
        else:
            exito, mensaje = self.service.agregar_habitacion(
                usuario_actual=self.usuario_actual,
                nombre=nombre,
                numero=numero,
                tipo=tipo,
                precio=precio,
                capacidad=capacidad,
                descripcion=descripcion,
                imagen=self.ruta_imagen,
            )

        if not exito:
            QMessageBox.warning(self, "No se pudo guardar", mensaje)
            return

        QMessageBox.information(self, "Éxito", mensaje)
        self.guardado.emit()
        self.close()