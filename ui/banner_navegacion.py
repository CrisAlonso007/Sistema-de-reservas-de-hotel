# ui/banner_navegacion.py
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QMenu
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
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
        # IDENTIDAD DEL SISTEMA
        # --------------------------------------------------
        bloque_titulo = QVBoxLayout()
        bloque_titulo.setSpacing(0)

        lbl_titulo = QLabel("Sistema de Reservas de Hotel")
        lbl_titulo.setObjectName("bannerTitulo")
        bloque_titulo.addWidget(lbl_titulo)

        lbl_subtitulo = QLabel("Módulo de recepción · uso interno del personal")
        lbl_subtitulo.setObjectName("bannerSubtitulo")
        bloque_titulo.addWidget(lbl_subtitulo)

        layout.addLayout(bloque_titulo)
        layout.addSpacing(30)

        # --------------------------------------------------
        # NAVEGACIÓN PRINCIPAL
        # --------------------------------------------------
        self.opciones = [
            ("dashboard", "Inicio", "Resumen de ocupación y llegadas del día."),
            ("catalogo", "Catálogo", "Ver y administrar las habitaciones del hotel."),
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
