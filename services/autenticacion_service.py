# services/autenticacion_service.py
from DATABASE.usuario_dao import UsuarioDAO
from utils.seguridad import (
    MENSAJE_SOLO_ADMIN,
    ROLES_VALIDOS,
    es_administrador,
    generar_hash,
    sesion_valida,
)
from utils.validaciones import (
    es_correo_valido,
    es_identificacion_valida,
    es_password_valido,
    es_usuario_valido,
    validar_nombre_completo,
    validar_telefono,
)

class AutenticacionService:
    """Servicio de acceso del personal y de gestión de la plantilla del hotel."""

    def __init__(self):
        self.dao = UsuarioDAO()

    # ------------------------------------------------------------------
    # ACCESO
    # ------------------------------------------------------------------
    def iniciar_sesion(self, username, passwrd) -> tuple[bool, str]:
        """Valida credenciales de recepcionista o administrador."""
        usuario = str(username or "").strip()
        password = str(passwrd or "")

        if not es_usuario_valido(usuario) or not es_password_valido(password):
            return False, "Ingresa un usuario válido y una contraseña de al menos 4 caracteres."

        return self.dao.autenticar_personal(usuario, password)

    # ------------------------------------------------------------------
    # GESTION DE PERSONAL (solo administradores)
    # ------------------------------------------------------------------
    def _solo_admin(self, usuario_actual) -> tuple[bool, str] | None:
        """Devuelve el rechazo si la sesión no es la de un administrador."""
        if not sesion_valida(usuario_actual):
            return False, "Debe iniciar sesión para administrar el personal."
        if not es_administrador(usuario_actual):
            return False, MENSAJE_SOLO_ADMIN
        return None

    def listar_personal(self, usuario_actual: dict) -> list[dict]:
        """Plantilla del hotel. Devuelve [] si quien consulta no es administrador."""
        if self._solo_admin(usuario_actual):
            return []
        return self.dao.listar_personal()

    def crear_personal(
        self,
        usuario_actual: dict,
        username,
        password,
        rol,
        nombre_completo,
        numero_identificacion,
        correo_electronico,
        numero_telefono,
    ) -> tuple[bool, str]:
        """Da de alta a un empleado nuevo."""
        rechazo = self._solo_admin(usuario_actual)
        if rechazo:
            return rechazo

        usuario = str(username or "").strip()
        password = str(password or "")

        if not es_usuario_valido(usuario):
            return False, "El nombre de usuario debe tener 3-20 letras, números o guion bajo."
        if not es_password_valido(password):
            return False, "La contraseña debe tener entre 4 y 30 caracteres, sin espacios."
        if rol not in ROLES_VALIDOS:
            return False, "El rol seleccionado no es válido."
        if not validar_nombre_completo(nombre_completo):
            return False, "El nombre completo no es válido."
        if not es_identificacion_valida(numero_identificacion):
            return False, "El número de identificación no es válido."
        if not es_correo_valido(correo_electronico):
            return False, "El correo electrónico no es válido."
        if not validar_telefono(numero_telefono):
            return False, "El número de teléfono no es válido."

        return self.dao.crear_usuario(
            username=usuario,
            passwrd_hash=generar_hash(password),
            rol=rol,
            nombre_completo=str(nombre_completo).strip(),
            numero_identificacion=str(numero_identificacion).strip(),
            correo_electronico=str(correo_electronico).strip(),
            numero_telefono=str(numero_telefono).strip(),
        )

    def actualizar_personal(
        self,
        usuario_actual: dict,
        empleado_id,
        rol,
        nombre_completo,
        numero_identificacion,
        correo_electronico,
        numero_telefono,
    ) -> tuple[bool, str]:
        """Actualiza los datos de un empleado."""
        rechazo = self._solo_admin(usuario_actual)
        if rechazo:
            return rechazo

        if empleado_id is None:
            return False, "Debe indicarse el empleado a editar."
        if rol not in ROLES_VALIDOS:
            return False, "El rol seleccionado no es válido."
        if not validar_nombre_completo(nombre_completo):
            return False, "El nombre completo no es válido."
        if not es_identificacion_valida(numero_identificacion):
            return False, "El número de identificación no es válido."
        if not es_correo_valido(correo_electronico):
            return False, "El correo electrónico no es válido."
        if not validar_telefono(numero_telefono):
            return False, "El número de teléfono no es válido."

        return self.dao.actualizar_usuario(
            id=empleado_id,
            rol=rol,
            nombre_completo=str(nombre_completo).strip(),
            numero_identificacion=str(numero_identificacion).strip(),
            correo_electronico=str(correo_electronico).strip(),
            numero_telefono=str(numero_telefono).strip(),
        )

    def cambiar_password(self, usuario_actual: dict, empleado_id, password) -> tuple[bool, str]:
        """Restablece la contraseña de un empleado."""
        rechazo = self._solo_admin(usuario_actual)
        if rechazo:
            return rechazo

        if empleado_id is None:
            return False, "Debe indicarse el empleado."
        if not es_password_valido(str(password or "")):
            return False, "La contraseña debe tener entre 4 y 30 caracteres, sin espacios."

        return self.dao.cambiar_password(empleado_id, generar_hash(str(password)))

    def cambiar_activo(self, usuario_actual: dict, empleado_id, activo) -> tuple[bool, str]:
        """Habilita o deshabilita a un empleado.

        Un administrador no puede deshabilitarse a sí mismo: se quedaría fuera
        del sistema sin nadie que lo reactive.
        """
        rechazo = self._solo_admin(usuario_actual)
        if rechazo:
            return rechazo

        if empleado_id is None:
            return False, "Debe indicarse el empleado."
        if not activo and empleado_id == usuario_actual.get("id"):
            return False, "No puede deshabilitar su propia cuenta."

        return self.dao.cambiar_activo(empleado_id, bool(activo))
