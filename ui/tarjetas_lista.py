# ui/tarjetas_lista.py
import os
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, Signal
from utils.stylesheets import TARJETAS_ESTILO

class TarjetaHabitacion(QWidget):
    editar_solicitado = Signal(dict)
    detalles_solicitados = Signal(dict)
    eliminar_solicitado = Signal(dict)

    def __init__(self, habitacion: dict, es_admin: bool = False):
        super().__init__()
        self.habitacion = habitacion
        self.es_admin = es_admin

        self.setCursor(Qt.PointingHandCursor)
        
        layout_tarjeta = QHBoxLayout(self)
        layout_tarjeta.setContentsMargins(10, 10, 10, 10)
        layout_tarjeta.setSpacing(15)

        # Foto
        self.lbl_foto = QLabel()
        self.lbl_foto.setFixedSize(110, 90)
        self.lbl_foto.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_foto.setStyleSheet(TARJETAS_ESTILO)

        ruta_img = habitacion.get("imagen", "")
        if ruta_img and os.path.exists(ruta_img):
            pixmap = QPixmap(ruta_img).scaled(
                self.lbl_foto.size(), 
                Qt.AspectRatioMode.KeepAspectRatioByExpanding, 
                Qt.TransformationMode.SmoothTransformation
            )
            self.lbl_foto.setPixmap(pixmap)
        else:
            self.lbl_foto.setText("Sin Foto")

        # Información
        layout_info = QVBoxLayout()
        layout_info.setSpacing(5)

        nombre_texto = habitacion.get("nombre", f"Habitación {habitacion.get('numero', '')}")
        lbl_nombre = QLabel(f"<b>{nombre_texto}</b> — ${habitacion.get('precio', 0):.2f}/noche")
        lbl_nombre.setStyleSheet("font-size: 15px; color: #2c3e50;")

        desc_texto = habitacion.get("descripcion", f"Tipo: {habitacion.get('tipo', 'N/A')} | Capacidad: {habitacion.get('capacidad', 'N/A')}")
        lbl_descripcion = QLabel(desc_texto)
        lbl_descripcion.setWordWrap(True)
        lbl_descripcion.setStyleSheet("color: #666; font-size: 12px;")

        layout_info.addWidget(lbl_nombre)
        layout_info.addWidget(lbl_descripcion)
        layout_info.addStretch()

        layout_tarjeta.addWidget(self.lbl_foto)
        layout_tarjeta.addLayout(layout_info)

        if self.es_admin:
            self.btn_editar = QPushButton("Editar")
            self.btn_editar.setFixedWidth(80)
            self.btn_editar.setCursor(Qt.ArrowCursor) 
            self.btn_editar.clicked.connect(lambda: self.editar_solicitado.emit(self.habitacion))
            layout_tarjeta.addWidget(self.btn_editar, alignment=Qt.AlignmentFlag.AlignVCenter)

            self.btn_eliminar = QPushButton("Eliminar")
            self.btn_eliminar.setFixedWidth(70)
            self.btn_eliminar.clicked.connect(lambda: self.eliminar_solicitado.emit(self.habitacion))

            layout_tarjeta.addWidget(self.btn_eliminar, alignment=Qt.AlignmentFlag.AlignVCenter)

    def mousePressEvent(self, event):
        """Detecta el clic en cualquier parte del widget de la tarjeta."""
        if event.button() == Qt.LeftButton:

            self.detalles_solicitados.emit(self.habitacion)
        super().mousePressEvent(event)