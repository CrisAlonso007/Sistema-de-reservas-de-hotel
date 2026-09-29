# main.py
import sys
from PySide6.QtWidgets import QApplication
from services.autenticacion_service import AutenticacionService
from services.habitacion_service import HabitacionService
from services.reserva_service import ReservaService
from ui.login_window import LoginPersonal
from ui.main_window import VentanaPrincipal

class AppController:
    """Orquesta el acceso del personal y el ciclo de vida de la ventana principal."""

    def __init__(self):
        self.app = QApplication(sys.argv)

        self.autenticacion_service = AutenticacionService()
        self.servicio_habitaciones = HabitacionService()
        self.servicio_reservas = ReservaService()

        self.login_window = LoginPersonal()
        self.login_window.login_exitoso.connect(self.mostrar_ventana_principal)

        self.main_window = None

        self.app.aboutToQuit.connect(self.cerrar_recursos)

    def iniciar(self):
        self.login_window.show()
        sys.exit(self.app.exec())

    def mostrar_ventana_principal(self, usuario_actual: dict):
        if self.main_window:
            self.main_window.close()
            self.main_window.deleteLater()

        self.main_window = VentanaPrincipal(
            usuario_actual=usuario_actual,
            habitacion_service=self.servicio_habitaciones,
            reserva_service=self.servicio_reservas,
        )
        self.main_window.sesion_cerrada.connect(self.volver_al_login)
        self.main_window.show()

    def volver_al_login(self):
        """Destruye la sesión anterior antes de volver a la pantalla de acceso."""
        if self.main_window:
            self.main_window.close()
            self.main_window.deleteLater()
            self.main_window = None

        self.login_window.limpiar_campos()
        self.login_window.show()
        self.login_window.activateWindow()
        self.login_window.txt_usuario.setFocus()

    def cerrar_recursos(self):
        if self.main_window:
            self.main_window.close()
            self.main_window = None

if __name__ == "__main__":
    controller = AppController()
    controller.iniciar()
