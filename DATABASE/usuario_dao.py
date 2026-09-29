# DATABASE/usuario_dao.py
from DATABASE.conexion import ConexionBD
from mysql.connector import Error
from utils.seguridad import verificar_password

class UsuarioDAO:
    """DAO de la tabla Usuario (personal del hotel: recepcionistas y administradores)."""

    def __init__(self):
        self.db = ConexionBD()

    def autenticar_personal(self, username, passwrd):
        """Valida las credenciales del personal y retorna su sesión."""
        conexion = self.db.conectar()
        if not conexion:
            return False, "No hay conexión con el servidor de base de datos."

        sql = """
            SELECT id, username, passwrd, rol, nombre_completo,
            numero_identificacion, correo_electronico, numero_telefono
            FROM Usuario
            WHERE username = %s AND activo = 1
        """

        try:
            cursor = conexion.cursor(dictionary=True)
            cursor.execute(sql, (username,))
            usuario = cursor.fetchone()
            cursor.close()

            if not usuario or not verificar_password(passwrd, usuario["passwrd"]):
                return False, "Usuario o contraseña incorrectos."

            return True, {
                "id": usuario["id"],
                "nombre": usuario["username"],
                "rol": usuario["rol"],
                "nombre_completo": usuario["nombre_completo"],
                "identificacion": usuario["numero_identificacion"],
                "contacto": usuario["numero_telefono"],
                "correo": usuario["correo_electronico"],
            }
        except Error as err:
            print(f"Error al autenticar al personal: {err}")
            return False, "No se pudo validar la sesión. Intente nuevamente."
        finally:
            self.db.desconectar()
