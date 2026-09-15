from DATABASE.conexion import ConexionBD
from mysql.connector import Error, errorcode

class RegistroDAO:
    """Clase DAO para gestionar la persistencia en MySQL."""

    def __init__(self):
        self.db = ConexionBD()

    def registro_usuario(self, username, passwrd, rol):
        conexion = self.db.conectar()
        if not conexion:
            return False, "No hay conexión con el servidor de base de datos."
        
        sql = "INSERT INTO Usuario (username, passwrd, rol) VALUES (%s, %s, %s)"
        valores = (username, passwrd, rol)

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
                return False, "El usuario ya está registrado en el sistema."
            return False, f"Error imprevisto al registrar: {err}"
        finally:
            self.db.desconectar()

    def realizar_reserva(self, cliente, identificacion, noches):
        conexion = self.db.conectar()
        if not conexion:
            return False, "No hay conexión con el servidor de base de datos."
        
        sql = "INSERT INTO Reserva (id, cliente, identificacion, noches) VALUES (NULL, %s, %s, %s)"
        valores = (cliente, identificacion, noches)

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
                return False, "El cliente ya está registrado en el sistema."
            return False, f"Error imprevisto al registrar: {err}"
        finally:
            self.db.desconectar()

    def registrar_habitacion(self, nombre, no_habitacion, tipo, precio, capacidad, descripcion):
        conexion = self.db.conectar()
        if not conexion:
            return False, "No hay conexión con el servidor de base de datos."

        sql = """
            INSERT INTO registro_habitacion
            (nombre, no_habitacion, tipo, precio, capacidad, descripcion)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        valores = (nombre, no_habitacion, tipo, precio, capacidad, descripcion)

        try:
            cursor = conexion.cursor()
            cursor.execute(sql, valores)
            conexion.commit()
            nuevo_id = cursor.lastrowid
            cursor.close()
            return True, f"Habitación registrada con éxito ID: {nuevo_id}"
        except Error as err:
            conexion.rollback()
            if err.errno == errorcode.ER_DUP_ENTRY:
                return False, "La habitación ya está registrada en el sistema."
            return False, f"Error imprevisto al registrar: {err}"
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