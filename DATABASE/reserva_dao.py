# DATABASE/reserva_dao.py
from datetime import date
from decimal import Decimal
from DATABASE.conexion import ConexionBD
from mysql.connector import Error

class ReservaDAO:
    """DAO de la tabla Reserva: estancias, ingresos y salidas."""

    # Prioridad de cada estado en las mesas de trabajo de recepción. El número
    # es el orden en que se muestran: lo que el personal todavía tiene que
    # atender va primero y lo que ya se cerró va al final. «Pendiente» y
    # «Confirmada» comparten prioridad porque las dos esperan al huésped.
    PRIORIDAD_ESTADOS = {
        "Pendiente": 1,
        "Confirmada": 1,
        "Iniciada": 2,
        "Cancelada": 3,
        "Finalizada": 4,
    }

    def __init__(self):
        self.db = ConexionBD()

    def _orden_prioridad(self):
        """Arma el ORDER BY que impone la jerarquía de estados en MySQL.

        Se construye con un CASE porque el campo `estado` es un ENUM guardado
        como texto: MySQL los ordena por orden alfabético («Cancelada» antes que
        «Confirmada» de la entrada), no por el orden en que le interesa al hotel.
        """
        casos = " ".join(
            f"WHEN '{estado}' THEN {prioridad}"
            for estado, prioridad in self.PRIORIDAD_ESTADOS.items()
        )
        # El 99 es para cualquier estado que se agregue en el futuro: queda al
        # final de la mesa en vez de intercalarse en medio de los conocidos.
        return f"CASE r.estado {casos} ELSE 99 END"

    def registrar_reserva(
        self,
        cliente,
        identificacion,
        contacto,
        correo,
        noches,
        fecha_entrada,
        fecha_salida,
        metodo_pago,
        empleado_id,
        habitacion_id,
        ingreso_inmediato=False,
    ):
        """Registra una estancia y calcula el total en el servidor.

        Si `ingreso_inmediato` es verdadero, el huésped se aloja en el momento y
        la estancia nace ya «Iniciada» (la habitación queda ocupada). En caso
        contrario queda «Pendiente» hasta su fecha de entrada.
        """
        conexion = self.db.conectar()
        if not conexion:
            return False, "No hay conexión con el servidor de base de datos."

        try:
            cursor = conexion.cursor(dictionary=True)

            # Bloquea la habitación para serializar los intentos de reserva sobre la misma.
            cursor.execute(
                "SELECT precio, mantenimiento FROM registro_habitacion WHERE id = %s FOR UPDATE",
                (habitacion_id,),
            )
            habitacion = cursor.fetchone()
            if not habitacion:
                cursor.close()
                return False, "La habitación seleccionada no existe."
            if habitacion["mantenimiento"]:
                cursor.close()
                return False, "La habitación está en mantenimiento y no admite reservas."

            # Un huésped ya alojado mantiene la habitación tomada hasta que se
            # registre su salida, así que se consulta aparte para poder
            # explicarlo con precisión.
            cursor.execute(
                """
                SELECT id
                FROM Reserva
                WHERE habitacion_id = %s
                AND estado = 'Iniciada'
                AND fecha_entrada <= %s
                AND fecha_salida >= %s
                LIMIT 1
                """,
                (habitacion_id, fecha_entrada, fecha_entrada),
            )
            if cursor.fetchone():
                cursor.close()
                return False, (
                    "La habitación sigue ocupada por un huésped que aún no "
                    "registra su salida."
                )

            cursor.execute(
                """
                SELECT id
                FROM Reserva
                WHERE habitacion_id = %s
                AND estado IN ('Pendiente', 'Confirmada')
                AND fecha_entrada < %s
                AND fecha_salida > %s
                LIMIT 1
                """,
                (habitacion_id, fecha_salida, fecha_entrada),
            )
            if cursor.fetchone():
                cursor.close()
                return False, "La habitación ya tiene una reserva activa para esas fechas."

            total = (Decimal(str(habitacion["precio"])) * int(noches)).quantize(Decimal("0.01"))

            # El hospedaje inmediato ocupa la habitación desde el primer momento.
            estado_inicial = "Iniciada" if ingreso_inmediato else "Pendiente"
            checkin_empleado_id = empleado_id if ingreso_inmediato else None

            cursor.execute(
                """
                INSERT INTO Reserva
                (cliente, identificacion, contacto, correo_electronico, noches,
                fecha_entrada, fecha_salida, metodo_pago, total, estado,
                habitacion_id, empleado_id, checkin_empleado_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (cliente, identificacion, contacto, correo, int(noches), fecha_entrada,
                 fecha_salida, metodo_pago, total, estado_inicial,
                 habitacion_id, empleado_id, checkin_empleado_id),
            )
            conexion.commit()
            nuevo_id = cursor.lastrowid
            cursor.close()
            return True, {"id": nuevo_id, "total": total}
        except Error as err:
            conexion.rollback()
            print(f"Error al registrar la reserva: {err}")
            return False, "No se pudo registrar la reserva."
        finally:
            self.db.desconectar()

    def registrar_checkin(self, reserva_id, empleado_id):
        """Registra el ingreso: la habitación pasa a estar ocupada."""
        conexion = self.db.conectar()
        if not conexion:
            return False, "No hay conexión con el servidor de base de datos."

        try:
            cursor = conexion.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT r.id, r.habitacion_id, r.fecha_entrada, r.estado, h.no_habitacion, h.mantenimiento
                FROM Reserva r
                JOIN registro_habitacion h ON h.id = r.habitacion_id
                WHERE r.id = %s
                FOR UPDATE
                """,
                (reserva_id,),
            )
            reserva = cursor.fetchone()
            if not reserva:
                cursor.close()
                return False, "La reserva no existe."
            if reserva["estado"] not in ("Pendiente", "Confirmada"):
                cursor.close()
                return False, f"La reserva ya está en estado «{reserva['estado']}»."
            if reserva["mantenimiento"]:
                cursor.close()
                return False, f"La habitación {reserva['no_habitacion']} está en mantenimiento."
            if reserva["fecha_entrada"] > date.today():
                cursor.close()
                return False, "La fecha de entrada de la reserva aún no llega."

            cursor.execute(
                """
                SELECT id FROM Reserva
                WHERE habitacion_id = %s
                AND id <> %s
                AND estado = 'Iniciada'
                AND fecha_entrada <= CURDATE()
                LIMIT 1
                """,
                (reserva["habitacion_id"], reserva_id),
            )
            ocupada = cursor.fetchone()
            if ocupada:
                cursor.close()
                return False, f"La habitación {reserva['no_habitacion']} ya está ocupada."

            cursor.execute(
                "UPDATE Reserva SET estado = 'Iniciada', checkin_empleado_id = %s WHERE id = %s",
                (empleado_id, reserva_id),
            )
            conexion.commit()
            cursor.close()
            return True, f"Ingreso registrado para la habitación {reserva['no_habitacion']}."
        except Error as err:
            conexion.rollback()
            print(f"Error al registrar el ingreso: {err}")
            return False, "No se pudo registrar el ingreso."
        finally:
            self.db.desconectar()

    def registrar_salida(self, reserva_id, empleado_id):
        """Cierra la estancia: la habitación vuelve a estar disponible."""
        conexion = self.db.conectar()
        if not conexion:
            return False, "No hay conexión con el servidor de base de datos."

        try:
            cursor = conexion.cursor()
            cursor.execute(
                """
                UPDATE Reserva
                SET estado = 'Finalizada', salida_empleado_id = %s
                WHERE id = %s AND estado = 'Iniciada'
                """,
                (empleado_id, reserva_id),
            )
            conexion.commit()
            afectadas = cursor.rowcount
            cursor.close()
            if afectadas == 0:
                return False, "No hay una estancia iniciada para esa reserva."
            return True, "Salida registrada correctamente."
        except Error as err:
            conexion.rollback()
            print(f"Error al registrar la salida: {err}")
            return False, "No se pudo registrar la salida."
        finally:
            self.db.desconectar()

    def cancelar_reserva(self, reserva_id, empleado_id):
        """Libera las fechas de una reserva que aún no inició la estancia."""
        conexion = self.db.conectar()
        if not conexion:
            return False, "No hay conexión con el servidor de base de datos."

        try:
            cursor = conexion.cursor()
            cursor.execute(
                """
                UPDATE Reserva
                SET estado = 'Cancelada', salida_empleado_id = %s
                WHERE id = %s AND estado IN ('Pendiente', 'Confirmada')
                """,
                (empleado_id, reserva_id),
            )
            conexion.commit()
            afectadas = cursor.rowcount
            cursor.close()
            if afectadas == 0:
                return False, "Solo se pueden cancelar reservas pendientes o confirmadas."
            return True, "Reserva cancelada correctamente."
        except Error as err:
            conexion.rollback()
            print(f"Error al cancelar la reserva: {err}")
            return False, "No se pudo cancelar la reserva."
        finally:
            self.db.desconectar()

    def obtener_llegadas(self, fecha):
        """Reservas pendientes de ingreso: las que entran hoy o de días anteriores.

        Incluye la estancia del propio día que sigue sin registrar: si no, el
        huésped desaparecería de todas las mesas sin que nadie lo aloje.
        """
        return self._listar(
            """
            AND r.estado IN ('Pendiente', 'Confirmada')
            AND r.fecha_entrada <= %s
            AND r.fecha_salida >= %s
            """,
            fecha, fecha,
        )

    def obtener_salidas(self, fecha):
        """Estancias que deben abandonar el hotel en la fecha indicada."""
        return self._listar(
            """
            AND r.estado = 'Iniciada'
            AND r.fecha_salida = %s
            """,
            fecha,
        )

    def obtener_en_casa(self, fecha):
        """Huéspedes que ya registraron el ingreso y siguen dentro.

        La condición es exactamente la misma con la que el catálogo marca una
        habitación como «Ocupado» (`Iniciada` cuya entrada ya llegó), así que
        esta mesa y el catálogo no pueden discrepar: quien figura aquí tiene la
        habitación tomada.

        No se filtra por la fecha de salida a propósito: el huésped sigue
        ocupando la habitación hasta que se registre su salida, y así también
        aparece quien se quedó más días de lo previsto.
        """
        return self._listar(
            """
            AND r.estado = 'Iniciada'
            AND r.fecha_entrada <= %s
            """,
            fecha,
        )

    def obtener_todas(self):
        """Reservas de cualquier fecha y cualquier estado, incluidas las canceladas.

        Es el listado completo del hotel. Antes la interfaz solo consultaba las
        llegadas del día, así que una reserva para dentro de un mes no aparecía
        en ninguna parte del sistema y parecía no existir.

        El orden jerárquico por estado lo impone la propia consulta, de modo que
        quien llama siempre recibe la mesa igual y ordenada sin tener que
        reacomodar los datos en Python.
        """
        return self._listar("", incluir_canceladas=True)

    def obtener_por_habitacion(self, habitacion_id):
        """Historial de reservas de una habitación para ver fechas ya comprometidas."""
        return self._listar(
            "AND r.habitacion_id = %s",
            habitacion_id,
        )

    def _listar(self, filtro, *valores, incluir_canceladas=False):
        """Consulta base del panel de recepción: reservas unidas al catálogo.

        Por defecto se esconden las canceladas, porque las mesas de trabajo son
        del día. El listado histórico las necesita, de ahí el interruptor.

        Todas las listas salen con el mismo orden: primero por la prioridad del
        estado y después por fecha de entrada ascendente, para que a igualdad de
        estado se vea primero la reserva que entra antes.
        """
        conexion = self.db.conectar()
        if not conexion:
            return []

        # `filtro` llega con su propio "AND"; la condición base es la primera
        # del WHERE, así que no lo lleva para no formar "WHERE AND ...".
        base = "" if incluir_canceladas else "r.estado <> 'Cancelada'"
        condiciones = " ".join(parte for parte in (base, filtro) if parte)

        sql = f"""
            SELECT r.id, r.cliente, r.identificacion, r.contacto, r.correo_electronico,
                r.noches, r.fecha_entrada, r.fecha_salida, r.metodo_pago, r.total,
                r.estado, r.habitacion_id, r.empleado_id, r.creado_en,
                h.nombre AS habitacion_nombre, h.no_habitacion AS habitacion_numero,
                e.nombre_completo AS empleado_nombre,
                s.nombre_completo AS checkin_empleado,
                f.nombre_completo AS salida_empleado
            FROM Reserva r
            JOIN registro_habitacion h ON h.id = r.habitacion_id
            JOIN Usuario e ON e.id = r.empleado_id
            LEFT JOIN Usuario s ON s.id = r.checkin_empleado_id
            LEFT JOIN Usuario f ON f.id = r.salida_empleado_id
            WHERE {condiciones or "1 = 1"}
            ORDER BY {self._orden_prioridad()}, r.fecha_entrada, h.no_habitacion, r.id
        """

        try:
            cursor = conexion.cursor(dictionary=True)
            cursor.execute(sql, valores)
            reservas = cursor.fetchall()
            cursor.close()
            return reservas
        except Error as err:
            print(f"Error al obtener las reservas: {err}")
            return []
        finally:
            self.db.desconectar()
