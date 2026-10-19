# ui/ventana_administracion.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QTabWidget, QGroupBox, QSpinBox, QLineEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QDialog, QAbstractItemView,
    QFormLayout, QInputDialog, QComboBox,
)
from PySide6.QtCore import Qt, Signal
from utils.stylesheets import ESTILO_PANEL, ESTILO_TABLA
from services.habitacion_service import HabitacionService
from services.reserva_service import ReservaService
from services.autenticacion_service import AutenticacionService
from utils.validaciones import MAX_TELEFONO

class DialogoEmpleado(QDialog):
    """Alta o edición de un empleado de la plantilla."""

    def __init__(self, autenticacion_service, usuario_actual, empleado=None, parent=None):
        super().__init__(parent)
        self.service = autenticacion_service
        self.usuario_actual = usuario_actual
        self.empleado = empleado

        self.setWindowTitle("Editar empleado" if empleado else "Nuevo empleado")
        self.setModal(True)
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        formulario = QFormLayout()
        formulario.setSpacing(8)

        self.txt_usuario = QLineEdit()
        self.txt_usuario.setMaxLength(20)
        self.txt_usuario.setPlaceholderText("usuario (3-20 letras, números o _)")

        self.txt_password = QLineEdit()
        self.txt_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_password.setPlaceholderText("Mínimo 4 caracteres")

        self.cmb_rol = QComboBox()
        self.cmb_rol.addItems(["recepcionista", "administrador"])

        self.txt_nombre = QLineEdit()
        self.txt_identificacion = QLineEdit()
        self.txt_correo = QLineEdit()
        self.txt_telefono = QLineEdit()
        self.txt_telefono.setMaxLength(MAX_TELEFONO)

        formulario.addRow("Usuario:", self.txt_usuario)
        formulario.addRow("Contraseña:", self.txt_password)
        formulario.addRow("Rol:", self.cmb_rol)
        formulario.addRow("Nombre completo:", self.txt_nombre)
        formulario.addRow("Identificación:", self.txt_identificacion)
        formulario.addRow("Correo:", self.txt_correo)
        formulario.addRow("Teléfono:", self.txt_telefono)
        layout.addLayout(formulario)

        if empleado:
            # En edición no se cambia el usuario ni la contraseña desde aquí:
            # la contraseña tiene su propia acción dedicada.
            self.txt_usuario.setText(empleado.get("username", ""))
            self.txt_usuario.setEnabled(False)
            self.txt_password.setEnabled(False)
            self.txt_password.setPlaceholderText("Use «Cambiar contraseña» en la lista")
            indice = self.cmb_rol.findText(empleado.get("rol", "recepcionista"))
            if indice >= 0:
                self.cmb_rol.setCurrentIndex(indice)
            self.txt_nombre.setText(empleado.get("nombre_completo", ""))
            self.txt_identificacion.setText(empleado.get("numero_identificacion", ""))
            self.txt_correo.setText(empleado.get("correo_electronico", ""))
            self.txt_telefono.setText(empleado.get("numero_telefono", ""))

        botones = QHBoxLayout()
        botones.addStretch()
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setObjectName("accionSecundaria")
        btn_cancelar.clicked.connect(self.reject)
        btn_guardar = QPushButton("Guardar")
        btn_guardar.setObjectName("accionPrimaria")
        btn_guardar.clicked.connect(self._guardar)
        botones.addWidget(btn_cancelar)
        botones.addWidget(btn_guardar)
        layout.addLayout(botones)

    def _guardar(self):
        if self.empleado:
            exito, mensaje = self.service.actualizar_personal(
                usuario_actual=self.usuario_actual,
                empleado_id=self.empleado.get("id"),
                rol=self.cmb_rol.currentText(),
                nombre_completo=self.txt_nombre.text(),
                numero_identificacion=self.txt_identificacion.text(),
                correo_electronico=self.txt_correo.text(),
                numero_telefono=self.txt_telefono.text(),
            )
        else:
            exito, mensaje = self.service.crear_personal(
                usuario_actual=self.usuario_actual,
                username=self.txt_usuario.text(),
                password=self.txt_password.text(),
                rol=self.cmb_rol.currentText(),
                nombre_completo=self.txt_nombre.text(),
                numero_identificacion=self.txt_identificacion.text(),
                correo_electronico=self.txt_correo.text(),
                numero_telefono=self.txt_telefono.text(),
            )

        if not exito:
            QMessageBox.warning(self, "No se pudo guardar", mensaje)
            return
        QMessageBox.information(self, "Empleado guardado", mensaje)
        self.accept()


