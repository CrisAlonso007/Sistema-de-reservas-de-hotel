# ui/panel_catalogo.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget,
    QListWidgetItem, QMessageBox
)
from PySide6.QtCore import Qt, QSize, Signal
from utils.stylesheets import ESTILO_PANEL
from ui.tarjetas_lista import TarjetaHabitacion

class PanelCatalogo(QWidget):
    """Listado de habitaciones con su ocupación en tiempo real y acciones de administración."""
    catalogo_modificado = Signal()

    def __init__(self, usuario_actual: dict = None, habitacion_service=None, al_abrir_detalle=None, al_editar_habitacion=None, parent=None):
        super().__init__(parent)
        self.usuario_actual = usuario_actual or {}
        self.habitacion_service = habitacion_service
        self.al_abrir_detalle = al_abrir_detalle
        self.al_editar_habitacion = al_editar_habitacion

        self.setObjectName("panelRaiz")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(ESTILO_PANEL)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)

        layout.addWidget(self._crear_encabezado())

        self.lista_habitaciones = QListWidget()
        self.lista_habitaciones.setSpacing(8)
        self.lista_habitaciones.setStyleSheet("QListWidget { background: transparent; }")
        layout.addWidget(self.lista_habitaciones)

    def _crear_encabezado(self):
        contenedor = QWidget()
        layout = QHBoxLayout(contenedor)
        layout.setContentsMargins(0, 0, 0, 0)

        textos = QVBoxLayout()
        textos.setSpacing(2)

        lbl_titulo = QLabel("Catálogo de Habitaciones")
        lbl_titulo.setObjectName("panelTitulo")
        textos.addWidget(lbl_titulo)

        self.lbl_resumen = QLabel("Cargando inventario...")
        self.lbl_resumen.setObjectName("panelSubtitulo")
        textos.addWidget(self.lbl_resumen)

        layout.addLayout(textos)
        layout.addStretch()

        self.btn_publicar = QPushButton("Publicar Habitación")
        self.btn_publicar.setObjectName("accionPrimaria")
        self.btn_publicar.setCursor(Qt.PointingHandCursor)
        self.btn_publicar.setFixedHeight(38)
        self.btn_publicar.clicked.connect(self._solicitar_publicar)
        if self.usuario_actual.get("rol") != "administrador":
            self.btn_publicar.setVisible(False)
        layout.addWidget(self.btn_publicar)

        return contenedor

    def _solicitar_publicar(self):
        """Abre el formulario de alta. La navegación la resuelve la ventana principal."""
        if self.al_editar_habitacion:
            self.al_editar_habitacion(None)
    def refrescar(self):
        """Recarga la lista de habitaciones y el resumen de inventario."""
        if not self.habitacion_service:
            return

        self.lista_habitaciones.clear()
        habitaciones = self.habitacion_service.obtener_todas()
        es_admin = self.usuario_actual.get("rol") == "administrador"

        for hab in habitaciones:
            item = QListWidgetItem(self.lista_habitaciones)
            item.setSizeHint(QSize(0, 118))

            tarjeta = TarjetaHabitacion(hab, es_admin=es_admin)
            tarjeta.detalles_solicitados.connect(self._solicitar_detalle)
            if es_admin:
                tarjeta.editar_solicitado.connect(self._solicitar_edicion)
                tarjeta.eliminar_solicitado.connect(self._solicitar_eliminacion)
                tarjeta.mantenimiento_solicitado.connect(self._solicitar_mantenimiento)

            self.lista_habitaciones.addItem(item)
            self.lista_habitaciones.setItemWidget(item, tarjeta)

        self.lbl_resumen.setText(self._resumen_texto(habitaciones))

    @staticmethod
    def _resumen_texto(habitaciones):
        if not habitaciones:
            return "No hay habitaciones registradas en el catálogo."

        disponibles = sum(1 for h in habitaciones if h.get("estatus") == "Disponible")
        ocupadas = sum(1 for h in habitaciones if h.get("estatus") == "Ocupado")
        reservadas = sum(1 for h in habitaciones if h.get("estatus") == "Reservado")
        mantenimiento = sum(1 for h in habitaciones if h.get("estatus") == "Mantenimiento")

        return (
            f"{len(habitaciones)} habitaciones · {disponibles} disponibles · "
            f"{reservadas} reservadas · {ocupadas} ocupadas · {mantenimiento} en mantenimiento"
        )

    def _solicitar_detalle(self, habitacion):
        if self.al_abrir_detalle:
            self.al_abrir_detalle(habitacion)

    def _solicitar_edicion(self, habitacion):
        if self.al_editar_habitacion:
            self.al_editar_habitacion(habitacion)

    def _solicitar_eliminacion(self, habitacion):
        confirmacion = QMessageBox.question(
            self,
            "Confirmar eliminación",
            f"¿Desea eliminar la habitación {habitacion.get('numero')}?\n\n"
            "Si tiene reservas asociadas, la operación se rechazará.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirmacion != QMessageBox.StandardButton.Yes:
            return

        exito, mensaje = self.habitacion_service.eliminar_habitacion(
            usuario_actual=self.usuario_actual,
            habitacion_id=habitacion.get("id"),
        )
        if exito:
            QMessageBox.information(self, "Éxito", mensaje)
            self.catalogo_modificado.emit()
            self.refrescar()
        else:
            QMessageBox.warning(self, "No se pudo eliminar", mensaje)

    def _solicitar_mantenimiento(self, habitacion):
        exito, mensaje = self.habitacion_service.alternar_mantenimiento(
            usuario_actual=self.usuario_actual,
            habitacion_id=habitacion.get("id"),
        )
        if exito:
            QMessageBox.information(self, "Estado actualizado", mensaje)
            self.catalogo_modificado.emit()
            self.refrescar()
        else:
            QMessageBox.warning(self, "No se pudo actualizar", mensaje)
