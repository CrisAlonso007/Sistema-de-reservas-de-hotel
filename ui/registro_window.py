# ui/registro_window.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QTabWidget, QMessageBox, QComboBox
)
from PySide6.QtCore import Qt, Signal

class RegistroUsuario(QWidget):
    # Emitimos un diccionario con el nombre de usuario y su rol ('admin' o 'user')
    login_exitoso = Signal(dict)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Registro e Inicio de Sesión - Sistema de Reservas")
        self.setFixedSize(360, 460)

        # Usuarios de prueba en memoria (simulando la base de datos)
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

    def _crear_tab_login(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 20, 15, 20)

        lbl_titulo = QLabel("LOGIN")
        lbl_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = lbl_titulo.font()
        font.setPointSize(16)
        font.setBold(True)
        lbl_titulo.setFont(font)

        self.txt_login_user = QLineEdit()
        self.txt_login_user.setPlaceholderText("Username")

        self.txt_login_pass = QLineEdit()
        self.txt_login_pass.setPlaceholderText("Password")
        self.txt_login_pass.setEchoMode(QLineEdit.EchoMode.Password)

        btn_signin = QPushButton("SIGN IN")
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

        lbl_titulo = QLabel("REGISTER")
        lbl_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = lbl_titulo.font()
        font.setPointSize(16)
        font.setBold(True)
        lbl_titulo.setFont(font)

        self.txt_reg_user = QLineEdit()
        self.txt_reg_user.setPlaceholderText("Username")

        self.txt_reg_email = QLineEdit()
        self.txt_reg_email.setPlaceholderText("Email")

        self.txt_reg_pass = QLineEdit()
        self.txt_reg_pass.setPlaceholderText("Password")
        self.txt_reg_pass.setEchoMode(QLineEdit.EchoMode.Password)

        # Combo box para seleccionar el tipo de cuenta
        self.cmb_rol = QComboBox()
        self.cmb_rol.addItems(["user", "Administrador"])

        btn_register = QPushButton("CREATE ACCOUNT")
        btn_register.setFixedHeight(35)
        btn_register.clicked.connect(self._procesar_registro)

        layout.addWidget(lbl_titulo)
        layout.addWidget(self.txt_reg_user)
        layout.addWidget(self.txt_reg_email)
        layout.addWidget(self.txt_reg_pass)
        layout.addWidget(QLabel("Tipo de cuenta:"))
        layout.addWidget(self.cmb_rol)
        layout.addSpacing(5)
        layout.addWidget(btn_register)
        layout.addStretch()

        return widget

    def _procesar_login(self):
        usuario = self.txt_login_user.text().strip()
        password = self.txt_login_pass.text().strip()

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
        email = self.txt_reg_email.text().strip()
        password = self.txt_reg_pass.text().strip()
        rol = "admin" if self.cmb_rol.currentText() == "Administrador" else "user"

        if not (usuario and email and password):
            QMessageBox.warning(self, "Error", "Todos los campos son obligatorios.")
            return

        if usuario in self.usuarios_db:
            QMessageBox.warning(self, "Error", "El usuario ya existe.")
            return

        # Guardar nuevo usuario
        self.usuarios_db[usuario] = {"pass": password, "rol": rol}
        QMessageBox.information(self, "Éxito", "Cuenta creada correctamente. Ya puedes iniciar sesión.")
        self.tabs.setCurrentIndex(0)