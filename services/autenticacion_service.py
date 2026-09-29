# services/autenticacion_service.py
from DATABASE.usuario_dao import UsuarioDAO
from utils.validaciones import es_usuario_valido, es_password_valido

class AutenticacionService:
    """Servicio de acceso exclusivo del personal del hotel."""

    def __init__(self):
        self.dao = UsuarioDAO()

    def iniciar_sesion(self, username, passwrd) -> tuple[bool, str]:
        """Valida credenciales de recepcionista o administrador."""
        usuario = str(username or "").strip()
        password = str(passwrd or "")

        if not es_usuario_valido(usuario) or not es_password_valido(password):
            return False, "Ingresa un usuario válido y una contraseña de al menos 4 caracteres."

        return self.dao.autenticar_personal(usuario, password)
