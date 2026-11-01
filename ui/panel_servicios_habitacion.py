from datetime import date

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QGroupBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from utils.stylesheets import ESTILO_PANEL, ESTILO_TABLA


class PanelServiciosHabitacion(QWidget):
    """Turnos de limpieza y mantenimiento de las habitaciones."""

    habitaciones_modificadas = Signal()

    def __init__(self, usuario_actual, habitacion_service, parent=None):
        super().__init__(parent)
        self.usuario_actual = usuario_actual or {}
        self.habitacion_service = habitacion_service
        self.es_admin = self.usuario_actual.get("rol") == "administrador"

        self.setObjectName("panelRaiz")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(ESTILO_PANEL)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)

        encabezado = QHBoxLayout()
        titulos = QVBoxLayout()
        titulo = QLabel("Limpieza y mantenimiento")
        titulo.setObjectName("panelTitulo")
        titulos.addWidget(titulo)
        self.lbl_resumen = QLabel(
            "Dos turnos de limpieza durante la estancia y limpieza obligatoria al salir."
        )
        self.lbl_resumen.setObjectName("panelSubtitulo")
        titulos.addWidget(self.lbl_resumen)
        encabezado.addLayout(titulos)
        encabezado.addStretch()

        self.btn_actualizar = QPushButton("Actualizar")
        self.btn_actualizar.setObjectName("accionSecundaria")
        self.btn_actualizar.setCursor(Qt.PointingHandCursor)
        self.btn_actualizar.setFixedHeight(38)
        self.btn_actualizar.clicked.connect(self.refrescar)
        encabezado.addWidget(self.btn_actualizar)
        layout.addLayout(encabezado)

        grupo = QGroupBox("Tareas de hoy")
        grupo.setObjectName("seccion")
        grupo_layout = QVBoxLayout(grupo)
        grupo_layout.setContentsMargins(14, 18, 14, 14)

        self.tabla = QTableWidget(0, 6)
        self.tabla.setHorizontalHeaderLabels(
            ["Habitación", "Servicio", "Turno", "Huésped", "Estado / duración", "Acción"]
        )
        self.tabla.setStyleSheet(ESTILO_TABLA)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.tabla.setColumnWidth(5, 145)
        grupo_layout.addWidget(self.tabla)
        layout.addWidget(grupo, stretch=1)

    def refrescar(self):
        self.aplicar_tareas(
            self.habitacion_service.obtener_tareas_habitacion(date.today())
        )

    def aplicar_tareas(self, tareas):
        self.tabla.setRowCount(0)

        for tarea in tareas:
            fila = self.tabla.rowCount()
            self.tabla.insertRow(fila)
            duracion = tarea.get("duracion_minutos")
            duracion_texto = (
                f"{int(duracion)} min"
                if duracion is not None
                else "Sin iniciar"
            )
            estado = tarea["estado"]
            if estado == "En proceso":
                estado_texto = f"En proceso · {duracion_texto}"
            elif estado == "Completada":
                estado_texto = f"Completada · {duracion_texto}"
            else:
                estado_texto = "Pendiente"

            valores = (
                str(tarea["habitacion_numero"]),
                tarea["tipo"],
                tarea["turno"],
                tarea["cliente"],
                estado_texto,
            )
            for columna, valor in enumerate(valores):
                item = QTableWidgetItem(str(valor))
                if columna == 0:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.tabla.setItem(fila, columna, item)

            self.tabla.setCellWidget(fila, 5, self._crear_accion(tarea))
            self.tabla.setRowHeight(fila, 44)

        if not tareas:
            self.tabla.setRowCount(1)
            item = QTableWidgetItem("No hay tareas de habitación para hoy.")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tabla.setItem(0, 0, item)
            self.tabla.setSpan(0, 0, 1, self.tabla.columnCount())

        pendientes = sum(1 for tarea in tareas if tarea["estado"] != "Completada")
        self.lbl_resumen.setText(
            f"{len(tareas)} tarea(s) programada(s) · {pendientes} pendiente(s) o en proceso. "
            "La habitación queda disponible solo al terminar la limpieza de salida."
        )

    def _crear_accion(self, tarea):
        contenedor = QWidget()
        layout = QHBoxLayout(contenedor)
        layout.setContentsMargins(3, 3, 3, 3)

        estado = tarea["estado"]
        tipo = tarea["tipo"]
        if estado == "Completada":
            boton = QPushButton("Terminada")
            boton.setEnabled(False)
        elif tipo == "Mantenimiento técnico" and not self.es_admin:
            boton = QPushButton("Solo admin")
            boton.setEnabled(False)
        else:
            finalizar = estado == "En proceso"
            boton = QPushButton("Finalizar" if finalizar else "Iniciar")
            boton.setObjectName(
                "accionTablaSecundaria" if finalizar else "accionTablaPrimaria"
            )
            boton.setCursor(Qt.PointingHandCursor)
            boton.clicked.connect(
                lambda _=False, t=tarea, f=finalizar: self._actualizar_tarea(t, f)
            )
        boton.setFixedHeight(30)
        layout.addWidget(boton)
        return contenedor

    def _actualizar_tarea(self, tarea, finalizar):
        verbo = "finalizar" if finalizar else "iniciar"
        pregunta = (
            f"¿Desea {verbo} {tarea['tipo'].lower()} de la habitación "
            f"{tarea['habitacion_numero']} ({tarea['turno'].lower()})?"
        )
        if QMessageBox.question(
            self,
            "Confirmar tarea",
            pregunta,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) != QMessageBox.StandardButton.Yes:
            return

        exito, mensaje = self.habitacion_service.actualizar_tarea_habitacion(
            usuario_actual=self.usuario_actual,
            tarea_id=tarea["id"],
            finalizar=finalizar,
        )
        if not exito:
            QMessageBox.warning(self, "No se pudo actualizar", mensaje)
            self.refrescar()
            return

        self.habitaciones_modificadas.emit()
