import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QFrame, QSizePolicy,
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, Signal
from utils.stylesheets import COLORES_ESTATUS, ESTILO_PANEL


class DetalleHabitacionWidget(QWidget):
    """Ficha de una habitación del catálogo.

    La ficha solo muestra los datos: el alta del huésped vive en el formulario
    único `ui/registro_huesped.py`, que la ventana principal abre con esta
    habitación ya seleccionada.
    """

    registro_solicitado = Signal(dict)

    def __init__(
        self,
        al_volver_callback,
        usuario_actual: dict = None,
        habitacion_service=None,
        reserva_service=None,
    ):
        super().__init__()
        self.al_volver_callback = al_volver_callback
        self.usuario_actual = usuario_actual or {}
        self.habitacion_service = habitacion_service
        self.reserva_service = reserva_service
        self.habitacion = {}
        self._foto_original = QPixmap()

        self.setObjectName("panelRaiz")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(ESTILO_PANEL)
        self.setStyleSheet(self.styleSheet() + """
            QFrame#detalleFoto, QFrame#detalleFicha, QFrame#detalleDescripcion {
                background-color: #ffffff;
                border: 1px solid #dfe4ea;
                border-radius: 12px;
            }
            QLabel#detalleNumero {
                color: #2f6fb0;
                font-size: 12px;
                font-weight: bold;
            }
            QLabel#detalleNombre {
                color: #1f2d3d;
                font-size: 21px;
                font-weight: bold;
            }
            QLabel#detalleEtiqueta {
                color: #7b8998;
                font-size: 11px;
            }
            QLabel#detalleValor {
                color: #26384a;
                font-size: 13px;
                font-weight: bold;
            }
            QLabel#detallePrecio {
                color: #2f6fb0;
                font-size: 25px;
                font-weight: bold;
            }
            QLabel#detalleDescripcion {
                color: #526273;
                font-size: 13px;
            }
        """)

        layout_base = QVBoxLayout(self)
        layout_base.setContentsMargins(0, 0, 0, 0)
        layout_base.setSpacing(0)
        layout_base.addWidget(self._crear_encabezado())

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        contenido = QWidget()
        contenido.setObjectName("panelRaiz")
        layout_contenido = QVBoxLayout(contenido)
        layout_contenido.setContentsMargins(30, 20, 30, 24)
        layout_contenido.setSpacing(18)
        layout_contenido.addLayout(self._crear_seccion_principal())
        layout_contenido.addWidget(self._crear_seccion_descripcion())
        layout_contenido.addStretch()

        scroll_area.setWidget(contenido)
        layout_base.addWidget(scroll_area, stretch=1)

    def _crear_encabezado(self):
        contenedor = QWidget()
        layout = QHBoxLayout(contenedor)
        layout.setContentsMargins(22, 16, 22, 14)
        layout.setSpacing(14)

        btn_volver = QPushButton("←  Volver al catálogo")
        btn_volver.setObjectName("accionSecundaria")
        btn_volver.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_volver.setFixedHeight(36)
        btn_volver.clicked.connect(self.al_volver_callback)
        layout.addWidget(btn_volver)

        textos = QVBoxLayout()
        textos.setSpacing(2)
        lbl_titulo = QLabel("Detalle de habitación")
        lbl_titulo.setObjectName("panelTitulo")
        lbl_subtitulo = QLabel("Información y disponibilidad de la habitación")
        lbl_subtitulo.setObjectName("panelSubtitulo")
        textos.addWidget(lbl_titulo)
        textos.addWidget(lbl_subtitulo)
        layout.addLayout(textos)
        layout.addStretch()
        return contenedor

    def _crear_seccion_principal(self):
        layout = QHBoxLayout()
        layout.setSpacing(18)

        marco_foto = QFrame()
        marco_foto.setObjectName("detalleFoto")
        marco_foto.setMinimumHeight(340)
        foto_layout = QVBoxLayout(marco_foto)
        foto_layout.setContentsMargins(8, 8, 8, 8)

        self.lbl_foto = QLabel("Seleccione una habitación del catálogo")
        self.lbl_foto.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_foto.setMinimumSize(300, 300)
        self.lbl_foto.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.lbl_foto.setStyleSheet(
            "background-color: #f4f6f8; color: #7b8998; "
            "border-radius: 8px; font-size: 13px;"
        )
        foto_layout.addWidget(self.lbl_foto)
        layout.addWidget(marco_foto, stretch=3)

        ficha = QFrame()
        ficha.setObjectName("detalleFicha")
        ficha.setMinimumWidth(280)
        ficha_layout = QVBoxLayout(ficha)
        ficha_layout.setContentsMargins(22, 20, 22, 20)
        ficha_layout.setSpacing(12)

        self.lbl_numero = QLabel("HABITACIÓN")
        self.lbl_numero.setObjectName("detalleNumero")
        ficha_layout.addWidget(self.lbl_numero)

        self.lbl_titulo = QLabel("Seleccione una habitación del catálogo")
        self.lbl_titulo.setObjectName("detalleNombre")
        self.lbl_titulo.setWordWrap(True)
        ficha_layout.addWidget(self.lbl_titulo)

        self.lbl_estado = QLabel("Estado no disponible")
        self.lbl_estado.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_estado.setFixedHeight(28)
        self.lbl_estado.setMaximumWidth(170)
        ficha_layout.addWidget(self.lbl_estado, alignment=Qt.AlignmentFlag.AlignLeft)

        separador = QFrame()
        separador.setFrameShape(QFrame.Shape.HLine)
        separador.setStyleSheet("color: #e8edf2;")
        ficha_layout.addWidget(separador)

        self.lbl_tipo = self._crear_dato(ficha_layout, "Tipo", "—")
        self.lbl_capacidad = self._crear_dato(ficha_layout, "Capacidad", "—")

        ficha_layout.addStretch()

        lbl_precio_titulo = QLabel("PRECIO POR NOCHE")
        lbl_precio_titulo.setObjectName("detalleEtiqueta")
        ficha_layout.addWidget(lbl_precio_titulo)
        self.lbl_precio = QLabel(self.reserva_service.formato_dinero(0))
        self.lbl_precio.setObjectName("detallePrecio")
        ficha_layout.addWidget(self.lbl_precio)

        self.btn_registrar_huesped = QPushButton("+  Registrar huésped")
        self.btn_registrar_huesped.setObjectName("accionPrimaria")
        self.btn_registrar_huesped.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_registrar_huesped.setFixedHeight(44)
        self.btn_registrar_huesped.setToolTip(
            "Registra al huésped que se aloja en esta habitación."
        )
        self.btn_registrar_huesped.clicked.connect(self._solicitar_registro)
        self.btn_registrar_huesped.setEnabled(False)
        ficha_layout.addWidget(self.btn_registrar_huesped)

        layout.addWidget(ficha, stretch=2)
        return layout

    @staticmethod
    def _crear_dato(layout_padre, etiqueta, valor):
        contenedor = QWidget()
        layout = QVBoxLayout(contenedor)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        lbl_etiqueta = QLabel(etiqueta)
        lbl_etiqueta.setObjectName("detalleEtiqueta")
        lbl_valor = QLabel(valor)
        lbl_valor.setObjectName("detalleValor")
        layout.addWidget(lbl_etiqueta)
        layout.addWidget(lbl_valor)
        layout_padre.addWidget(contenedor)
        return lbl_valor

    def _crear_seccion_descripcion(self):
        marco = QFrame()
        marco.setObjectName("detalleDescripcion")
        layout = QVBoxLayout(marco)
        layout.setContentsMargins(20, 16, 20, 18)
        layout.setSpacing(7)

        titulo = QLabel("Acerca de esta habitación")
        titulo.setObjectName("panelTitulo")
        titulo.setStyleSheet("font-size: 15px;")
        layout.addWidget(titulo)

        self.lbl_descripcion = QLabel("La descripción aparecerá aquí.")
        self.lbl_descripcion.setObjectName("detalleDescripcion")
        self.lbl_descripcion.setWordWrap(True)
        layout.addWidget(self.lbl_descripcion)
        return marco

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._ajustar_foto()

    def _solicitar_registro(self):
        if self.habitacion:
            self.registro_solicitado.emit(self.habitacion)

    def cargar_datos(self, habitacion: dict):
        """Puebla los datos de la habitación seleccionada."""
        self.habitacion = habitacion or {}

        if not self.habitacion:
            self.lbl_titulo.setText("Seleccione una habitación del catálogo")
            self.lbl_numero.setText("HABITACIÓN")
            self.lbl_estado.setText("Estado no disponible")
            self.lbl_precio.setText(self.reserva_service.formato_dinero(0))
            self.lbl_tipo.setText("—")
            self.lbl_capacidad.setText("—")
            self.lbl_descripcion.setText("La descripción aparecerá aquí.")
            self._cargar_foto("")
            self.btn_registrar_huesped.setEnabled(False)
            return

        numero = self.habitacion.get("numero", "N/A")
        estado = self.habitacion.get("estatus", "Disponible")
        capacidad = self.habitacion.get("capacidad_texto") or (
            f"{self.habitacion['capacidad']} personas"
            if self.habitacion.get("capacidad") is not None
            else "N/A"
        )

        self.lbl_numero.setText(f"HABITACIÓN {numero}")
        self.lbl_titulo.setText(
            self.habitacion.get("nombre") or "Habitación sin nombre"
        )
        self.lbl_tipo.setText(self.habitacion.get("tipo", "N/A"))
        self.lbl_capacidad.setText(capacidad)
        self.lbl_precio.setText(self.reserva_service.formato_dinero(self._precio()))

        color = COLORES_ESTATUS.get(estado, "#5d6d7e")
        fondo_estado = {
            "Disponible": "#eaf6ee",
            "Ocupado": "#fbefee",
            "Reservado": "#fbf5e8",
            "Mantenimiento": "#eef1f4",
        }.get(estado, "#eef1f4")
        self.lbl_estado.setText(estado)
        self.lbl_estado.setStyleSheet(
            f"background-color: {fondo_estado}; color: {color}; "
            "border-radius: 14px; padding: 4px 12px; font-size: 12px; "
            "font-weight: bold;"
        )

        descripcion = self.habitacion.get("descripcion") or (
            "Sin descripción detallada."
        )
        self.lbl_descripcion.setText(descripcion)
        self._cargar_foto(self.habitacion.get("imagen", ""))
        self.btn_registrar_huesped.setEnabled(True)

    def _cargar_foto(self, ruta_img):
        """Carga la imagen seleccionada y conserva su proporción al redimensionar."""
        self._foto_original = (
            QPixmap(ruta_img) if ruta_img and os.path.exists(ruta_img) else QPixmap()
        )
        self._ajustar_foto()

    def _ajustar_foto(self):
        if not hasattr(self, "lbl_foto"):
            return
        if self._foto_original.isNull():
            self.lbl_foto.setPixmap(QPixmap())
            self.lbl_foto.setText(
                "Sin foto disponible" if self.habitacion else
                "Seleccione una habitación del catálogo"
            )
            return

        tamano = self.lbl_foto.size()
        if tamano.width() <= 0 or tamano.height() <= 0:
            return
        pixmap = self._foto_original.scaled(
            tamano,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.lbl_foto.setText("")
        self.lbl_foto.setPixmap(pixmap)

    def _precio(self) -> float:
        try:
            return float(self.habitacion.get("precio") or 0)
        except (TypeError, ValueError):
            return 0.0
