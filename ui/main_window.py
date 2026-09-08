# ui/main_window.py
import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, 
    QListWidgetItem, QPushButton, QStackedWidget, QMenu, QMessageBox
)
from PySide6.QtGui import QAction, QIcon
from PySide6.QtCore import QSize, Qt
from ui.admin_window import AdminWindow
from ui.tarjetas_lista import TarjetaHabitacion
from ui.detalle_habitacion import DetalleHabitacionWidget
from services.habitacion_service import HabitacionService
from ui.registro_window import RegistroUsuario

class VentanaPrincipal(QMainWindow):
    def __init__(self, usuario_actual: dict = None, habitacion_service: HabitacionService = None):
        super().__init__()
        self.setWindowTitle("Sistema de Reservas de Hotel")
        self.resize(850, 600)

        self.usuario_actual = usuario_actual or {"nombre": "Invitado", "rol": "user"}
        self.habitacion_service = habitacion_service or HabitacionService()
        self.ventana_admin = None

        # -------------------------------------------------------------
        # BOTÓN DE USUARIO
        # -------------------------------------------------------------
        nombre_usuario = self.usuario_actual.get("nombre", "Invitado")
        
        #Formato del boton Hola, Nombre_usuario
        self.btn_usuario = QPushButton(f"Hola, {nombre_usuario}")
        self.btn_usuario.setCursor(Qt.PointingHandCursor)
        self.btn_usuario.setFixedHeight(38)

        # Menú desplegable para el botón
        menu_usuario = QMenu(self)
        
        accion_cerrar_sesion = QAction("Cerrar Sesión", self)
        accion_cerrar_sesion.triggered.connect(self._cerrar_sesion)
        
        menu_usuario.addAction(accion_cerrar_sesion)
        self.btn_usuario.setMenu(menu_usuario)

        self.stack = QStackedWidget()

        self.vista_catalogo = QWidget()
        layout_principal = QVBoxLayout(self.vista_catalogo)
        
        layout_top = QHBoxLayout()
        lbl_titulo = QLabel("<b>Catálogo de Habitaciones Disponibles</b>")
        
        self.btn_publicar = QPushButton("Publicar Habitación")
        self.btn_publicar.setFixedHeight(35)
        self.btn_publicar.clicked.connect(self._abrir_publicar_habitacion)
        
        if self.usuario_actual.get("rol") != "admin":
            self.btn_publicar.setVisible(False)

        layout_top.addWidget(lbl_titulo)
        layout_top.addStretch()
        layout_top.addWidget(self.btn_publicar)
        layout_top.addSpacing(15)
        layout_top.addWidget(self.btn_usuario)
        
        layout_principal.addLayout(layout_top)

        self.lista_habitaciones = QListWidget()
        self.lista_habitaciones.setSpacing(8) 
        layout_principal.addWidget(self.lista_habitaciones)

        self.vista_detalle = DetalleHabitacionWidget(al_volver_callback=self._volver_al_catalogo)

        self.stack.addWidget(self.vista_catalogo)
        self.stack.addWidget(self.vista_detalle)

        self.setCentralWidget(self.stack)
        self.actualizar_catalogo()

    def _cerrar_sesion(self):
        """Cierra la ventana principal"""
        self.close()

    def _abrir_publicar_habitacion(self):
        self.ventana_admin = AdminWindow(
            habitacion_service=self.habitacion_service,
            al_actualizar_callback=self.actualizar_catalogo
        )
        self.ventana_admin.show()

    def _abrir_editar_habitacion(self, habitacion: dict):
        self.ventana_admin = AdminWindow(
            habitacion_service=self.habitacion_service,
            al_actualizar_callback=self.actualizar_catalogo,
            habitacion_a_editar=habitacion
        )
        self.ventana_admin.show()

    def _eliminar_habitacion(self, habitacion: dict):
        confirmacion = QMessageBox.question(
            self,
            "Confirmar eliminación",
            f"¿Estás seguro de que deseas eliminar la habitación {habitacion.get('numero')}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirmacion == QMessageBox.StandardButton.Yes:
            self.habitacion_service.eliminar_habitacion(habitacion.get("numero"))
            self.actualizar_catalogo()

    def _mostrar_detalles(self, habitacion: dict):
        self.vista_detalle.cargar_datos(habitacion)
        es_cliente = self.usuario_actual.get("rol") != "admin"
        self.vista_detalle.configurar_modo(es_cliente)
        self.stack.setCurrentWidget(self.vista_detalle)

    def _volver_al_catalogo(self):
        self.stack.setCurrentWidget(self.vista_catalogo)

    def actualizar_catalogo(self):
        self.lista_habitaciones.clear()
        habitaciones = self.habitacion_service.obtener_todas()
        es_admin = self.usuario_actual.get("rol") == "admin"

        for hab in habitaciones:
            item = QListWidgetItem(self.lista_habitaciones)
            item.setSizeHint(QSize(0, 110)) 

            widget_tarjeta = TarjetaHabitacion(hab, es_admin=es_admin)
            widget_tarjeta.detalles_solicitados.connect(self._mostrar_detalles)

            if es_admin:
                widget_tarjeta.editar_solicitado.connect(self._abrir_editar_habitacion)
                widget_tarjeta.eliminar_solicitado.connect(self._eliminar_habitacion)
            self.lista_habitaciones.addItem(item)
            self.lista_habitaciones.setItemWidget(item, widget_tarjeta)