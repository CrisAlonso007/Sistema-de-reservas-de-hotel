# DATABASE/habitacion_dao.py
from DATABASE.conexion import ConexionBD
from mysql.connector import Error, errorcode

class HabitacionDAO:
    """DAO de la tabla registro_habitacion y del estado de ocupación derivado."""

    def __init__(self):
        self.db = ConexionBD()

    def registrar_habitacion(self, nombre, no_habitacion, tipo, precio, capacidad, descripcion, imagen=""):
        conexion = self.db.conectar()
        if not conexion:
            return False, "No hay conexión con el servidor de base de datos."

        sql = """
            INSERT INTO registro_habitacion
            (nombre, no_habitacion, tipo, precio, capacidad, descripcion, imagen)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        try:
            cursor = conexion.cursor()
            cursor.execute(sql, (nombre, int(no_habitacion), tipo, precio, int(capacidad), descripcion, imagen))
            conexion.commit()
            nuevo_id = cursor.lastrowid
            cursor.close()
            return True, f"Habitación registrada con éxito ID: {nuevo_id}"
        except Error as err:
            conexion.rollback()
            if err.errno == errorcode.ER_DUP_ENTRY:
                return False, f"Ya existe una habitación con el número {no_habitacion}."
            print(f"Error al registrar la habitación: {err}")
            return False, "No se pudo registrar la habitación."
        finally:
            self.db.desconectar()

    def actualizar_habitacion(self, id, nombre, no_habitacion, tipo, precio, capacidad, descripcion, imagen):
        conexion = self.db.conectar()
        if not conexion:
            return False, "No hay conexión con el servidor de base de datos."

        sql = """
            UPDATE registro_habitacion
            SET nombre = %s,
                no_habitacion = %s,
                tipo = %s,
                precio = %s,
                capacidad = %s,
                descripcion = %s,
                imagen = %s
            WHERE id = %s
        """
        valores = (nombre, int(no_habitacion), tipo, precio, int(capacidad), descripcion, imagen, id)

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
            if err.errno == errorcode.ER_DUP_ENTRY:
                return False, f"Ya existe una habitación con el número {no_habitacion}."
            print(f"Error al actualizar la habitación: {err}")
            return False, "No se pudo actualizar la habitación."
        finally:
            self.db.desconectar()

    def eliminar_habitacion(self, id):
        conexion = self.db.conectar()
        if not conexion:
            return False, "No hay conexión con el servidor de base de datos."

        try:
            cursor = conexion.cursor()
            cursor.execute("DELETE FROM registro_habitacion WHERE id = %s", (id,))
            conexion.commit()
            afectadas = cursor.rowcount
            cursor.close()
            if afectadas == 0:
                return False, "No se encontró la habitación para eliminar."
            return True, "Habitación eliminada correctamente."
        except Error as err:
            conexion.rollback()
            if err.errno == errorcode.ER_ROW_IS_REFERENCED_2:
                return False, "La habitación tiene reservas asociadas y no puede eliminarse."
            print(f"Error al eliminar la habitación: {err}")
            return False, "No se pudo eliminar la habitación."
        finally:
            self.db.desconectar()

    def alternar_mantenimiento(self, id):
        """Pone la habitación fuera de servicio o la devuelve a operación.

        Solo entra en mantenimiento una habitación sin reservas activas: sacar
        de servicio una habitación con una reserva pendiente o una estancia en
        curso dejaría esa reserva sin habitación. Salir de mantenimiento siempre
        está permitido.
        """
        conexion = self.db.conectar()
        if not conexion:
            return False, "No hay conexión con el servidor de base de datos."

        try:
            cursor = conexion.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT h.mantenimiento,
                    EXISTS (
                        SELECT 1 FROM Reserva r
                        WHERE r.habitacion_id = h.id
                        AND r.estado IN ('Pendiente', 'Iniciada')
                    ) AS reserva_activa
                FROM registro_habitacion h
                WHERE h.id = %s
                FOR UPDATE
                """,
                (id,),
            )
            fila = cursor.fetchone()
            if not fila:
                cursor.close()
                return False, "No se encontró la habitación."

            en_mantenimiento = bool(fila["mantenimiento"])
            if not en_mantenimiento and fila["reserva_activa"]:
                cursor.close()
                return False, (
                    "No se puede poner en mantenimiento: la habitación tiene una "
                    "reserva o estancia activa."
                )

            cursor.execute(
                "UPDATE registro_habitacion SET mantenimiento = 1 - mantenimiento WHERE id = %s",
                (id,),
            )
            conexion.commit()
            cursor.close()
            if en_mantenimiento:
                return True, "Habitación puesta en servicio."
            return True, "Habitación marcada en mantenimiento."
        except Error as err:
            conexion.rollback()
            print(f"Error al cambiar el estado de la habitación: {err}")
            return False, "No se pudo actualizar el estado de la habitación."
        finally:
            self.db.desconectar()

    def obtener_habitaciones(self):
        """Trae el catálogo con el estatus de ocupación calculado en tiempo real."""
        conexion = self.db.conectar()
        if not conexion:
            return []

        sql = """
            SELECT h.id, h.nombre, h.no_habitacion AS numero, h.tipo, h.precio,
                h.capacidad, h.descripcion, h.imagen, h.mantenimiento,
                CASE
                    WHEN h.mantenimiento = 1 THEN 'Mantenimiento'
                    WHEN EXISTS (
                        SELECT 1 FROM Reserva r
                        WHERE r.habitacion_id = h.id
                        AND r.estado = 'Iniciada'
                        AND r.fecha_entrada <= CURDATE()
                    ) THEN 'Ocupado'
                    WHEN EXISTS (
                        SELECT 1 FROM Reserva r
                        WHERE r.habitacion_id = h.id
                        AND r.estado = 'Pendiente'
                        AND r.fecha_entrada <= CURDATE()
                        AND r.fecha_salida >= CURDATE()
                    ) THEN 'Reservado'
                    ELSE 'Disponible'
                END AS estatus,
                EXISTS (
                    SELECT 1 FROM Reserva r
                    WHERE r.habitacion_id = h.id
                    AND r.estado IN ('Pendiente', 'Iniciada')
                ) AS reserva_activa
            FROM registro_habitacion h
            ORDER BY h.no_habitacion
        """

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

    def obtener_disponibles(self, fecha_entrada, fecha_salida):
        """Habitaciones libres para el tramo pedido, excluyendo las ocupadas.

        Usa la misma regla de solape que el registro de reservas para que la
        oferta de habitaciones y la validación de choque nunca discrepen:

        - Pendiente es una reserva: usa intervalos abiertos, así que una salida
          el mismo día que la siguiente entrada no choca.
        - Iniciada significa que el huésped ya está dentro. La habitación no se
          libera por calendario, sino cuando el recepcionista registra la
          salida, por lo que bloquea también el día de su salida.
        """
        conexion = self.db.conectar()
        if not conexion:
            return []

        sql = """
            SELECT h.id, h.nombre, h.no_habitacion AS numero, h.tipo, h.precio,
                h.capacidad, h.descripcion, h.imagen
            FROM registro_habitacion h
            WHERE h.mantenimiento = 0
            AND NOT EXISTS (
                SELECT 1 FROM Reserva r
                WHERE r.habitacion_id = h.id
                AND (
                    (
                        r.estado = 'Pendiente'
                        AND r.fecha_entrada < %s
                        AND r.fecha_salida > %s
                    )
                    OR
                    (
                        r.estado = 'Iniciada'
                        AND r.fecha_entrada < %s
                        AND r.fecha_salida >= %s
                    )
                )
            )
            ORDER BY h.no_habitacion
        """

        try:
            cursor = conexion.cursor(dictionary=True)
            cursor.execute(sql, (fecha_salida, fecha_entrada, fecha_salida, fecha_entrada))
            habitaciones = cursor.fetchall()
            cursor.close()
            return habitaciones
        except Error as err:
            print(f"Error al obtener habitaciones disponibles: {err}")
            return []
        finally:
            self.db.desconectar()

