# main.py
import sys
from PySide6.QtWidgets import QApplication
from ui.registro_window import RegistroUsuario
from ui.main_window import VentanaPrincipal

class AppController:
    def __init__(self):
        self.app = QApplication(sys.argv)
        # Instanciamos la ventana de registro/login una sola vez para mantener los datos en memoria
        self.login_window = RegistroUsuario()
        self.main_window = None
        
        # Conectamos la señal de login
        self.login_window.login_exitoso.connect(self.mostrar_ventana_principal)

    def iniciar(self):
        self.login_window.show()
        sys.exit(self.app.exec())

    def mostrar_ventana_principal(self, usuario_actual: dict):
        self.main_window = VentanaPrincipal(usuario_actual=usuario_actual)
        
        # Si la VentanaPrincipal cierra sesión, reconectamos para volver al login
        self.main_window.btn_usuario.menu().actions()[0].triggered.connect(self.volver_al_login)
        self.main_window.show()

    def volver_al_login(self):
        if self.main_window:
            self.main_window.close()
        
        # Limpiamos los campos de texto
        self.login_window.txt_login_user.clear()
        self.login_window.txt_login_pass.clear()
        
        # Volvemos a mostrar la ventana de login existente (conserva usuarios registrados)
        self.login_window.show()

if __name__ == "__main__":
    controller = AppController()
    controller.iniciar()