# ui/registro_window.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QTabWidget, QMessageBox, QComboBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtCore import QRegularExpression
from utils.validaciones import es_usuario_valido, es_password_valido, es_identificacion_valida, es_texto_valido
from utils.stylesheets import ESTILO_CAMPO_VALIDO, ESTILO_CAMPO_INVALIDO
from DATABASE.registro import RegistroDAO

class RegistroUsuario(QWidget):
    login_exitoso = Signal(dict)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Registro e Inicio de Sesión - Sistema de Reservas")
        self.setFixedSize(420, 650)

        self.registro_dao = RegistroDAO()

        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(20, 20, 20, 20)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._crear_tab_login(), "Iniciar Sesión")
        self.tabs.addTab(self._crear_tab_registro(), "Crear Cuenta")

        layout_principal.addWidget(self.tabs)

    @staticmethod
    def _aplicar_estado_campo(widget, es_valido):
        widget.setStyleSheet(ESTILO_CAMPO_VALIDO if es_valido else ESTILO_CAMPO_INVALIDO)

    def _crear_tab_login(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 20, 15, 20)

        lbl_titulo = QLabel("INICIAR SESION")
        lbl_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = lbl_titulo.font()
        font.setPointSize(16)
        font.setBold(True)
        lbl_titulo.setFont(font)

        self.txt_login_user = QLineEdit()
        self.txt_login_user.setPlaceholderText("Nombre de usuario")
        self.txt_login_user.setValidator(QRegularExpressionValidator(QRegularExpression(r"[A-Za-z0-9_]{0,20}")))
        self.txt_login_user.textChanged.connect(self._validar_login_user)

        self.txt_login_pass = QLineEdit()
        self.txt_login_pass.setPlaceholderText("Contraseña")
        self.txt_login_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_login_pass.setValidator(QRegularExpressionValidator(QRegularExpression(r"[^\n]{0,30}")))
        self.txt_login_pass.textChanged.connect(self._validar_login_pass)

        btn_signin = QPushButton("Enter")
        btn_signin.setFixedHeight(35)
        btn_signin.clicked.connect(self._procesar_login)

        layout.addWidget(lbl_titulo)
        layout.addSpacing(10)
        layout.addWidget(self.txt_login_user)
        layout.addWidget(self.txt_login_pass)
        layout.addSpacing(10)
        layout.addWidget(btn_signin)
        layout.addStretch()

        return widget

    def _crear_tab_registro(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 15, 15, 15)

        lbl_titulo = QLabel("CREAR CUENTA")
        lbl_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = lbl_titulo.font()
        font.setPointSize(16)
        font.setBold(True)
        lbl_titulo.setFont(font)

        self.txt_reg_user = QLineEdit()
        self.txt_reg_user.setPlaceholderText("Nombre de usuario")
        self.txt_reg_user.setValidator(QRegularExpressionValidator(QRegularExpression(r"[A-Za-z0-9_]{0,20}")))
        self.txt_reg_user.textChanged.connect(self._validar_registro_user)

        self.txt_reg_pass = QLineEdit()
        self.txt_reg_pass.setPlaceholderText("contraseña")
        self.txt_reg_pass.setEchoMode(QLineEdit.EchoMode.Password)

        self.txt_reg_pass.setValidator(QRegularExpressionValidator(QRegularExpression(r"[^\n]{0,30}")))
        self.txt_reg_pass.textChanged.connect(self._validar_registro_pass)

        self.txt_nombre_completo = QLineEdit()
        self.txt_nombre_completo.setPlaceholderText("Nombre completo")
        self.txt_nombre_completo.textChanged.connect(self._validar_registro_datos)

        self.txt_identificacion = QLineEdit()
        self.txt_identificacion.setPlaceholderText("Cédula o pasaporte")
        self.txt_identificacion.textChanged.connect(self._validar_registro_datos)

        self.txt_contacto = QLineEdit()
        self.txt_contacto.setPlaceholderText("Teléfono o correo")
        self.txt_contacto.textChanged.connect(self._validar_registro_datos)

        # Combo box para seleccionar el tipo de cuenta
        self.cmb_rol = QComboBox()
        self.cmb_rol.addItems(["user", "Administrador"])

        btn_register = QPushButton("Enter")
        btn_register.setFixedHeight(35)
        btn_register.clicked.connect(self._procesar_registro)

        layout.addWidget(lbl_titulo)
        layout.addWidget(self.txt_reg_user)
        layout.addWidget(self.txt_reg_pass)
        layout.addWidget(self.txt_nombre_completo)
        layout.addWidget(self.txt_identificacion)
        layout.addWidget(self.txt_contacto)
        layout.addWidget(QLabel("Tipo de cuenta:"))
        layout.addWidget(self.cmb_rol)
        layout.addSpacing(5)
        layout.addWidget(btn_register)
        layout.addStretch()

        return widget

    def _aplicar_estilo_campo(self, campo, valido: bool):
        campo.setStyleSheet(ESTILO_CAMPO_VALIDO if valido else ESTILO_CAMPO_INVALIDO)

    def _validar_login_user(self):
        self._aplicar_estilo_campo(self.txt_login_user, es_usuario_valido(self.txt_login_user.text()))

    def _validar_login_pass(self):
        self._aplicar_estilo_campo(self.txt_login_pass, es_password_valido(self.txt_login_pass.text()))

    def _validar_registro_user(self):
        self._aplicar_estilo_campo(self.txt_reg_user, es_usuario_valido(self.txt_reg_user.text()))

    def _validar_registro_pass(self):
        self._aplicar_estilo_campo(self.txt_reg_pass, es_password_valido(self.txt_reg_pass.text()))

    def _validar_registro_datos(self):
        self._aplicar_estilo_campo(
            self.txt_nombre_completo,
            es_texto_valido(self.txt_nombre_completo.text(), longitud_minima=2)
        )
        self._aplicar_estilo_campo(
            self.txt_identificacion,
            es_identificacion_valida(self.txt_identificacion.text())
        )
        self._aplicar_estilo_campo(
            self.txt_contacto,
            es_texto_valido(self.txt_contacto.text(), longitud_minima=5)
        )

    def _procesar_login(self):
        usuario = self.txt_login_user.text().strip()
        password = self.txt_login_pass.text().strip()

        if not (es_usuario_valido(usuario) and es_password_valido(password)):
            QMessageBox.warning(self, "Error", "Ingresa un usuario válido y una contraseña de al menos 4 caracteres.")
            return
        if not usuario or not password:
            QMessageBox.warning(self, "Error", "Por favor ingresa usuario y contraseña.")
            return

        exito, resultado = self.registro_dao.autenticar_usuario(usuario, password)
        if exito:
            datos_usuario = resultado
            self.login_exitoso.emit(datos_usuario)
            self.close()
        else:
            QMessageBox.critical(self, "Error", resultado)

    def _procesar_registro(self):
        usuario = self.txt_reg_user.text().strip()
        password = self.txt_reg_pass.text().strip()
        nombre_completo = self.txt_nombre_completo.text().strip()
        identificacion = self.txt_identificacion.text().strip()
        contacto = self.txt_contacto.text().strip()
        rol = "administrador" if self.cmb_rol.currentText() == "Administrador" else "user"

        if not (
            es_usuario_valido(usuario)
            and es_password_valido(password)
            and es_texto_valido(nombre_completo, longitud_minima=2)
            and es_identificacion_valida(identificacion)
            and es_texto_valido(contacto, longitud_minima=5)
        ):
            QMessageBox.warning(self, "Error", "Completa correctamente todos los datos de la cuenta.")
            return

        exito, mensaje = self.registro_dao.registro_usuario(
            usuario, password, rol, nombre_completo, identificacion, contacto
        )
        if not exito:
            QMessageBox.warning(self, "Error", mensaje)
            return

        QMessageBox.information(self, "Éxito", "Cuenta creada correctamente. Ya puedes iniciar sesión.")
        self.tabs.setCurrentIndex(0)