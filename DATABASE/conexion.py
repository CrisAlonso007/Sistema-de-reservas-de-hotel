import mysql.connector
from mysql.connector import Error

class ConexionBD:
    """Clase encargada de gestionar las conexiones a MySQL."""

    def __init__(self):
        self.host = "localhost"
        self.user = "root"
        self.password = "root"
        self.database = "db_sistema_reserva"
        self.port = 3306
        self.conexion = None

    def conectar(self):
        """Establece y retorna una conexión a la base de datos."""
        try:
            self.conexion = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                port=self.port
            )

            if self.conexion.is_connected():
                print("Conexión exitosa a la base de datos.")
                return self.conexion

        except Error as e:
            print(f"Error al conectar a MySQL: {e}")
            self.conexion = None
            return None

        return None

    def desconectar(self):
        """Cierra la conexión activa."""
        try:
            if self.conexion and self.conexion.is_connected():
                self.conexion.close()
        except Error as e:
            print(f"Error al cerrar la conexión: {e}")
        finally:
            self.conexion = None