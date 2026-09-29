# DATABASE/conexion.py
import os
import mysql.connector
from mysql.connector import Error

class ConexionBD:
    """Clase encargada de gestionar las conexiones a MySQL."""

    def __init__(self):
        self.host = os.getenv("DB_HOST", "localhost")
        self.user = os.getenv("DB_USER", "root")
        self.password = os.getenv("DB_PASSWORD", "root")
        self.database = os.getenv("DB_NAME", "db_sistema_reserva")
        self.port = int(os.getenv("DB_PORT", "3306"))
        self.conexion = None

    def conectar(self):
        """Establece y retorna una conexión a la base de datos."""
        if self.conexion and self.conexion.is_connected():
            return self.conexion

        try:
            self.conexion = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                port=self.port,
                charset="utf8mb4",
                collation="utf8mb4_unicode_ci",
                use_unicode=True,
                sql_mode="STRICT_TRANS_TABLES,NO_ENGINE_SUBSTITUTION"
            )

            if self.conexion.is_connected():
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
