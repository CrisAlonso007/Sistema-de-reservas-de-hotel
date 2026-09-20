from DATABASE.conexion import ConexionBD
from mysql.connector import Error, errorcode

class RegistroDAO:
    """Clase DAO para gestionar la persistencia en MySQL."""

    @staticmethod
    def _normalizar_tipo_habitacion(tipo):
        valor = str(tipo or "Simple").strip()
        equivalencias = {
            "Presidencial": "Presencial",
            "Presencial": "Presencial",
        }
        return equivalencias.get(valor, valor)

    def __init__(self):
        self.db = ConexionBD()

    def autenticar_usuario(self, username, passwrd):
        conexion = self.db.conectar()
        if not conexion:
            return False, "No hay conexión con el servidor de base de datos."

        sql = """
            SELECT id, username, rol, nombre_completo, identificacion, contacto
            FROM Usuario
            WHERE username = %s AND passwrd = %s
        """

        try:
            cursor = conexion.cursor(dictionary=True)
            cursor.execute(sql, (username, passwrd))
            usuario = cursor.fetchone()
            cursor.close()

            if not usuario:
                return False, "Usuario o contraseña incorrectos."

            telefono = usuario.get("telefono") or usuario.get("contacto") or ""
            correo = usuario.get("correo") or usuario.get("email") or usuario.get("contacto") or ""

            return True, {
                "id": usuario["id"],
                "nombre": usuario["username"],
                "rol": "admin" if usuario["rol"] == "administrador" else usuario["rol"],
                "nombre_completo": usuario["nombre_completo"],
                "identificacion": usuario["identificacion"],
                "contacto": usuario.get("contacto") or telefono,
                "telefono": telefono,
                "correo": correo,
            }
        except Error as err:
            return False, f"Error al autenticar el usuario: {err}"
        finally:
            self.db.desconectar()

    def registro_usuario(self, username, passwrd, rol, nombre_completo, identificacion, contacto):
        conexion = self.db.conectar()
        if not conexion:
            return False, "No hay conexión con el servidor de base de datos."
        
        sql = """
            INSERT INTO Usuario
            (username, passwrd, rol, nombre_completo, identificacion, contacto)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        valores = (username, passwrd, rol, nombre_completo, identificacion, contacto)

        try:
            cursor = conexion.cursor()
            cursor.execute(sql, valores)
            conexion.commit()
            nuevo_id = cursor.lastrowid
            cursor.close()
            return True, f"Usuario registrado con éxito ID: {nuevo_id}"
        except Error as err:
            conexion.rollback()
            if err.errno == errorcode.ER_DUP_ENTRY:
                return False, "El usuario o la identificación ya están registrados en el sistema."
            return False, f"Error imprevisto al registrar: {err}"
        finally:
            self.db.desconectar()

    def realizar_reserva(
        self,
        cliente,
        identificacion,
        contacto,
        noches,
        fecha_entrada,
        fecha_salida,
        metodo_pago,
        total,
        usuario_id,
        habitacion_id,
    ):
        conexion = self.db.conectar()
        if not conexion:
            return False, "No hay conexión con el servidor de base de datos."
        
        sql = """
            INSERT INTO Reserva
            (cliente, identificacion, contacto, noches, fecha_entrada, fecha_salida,
             metodo_pago, total, usuario_id, habitacion_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        valores = (
            cliente, identificacion, contacto, noches, fecha_entrada, fecha_salida,
            metodo_pago, total, usuario_id, habitacion_id
        )

        try:
            cursor = conexion.cursor()
            cursor.execute(sql, valores)
            conexion.commit()
            nuevo_id = cursor.lastrowid
            cursor.close()
            return True, f"Reserva realizada con éxito ID: {nuevo_id}"
        except Error as err:
            conexion.rollback()
            if err.errno == errorcode.ER_DUP_ENTRY:
                return False, "La reserva ya está registrada."
            return False, f"Error imprevisto al registrar: {err}"
        finally:
            self.db.desconectar()

    def registrar_habitacion(self, nombre, no_habitacion, tipo, precio, capacidad, descripcion):
        conexion = self.db.conectar()
        if not conexion:
            return False, "No hay conexión con el servidor de base de datos."

        tipo = self._normalizar_tipo_habitacion(tipo)
        numero = int(no_habitacion)

        sql = """
            INSERT INTO registro_habitacion
            (id, nombre, no_habitacion, tipo, precio, capacidad, descripcion)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        try:
            cursor = conexion.cursor()
            cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 AS siguiente_id FROM registro_habitacion")
            siguiente_id = cursor.fetchone()[0]
            cursor.close()

            cursor = conexion.cursor()
            cursor.execute(sql, (siguiente_id, nombre, numero, tipo, precio, capacidad, descripcion))
            conexion.commit()
            cursor.close()
            return True, f"Habitación registrada con éxito ID: {siguiente_id}"
        except Error as err:
            conexion.rollback()
            if err.errno == errorcode.ER_DUP_ENTRY:
                return False, "La habitación ya está registrada en el sistema."
            return False, f"Error imprevisto al registrar: {err}"
        finally:
            self.db.desconectar()

    def actualizar_habitacion(self, id=None, nombre=None, no_habitacion=None, tipo=None, precio=None, capacidad=None, descripcion=None):
        conexion = self.db.conectar()
        if not conexion:
            return False, "No hay conexión con el servidor de base de datos."

        if id is None and no_habitacion is None:
            return False, "No se indicó qué habitación actualizar."

        tipo = self._normalizar_tipo_habitacion(tipo)

        if no_habitacion is None and id is not None:
            try:
                cursor = conexion.cursor(dictionary=True)
                cursor.execute("SELECT no_habitacion FROM registro_habitacion WHERE id = %s", (id,))
                resultado = cursor.fetchone()
                cursor.close()
                if not resultado:
                    return False, "No se encontró la habitación para actualizar."
                no_habitacion = resultado["no_habitacion"]
            except Error as err:
                return False, f"Error al buscar la habitación: {err}"

        sql = """
            UPDATE registro_habitacion
            SET nombre = %s,
                no_habitacion = %s,
                tipo = %s,
                precio = %s,
                capacidad = %s,
                descripcion = %s
            WHERE id = %s
        """
        valores = (nombre, int(no_habitacion), tipo, precio, capacidad, descripcion, id)

        if id is None:
            sql = """
                UPDATE registro_habitacion
                SET nombre = %s,
                    no_habitacion = %s,
                    tipo = %s,
                    precio = %s,
                    capacidad = %s,
                    descripcion = %s
                WHERE no_habitacion = %s
            """
            valores = (nombre, int(no_habitacion), tipo, precio, capacidad, descripcion, int(no_habitacion))

        try:
            cursor = conexion.cursor()
            cursor.execute(sql, valores)
            conexion.commit()
            afectadas = cursor.rowcount
            cursor.close()
            if afectadas == 0:
                return False, "No se encontró la habitación para actualizar."
            return True, "Habitación actualizada correctamente."
        except Error as err:
            conexion.rollback()
            return False, f"Error al actualizar la habitación: {err}"
        finally:
            self.db.desconectar()

    def eliminar_habitacion(self, id=None, no_habitacion=None):
        conexion = self.db.conectar()
        if not conexion:
            return False, "No hay conexión con el servidor de base de datos."

        if id is None and no_habitacion is None:
            return False, "No se indicó qué habitación eliminar."

        sql = "DELETE FROM registro_habitacion WHERE id = %s"
        valores = (id,)

        if id is None:
            sql = "DELETE FROM registro_habitacion WHERE no_habitacion = %s"
            valores = (int(no_habitacion),)

        try:
            cursor = conexion.cursor()
            cursor.execute(sql, valores)
            conexion.commit()
            afectadas = cursor.rowcount
            cursor.close()
            if afectadas == 0:
                return False, "No se encontró la habitación para eliminar."
            return True, "Habitación eliminada correctamente."
        except Error as err:
            conexion.rollback()
            return False, f"Error al eliminar la habitación: {err}"
        finally:
            self.db.desconectar()

    def obtener_habitaciones(self):
        conexion = self.db.conectar()
        if not conexion:
            return []

        sql = "SELECT id, nombre, no_habitacion AS numero, tipo, precio, capacidad, descripcion FROM registro_habitacion"
        
        try:
            cursor = conexion.cursor(dictionary=True)
            cursor.execute(sql)
            habitaciones = cursor.fetchall()
            cursor.close()
            return habitaciones
        except Error as err:
            print(f"Error al obtener habitaciones: {err}")
            return []
        finally:
            self.db.desconectar()