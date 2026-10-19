# DATABASE/usuario_dao.py
from DATABASE.conexion import ConexionBD
from mysql.connector import Error, errorcode
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

    # ------------------------------------------------------------------
    # GESTION DE PERSONAL (solo administradores)
    # ------------------------------------------------------------------
    @staticmethod
    def _mensaje_duplicado(err):
        """Traduce el error de MySQL a un mensaje entendible para cada campo."""
        detalle = str(err)
        if "username" in detalle:
            return "Ya existe un usuario con ese nombre."
        if "numero_identificacion" in detalle:
            return "Ya existe un empleado con esa identificación."
        if "correo_electronico" in detalle:
            return "Ya existe un empleado con ese correo."
        if "numero_telefono" in detalle:
            return "Ya existe un empleado con ese teléfono."
        return "Ya existe un empleado con esos datos."

    def listar_personal(self):
        """Devuelve todo el personal del hotel, activo e inactivo."""
        conexion = self.db.conectar()
        if not conexion:
            return []

        sql = """
            SELECT id, username, rol, nombre_completo, numero_identificacion,
                correo_electronico, numero_telefono, activo, creado_en
            FROM Usuario
            ORDER BY activo DESC, rol, nombre_completo
        """

        try:
            cursor = conexion.cursor(dictionary=True)
            cursor.execute(sql)
            personal = cursor.fetchall()
            cursor.close()
            return personal
        except Error as err:
            print(f"Error al obtener el personal: {err}")
            return []
        finally:
            self.db.desconectar()

    def crear_usuario(self, username, passwrd_hash, rol, nombre_completo,
                      numero_identificacion, correo_electronico, numero_telefono):
        """Da de alta a un empleado nuevo."""
        conexion = self.db.conectar()
        if not conexion:
            return False, "No hay conexión con el servidor de base de datos."

        sql = """
            INSERT INTO Usuario
            (username, passwrd, rol, nombre_completo, numero_identificacion,
            correo_electronico, numero_telefono, activo)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 1)
        """
        valores = (username, passwrd_hash, rol, nombre_completo,
                   numero_identificacion, correo_electronico, numero_telefono)

        try:
            cursor = conexion.cursor()
            cursor.execute(sql, valores)
            conexion.commit()
            cursor.close()
            return True, "Empleado registrado correctamente."
        except Error as err:
            conexion.rollback()
            if err.errno == errorcode.ER_DUP_ENTRY:
                return False, self._mensaje_duplicado(err)
            print(f"Error al crear el empleado: {err}")
            return False, "No se pudo registrar el empleado."
        finally:
            self.db.desconectar()

    def _existe(self, cursor, id):
        cursor.execute("SELECT 1 FROM Usuario WHERE id = %s", (id,))
        return cursor.fetchone() is not None

    def actualizar_usuario(self, id, rol, nombre_completo, numero_identificacion,
                           correo_electronico, numero_telefono):
        """Actualiza los datos de un empleado (sin tocar su contraseña)."""
        conexion = self.db.conectar()
        if not conexion:
            return False, "No hay conexión con el servidor de base de datos."

        sql = """
            UPDATE Usuario
            SET rol = %s, nombre_completo = %s, numero_identificacion = %s,
                correo_electronico = %s, numero_telefono = %s
            WHERE id = %s
        """
        valores = (rol, nombre_completo, numero_identificacion,
                   correo_electronico, numero_telefono, id)

        try:
            cursor = conexion.cursor()
            cursor.execute(sql, valores)
            # rowcount no sirve aquí: guardar sin cambios da 0 aunque el empleado
            # exista, así que la existencia se comprueba aparte.
            if not self._existe(cursor, id):
                cursor.close()
                return False, "No se encontró el empleado para actualizar."
            conexion.commit()
            cursor.close()
            return True, "Empleado actualizado correctamente."
        except Error as err:
            conexion.rollback()
            if err.errno == errorcode.ER_DUP_ENTRY:
                return False, self._mensaje_duplicado(err)
            print(f"Error al actualizar el empleado: {err}")
            return False, "No se pudo actualizar el empleado."
        finally:
            self.db.desconectar()

    def cambiar_password(self, id, passwrd_hash):
        """Restablece la contraseña de un empleado."""
        conexion = self.db.conectar()
        if not conexion:
            return False, "No hay conexión con el servidor de base de datos."

        try:
            cursor = conexion.cursor()
            cursor.execute(
                "UPDATE Usuario SET passwrd = %s WHERE id = %s",
                (passwrd_hash, id),
            )
            if not self._existe(cursor, id):
                cursor.close()
                return False, "No se encontró el empleado."
            conexion.commit()
            cursor.close()
            return True, "Contraseña actualizada correctamente."
        except Error as err:
            conexion.rollback()
            print(f"Error al cambiar la contraseña: {err}")
            return False, "No se pudo cambiar la contraseña."
        finally:
            self.db.desconectar()

    def cambiar_activo(self, id, activo):
        """Habilita o deshabilita a un empleado (no lo borra, conserva su historial)."""
        conexion = self.db.conectar()
        if not conexion:
            return False, "No hay conexión con el servidor de base de datos."

        try:
            cursor = conexion.cursor()
            cursor.execute(
                "UPDATE Usuario SET activo = %s WHERE id = %s",
                (1 if activo else 0, id),
            )
            if not self._existe(cursor, id):
                cursor.close()
                return False, "No se encontró el empleado."
            conexion.commit()
            cursor.close()
            return True, "Empleado habilitado." if activo else "Empleado deshabilitado."
        except Error as err:
            conexion.rollback()
            print(f"Error al cambiar el estado del empleado: {err}")
            return False, "No se pudo cambiar el estado del empleado."
        finally:
            self.db.desconectar()
