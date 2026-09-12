# ui/registro_window.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QTabWidget, QMessageBox, QComboBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtCore import QRegularExpression
from utils.validaciones import es_usuario_valido, es_password_valido
from utils.stylesheets import ESTILO_CAMPO_VALIDO, ESTILO_CAMPO_INVALIDO

class RegistroUsuario(QWidget):
    login_exitoso = Signal(dict)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Registro e Inicio de Sesión - Sistema de Reservas")
        self.setFixedSize(360, 460)

        self.usuarios_db = {
            "admin": {"pass": "1234", "rol": "admin"},
            "user": {"pass": "1234", "rol": "user"}
        }

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

        # Combo box para seleccionar el tipo de cuenta
        self.cmb_rol = QComboBox()
        self.cmb_rol.addItems(["user", "Administrador"])

        btn_register = QPushButton("Enter")
        btn_register.setFixedHeight(35)
        btn_register.clicked.connect(self._procesar_registro)

        layout.addWidget(lbl_titulo)
        layout.addWidget(self.txt_reg_user)
        layout.addWidget(self.txt_reg_pass)
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

    def _procesar_login(self):
        usuario = self.txt_login_user.text().strip()
        password = self.txt_login_pass.text().strip()

        if not (es_usuario_valido(usuario) and es_password_valido(password)):
            QMessageBox.warning(self, "Error", "Ingresa un usuario válido y una contraseña de al menos 4 caracteres.")
        if not usuario or not password:
            QMessageBox.warning(self, "Error", "Por favor ingresa usuario y contraseña.")
            return

        # Validación de credenciales
        if usuario in self.usuarios_db and self.usuarios_db[usuario]["pass"] == password:
            datos_usuario = {
                "nombre": usuario,
                "rol": self.usuarios_db[usuario]["rol"]
            }
            self.login_exitoso.emit(datos_usuario)
            self.close()
        else:
            QMessageBox.critical(self, "Error", "Usuario o contraseña incorrectos.")

    def _procesar_registro(self):
        usuario = self.txt_reg_user.text().strip()
        password = self.txt_reg_pass.text().strip()
        rol = "admin" if self.cmb_rol.currentText() == "Administrador" else "user"

        if not (es_usuario_valido(usuario) and es_password_valido(password)):
            QMessageBox.warning(self, "Error", "El usuario debe tener entre 3 y 20 caracteres y la contraseña al menos 4 caracteres.")
            return

        if usuario in self.usuarios_db:
            QMessageBox.warning(self, "Error", "El usuario ya existe.")
            return

        # Guardar nuevo usuario
        self.usuarios_db[usuario] = {"pass": password, "rol": rol}
        QMessageBox.information(self, "Éxito", "Cuenta creada correctamente. Ya puedes iniciar sesión.")
        self.tabs.setCurrentIndex(0)