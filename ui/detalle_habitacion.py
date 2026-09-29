# ui/detalle_habitacion.py
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, Signal
from utils.stylesheets import COLORES_ESTATUS, ESTILO_PANEL, TARJETAS_ESTILO

class DetalleHabitacionWidget(QWidget):
    """Ficha de una habitación del catálogo.

    La ficha solo muestra los datos: el alta del huésped vive en el formulario
    único `ui/registro_huesped.py`, que la ventana principal abre con esta
    habitación ya seleccionada.
    """

    # Se emite con la habitación de la ficha para que el formulario la preseleccione.
    registro_solicitado = Signal(dict)

    def __init__(self, al_volver_callback, usuario_actual: dict = None, habitacion_service=None, reserva_service=None):
        super().__init__()
        self.al_volver_callback = al_volver_callback
        self.usuario_actual = usuario_actual or {}
        self.habitacion_service = habitacion_service
        self.reserva_service = reserva_service
        self.habitacion = {}

        self.setObjectName("panelRaiz")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(ESTILO_PANEL)

        layout_base = QVBoxLayout(self)
        layout_base.setContentsMargins(0, 0, 0, 0)
        layout_base.setSpacing(0)

        layout_base.addWidget(self._crear_encabezado())

        # -------------------------------------------------------------
        # ÁREA CON SCROLL
        # -------------------------------------------------------------
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)

        contenido_widget = QWidget()
        layout_contenido = QVBoxLayout(contenido_widget)
        layout_contenido.setContentsMargins(30, 20, 30, 20)
        layout_contenido.setSpacing(16)

        self.lbl_titulo = QLabel("Seleccione una habitación del catálogo")
        self.lbl_titulo.setObjectName("panelTitulo")
        self.lbl_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_contenido.addWidget(self.lbl_titulo)

        self.lbl_foto = QLabel()
        self.lbl_foto.setFixedHeight(220)
        self.lbl_foto.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_foto.setStyleSheet(TARJETAS_ESTILO)
        layout_contenido.addWidget(self.lbl_foto)

        self.lbl_info = QLabel("—")
        self.lbl_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_info.setWordWrap(True)
        self.lbl_info.setTextFormat(Qt.TextFormat.RichText)
        layout_contenido.addWidget(self.lbl_info)

        self.lbl_descripcion = QLabel("—")
        self.lbl_descripcion.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_descripcion.setWordWrap(True)
        self.lbl_descripcion.setTextFormat(Qt.TextFormat.RichText)
        layout_contenido.addWidget(self.lbl_descripcion)

        self.btn_registrar_huesped = QPushButton("+  Registrar Huésped")
        self.btn_registrar_huesped.setObjectName("accionPrimaria")
        self.btn_registrar_huesped.setCursor(Qt.PointingHandCursor)
        self.btn_registrar_huesped.setFixedHeight(40)
        self.btn_registrar_huesped.setToolTip(
            "Registra al huésped que se aloja en esta habitación."
        )
        self.btn_registrar_huesped.clicked.connect(self._solicitar_registro)
        self.btn_registrar_huesped.setEnabled(False)
        layout_contenido.addWidget(self.btn_registrar_huesped)

        layout_contenido.addStretch()

        scroll_area.setWidget(contenido_widget)
        layout_base.addWidget(scroll_area, stretch=1)

    def _crear_encabezado(self):
        contenedor = QWidget()
        layout = QHBoxLayout(contenedor)
        layout.setContentsMargins(22, 16, 22, 16)
        layout.setSpacing(12)

        btn_volver = QPushButton("← Volver al catálogo")
        btn_volver.setObjectName("accionSecundaria")
        btn_volver.setCursor(Qt.PointingHandCursor)
        btn_volver.setFixedHeight(36)
        btn_volver.clicked.connect(self.al_volver_callback)
        layout.addWidget(btn_volver)

        lbl_menu = QLabel("Detalle de habitación")
        lbl_menu.setObjectName("panelSubtitulo")
        layout.addWidget(lbl_menu, stretch=1)

        return contenedor

    def _solicitar_registro(self):
        if not self.habitacion:
            return
        self.registro_solicitado.emit(self.habitacion)

    def cargar_datos(self, habitacion: dict):
        """Puebla los datos de la habitación seleccionada."""
        self.habitacion = habitacion or {}

        if not self.habitacion:
            self.lbl_titulo.setText("Seleccione una habitación del catálogo")
            self.btn_registrar_huesped.setEnabled(False)
            return

        self.lbl_titulo.setText(self.habitacion.get("nombre") or "Habitación sin nombre")

        precio = self._precio()
        estatus = self.habitacion.get("estatus", "Disponible")
        color_estatus = COLORES_ESTATUS.get(estatus, "#5d6d7e")
        capacidad = self.habitacion.get("capacidad_texto") or (
            f"{self.habitacion['capacidad']} personas"
            if self.habitacion.get("capacidad") is not None
            else "N/A"
        )

        self.lbl_info.setText(
            f"<b>Tipo:</b> {self.habitacion.get('tipo', 'N/A')}<br>"
            f"<b>Número:</b> {self.habitacion.get('numero', 'N/A')}<br>"
            f"<b>Capacidad:</b> {capacidad}<br>"
            f"<b>Estado:</b> <span style='color:{color_estatus};'>{estatus}</span><br>"
            f"<b>Precio por noche:</b> ${precio:,.2f}"
        )

        descripcion = self.habitacion.get("descripcion") or "Sin descripción detallada."
        self.lbl_descripcion.setText(f"<b>Descripción:</b><br>{descripcion}")

        self._cargar_foto(self.habitacion.get("imagen", ""))
        self.btn_registrar_huesped.setEnabled(True)

    def _cargar_foto(self, ruta_img):
        """Muestra la imagen de la habitación o el aviso cuando no hay archivo."""
        if ruta_img and os.path.exists(ruta_img):
            pixmap = QPixmap(ruta_img).scaled(
                self.lbl_foto.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.lbl_foto.setPixmap(pixmap)
        else:
            self.lbl_foto.clear()
            self.lbl_foto.setText("Sin foto disponible")

    def _precio(self) -> float:
        try:
            return float(self.habitacion.get("precio") or 0)
        except (TypeError, ValueError):
            return 0.0
