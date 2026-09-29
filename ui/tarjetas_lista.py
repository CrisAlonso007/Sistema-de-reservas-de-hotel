# ui/tarjetas_lista.py
import os
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, Signal, QEvent
from utils.stylesheets import COLORES_ESTATUS, TARJETAS_ESTILO

class TarjetaHabitacion(QWidget):
    """Tarjeta del catálogo con el estado de ocupación calculado en tiempo real."""

    editar_solicitado = Signal(dict)
    detalles_solicitados = Signal(dict)
    eliminar_solicitado = Signal(dict)
    mantenimiento_solicitado = Signal(dict)

    def __init__(self, habitacion: dict, es_admin: bool = False, parent=None):
        super().__init__(parent)
        self.habitacion = habitacion
        self.es_admin = es_admin

        self.setCursor(Qt.PointingHandCursor)

        layout_tarjeta = QHBoxLayout(self)
        layout_tarjeta.setContentsMargins(12, 12, 12, 12)
        layout_tarjeta.setSpacing(14)

        # --------------------------------------------------
        # FOTO
        # --------------------------------------------------
        self.lbl_foto = QLabel()
        self.lbl_foto.setFixedSize(112, 92)
        self.lbl_foto.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_foto.setStyleSheet(TARJETAS_ESTILO)

        ruta_img = habitacion.get("imagen", "")
        if ruta_img and os.path.exists(ruta_img):
            pixmap = QPixmap(ruta_img).scaled(
                self.lbl_foto.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.lbl_foto.setPixmap(pixmap)
        else:
            self.lbl_foto.setText("Sin Foto")

        # --------------------------------------------------
        # INFORMACIÓN
        # --------------------------------------------------
        layout_info = QVBoxLayout()
        layout_info.setSpacing(4)

        nombre = habitacion.get("nombre", f"Habitación {habitacion.get('numero', '')}")
        precio = float(habitacion.get("precio") or 0)

        fila_titulo = QHBoxLayout()
        fila_titulo.setSpacing(8)

        lbl_nombre = QLabel(f"{nombre}  —  Hab. {habitacion.get('numero', 'N/A')}")
        lbl_nombre.setStyleSheet("font-size: 15px; color: #2c3e50; background: transparent; font-weight: bold;")
        lbl_nombre.setTextFormat(Qt.TextFormat.PlainText)
        fila_titulo.addWidget(lbl_nombre)

        lbl_estatus = QLabel(habitacion.get("estatus", "Disponible"))
        lbl_estatus.setStyleSheet(
            f"background-color: {COLORES_ESTATUS.get(habitacion.get('estatus'), '#5d6d7e')};"
            "color: white; border-radius: 9px; padding: 3px 10px; font-size: 11px; font-weight: bold;"
        )
        fila_titulo.addWidget(lbl_estatus)
        fila_titulo.addStretch()

        lbl_precio = QLabel(f"${precio:,.2f} / noche")
        lbl_precio.setStyleSheet("font-size: 14px; color: #2f6fb0; font-weight: bold; background: transparent;")
        fila_titulo.addWidget(lbl_precio)

        layout_info.addLayout(fila_titulo)

        descripcion = habitacion.get("descripcion", "Sin descripción disponible.")
        lbl_descripcion = QLabel(descripcion)
        lbl_descripcion.setWordWrap(True)
        lbl_descripcion.setStyleSheet("color: #666; font-size: 12px; background: transparent;")
        lbl_descripcion.setTextFormat(Qt.TextFormat.PlainText)
        layout_info.addWidget(lbl_descripcion)

        detalles = (
            f"Tipo: {habitacion.get('tipo', 'N/A')}  ·  "
            f"Capacidad: {habitacion.get('capacidad_texto', 'N/A')}"
        )
        lbl_detalles = QLabel(detalles)
        lbl_detalles.setStyleSheet("color: #8a97a6; font-size: 11px; background: transparent;")
        lbl_detalles.setTextFormat(Qt.TextFormat.PlainText)
        layout_info.addWidget(lbl_detalles)
        layout_info.addStretch()

        # Las etiquetas consumen el clic, así que se reenvía a la tarjeta para
        # que el detalle abra tanto desde el texto como desde el fondo.
        for etiqueta in (self.lbl_foto, lbl_nombre, lbl_estatus, lbl_precio, lbl_descripcion, lbl_detalles):
            etiqueta.installEventFilter(self)

        layout_tarjeta.addWidget(self.lbl_foto)
        layout_tarjeta.addLayout(layout_info, stretch=1)

        # --------------------------------------------------
        # ACCIONES DE ADMINISTRACIÓN
        # --------------------------------------------------
        if self.es_admin:
            self._agregar_boton("Mantenim.", self.mantenimiento_solicitado, "botonTarjeta")
            self._agregar_boton("Editar", self.editar_solicitado, "botonTarjeta")
            self._agregar_boton("Eliminar", self.eliminar_solicitado, "botonTarjetaPeligro")

    def _agregar_boton(self, texto, senal, estilo):
        boton = QPushButton(texto)
        boton.setObjectName(estilo)
        boton.setFixedHeight(30)
        boton.setCursor(Qt.PointingHandCursor)
        boton.clicked.connect(lambda: senal.emit(self.habitacion))
        layout = self.layout()
        layout.addWidget(boton, alignment=Qt.AlignmentFlag.AlignVCenter)
        return boton

    def mousePressEvent(self, event):
        """Abre el detalle de la habitación con un clic en el cuerpo de la tarjeta."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.detalles_solicitados.emit(self.habitacion)
        super().mousePressEvent(event)

    def eventFilter(self, watched, event):
        """Reenvía el clic de las etiquetas a la tarjeta sin consumirlo."""
        if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            self.detalles_solicitados.emit(self.habitacion)
        return super().eventFilter(watched, event)
