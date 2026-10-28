# ui/main_window.py
from PySide6.QtWidgets import (
    QMainWindow, QStackedWidget, QVBoxLayout, QWidget, QMessageBox
)
from PySide6.QtCore import Signal, QTimer
from services.autenticacion_service import AutenticacionService
from services.habitacion_service import HabitacionService
from services.reserva_service import ReservaService
from ui.admin_window import AdminWindow
from ui.banner_navegacion import BannerNavegacion
from ui.detalle_habitacion import DetalleHabitacionWidget
from ui.dialogs import DialogoEditarReserva
from ui.panel_catalogo import PanelCatalogo
from ui.panel_dashboard import PanelDashboard
from ui.panel_pagos_reportes import PanelPagosReportes
from ui.ventana_administracion import VentanaAdministracion
from ui.panel_notificaciones import PanelNotificaciones
from ui.historial_huespedes import HistorialHuespedesWindow
from ui.registro_huesped import RegistroHuespedDialog
from utils.seguridad import es_administrador, puede_administrar_catalogo

class VentanaPrincipal(QMainWindow):
    """Shell de la aplicación: banner superior y paneles apilados."""

    sesion_cerrada = Signal()

    PANEL_DETALLE = "__detalle__"

    INTERVALO_REFRESCO_MS = 30000

    def __init__(self, usuario_actual: dict = None, habitacion_service=None, reserva_service=None, autenticacion_service=None):
        super().__init__()
        self.usuario_actual = usuario_actual or {}
        self.habitacion_service = habitacion_service or HabitacionService()
        self.reserva_service = reserva_service or ReservaService()
        self.autenticacion_service = autenticacion_service or AutenticacionService()
        self.es_admin = es_administrador(self.usuario_actual)
        self.ventana_admin = None
        self.dialogo_registro = None
        self.ventana_historial = None
        self.habitacion_en_detalle = None
        self.popup_notificaciones = PanelNotificaciones(self.reserva_service, self)

        self.setWindowTitle("Sistema de Reservas de Hotel · Recepción")
        self.resize(1180, 720)

        # --------------------------------------------------
        # BANNER SUPERIOR
        # --------------------------------------------------
        self.banner = BannerNavegacion(usuario_actual=self.usuario_actual)
        self.banner.panel_solicitado.connect(self._ir_a_panel)
        self.banner.sesion_cerrada_solicitada.connect(self._cerrar_sesion)
        self.banner.configuracion_solicitada.connect(self._abrir_configuracion)
        self.banner.notificaciones_solicitada.connect(self._abrir_notificaciones)

        # --------------------------------------------------
        # PANELES
        # --------------------------------------------------
        self.panel_dashboard = PanelDashboard(
            usuario_actual=self.usuario_actual,
            habitacion_service=self.habitacion_service,
            reserva_service=self.reserva_service,
        )
        self.panel_dashboard.navegar_a.connect(self._ir_a_panel)
        self.panel_dashboard.registro_solicitado.connect(self._abrir_registro_huesped)
        self.panel_dashboard.historial_solicitado.connect(self._abrir_historial)
        self.panel_dashboard.ocupacion_cambiada.connect(self.refrescar_paneles)
        self.panel_dashboard.editar_reserva_solicitada.connect(self._abrir_editar_reserva)

        self.panel_catalogo = PanelCatalogo(
            usuario_actual=self.usuario_actual,
            habitacion_service=self.habitacion_service,
            al_abrir_detalle=self._abrir_detalle_habitacion,
            al_editar_habitacion=self._abrir_admin_habitacion,
        )
        self.panel_catalogo.catalogo_modificado.connect(self._al_modificar_catalogo)

        self.panel_pagos_y_reportes = PanelPagosReportes(
            usuario_actual=self.usuario_actual,
            reserva_service=self.reserva_service,
            habitacion_service=self.habitacion_service,
            es_admin=self.es_admin,
        )
        self.panel_pagos_y_reportes.pago_registrado.connect(self.refrescar_paneles)

        self.vista_detalle = DetalleHabitacionWidget(
            al_volver_callback=self._volver_al_catalogo,
            usuario_actual=self.usuario_actual,
            habitacion_service=self.habitacion_service,
            reserva_service=self.reserva_service,
        )
        self.vista_detalle.registro_solicitado.connect(self._abrir_registro_huesped)

        self.paneles = {
            "dashboard": self.panel_dashboard,
            "catalogo": self.panel_catalogo,
            "pagos_reportes": self.panel_pagos_y_reportes,
            self.PANEL_DETALLE: self.vista_detalle,
        }

        # Los paneles de administración se agrupan bajo «Configuración del hotel»
        # y se construyen solo para el administrador.
        self.panel_administracion = None
        if self.es_admin:
            self.panel_administracion = VentanaAdministracion(
                usuario_actual=self.usuario_actual,
                reserva_service=self.reserva_service,
                habitacion_service=self.habitacion_service,
                autenticacion_service=self.autenticacion_service,
            )
            self.panel_administracion.catalogo_modificado.connect(self._al_modificar_catalogo)
            # Se registra como un panel accesible desde la barra o desde el menú:
            # en la nueva estructura lo abrimos desde el menú de sesión, pero lo
            # dejamos disponible en el stack para reaprovechar la navegación.
            self.paneles["administracion"] = self.panel_administracion
        self.panel_reportes = getattr(self.panel_pagos_y_reportes, "panel_reportes", None)

        self.stack = QStackedWidget()
        for panel in self.paneles.values():
            self.stack.addWidget(panel)

        layout_principal = QVBoxLayout()
        layout_principal.setContentsMargins(0, 0, 0, 0)
        layout_principal.setSpacing(0)
        layout_principal.addWidget(self.banner)
        layout_principal.addWidget(self.stack, stretch=1)

        contenedor = QWidget()
        contenedor.setLayout(layout_principal)
        self.setCentralWidget(contenedor)

        # El refresco periódico no debe pisar un formulario abierto: mientras el
        # administrador edita, el inventario puede cambiar y borrarle los datos.
        self.timer_refresco = QTimer(self)
        self.timer_refresco.setInterval(self.INTERVALO_REFRESCO_MS)
        self.timer_refresco.timeout.connect(self._refresco_periodico)
        self.timer_refresco.start()

        self._ir_a_panel("dashboard")

    # ------------------------------------------------------------------
    # NAVEGACIÓN
    # ------------------------------------------------------------------
    def _ir_a_panel(self, clave):
        panel = self.paneles.get(clave)
        if not panel:
            return

        self.stack.setCurrentWidget(panel)

        if clave != self.PANEL_DETALLE:
            self.banner.set_panel_activo(clave)
        else:
            self.banner.set_panel_activo("catalogo")

        # Los paneles de administración se recargan al entrar (no en el refresco
        # periódico, que borraría un formulario a medio llenar).
        if clave == "reportes" and self.panel_reportes is not None:
            self.panel_reportes.refrescar()
        elif clave == "administracion" and self.panel_administracion is not None:
            self.panel_administracion.refrescar()

        self.refrescar_paneles()

    def refrescar_paneles(self):
        """Mantiene sincronizados los paneles con el estado real de la base de datos."""
        self.panel_dashboard.refrescar()
        self.panel_catalogo.refrescar()
        self.panel_pagos_y_reportes.refrescar()
        if self.ventana_historial is not None:
            self.ventana_historial.refrescar()

    def _al_modificar_catalogo(self):
        """Renueva el tablero y pagos; el catálogo ya se refrescó en su propia señal."""
        self.panel_dashboard.refrescar()
        self.panel_pagos_y_reportes.refrescar()

    def _refresco_periodico(self):
        """Mantiene la ocupación al día aunque nadie navegue por los paneles."""
        if not self.isVisible():
            return
        if self.ventana_admin is not None:
            return
        # La ficha abierta puede estar recien llenándose: no se toca.
        if self.stack.currentWidget() is self.vista_detalle:
            return

        try:
            self.refrescar_paneles()
        except Exception:
            # Un fallo puntual de red no debe cerrar la sesión del empleado.
            pass

    def _volver_al_catalogo(self):
        self.habitacion_en_detalle = None
        self._ir_a_panel("catalogo")

    # ------------------------------------------------------------------
    # CATÁLOGO
    # ------------------------------------------------------------------
    def _abrir_detalle_habitacion(self, habitacion):
        self.habitacion_en_detalle = habitacion
        self.vista_detalle.cargar_datos(habitacion)
        self._ir_a_panel(self.PANEL_DETALLE)

    # ------------------------------------------------------------------
    # ALTA DE HUÉSPED
    # ------------------------------------------------------------------
    def _abrir_registro_huesped(self, habitacion_preseleccionada: dict = None):
        """Abre el formulario de registro de huésped.

        Es el flujo principal de recepción: se llama desde el botón de la mesa
        de trabajo, desde el tablero y desde la ficha de una habitación.
        """
        if self.dialogo_registro is not None:
            self.dialogo_registro.raise_()
            self.dialogo_registro.activateWindow()
            return self.dialogo_registro

        dialogo = RegistroHuespedDialog(
            usuario_actual=self.usuario_actual,
            habitacion_service=self.habitacion_service,
            reserva_service=self.reserva_service,
            habitacion_preseleccionada=habitacion_preseleccionada,
            parent=self,
        )
        dialogo.reserva_registrada.connect(self._al_registrar_huesped)
        dialogo.finished.connect(self._al_cerrar_registro)
        self.dialogo_registro = dialogo
        dialogo.exec()
        return dialogo

    def _al_cerrar_registro(self, _codigo):
        self.dialogo_registro = None

    def _al_registrar_huesped(self, reserva: dict, mensaje: str):
        """Confirma el alta y renueva tablero, catálogo y pagos."""
        QMessageBox.information(self, "Huésped registrado", mensaje)
        self.refrescar_paneles()

    def _abrir_admin_habitacion(self, habitacion):
        if not puede_administrar_catalogo(self.usuario_actual):
            return

        self.ventana_admin = AdminWindow(
            habitacion_service=self.habitacion_service,
            usuario_actual=self.usuario_actual,
            habitacion_a_editar=habitacion,
            parent=self,
        )
        self.ventana_admin.guardado.connect(self.refrescar_paneles)
        self.ventana_admin.destroyed.connect(self._al_cerrar_admin)
        self.ventana_admin.show()
        self.ventana_admin.raise_()
        self.ventana_admin.activateWindow()

    def _al_cerrar_admin(self):
        """Libera la referencia al formulario de administración ya destruido."""
        self.ventana_admin = None

    # ------------------------------------------------------------------
    # EDICIÓN DE RESERVAS (solo administrador)
    # ------------------------------------------------------------------
    def _abrir_editar_reserva(self, reserva):
        """Abre el formulario de edición de fechas/habitación de una reserva."""
        if not self.es_admin or not reserva:
            return

        dialogo = DialogoEditarReserva(
            reserva=reserva,
            usuario_actual=self.usuario_actual,
            reserva_service=self.reserva_service,
            habitacion_service=self.habitacion_service,
            parent=self,
        )
        dialogo.guardado.connect(self.refrescar_paneles)
        dialogo.exec()

    # ------------------------------------------------------------------
    # HISTORIAL DE HUÉSPEDES
    # ------------------------------------------------------------------
    def _abrir_historial(self):
        """Abre (o trae al frente) la ventana independiente del historial."""
        if self.ventana_historial is not None:
            self.ventana_historial.show()
            self.ventana_historial.raise_()
            self.ventana_historial.activateWindow()
            return

        self.ventana_historial = HistorialHuespedesWindow(
            usuario_actual=self.usuario_actual,
            reserva_service=self.reserva_service,
            parent=self,
        )
        self.ventana_historial.destroyed.connect(self._al_cerrar_historial)
        self.ventana_historial.show()
        self.ventana_historial.raise_()
        self.ventana_historial.activateWindow()

    def _al_cerrar_historial(self):
        """Libera la referencia a la ventana de historial ya destruida."""
        self.ventana_historial = None

    # ------------------------------------------------------------------
    # SESIÓN
    # ------------------------------------------------------------------
    def _cerrar_sesion(self):
        # Se detiene el refresco para no consultar la base con la sesión cerrada.
        self.timer_refresco.stop()
        self.sesion_cerrada.emit()

    def closeEvent(self, event):
        """Cierra los cuadros secundarios y detiene el refresco antes de destruirlos."""
        self.timer_refresco.stop()
        if self.ventana_admin:
            self.ventana_admin.close()
        if self.ventana_historial:
            self.ventana_historial.close()
        super().closeEvent(event)

    def _actualizar_conteo_notificaciones(self):
        try:
            avisos = self.reserva_service.obtener_alertas_cobro()
            self.banner.set_notificaciones(len(avisos))
        except Exception:
            self.banner.set_notificaciones(0)

    def _abrir_configuracion(self):
        if not self.es_admin:
            return
        self._ir_a_panel("administracion")
        if self.panel_administracion is not None:
            self.panel_administracion.refrescar()

    def _abrir_notificaciones(self):
        if self.popup_notificaciones is None:
            self.popup_notificaciones = PanelNotificaciones(self.reserva_service, self)
        self.popup_notificaciones.mostrar_bajo(self.banner.btn_notificaciones)
        self._actualizar_conteo_notificaciones()
