# ui/login_window.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFrame,
    QDialog, QFormLayout, QMessageBox,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtCore import QRegularExpression
from services.autenticacion_service import AutenticacionService
from utils.stylesheets import ESTILO_LOGIN, ESTILO_PANEL
from utils.validaciones import es_password_valido, es_usuario_valido, MAX_TELEFONO

class LoginPersonal(QWidget):
    """Acceso del personal del hotel, con opción de crear una cuenta de recepción."""

    login_exitoso = Signal(dict)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Acceso al Sistema - Recepción")
        self.setFixedSize(1000, 600)
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

        lbl_titulo = QLabel("Inicio de Sesión")
        lbl_titulo.setObjectName("loginTitulo")
        lbl_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_titulo)

        lbl_subtitulo = QLabel("Sistema de gestión de reservas de hotel para el personal autorizado")
        lbl_subtitulo.setObjectName("loginSubtitulo")
        lbl_subtitulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_subtitulo)

        layout.addSpacing(10)

        lbl_usuario = QLabel("Usuario")
        layout.addWidget(lbl_usuario)
        self.txt_usuario = QLineEdit()
        self.txt_usuario.setPlaceholderText("ingrese su nombre de usuario")
        self.txt_usuario.setFixedHeight(36)
        self.txt_usuario.setMaxLength(20)
        self.txt_usuario.setValidator(
            QRegularExpressionValidator(QRegularExpression(r"[A-Za-z0-9_]*"))
        )
        layout.addWidget(self.txt_usuario)

        lbl_password = QLabel("Contraseña")
        layout.addWidget(lbl_password)
        self.txt_password = QLineEdit()
        self.txt_password.setPlaceholderText("ingrese su contraseña")
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

        btn_ingresar = QPushButton("Ingresar")
        btn_ingresar.setObjectName("loginBoton")
        btn_ingresar.setFixedHeight(42)
        btn_ingresar.setCursor(Qt.PointingHandCursor)
        btn_ingresar.clicked.connect(self._procesar_login)
        layout.addWidget(btn_ingresar)

        btn_registro = QPushButton("Agregar empleado")
        btn_registro.setObjectName("loginEnlace")
        btn_registro.setFlat(True)
        btn_registro.setCursor(Qt.PointingHandCursor)
        btn_registro.clicked.connect(self._abrir_registro)
        layout.addWidget(btn_registro, alignment=Qt.AlignmentFlag.AlignCenter)

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

    def _abrir_registro(self):
        """Abre el autorregistro y deja el usuario listo para iniciar sesión."""
        dialogo = DialogoRegistro(self.autenticacion_service, self)
        if dialogo.exec() == QDialog.DialogCode.Accepted and dialogo.usuario_creado:
            self.limpiar_campos()
            self.txt_usuario.setText(dialogo.usuario_creado)
            self.txt_password.setFocus()

    def limpiar_campos(self):
        """Deja el formulario sin residuos de la sesión anterior."""
        self.txt_usuario.clear()
        self.txt_password.clear()
        self.lbl_estado.clear()
        self.lbl_estado.setText("")


class DialogoRegistro(QDialog):
    """Crea una cuenta de recepción desde la pantalla de acceso.

    El rol no se elige: el autorregistro siempre otorga el rol de
    recepcionista, para que nadie pueda darse de alta como administrador.
    """

    def __init__(self, autenticacion_service, parent=None):
        super().__init__(parent)
        self.service = autenticacion_service
        self.usuario_creado = None

        self.setWindowTitle("Crear cuenta")
        self.setModal(True)
        self.setObjectName("panelRaiz")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(ESTILO_PANEL)
        self.setMinimumWidth(430)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        lbl_titulo = QLabel("Crear cuenta")
        lbl_titulo.setObjectName("panelTitulo")
        layout.addWidget(lbl_titulo)

        lbl_subtitulo = QLabel("La cuenta nueva se crea con el rol de recepcionista.")
        lbl_subtitulo.setObjectName("panelSubtitulo")
        layout.addWidget(lbl_subtitulo)

        formulario = QFormLayout()
        formulario.setSpacing(8)

        self.txt_usuario = QLineEdit()
        self.txt_usuario.setMaxLength(20)
        self.txt_usuario.setPlaceholderText("usuario (3-20 letras, números o _)")

        self.txt_password = QLineEdit()
        self.txt_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_password.setMaxLength(30)
        self.txt_password.setPlaceholderText("Mínimo 4 caracteres")

        self.txt_confirmar = QLineEdit()
        self.txt_confirmar.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_confirmar.setMaxLength(30)
        self.txt_confirmar.setPlaceholderText("Repita la contraseña")

        self.txt_nombre = QLineEdit()
        self.txt_identificacion = QLineEdit()
        self.txt_correo = QLineEdit()
        self.txt_telefono = QLineEdit()
        self.txt_telefono.setMaxLength(MAX_TELEFONO)

        formulario.addRow("Usuario:", self.txt_usuario)
        formulario.addRow("Contraseña:", self.txt_password)
        formulario.addRow("Confirmar contraseña:", self.txt_confirmar)
        formulario.addRow("Rol:", QLabel("Recepcionista"))
        formulario.addRow("Nombre completo:", self.txt_nombre)
        formulario.addRow("Identificación:", self.txt_identificacion)
        formulario.addRow("Correo:", self.txt_correo)
        formulario.addRow("Teléfono:", self.txt_telefono)
        layout.addLayout(formulario)

        botones = QHBoxLayout()
        botones.addStretch()
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setObjectName("accionSecundaria")
        btn_cancelar.clicked.connect(self.reject)
        btn_crear = QPushButton("Crear cuenta")
        btn_crear.setObjectName("accionPrimaria")
        btn_crear.clicked.connect(self._guardar)
        botones.addWidget(btn_cancelar)
        botones.addWidget(btn_crear)
        layout.addLayout(botones)

    def _guardar(self):
        exito, mensaje = self.service.registrar_cuenta(
            username=self.txt_usuario.text(),
            password=self.txt_password.text(),
            confirmacion=self.txt_confirmar.text(),
            nombre_completo=self.txt_nombre.text(),
            numero_identificacion=self.txt_identificacion.text(),
            correo_electronico=self.txt_correo.text(),
            numero_telefono=self.txt_telefono.text(),
        )
        if not exito:
            QMessageBox.warning(self, "No se pudo crear la cuenta", mensaje)
            return

        self.usuario_creado = self.txt_usuario.text().strip()
        QMessageBox.information(
            self, "Cuenta creada", f"{mensaje}\n\nYa puede iniciar sesión."
        ) 
        self.accept()
