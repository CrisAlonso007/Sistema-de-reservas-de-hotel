# ui/login_window.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtCore import QRegularExpression
from services.autenticacion_service import AutenticacionService
from utils.stylesheets import ESTILO_LOGIN
from utils.validaciones import es_password_valido, es_usuario_valido

class LoginPersonal(QWidget):
    """Acceso exclusivo del personal del hotel. No existe registro público de usuarios."""

    login_exitoso = Signal(dict)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Acceso al Sistema - Recepción")
        self.setFixedSize(430, 500)
        self.setStyleSheet(ESTILO_LOGIN)

        self.autenticacion_service = AutenticacionService()

        self.setObjectName("loginRaiz")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout_raiz = QVBoxLayout(self)
        layout_raiz.setContentsMargins(0, 0, 0, 0)
        layout_raiz.addStretch()

        self.tarjeta = QFrame()
        self.tarjeta.setObjectName("loginTarjeta")
        layout_raiz.addWidget(self.tarjeta, alignment=Qt.AlignmentFlag.AlignHCenter)

        layout = QVBoxLayout(self.tarjeta)
        layout.setContentsMargins(40, 36, 40, 36)
        layout.setSpacing(14)

        lbl_titulo = QLabel("Sistema de Reservas")
        lbl_titulo.setObjectName("loginTitulo")
        lbl_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_titulo)

        lbl_subtitulo = QLabel("Acceso interno · Personal de Recepción")
        lbl_subtitulo.setObjectName("loginSubtitulo")
        lbl_subtitulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_subtitulo)

        layout.addSpacing(10)

        lbl_usuario = QLabel("Usuario")
        layout.addWidget(lbl_usuario)

        self.txt_usuario = QLineEdit()
        self.txt_usuario.setPlaceholderText("usuario del hotel")
        self.txt_usuario.setFixedHeight(36)
        self.txt_usuario.setMaxLength(20)
        self.txt_usuario.setValidator(
            QRegularExpressionValidator(QRegularExpression(r"[A-Za-z0-9_]*"))
        )
        layout.addWidget(self.txt_usuario)

        lbl_password = QLabel("Contraseña")
        layout.addWidget(lbl_password)

        self.txt_password = QLineEdit()
        self.txt_password.setPlaceholderText("contraseña")
        self.txt_password.setFixedHeight(36)
        self.txt_password.setMaxLength(30)
        self.txt_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_password.returnPressed.connect(self._procesar_login)
        layout.addWidget(self.txt_password)

        # El foco encadenado se conecta cuando ambos campos ya existen.
        self.txt_usuario.returnPressed.connect(self.txt_password.setFocus)

        self.lbl_estado = QLabel("")
        self.lbl_estado.setObjectName("loginAviso")
        self.lbl_estado.setWordWrap(True)
        self.lbl_estado.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_estado)

        btn_ingresar = QPushButton("Ingresar al Sistema")
        btn_ingresar.setObjectName("loginBoton")
        btn_ingresar.setFixedHeight(42)
        btn_ingresar.setCursor(Qt.PointingHandCursor)
        btn_ingresar.clicked.connect(self._procesar_login)
        layout.addWidget(btn_ingresar)

        layout.addStretch()

        layout_raiz.addStretch()
        self.limpiar_campos()
        self.txt_usuario.setFocus()

    def _procesar_login(self):
        usuario = self.txt_usuario.text().strip()
        password = self.txt_password.text()

        if not (es_usuario_valido(usuario) and es_password_valido(password)):
            self.lbl_estado.setText("Ingresa un usuario válido y una contraseña de al menos 4 caracteres.")
            return

        exito, resultado = self.autenticacion_service.iniciar_sesion(usuario, password)
        if not exito:
            self.lbl_estado.setText(str(resultado))
            self.txt_password.clear()
            self.txt_password.setFocus()
            return

        self.limpiar_campos()
        self.login_exitoso.emit(resultado)

    def limpiar_campos(self):
        """Deja el formulario sin residuos de la sesión anterior."""
        self.txt_usuario.clear()
        self.txt_password.clear()
        self.lbl_estado.clear()
        self.lbl_estado.setText("")
