# ui/banner_navegacion.py
from pathlib import Path

from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QMenu
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QPixmap
from utils.stylesheets import ESTILO_BANNER

class BannerNavegacion(QWidget):
    """Cabecera del sistema: identidad, navegación por paneles y menú de sesión."""

    panel_solicitado = Signal(str)
    sesion_cerrada_solicitada = Signal()
    # Abre el popup de avisos junto al botón de la campana.
    notificaciones_solicitada = Signal()

    def __init__(self, usuario_actual: dict = None, parent=None):
        super().__init__(parent)
        self.usuario_actual = usuario_actual or {}
        self.setObjectName("bannerContenedor")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedHeight(64)
        self.setStyleSheet(ESTILO_BANNER)

        self.boton_activo = None
        self.botones = {}
        self.es_admin = self.usuario_actual.get("rol") == "administrador"

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 10, 18, 10)
        layout.setSpacing(6)

        # --------------------------------------------------
        # IDENTIDAD DE MARCA
        # --------------------------------------------------
        bloque_marca = QHBoxLayout()
        bloque_marca.setSpacing(9)

        ruta_logo = (
            Path(__file__).resolve().parents[1]
            / "recursos"
            / "iconos-de-la-marca"
            / "Allogi-logotipo-removebg-preview.png"
        )
        logo = QPixmap(str(ruta_logo))
        if not logo.isNull():
            logo = logo.copy(85, 85, 286, 290)
            lbl_marca = QLabel()
            lbl_marca.setObjectName("bannerMarca")
            lbl_marca.setFixedSize(36, 36)
            lbl_marca.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_marca.setAccessibleName("Logotipo de Allogi")
            lbl_marca.setPixmap(
                logo.scaled(
                    32,
                    32,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            bloque_marca.addWidget(lbl_marca)

        bloque_titulo = QVBoxLayout()
        bloque_titulo.setSpacing(1)

        self.lbl_titulo = QLabel("Allogi")
        self.lbl_titulo.setObjectName("bannerTitulo")
        bloque_titulo.addWidget(self.lbl_titulo)

        self.lbl_subtitulo = QLabel("Sistema de reservas · uso interno del personal")
        self.lbl_subtitulo.setObjectName("bannerSubtitulo")
        bloque_titulo.addWidget(self.lbl_subtitulo)

        bloque_marca.addLayout(bloque_titulo)
        layout.addLayout(bloque_marca)
        layout.addSpacing(24)

        # --------------------------------------------------
        # NAVEGACIÓN PRINCIPAL
        # --------------------------------------------------
        self.opciones = [
            ("dashboard", "Inicio", "Resumen de ocupación y llegadas del día."),
            ("catalogo", "Catálogo", "Ver y administrar las habitaciones del hotel."),
            ("servicios", "Limpieza", "Gestionar turnos de limpieza y mantenimiento."),
            ("pagos_reportes", "Pagos", "Consultar pagos y saldos de reservas."),
        ]
        if self.es_admin:
            self.opciones.extend([
                ("reportes", "Reportes", "Consultar y exportar reportes del hotel."),
                ("administracion", "Configuración", "Configurar el hotel y gestionar al personal."),
            ])

        for clave, titulo, ayuda in self.opciones:
            boton = QPushButton(titulo)
            boton.setObjectName("bannerBoton")
            boton.setCheckable(True)
            boton.setCursor(Qt.PointingHandCursor)
            boton.setMinimumHeight(34)
            boton.setToolTip(ayuda)
            boton.clicked.connect(lambda _=False, clave=clave: self._navegar(clave))
            self.botones[clave] = boton
            layout.addWidget(boton)

        layout.addStretch()

        # --------------------------------------------------
        # CAMPANA DE AVISOS
        # --------------------------------------------------
        # Visible para ambos perfiles: a recepción también le interesa saber
        # quién se quedó en la habitación de más.
        self.btn_notificaciones = QPushButton("Notificaciones")
        self.btn_notificaciones.setObjectName("campanaNotificaciones")
        self.btn_notificaciones.setCursor(Qt.PointingHandCursor)
        self.btn_notificaciones.setMinimumHeight(34)
        self.btn_notificaciones.clicked.connect(self.notificaciones_solicitada.emit)
        self.set_notificaciones(0)
        layout.addWidget(self.btn_notificaciones)

        # --------------------------------------------------
        # MENÚ DE SESIÓN
        # --------------------------------------------------
        nombre = self.usuario_actual.get("nombre_completo") or self.usuario_actual.get("nombre", "")

        menu_usuario = QMenu(self)

        accion_rol = QAction(f"Rol: {self._etiqueta_rol(self.es_admin)}", self)
        accion_rol.setEnabled(False)
        menu_usuario.addAction(accion_rol)
        menu_usuario.addSeparator()

        accion_cerrar = QAction("Cerrar Sesión", self)
        accion_cerrar.triggered.connect(self.sesion_cerrada_solicitada.emit)
        menu_usuario.addAction(accion_cerrar)

        self.btn_usuario = QPushButton(f"Hola, {nombre}")
        self.btn_usuario.setObjectName("bannerUsuario")
        self.btn_usuario.setCursor(Qt.PointingHandCursor)
        self.btn_usuario.setMinimumHeight(34)
        self.btn_usuario.setToolTip(
            f"Sesión iniciada como {nombre} ({self._etiqueta_rol(self.es_admin)}). "
            "Haga clic para ver las opciones de sesión."
        )
        self.btn_usuario.setMenu(menu_usuario)
        layout.addWidget(self.btn_usuario)

    def _navegar(self, clave):
        self.set_panel_activo(clave)
        self.panel_solicitado.emit(clave)

    def set_panel_activo(self, clave):
        """Resalta el botón correspondiente al panel visible."""
        for nombre, boton in self.botones.items():
            boton.setChecked(nombre == clave)
        self.boton_activo = clave

    def set_notificaciones(self, conteo):
        """Actualiza la campana con el número de avisos pendientes."""
        if conteo > 0:
            self.btn_notificaciones.setText(f"Notificaciones ({conteo})")
            self.btn_notificaciones.setProperty("conAvisos", True)
            ayuda = f"{conteo} aviso(s) pendiente(s). Haga clic para verlos."
        else:
            self.btn_notificaciones.setText("Notificaciones")
            self.btn_notificaciones.setProperty("conAvisos", False)
            ayuda = "No hay avisos pendientes. Haga clic para revisarlos."

        # La propiedad de hoja de estilos solo se reaplica al refrescar el estilo.
        self.btn_notificaciones.style().unpolish(self.btn_notificaciones)
        self.btn_notificaciones.style().polish(self.btn_notificaciones)
        self.btn_notificaciones.setToolTip(ayuda)


    @staticmethod
    def _etiqueta_rol(es_admin):
        return "Administrador" if es_admin else "Recepcionista"