class VentanaAdministracion(QWidget):
    """Panel de configuración del hotel. Solo visible para administradores.

    Reúne en pestañas todo lo que ajusta el funcionamiento del hotel:
    parámetros de las estancias, tarifas y temporadas, y gestión del personal.
    """

    catalogo_modificado = Signal()

    def __init__(self, usuario_actual: dict = None, reserva_service=None,
                 habitacion_service=None, autenticacion_service=None, parent=None):
        super().__init__(parent)
        self.usuario_actual = usuario_actual or {}
        self.reserva_service = reserva_service or ReservaService()
        self.habitacion_service = habitacion_service or HabitacionService()
        self.autenticacion_service = autenticacion_service or AutenticacionService()

        self.setObjectName("panelRaiz")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(ESTILO_PANEL)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)

        encabezado = QVBoxLayout()
        encabezado.setSpacing(2)
        lbl_titulo = QLabel("Administración")
        lbl_titulo.setObjectName("panelTitulo")
        encabezado.addWidget(lbl_titulo)
        lbl_sub = QLabel("Parámetros del hotel y gestión del personal")
        lbl_sub.setObjectName("panelSubtitulo")
        encabezado.addWidget(lbl_sub)
        layout.addLayout(encabezado)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._crear_tab_parametros(), "Parámetros del hotel")
        self.tabs.addTab(self._crear_tab_personal(), "Gestión de personal")
        layout.addWidget(self.tabs, stretch=1)

        self.refrescar()

    # ------------------------------------------------------------------
    # PESTAÑA: PARÁMETROS DEL HOTEL
    # ------------------------------------------------------------------
    def _crear_tab_parametros(self):
        pagina = QWidget()
        layout = QVBoxLayout(pagina)
        layout.setContentsMargins(14, 16, 14, 14)
        layout.setSpacing(14)

        grupo = QGroupBox("Reglas de las estancias")
        grupo.setObjectName("seccion")
        grid = QGridLayout(grupo)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(12)

        self.spn_anticipacion = QSpinBox()
        self.spn_anticipacion.setRange(0, 3650)
        self.spn_anticipacion.setSuffix(" días")
        self.spn_anticipacion.setFixedHeight(32)

        self.spn_noches_min = QSpinBox()
        self.spn_noches_min.setRange(1, 365)
        self.spn_noches_min.setSuffix(" noche(s)")
        self.spn_noches_min.setFixedHeight(32)

        self.spn_noches_max = QSpinBox()
        self.spn_noches_max.setRange(1, 365)
        self.spn_noches_max.setSuffix(" noche(s)")
        self.spn_noches_max.setFixedHeight(32)

        campos = [
            ("Antelación máxima para reservar:", self.spn_anticipacion, 0),
            ("Duración mínima de la estadía:", self.spn_noches_min, 1),
            ("Duración máxima de la estadía:", self.spn_noches_max, 2),
        ]
        for etiqueta, campo, fila in campos:
            grid.addWidget(QLabel(etiqueta), fila, 0)
            grid.addWidget(campo, fila, 1)
        grid.setColumnStretch(1, 1)

        layout.addWidget(grupo)

        btn_guardar = QPushButton("Guardar parámetros")
        btn_guardar.setObjectName("accionPrimaria")
        btn_guardar.setCursor(Qt.PointingHandCursor)
        btn_guardar.setFixedHeight(38)
        btn_guardar.setMaximumWidth(220)
        btn_guardar.clicked.connect(self._guardar_parametros)

        fila_boton = QHBoxLayout()
        fila_boton.addWidget(btn_guardar)
        fila_boton.addStretch()
        layout.addLayout(fila_boton)
        layout.addStretch()

        return pagina

    def _guardar_parametros(self):
        parametros = self.reserva_service.obtener_parametros()
        datos = {
            "dias_anticipacion_max": self.spn_anticipacion.value(),
            "noches_minimas": self.spn_noches_min.value(),
            "noches_maximas": self.spn_noches_max.value(),
            "factor_temporada_alta": parametros["factor_temporada_alta"],
            "descuento_porcentaje": parametros["descuento_porcentaje"],
            "temporada_alta_inicio": parametros["temporada_alta_inicio"],
            "temporada_alta_fin": parametros["temporada_alta_fin"],
        }
        exito, mensaje = self.reserva_service.actualizar_parametros(self.usuario_actual, datos)
        self._avisar(exito, mensaje, "Parámetros guardados")

    # ------------------------------------------------------------------
    # PESTAÑA: TARIFAS Y TEMPORADAS
    # ------------------------------------------------------------------
    def _alternar_temporada(self, activo):
        self.dt_inicio.setEnabled(activo)
        self.dt_fin.setEnabled(activo)
        self.spn_factor.setEnabled(activo)

    # ------------------------------------------------------------------
    # PESTAÑA: GESTIÓN DE PERSONAL
    # ------------------------------------------------------------------
    def _crear_tab_personal(self):
        pagina = QWidget()
        layout = QVBoxLayout(pagina)
        layout.setContentsMargins(14, 16, 14, 14)
        layout.setSpacing(12)

        self.tabla_personal = QTableWidget(0, 6)
        self.tabla_personal.setHorizontalHeaderLabels(
            ["Usuario", "Nombre", "Rol", "Identificación", "Correo", "Estado"]
        )
        self.tabla_personal.setStyleSheet(ESTILO_TABLA)
        self.tabla_personal.verticalHeader().setVisible(False)
        self.tabla_personal.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla_personal.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tabla_personal.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla_personal.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla_personal.setMinimumHeight(260)
        self.tabla_personal.doubleClicked.connect(self._editar_empleado)
        layout.addWidget(self.tabla_personal, stretch=1)

        botones = QHBoxLayout()
        botones.setSpacing(8)

        btn_nuevo = QPushButton("Nuevo empleado")
        btn_nuevo.setObjectName("accionPrimaria")
        btn_nuevo.clicked.connect(self._nuevo_empleado)

        btn_editar = QPushButton("Editar")
        btn_editar.setObjectName("accionSecundaria")
        btn_editar.clicked.connect(self._editar_empleado)

        btn_password = QPushButton("Cambiar contraseña")
        btn_password.setObjectName("accionSecundaria")
        btn_password.clicked.connect(self._cambiar_password)

        self.btn_activar = QPushButton("Activar / Desactivar")
        self.btn_activar.setObjectName("accionSecundaria")
        self.btn_activar.clicked.connect(self._alternar_activo)

        for boton in (btn_nuevo, btn_editar, btn_password, self.btn_activar):
            boton.setCursor(Qt.PointingHandCursor)
            boton.setFixedHeight(36)
            botones.addWidget(boton)
        botones.addStretch()
        layout.addLayout(botones)

        return pagina

    def _empleado_seleccionado(self):
        fila = self.tabla_personal.currentRow()
        if fila < 0:
            return None
        item = self.tabla_personal.item(fila, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _nuevo_empleado(self):
        dialogo = DialogoEmpleado(self.autenticacion_service, self.usuario_actual, parent=self)
        if dialogo.exec() == QDialog.DialogCode.Accepted:
            self._cargar_personal()

    def _editar_empleado(self, *_):
        empleado = self._empleado_seleccionado()
        if not empleado:
            QMessageBox.information(self, "Seleccione un empleado",
                                    "Elija primero un empleado de la lista.")
            return
        dialogo = DialogoEmpleado(self.autenticacion_service, self.usuario_actual,
                                  empleado=empleado, parent=self)
        if dialogo.exec() == QDialog.DialogCode.Accepted:
            self._cargar_personal()

    def _cambiar_password(self):
        empleado = self._empleado_seleccionado()
        if not empleado:
            QMessageBox.information(self, "Seleccione un empleado",
                                    "Elija primero un empleado de la lista.")
            return

        # Se reutiliza el diálogo de edición solo para capturar la contraseña.
        password, aceptado = QInputDialog.getText(
            self, "Cambiar contraseña",
            f"Nueva contraseña para {empleado.get('nombre_completo')}:",
            QLineEdit.EchoMode.Password,
        )
        if not aceptado:
            return

        exito, mensaje = self.autenticacion_service.cambiar_password(
            self.usuario_actual, empleado.get("id"), password
        )
        self._avisar(exito, mensaje, "Contraseña actualizada")

    def _alternar_activo(self):
        empleado = self._empleado_seleccionado()
        if not empleado:
            QMessageBox.information(self, "Seleccione un empleado",
                                    "Elija primero un empleado de la lista.")
            return

        activo_actual = bool(empleado.get("activo"))
        accion = "deshabilitar" if activo_actual else "habilitar"
        respuesta = QMessageBox.question(
            self,
            "Confirmar",
            f"¿Desea {accion} a {empleado.get('nombre_completo')}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if respuesta != QMessageBox.StandardButton.Yes:
            return

        exito, mensaje = self.autenticacion_service.cambiar_activo(
            self.usuario_actual, empleado.get("id"), not activo_actual
        )
        if exito:
            self._cargar_personal()
        self._avisar(exito, mensaje, "Estado actualizado")

    # ------------------------------------------------------------------
    # CARGA DE DATOS
    # ------------------------------------------------------------------
    def refrescar(self):
        """Recarga las tres pestañas desde la base de datos."""
        self._cargar_parametros()
        self._cargar_personal()

    def _cargar_parametros(self):
        parametros = self.reserva_service.obtener_parametros()

        self.spn_anticipacion.setValue(parametros["dias_anticipacion_max"])
        self.spn_noches_min.setValue(parametros["noches_minimas"])
        self.spn_noches_max.setValue(parametros["noches_maximas"])

    def _cargar_personal(self):
        personal = self.autenticacion_service.listar_personal(self.usuario_actual)
        self.tabla_personal.setRowCount(0)

        for empleado in personal:
            fila = self.tabla_personal.rowCount()
            self.tabla_personal.insertRow(fila)

            activo = bool(empleado.get("activo"))
            valores = [
                empleado.get("username", ""),
                empleado.get("nombre_completo", ""),
                "Administrador" if empleado.get("rol") == "administrador" else "Recepcionista",
                empleado.get("numero_identificacion", ""),
                empleado.get("correo_electronico", ""),
                "Activo" if activo else "Inactivo",
            ]
            for columna, valor in enumerate(valores):
                item = QTableWidgetItem(str(valor))
                if columna == 0:
                    # La fila lleva el empleado completo para las acciones.
                    item.setData(Qt.ItemDataRole.UserRole, empleado)
                self.tabla_personal.setItem(fila, columna, item)

    def _avisar(self, exito, mensaje, titulo):
        caja = QMessageBox.information if exito else QMessageBox.warning
        caja(self, titulo, mensaje)
