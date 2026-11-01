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

    def actualizar_precio_por_tipo(self, tipo, precio):
        """Fija el precio por noche de todas las habitaciones de un mismo tipo.

        Es la herramienta de tarifas del administrador: en vez de editar la
        habitación una por una, ajusta de golpe la tarifa de un tipo completo.
        Devuelve cuántas habitaciones quedaron con el nuevo precio.
        """
        conexion = self.db.conectar()
        if not conexion:
            return False, "No hay conexión con el servidor de base de datos."

        try:
            cursor = conexion.cursor()
            # Se cuenta primero cuántas habitaciones hay del tipo: rowcount de un
            # UPDATE solo refleja las filas que cambiaron, así que fijar un precio
            # que ya estaba en todas devolvería 0 y parecería que no hay ninguna.
            cursor.execute(
                "SELECT COUNT(*) FROM registro_habitacion WHERE tipo = %s",
                (tipo,),
            )
            total = cursor.fetchone()[0]
            if total == 0:
                cursor.close()
                return False, f"No hay habitaciones del tipo «{tipo}» para actualizar."

            cursor.execute(
                "UPDATE registro_habitacion SET precio = %s WHERE tipo = %s",
                (precio, tipo),
            )
            conexion.commit()
            cursor.close()
            return True, f"Precio actualizado en {total} habitación(es) de tipo {tipo}."
        except Error as err:
            conexion.rollback()
            print(f"Error al actualizar el precio por tipo: {err}")
            return False, "No se pudo actualizar el precio."
        finally:
            self.db.desconectar()

    def alternar_mantenimiento(self, id, empleado_id=None):
        """Pone la habitación fuera de servicio o la devuelve a operación.

        No se puede sacar de servicio una habitación ocupada o reservada para
        hoy: se usa la misma regla que el estatus del catálogo, así que toda
        habitación que se vea "Disponible" puede pasar a mantenimiento. Las
        reservas antiguas o futuras no la bloquean. Salir de mantenimiento
        siempre está permitido.
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
                        AND (
                            (r.estado = 'Iniciada' AND r.fecha_entrada <= CURDATE())
                            OR (r.estado = 'Pendiente'
                                AND r.fecha_entrada <= CURDATE()
                                AND r.fecha_salida >= CURDATE())
                        )
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
                    "No se puede poner en mantenimiento: la habitación está "
                    "ocupada o reservada para hoy."
                )

            cursor.execute(
                "UPDATE registro_habitacion SET mantenimiento = 1 - mantenimiento WHERE id = %s",
                (id,),
            )
            if en_mantenimiento:
                cursor.execute(
                    """
                    UPDATE TareaHabitacion
                    SET estado = 'Completada', finalizada_en = NOW(),
                        finalizada_por = %s
                    WHERE habitacion_id = %s
                      AND tipo = 'Mantenimiento técnico'
                      AND estado = 'En proceso'
                    """,
                    (empleado_id, id),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO TareaHabitacion
                        (habitacion_id, tipo, turno, fecha_programada,
                         estado, iniciada_en, iniciada_por)
                    VALUES (%s, 'Mantenimiento técnico', 'Mantenimiento',
                            CURDATE(), 'En proceso', NOW(), %s)
                    """,
                    (id, empleado_id),
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
                    WHEN EXISTS (
                        SELECT 1 FROM TareaHabitacion t
                        WHERE t.habitacion_id = h.id
                          AND t.tipo = 'Limpieza de salida'
                          AND t.estado IN ('Pendiente', 'En proceso')
                    ) THEN 'Pendiente de limpieza'
                    ELSE 'Disponible'
                END AS estatus,
                EXISTS (
                    SELECT 1 FROM Reserva r
                    WHERE r.habitacion_id = h.id
                    AND (
                        (r.estado = 'Iniciada' AND r.fecha_entrada <= CURDATE())
                        OR (r.estado = 'Pendiente'
                            AND r.fecha_entrada <= CURDATE()
                            AND r.fecha_salida >= CURDATE())
                    )
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
            AND NOT EXISTS (
                SELECT 1 FROM TareaHabitacion t
                WHERE t.habitacion_id = h.id
                  AND t.tipo = 'Limpieza de salida'
                  AND t.estado IN ('Pendiente', 'En proceso')
                  AND t.fecha_programada < %s
                  AND DATE_ADD(t.fecha_programada, INTERVAL 1 DAY) > %s
            )
            ORDER BY h.no_habitacion
        """

        try:
            cursor = conexion.cursor(dictionary=True)
            cursor.execute(
                sql,
                (
                    fecha_salida, fecha_entrada, fecha_salida, fecha_entrada,
                    fecha_salida, fecha_entrada,
                ),
            )
            habitaciones = cursor.fetchall()
            cursor.close()
            return habitaciones
        except Error as err:
            print(f"Error al obtener habitaciones disponibles: {err}")
            return []
        finally:
            self.db.desconectar()

    def obtener_tareas_habitacion(self, fecha):
        """Genera los dos turnos diarios pendientes y devuelve el tablero de tareas."""
        conexion = self.db.conectar()
        if not conexion:
            return []

        try:
            cursor = conexion.cursor(dictionary=True)
            cursor.execute(
                """
                INSERT IGNORE INTO TareaHabitacion
                    (habitacion_id, reserva_id, tipo, turno, fecha_programada)
                SELECT r.habitacion_id, r.id, 'Limpieza diaria', turnos.turno, %s
                FROM Reserva r
                CROSS JOIN (
                    SELECT 'Mañana' AS turno
                    UNION ALL SELECT 'Tarde'
                ) turnos
                WHERE r.estado = 'Iniciada'
                  AND r.fecha_entrada <= %s
                  AND r.fecha_salida >= %s
                """,
                (fecha, fecha, fecha),
            )
            conexion.commit()
            cursor.execute(
                """
                SELECT t.id, t.habitacion_id, t.reserva_id, t.tipo, t.turno,
                    t.fecha_programada, t.estado, t.iniciada_en, t.finalizada_en,
                    h.no_habitacion AS habitacion_numero,
                    COALESCE(r.cliente, '—') AS cliente,
                    TIMESTAMPDIFF(
                        MINUTE, t.iniciada_en, COALESCE(t.finalizada_en, NOW())
                    ) AS duracion_minutos
                FROM TareaHabitacion t
                JOIN registro_habitacion h ON h.id = t.habitacion_id
                LEFT JOIN Reserva r ON r.id = t.reserva_id
                WHERE (
                    (t.fecha_programada = %s AND t.estado <> 'Cancelada')
                    OR (
                        t.tipo = 'Limpieza de salida'
                        AND t.estado IN ('Pendiente', 'En proceso')
                        AND t.fecha_programada < %s
                    )
                    OR (
                        t.tipo = 'Mantenimiento técnico'
                        AND t.estado = 'En proceso'
                    )
                )
                ORDER BY
                    CASE t.estado
                        WHEN 'En proceso' THEN 1
                        WHEN 'Pendiente' THEN 2
                        WHEN 'Completada' THEN 3
                        ELSE 4
                    END,
                    t.turno, h.no_habitacion, t.id
                """,
                (fecha, fecha),
            )
            tareas = cursor.fetchall()
            cursor.close()
            return tareas
        except Error as err:
            conexion.rollback()
            print(f"Error al obtener las tareas de habitación: {err}")
            return []
        finally:
            self.db.desconectar()

    def actualizar_tarea_habitacion(self, tarea_id, empleado_id, finalizar=False):
        """Inicia o completa una tarea y conserva su duración real."""
        conexion = self.db.conectar()
        if not conexion:
            return False, "No hay conexión con el servidor de base de datos."

        try:
            cursor = conexion.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT habitacion_id, tipo, estado
                FROM TareaHabitacion
                WHERE id = %s
                FOR UPDATE
                """,
                (tarea_id,),
            )
            tarea = cursor.fetchone()
            if not tarea:
                cursor.close()
                return False, "La tarea ya no existe."
            estado_esperado = "En proceso" if finalizar else "Pendiente"
            if tarea["estado"] != estado_esperado:
                cursor.close()
                return False, "La tarea cambió de estado. Actualice la lista."

            if finalizar:
                cursor.execute(
                    """
                    UPDATE TareaHabitacion
                    SET estado = 'Completada', finalizada_en = NOW(),
                        finalizada_por = %s
                    WHERE id = %s AND estado = 'En proceso'
                    """,
                    (empleado_id, tarea_id),
                )
                if tarea["tipo"] == "Mantenimiento técnico":
                    cursor.execute(
                        "UPDATE registro_habitacion SET mantenimiento = 0 WHERE id = %s",
                        (tarea["habitacion_id"],),
                    )
            else:
                cursor.execute(
                    """
                    UPDATE TareaHabitacion
                    SET estado = 'En proceso', iniciada_en = NOW(),
                        iniciada_por = %s
                    WHERE id = %s AND estado = 'Pendiente'
                    """,
                    (empleado_id, tarea_id),
                )

            conexion.commit()
            cursor.close()
            return True, "Tarea completada." if finalizar else "Tarea iniciada."
        except Error as err:
            conexion.rollback()
            print(f"Error al actualizar la tarea de habitación: {err}")
            return False, "No se pudo actualizar la tarea."
        finally:
            self.db.desconectar()

    def obtener_tarea_habitacion(self, tarea_id):
        conexion = self.db.conectar()
        if not conexion:
            return None

        try:
            cursor = conexion.cursor(dictionary=True)
            cursor.execute(
                "SELECT id, tipo, estado FROM TareaHabitacion WHERE id = %s",
                (tarea_id,),
            )
            tarea = cursor.fetchone()
            cursor.close()
            return tarea
        except Error as err:
            print(f"Error al consultar la tarea de habitación: {err}")
            return None
        finally:
            self.db.desconectar()
