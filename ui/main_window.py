# ui/main_window.py
from PySide6.QtWidgets import (
    QMainWindow, QStackedWidget, QVBoxLayout, QWidget, QMessageBox
)
from PySide6.QtCore import Signal, QTimer
from services.autenticacion_service import AutenticacionService
from services.habitacion_service import HabitacionService
from services.hilo_carga_panel import HiloCargaPanel
from services.reserva_service import ReservaService
from ui.admin_window import AdminWindow
from ui.banner_navegacion import BannerNavegacion
from ui.detalle_habitacion import DetalleHabitacionWidget
from ui.dialogs import (
    DialogoCobro,
    DialogoDetalleReserva,
    DialogoEditarReserva,
)
from ui.panel_catalogo import PanelCatalogo
from ui.panel_dashboard import PanelDashboard
from ui.panel_pagos_reportes import PanelPagosReportes
from ui.panel_reportes import PanelReportes
from ui.panel_servicios_habitacion import PanelServiciosHabitacion
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
        self._worker_refresco = None
        self._refresco_pendiente = False
        self._cerrar_despues_del_refresco = False
        self.popup_notificaciones = PanelNotificaciones(self.reserva_service, self)

        self.setWindowTitle("Allogi · Recepción")
        self.resize(1180, 720)

        # --------------------------------------------------
        # BANNER SUPERIOR
        # --------------------------------------------------
        self.banner = BannerNavegacion(usuario_actual=self.usuario_actual)
        self.banner.panel_solicitado.connect(self._ir_a_panel)
        self.banner.sesion_cerrada_solicitada.connect(self._cerrar_sesion)
        self.banner.notificaciones_solicitada.connect(self._abrir_notificaciones)

        # --------------------------------------------------
        # PANELES
        # --------------------------------------------------
        self.panel_dashboard = PanelDashboard(
            usuario_actual=self.usuario_actual,
            habitacion_service=self.habitacion_service,
            reserva_service=self.reserva_service,
        )
        self.panel_dashboard.set_hotel_name(
            self.reserva_service.obtener_configuracion_hotel()["hotel_nombre"]
        )
        self.panel_dashboard.navegar_a.connect(self._ir_a_panel)
        self.panel_dashboard.registro_solicitado.connect(self._abrir_registro_huesped)
        self.panel_dashboard.historial_solicitado.connect(self._abrir_historial)
        self.panel_dashboard.ocupacion_cambiada.connect(self.refrescar_paneles)
        self.panel_dashboard.editar_reserva_solicitada.connect(self._abrir_editar_reserva)
        self.panel_dashboard.cobro_solicitado.connect(self._abrir_cobro_dashboard)
        self.panel_dashboard.detalle_reserva_solicitado.connect(
            self._abrir_detalle_reserva
        )

        self.panel_catalogo = PanelCatalogo(
            usuario_actual=self.usuario_actual,
            habitacion_service=self.habitacion_service,
            reserva_service=self.reserva_service,
            al_abrir_detalle=self._abrir_detalle_habitacion,
            al_editar_habitacion=self._abrir_admin_habitacion,
        )
        self.panel_catalogo.catalogo_modificado.connect(self._al_modificar_catalogo)

        self.panel_servicios = PanelServiciosHabitacion(
            usuario_actual=self.usuario_actual,
            habitacion_service=self.habitacion_service,
        )
        self.panel_servicios.habitaciones_modificadas.connect(self.refrescar_paneles)

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
            "servicios": self.panel_servicios,
            "pagos_reportes": self.panel_pagos_y_reportes,
            self.PANEL_DETALLE: self.vista_detalle,
        }

        self.panel_reportes = None
        self.panel_administracion = None
        if self.es_admin:
            self.panel_reportes = PanelReportes(
                usuario_actual=self.usuario_actual,
                reserva_service=self.reserva_service,
                habitacion_service=self.habitacion_service,
            )
            self.panel_reportes.actualizar_solicitado.connect(
                lambda: self._solicitar_carga_panel("reportes")
            )
            self.paneles["reportes"] = self.panel_reportes

            self.panel_administracion = VentanaAdministracion(
                usuario_actual=self.usuario_actual,
                reserva_service=self.reserva_service,
                habitacion_service=self.habitacion_service,
                autenticacion_service=self.autenticacion_service,
            )
            self.panel_administracion.catalogo_modificado.connect(self._al_modificar_catalogo)
            self.panel_administracion.configuracion_modificada.connect(
                self._actualizar_configuracion_hotel
            )
            self.paneles["administracion"] = self.panel_administracion

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

        self.refrescar_paneles()

    def refrescar_paneles(self):
        """Solicita la carga del panel visible sin bloquear la interfaz."""
        panel = self.stack.currentWidget()
        clave = next(
            (nombre for nombre, widget in self.paneles.items() if widget is panel),
            None,
        )
        if clave in {"dashboard", "catalogo", "servicios", "pagos_reportes"}:
            self._solicitar_carga_panel(clave)
        elif clave == "reportes" and self.panel_reportes is not None:
            self._solicitar_carga_panel(clave)
        elif clave == "administracion" and self.panel_administracion is not None:
            self.panel_administracion.refrescar()

        if self.ventana_historial is not None:
            self.ventana_historial.refrescar()

    def _solicitar_carga_panel(self, clave):
        if self._worker_refresco is not None:
            self._refresco_pendiente = (
                self._worker_refresco.clave_panel != clave
            )
            return

        parametros = None
        if clave == "reportes" and self.panel_reportes is not None:
            parametros = {
                "fecha_inicio": self.panel_reportes.dt_inicio.date().toString("yyyy-MM-dd"),
                "fecha_fin": self.panel_reportes.dt_fin.date().toString("yyyy-MM-dd"),
            }
        worker = HiloCargaPanel(
            clave,
            usuario_actual=self.usuario_actual,
            parametros=parametros,
            parent=self,
        )
        self._worker_refresco = worker
        worker.datos_cargados.connect(self._aplicar_datos_panel)
        worker.error_carga.connect(self._mostrar_error_carga_panel)
        worker.finished.connect(
            lambda worker=worker: self._al_terminar_carga_panel(worker)
        )
        worker.start()

    def _aplicar_datos_panel(self, clave, datos):
        if clave == "dashboard":
            self.panel_dashboard.aplicar_datos(datos)
        elif clave == "catalogo":
            self.panel_catalogo.aplicar_habitaciones(datos)
        elif clave == "servicios":
            self.panel_servicios.aplicar_tareas(datos)
        elif clave == "pagos_reportes":
            self.panel_pagos_y_reportes.aplicar_cuentas(datos)
        elif clave == "reportes" and self.panel_reportes is not None:
            self.panel_reportes.aplicar_datos(datos)

    def _mostrar_error_carga_panel(self, clave, mensaje):
        self.statusBar().showMessage(
            f"No se pudo actualizar {clave}: {mensaje}",
            10000,
        )

    def _al_terminar_carga_panel(self, worker):
        if self._worker_refresco is worker:
            self._worker_refresco = None
        worker.deleteLater()

        if self._cerrar_despues_del_refresco:
            self._cerrar_despues_del_refresco = False
            self.close()
            return

        if self._refresco_pendiente and self.isVisible():
            self._refresco_pendiente = False
            self.refrescar_paneles()

    def _al_modificar_catalogo(self):
        """Actualiza el panel visible después de modificar el catálogo."""
        self.refrescar_paneles()

    def _actualizar_configuracion_hotel(self):
        config = self.reserva_service.obtener_configuracion_hotel(refrescar=True)
        self.panel_dashboard.set_hotel_name(config["hotel_nombre"])
        if self.habitacion_en_detalle:
            self.vista_detalle.cargar_datos(self.habitacion_en_detalle)
        if self.panel_reportes is not None:
            self._solicitar_carga_panel("reportes")

    def _refresco_periodico(self):
        """Mantiene la ocupación al día aunque nadie navegue por los paneles."""
        if not self.isVisible():
            return
        if self.ventana_admin is not None:
            return
        # La ficha abierta puede estar recien llenándose: no se toca.
        if self.stack.currentWidget() is self.vista_detalle:
            return
        if (
            self.panel_administracion is not None
            and self.stack.currentWidget() is self.panel_administracion
        ):
            return

        self.refrescar_paneles()

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

    def _abrir_cobro_dashboard(self, reserva):
        dialogo = DialogoCobro(
            usuario_actual=self.usuario_actual,
            reserva_service=self.reserva_service,
            reserva=reserva,
            parent=self,
        )
        dialogo.pago_registrado.connect(self.refrescar_paneles)
        dialogo.exec()

    def _abrir_detalle_reserva(self, reserva):
        dialogo = DialogoDetalleReserva(
            reserva=reserva,
            reserva_service=self.reserva_service,
            parent=self,
        )
        dialogo.exec()

    def _abrir_admin_habitacion(self, habitacion):
        if not puede_administrar_catalogo(self.usuario_actual):
            return

        self.ventana_admin = AdminWindow(
            habitacion_service=self.habitacion_service,
            usuario_actual=self.usuario_actual,
            habitacion_a_editar=habitacion,
            moneda=self.reserva_service.obtener_configuracion_hotel()["moneda"],
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
    # EDICIÓN DE RESERVAS PENDIENTES
    # ------------------------------------------------------------------
    def _abrir_editar_reserva(self, reserva):
        """Abre el formulario de edición de fechas/habitación de una reserva."""
        if not reserva or reserva.get("estado") != "Pendiente":
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
        if self._worker_refresco is not None and self._worker_refresco.isRunning():
            self._cerrar_despues_del_refresco = True
            self.statusBar().showMessage(
                "Terminando la consulta actual antes de cerrar..."
            )
            event.ignore()
            return
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

    def _abrir_notificaciones(self):
        if self.popup_notificaciones is None:
            self.popup_notificaciones = PanelNotificaciones(self.reserva_service, self)
        self.popup_notificaciones.mostrar_bajo(self.banner.btn_notificaciones)
        self._actualizar_conteo_notificaciones()
