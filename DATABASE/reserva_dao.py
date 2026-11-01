# DATABASE/reserva_dao.py
from datetime import date, datetime, time
from decimal import Decimal

from DATABASE.conexion import ConexionBD
from DATABASE.models import Configuracion, Habitacion, Reserva
from DATABASE.conexion_orm import SessionLocal
from mysql.connector import Error
from sqlalchemy import case, select
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import joinedload

class ReservaDAO:
    """DAO de la tabla Reserva: estancias, ingresos y salidas."""

    # Prioridad de cada estado en las mesas de trabajo de recepción. El número
    # es el orden en que se muestran: lo que el personal todavía tiene que
    # atender va primero y lo que ya se cerró va al final.
    PRIORIDAD_ESTADOS = {
        "Pendiente": 1,
        "Iniciada": 2,
        "No presentada": 3,
        "Cancelada": 4,
        "Finalizada": 5,
    }

    def __init__(self):
        self.db = ConexionBD()

    def _orden_prioridad(self):
        """Arma el ORDER BY que impone la jerarquía de estados en MySQL.

        Se construye con un CASE porque el campo `estado` es un ENUM guardado
        como texto: MySQL los ordena alfabéticamente, no por el orden en que le
        interesa al hotel.
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
        noches,
        fecha_entrada,
        fecha_salida,
        metodo_pago,
        empleado_id,
        habitacion_id,
        ingreso_inmediato=False,
        factor_temporada=1.0,
        descuento_porcentaje=0.0,
        numero_huespedes=1,
    ):
        """Registra una estancia y calcula el total en el servidor.

        Si `ingreso_inmediato` es verdadero, el huésped se aloja en el momento y
        la estancia nace ya «Iniciada» (la habitación queda ocupada). En caso
        contrario queda «Pendiente» hasta su fecha de entrada.

        `factor_temporada` y `descuento_porcentaje` los calcula el servicio a
        partir de los parámetros del hotel (temporada alta y descuento general)
        y aquí solo se aplican al total: precio/noche * noches * factor - descuento.
        """
        conexion = self.db.conectar()
        if not conexion:
            return False, "No hay conexión con el servidor de base de datos."

        try:
            cursor = conexion.cursor(dictionary=True)

            # Bloquea la habitación para serializar los intentos de reserva sobre la misma.
            cursor.execute(
                "SELECT precio, capacidad, mantenimiento "
                "FROM registro_habitacion WHERE id = %s FOR UPDATE",
                (habitacion_id,),
            )
            habitacion = cursor.fetchone()
            if not habitacion:
                cursor.close()
                return False, "La habitación seleccionada no existe."
            if habitacion["mantenimiento"]:
                cursor.close()
                return False, "La habitación está en mantenimiento y no admite reservas."
            if numero_huespedes < 1:
                cursor.close()
                return False, "Debe registrarse al menos un huésped."
            if numero_huespedes > habitacion["capacidad"]:
                cursor.close()
                return False, (
                    f"La habitación admite hasta {habitacion['capacidad']} "
                    f"huésped(es); no puede alojar a {numero_huespedes}."
                )

            # Una sola regla de solape para toda la aplicación: la reserva
            # «Pendiente» ocupa un tramo semiabierto [entrada, salida), y una
            # estancia «Iniciada» bloquea además el día de su salida, porque el
            # huésped sigue dentro hasta que registra el egreso.
            estado_choque = self._buscar_choque(cursor, habitacion_id, fecha_entrada, fecha_salida)
            if estado_choque == "Iniciada":
                cursor.close()
                return False, (
                    "La habitación sigue ocupada por un huésped que aún no "
                    "registra su salida."
                )
            if estado_choque is not None:
                cursor.close()
                if estado_choque == "Limpieza":
                    return False, (
                        "La habitación aún tiene pendiente una limpieza de salida "
                        "que coincide con esas fechas."
                    )
                return False, "La habitación ya tiene una reserva activa para esas fechas."

            total = self._calcular_total(
                habitacion["precio"], noches, factor_temporada, descuento_porcentaje
            )

            # El hospedaje inmediato ocupa la habitación desde el primer momento.
            estado_inicial = "Iniciada" if ingreso_inmediato else "Pendiente"
            checkin_empleado_id = empleado_id if ingreso_inmediato else None

            cursor.execute(
                """
                INSERT INTO Reserva
                (cliente, identificacion, contacto, numero_huespedes, noches,
                fecha_entrada, fecha_salida, metodo_pago, total, estado,
                habitacion_id, empleado_id, checkin_empleado_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (cliente, identificacion, contacto, numero_huespedes, int(noches),
                fecha_entrada, fecha_salida, metodo_pago, total, estado_inicial,
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

    def marcar_no_show(self, reserva_id, empleado_id, penalizacion_pct=30, moneda="NIO"):
        """Cierra como no presentada una reserva pasada y registra el reembolso."""
        conexion = self.db.conectar()
        if not conexion:
            return False, "No hay conexión con el servidor de base de datos."

        try:
            cursor = conexion.cursor(dictionary=True)
            cursor.execute(
                "SELECT estado, fecha_entrada, total, monto_pagado "
                "FROM Reserva WHERE id = %s FOR UPDATE",
                (reserva_id,),
            )
            reserva = cursor.fetchone()
            if not reserva:
                cursor.close()
                return False, "La reserva no existe."
            if reserva["estado"] != "Pendiente":
                cursor.close()
                return False, "Solo se puede marcar como no presentada una reserva pendiente."
            if reserva["fecha_entrada"] >= date.today():
                cursor.close()
                return False, "El no-show solo se registra después de la fecha de entrada."

            total = Decimal(str(reserva["total"]))
            pagado = Decimal(str(reserva["monto_pagado"]))
            porcentaje = Decimal(str(penalizacion_pct)) / Decimal("100")
            retenido = min((total * porcentaje).quantize(Decimal("0.01")), pagado)
            devolucion = max(pagado - retenido, Decimal("0.00"))
            if devolucion:
                self._registrar_devolucion(
                    cursor, reserva_id, empleado_id, devolucion,
                    "Reembolso por no presentación",
                )

            cursor.execute(
                """
                UPDATE Reserva
                SET estado = 'No presentada', salida_empleado_id = %s,
                    monto_pagado = monto_pagado - %s
                WHERE id = %s AND estado = 'Pendiente'
                """,
                (empleado_id, devolucion, reserva_id),
            )
            if cursor.rowcount != 1:
                conexion.rollback()
                cursor.close()
                return False, "La reserva cambió y no pudo marcarse como no presentada."
            conexion.commit()
            cursor.close()
            return True, (
                "Reserva marcada como no presentada. "
                f"Penalización retenida: {self._importe(retenido, moneda)}; "
                f"reembolso registrado: {self._importe(devolucion, moneda)}."
            )
        except Error as err:
            conexion.rollback()
            print(f"Error al marcar no-show: {err}")
            return False, "No se pudo marcar la reserva como no presentada."
        finally:
            self.db.desconectar()

    @staticmethod
    def _registrar_devolucion(cursor, reserva_id, empleado_id, monto, motivo):
        cursor.execute(
            """
            INSERT INTO Devolucion (reserva_id, empleado_id, monto, motivo)
            VALUES (%s, %s, %s, %s)
            """,
            (reserva_id, empleado_id, monto, motivo),
        )

    @staticmethod
    def _calcular_total(precio, noches, factor_temporada=1.0, descuento_porcentaje=0.0):
        """Total de la estancia: precio/noche * noches, aplicando temporada y descuento.

        La temporada alta sube el precio (factor > 1) y el descuento general lo
        baja (porcentaje 0-100). Se calcula aquí, en el servidor, para que el
        importe guardado y el que ve la interfaz no puedan discrepar.
        """
        base = Decimal(str(precio)) * int(noches) * Decimal(str(factor_temporada))
        descuento = Decimal(str(descuento_porcentaje)) / Decimal("100")
        total = base * (Decimal("1") - descuento)
        return total.quantize(Decimal("0.01"))

    def _buscar_choque(self, cursor, habitacion_id, fecha_entrada, fecha_salida, excluir_reserva_id=None):
        """Devuelve el estado de la reserva que pisa el tramo, o None si está libre.

        Regla única de solape, reutilizada por la validación previa y por el
        registro transaccional (así ambos no pueden discrepar):
          - «Pendiente»: tramo semiabierto, una salida el mismo día que la
            siguiente entrada no choca.
          - «Iniciada»: el huésped sigue dentro hasta registrar su salida, por
            lo que bloquea también el día de su salida.
        """
        condicion_extra = ""
        valores = [habitacion_id, fecha_salida, fecha_entrada, fecha_entrada]
        if excluir_reserva_id is not None:
            condicion_extra = "AND id <> %s"
            valores.append(excluir_reserva_id)

        cursor.execute(
            f"""
            SELECT estado
            FROM Reserva
            WHERE habitacion_id = %s
            AND estado IN ('Pendiente', 'Iniciada')
            AND fecha_entrada < %s
            AND (
                (estado = 'Pendiente' AND fecha_salida > %s)
                OR
                (estado = 'Iniciada' AND fecha_salida >= %s)
            )
            {condicion_extra}
            LIMIT 1
            """,
            tuple(valores),
        )
        fila = cursor.fetchone()
        if fila:
            return fila["estado"] if isinstance(fila, dict) else fila[0]

        cursor.execute(
            """
            SELECT 'Limpieza' AS estado
            FROM TareaHabitacion t
            WHERE t.habitacion_id = %s
              AND t.tipo = 'Limpieza de salida'
              AND t.estado IN ('Pendiente', 'En proceso')
              AND t.fecha_programada < %s
              AND DATE_ADD(t.fecha_programada, INTERVAL 1 DAY) > %s
            LIMIT 1
            """,
            (habitacion_id, fecha_salida, fecha_entrada),
        )
        return "Limpieza" if cursor.fetchone() else None

    def existe_choque(self, habitacion_id, fecha_entrada, fecha_salida, excluir_reserva_id=None):
        """Comprueba si la habitación ya está comprometida en ese tramo.

        Es la validación previa (fuera de transacción) que da un mensaje
        inmediato al recepcionista. El registro vuelve a validar con la fila
        bloqueada, por lo que un falso negativo aquí nunca colaría una reserva
        superpuesta.
        """
        conexion = self.db.conectar()
        if not conexion:
            return False

        try:
            cursor = conexion.cursor(dictionary=True)
            choque = self._buscar_choque(
                cursor, habitacion_id, fecha_entrada, fecha_salida, excluir_reserva_id
            )
            cursor.close()
            return choque is not None
        except Error as err:
            print(f"Error al verificar el choque de cuentas: {err}")
            return False
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
                SELECT r.id, r.habitacion_id, r.fecha_entrada, r.fecha_salida,
                    r.estado, h.no_habitacion, h.mantenimiento
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
            if reserva["estado"] != "Pendiente":
                cursor.close()
                return False, f"La reserva ya está en estado «{reserva['estado']}»."
            if reserva["mantenimiento"]:
                cursor.close()
                return False, f"La habitación {reserva['no_habitacion']} está en mantenimiento."
            if reserva["fecha_entrada"] > date.today():
                cursor.close()
                return False, "La fecha de entrada de la reserva aún no llega."
            if reserva["fecha_salida"] <= date.today():
                cursor.close()
                return False, (
                    "La fecha de salida de la reserva ya llegó. Un administrador "
                    "debe corregir las fechas antes de registrar el ingreso."
                )

            choque = self._buscar_choque(
                cursor,
                reserva["habitacion_id"],
                reserva["fecha_entrada"],
                reserva["fecha_salida"],
                excluir_reserva_id=reserva_id,
            )
            if choque == "Iniciada":
                cursor.close()
                return False, (
                    f"La habitación {reserva['no_habitacion']} tiene otra "
                    "estancia activa durante esas fechas."
                )
            if choque is not None:
                cursor.close()
                if choque == "Limpieza":
                    return False, (
                        f"La habitación {reserva['no_habitacion']} aún tiene "
                        "pendiente la limpieza de una salida anterior."
                    )
                return False, (
                    f"La habitación {reserva['no_habitacion']} tiene otra "
                    "reserva durante esas fechas."
                )

            cursor.execute(
                """
                SELECT id FROM TareaHabitacion
                WHERE habitacion_id = %s
                  AND tipo = 'Limpieza de salida'
                  AND estado IN ('Pendiente', 'En proceso')
                LIMIT 1
                """,
                (reserva["habitacion_id"],),
            )
            limpieza_pendiente = cursor.fetchone()
            if limpieza_pendiente:
                cursor.close()
                return False, (
                    f"La habitación {reserva['no_habitacion']} aún tiene "
                    "pendiente la limpieza de una salida anterior."
                )

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

    def registrar_salida(self, reserva_id, empleado_id, forzar=False, moneda="NIO"):
        """Cierra la estancia y libera la habitación.

        La habitación no se libera mientras la cuenta tenga saldo pendiente: el
        pago puede registrarse en cualquier momento, pero la salida exige cuenta
        saldada. La comprobación se hace dentro de la transacción y con la fila
        bloqueada, de modo que un cobro concurrente tampoco deje pasar una
        salida con deuda.

        `forzar` es la salida excepcional del administrador: libera la
        habitación aunque la cuenta quede con deuda (huésped que se retira sin
        pagar). El servicio es quien decide si el usuario puede forzarla.
        """
        conexion = self.db.conectar()
        if not conexion:
            return False, "No hay conexión con el servidor de base de datos."

        try:
            cursor = conexion.cursor(dictionary=True)
            cursor.execute(
                "SELECT estado, total, monto_pagado, habitacion_id "
                "FROM Reserva WHERE id = %s FOR UPDATE",
                (reserva_id,),
            )
            reserva = cursor.fetchone()
            if not reserva:
                cursor.close()
                return False, "La reserva no existe."
            if reserva["estado"] != "Iniciada":
                cursor.close()
                return False, "No hay una estancia iniciada para esa reserva."

            saldo = Decimal(str(reserva["total"])) - Decimal(str(reserva["monto_pagado"]))
            if saldo > 0 and not forzar:
                cursor.close()
                return False, (
                    "No se puede registrar la salida: la cuenta tiene un saldo "
                    f"pendiente de {self._importe(saldo, moneda)}. Cobre la cuenta antes de liberar "
                    "la habitación."
                )

            cursor.execute(
                "SELECT id FROM registro_habitacion WHERE id = %s FOR UPDATE",
                (reserva["habitacion_id"],),
            )
            habitacion = cursor.fetchone()
            if not habitacion:
                cursor.close()
                return False, "No se encontró la habitación de la reserva."
            cursor.execute(
                """
                UPDATE Reserva
                SET estado = 'Finalizada', salida_empleado_id = %s
                WHERE id = %s AND estado = 'Iniciada'
                """,
                (empleado_id, reserva_id),
            )
            self._crear_tarea_limpieza_salida(
                cursor, reserva_id, reserva["habitacion_id"]
            )
            conexion.commit()
            cursor.close()
            if saldo > 0:
                return True, (
                    "Salida registrada con saldo pendiente de "
                    f"{self._importe(saldo, moneda)}. La habitación quedó pendiente de limpieza."
                )
            return True, (
                "Salida registrada. La habitación quedó pendiente de limpieza "
                "y no estará disponible hasta que termine el servicio."
            )
        except Error as err:
            conexion.rollback()
            print(f"Error al registrar la salida: {err}")
            return False, "No se pudo registrar la salida."
        finally:
            self.db.desconectar()

    def cancelar_reserva(
        self, reserva_id, empleado_id, permitir_iniciada=False,
        horas_limite=48, penalizacion_pct=20, hora_checkin="14:00", moneda="NIO",
    ):
        """Libera las fechas de una reserva que aún no inició la estancia.

        `permitir_iniciada` habilita la anulación administrativa de una estancia
        en curso (huésped que se retira antes de tiempo). El recepcionista solo
        puede cancelar reservas pendientes.
        """
        conexion = self.db.conectar()
        if not conexion:
            return False, "No hay conexión con el servidor de base de datos."

        try:
            cursor = conexion.cursor(dictionary=True)
            cursor.execute(
                "SELECT estado, habitacion_id, fecha_entrada, total, monto_pagado "
                "FROM Reserva WHERE id = %s FOR UPDATE",
                (reserva_id,),
            )
            reserva = cursor.fetchone()
            if not reserva:
                cursor.close()
                return False, "No se encontró la reserva."
            estados = ("Pendiente", "Iniciada") if permitir_iniciada else ("Pendiente",)
            if reserva["estado"] not in estados:
                cursor.close()
                return False, "Solo se pueden cancelar reservas pendientes."

            if reserva["estado"] == "Iniciada":
                cursor.execute(
                    "SELECT id FROM registro_habitacion WHERE id = %s FOR UPDATE",
                    (reserva["habitacion_id"],),
                )
                habitacion = cursor.fetchone()
                if not habitacion:
                    cursor.close()
                    return False, "No se encontró la habitación de la reserva."

            devolucion = Decimal("0.00")
            retenido = Decimal("0.00")
            if reserva["estado"] == "Pendiente":
                try:
                    hora = time.fromisoformat(str(hora_checkin))
                except ValueError:
                    cursor.close()
                    return False, "La hora de check-in configurada no es válida."
                entrada = datetime.combine(reserva["fecha_entrada"], hora)
                horas_restantes = Decimal(str((entrada - datetime.now()).total_seconds())) / Decimal("3600")
                if horas_restantes >= Decimal(str(horas_limite)):
                    porcentaje = Decimal("0")
                else:
                    porcentaje = Decimal(str(penalizacion_pct)) / Decimal("100")
                total = Decimal(str(reserva["total"]))
                pagado = Decimal(str(reserva["monto_pagado"]))
                retenido = min((total * porcentaje).quantize(Decimal("0.01")), pagado)
                devolucion = max(pagado - retenido, Decimal("0.00"))
                if devolucion:
                    self._registrar_devolucion(
                        cursor, reserva_id, empleado_id, devolucion,
                        "Reembolso por cancelación de reserva",
                    )

            cursor.execute(
                f"""
                UPDATE Reserva
                SET estado = 'Cancelada', salida_empleado_id = %s,
                    monto_pagado = monto_pagado - %s
                WHERE id = %s AND estado IN ({", ".join(["%s"] * len(estados))})
                """,
                (empleado_id, devolucion, reserva_id, *estados),
            )
            afectadas = cursor.rowcount
            if afectadas == 0:
                conexion.rollback()
                cursor.close()
                return False, "Solo se pueden cancelar reservas pendientes."
            if reserva["estado"] == "Iniciada":
                self._crear_tarea_limpieza_salida(
                    cursor, reserva_id, reserva["habitacion_id"]
                )
            cursor.close()
            conexion.commit()
            mensaje = "Reserva cancelada correctamente."
            if reserva["estado"] == "Pendiente":
                mensaje += (
                    f" Penalización retenida: {self._importe(retenido, moneda)}; "
                    f"reembolso registrado: {self._importe(devolucion, moneda)}."
                )
            if reserva["estado"] == "Iniciada":
                mensaje += " La habitación quedó pendiente de limpieza."
            return True, mensaje
        except Error as err:
            conexion.rollback()
            print(f"Error al cancelar la reserva: {err}")
            return False, "No se pudo cancelar la reserva."
        finally:
            self.db.desconectar()

    @staticmethod
    def _crear_tarea_limpieza_salida(cursor, reserva_id, habitacion_id):
        cursor.execute(
            """
            UPDATE TareaHabitacion
            SET finalizada_en = CASE
                    WHEN estado = 'En proceso' THEN NOW()
                    ELSE finalizada_en
                END,
                estado = 'Cancelada'
            WHERE reserva_id = %s
              AND tipo = 'Limpieza diaria'
              AND estado IN ('Pendiente', 'En proceso')
            """,
            (reserva_id,),
        )
        cursor.execute(
            """
            INSERT IGNORE INTO TareaHabitacion
                (habitacion_id, reserva_id, tipo, turno, fecha_programada)
            VALUES (%s, %s, 'Limpieza de salida', 'Salida', CURDATE())
            """,
            (habitacion_id, reserva_id),
        )

    def reactivar_reserva(self, reserva_id, empleado_id):
        """Devuelve una reserva cancelada al estado Pendiente.

        Es la corrección administrativa de una cancelación hecha por error. Se
        comprueba, con la fila bloqueada, que la habitación siga libre para esas
        fechas: si en el mientras tanto se reservó, no se reactiva.
        """
        conexion = self.db.conectar()
        if not conexion:
            return False, "No hay conexión con el servidor de base de datos."

        try:
            cursor = conexion.cursor(dictionary=True)
            cursor.execute(
                "SELECT id, habitacion_id, fecha_entrada, fecha_salida, estado "
                "FROM Reserva WHERE id = %s FOR UPDATE",
                (reserva_id,),
            )
            reserva = cursor.fetchone()
            if not reserva:
                cursor.close()
                return False, "La reserva no existe."
            if reserva["estado"] != "Cancelada":
                cursor.close()
                return False, "Solo se pueden reactivar reservas canceladas."

            choque = self._buscar_choque(
                cursor,
                reserva["habitacion_id"],
                reserva["fecha_entrada"],
                reserva["fecha_salida"],
                excluir_reserva_id=reserva_id,
            )
            if choque is not None:
                cursor.close()
                if choque == "Limpieza":
                    return False, (
                        "No se puede reactivar: la habitación tiene pendiente "
                        "una limpieza de salida para esas fechas."
                    )
                return False, (
                    "No se puede reactivar: la habitación ya está comprometida "
                    "para esas fechas."
                )

            cursor.execute(
                "UPDATE Reserva SET estado = 'Pendiente', salida_empleado_id = NULL WHERE id = %s",
                (reserva_id,),
            )
            conexion.commit()
            cursor.close()
            return True, "Reserva reactivada correctamente."
        except Error as err:
            conexion.rollback()
            print(f"Error al reactivar la reserva: {err}")
            return False, "No se pudo reactivar la reserva."
        finally:
            self.db.desconectar()

    def actualizar_reserva(self, reserva_id, fecha_entrada, fecha_salida, noches,
                           habitacion_id, empleado_id,
                           factor_temporada=1.0, descuento_porcentaje=0.0,
                           moneda="NIO"):
        """Modifica las fechas y la habitación de una reserva pendiente.

        Es una corrección administrativa: vuelve a validar el solape ignorando
        la propia reserva, relee el precio de la habitación elegida y deja
        constancia del empleado que la editó. No toca el estado ni los pagos.
        """
        conexion = self.db.conectar()
        if not conexion:
            return False, "No hay conexión con el servidor de base de datos."

        try:
            cursor = conexion.cursor(dictionary=True)
            cursor.execute(
                "SELECT estado, monto_pagado, numero_huespedes "
                "FROM Reserva WHERE id = %s FOR UPDATE",
                (reserva_id,),
            )
            reserva = cursor.fetchone()
            if not reserva:
                cursor.close()
                return False, "La reserva no existe."
            if reserva["estado"] != "Pendiente":
                cursor.close()
                return False, "Solo se pueden editar reservas pendientes de ingreso."

            cursor.execute(
                "SELECT precio, capacidad, mantenimiento "
                "FROM registro_habitacion WHERE id = %s FOR UPDATE",
                (habitacion_id,),
            )
            habitacion = cursor.fetchone()
            if not habitacion:
                cursor.close()
                return False, "La habitación seleccionada no existe."
            if habitacion["mantenimiento"]:
                cursor.close()
                return False, "La habitación está en mantenimiento y no admite reservas."
            if reserva["numero_huespedes"] > habitacion["capacidad"]:
                cursor.close()
                return False, (
                    f"La habitación seleccionada admite hasta {habitacion['capacidad']} "
                    f"huésped(es), pero la reserva tiene {reserva['numero_huespedes']}."
                )

            choque = self._buscar_choque(
                cursor, habitacion_id, fecha_entrada, fecha_salida,
                excluir_reserva_id=reserva_id,
            )
            if choque == "Iniciada":
                cursor.close()
                return False, "La habitación sigue ocupada por un huésped que aún no registra su salida."
            if choque is not None:
                cursor.close()
                if choque == "Limpieza":
                    return False, (
                        "La habitación tiene pendiente una limpieza de salida "
                        "para esas fechas."
                    )
                return False, "La habitación ya tiene una reserva activa para esas fechas."

            total = self._calcular_total(
                habitacion["precio"], noches, factor_temporada, descuento_porcentaje
            )
            monto_pagado = Decimal(str(reserva["monto_pagado"] or 0))
            if total < monto_pagado:
                cursor.close()
                return False, (
                    f"El nuevo total ({self._importe(total, moneda)}) sería inferior a lo ya "
                    f"pagado ({self._importe(monto_pagado, moneda)}). Ajuste la reserva sin "
                    "reducir el total por debajo de lo cobrado."
                )

            cursor.execute(
                """
                UPDATE Reserva
                SET fecha_entrada = %s, fecha_salida = %s, noches = %s,
                    total = %s, habitacion_id = %s, empleado_id = %s
                WHERE id = %s AND estado = 'Pendiente'
                """,
                (fecha_entrada, fecha_salida, noches, total, habitacion_id,
                 empleado_id, reserva_id),
            )
            conexion.commit()
            cursor.close()
            return True, "Reserva actualizada correctamente."
        except Error as err:
            conexion.rollback()
            print(f"Error al actualizar la reserva: {err}")
            return False, "No se pudo actualizar la reserva."
        finally:
            self.db.desconectar()

    def obtener_reserva(self, reserva_id):
        """Datos mínimos de una reserva para validar una extensión de estadía.

        Es la comprobación previa del servicio: informa el estado y las fechas.
        La extensión vuelve a validar con la fila bloqueada, así que un cambio
        entre ambas lecturas no puede colarse.
        """
        conexion = self.db.conectar()
        if not conexion:
            return None

        try:
            cursor = conexion.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT id, estado, fecha_entrada, fecha_salida, habitacion_id,
                    total, monto_pagado
                FROM Reserva
                WHERE id = %s
                """,
                (reserva_id,),
            )
            reserva = cursor.fetchone()
            cursor.close()
            return reserva
        except Error as err:
            print(f"Error al obtener la reserva: {err}")
            return None
        finally:
            self.db.desconectar()

    def extender_estadia(self, reserva_id, nueva_salida, empleado_id,
                         factor_temporada=1.0, descuento_porcentaje=0.0,
                         moneda="NIO"):
        """Alarga la salida de una estancia en curso y recalcula el total.

        Solo aplica a reservas ``Iniciada``. Revalida el solape en el tramo que
        se agrega (desde la salida actual hasta la nueva) para no pisar una
        reserva futura de la misma habitación. No toca los pagos: si el total
        crece, el saldo pendiente crece con él.
        """
        conexion = self.db.conectar()
        if not conexion:
            return False, "No hay conexión con el servidor de base de datos."

        try:
            cursor = conexion.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT estado, fecha_entrada, fecha_salida, habitacion_id, monto_pagado
                FROM Reserva
                WHERE id = %s
                FOR UPDATE
                """,
                (reserva_id,),
            )
            reserva = cursor.fetchone()
            if not reserva:
                cursor.close()
                return False, "La reserva no existe."
            if reserva["estado"] != "Iniciada":
                cursor.close()
                return False, "Solo se puede extender una estadía que esté en curso."

            salida_actual = reserva["fecha_salida"]
            if nueva_salida <= salida_actual:
                cursor.close()
                return False, "La nueva salida debe ser posterior a la actual."

            cursor.execute(
                "SELECT precio, mantenimiento FROM registro_habitacion WHERE id = %s FOR UPDATE",
                (reserva["habitacion_id"],),
            )
            habitacion = cursor.fetchone()
            if not habitacion:
                cursor.close()
                return False, "La habitación de la reserva no existe."
            if habitacion["mantenimiento"]:
                cursor.close()
                return False, "La habitación está en mantenimiento."

            choque = self._buscar_choque(
                cursor, reserva["habitacion_id"], salida_actual, nueva_salida,
                excluir_reserva_id=reserva_id,
            )
            if choque == "Iniciada":
                cursor.close()
                return False, "La habitación sigue ocupada por otro huésped."
            if choque is not None:
                cursor.close()
                if choque == "Limpieza":
                    return False, (
                        "No se puede extender: la habitación tiene pendiente "
                        "una limpieza de salida para esas fechas."
                    )
                return False, "La habitación ya tiene una reserva para las fechas de la extensión."

            noches = (nueva_salida - reserva["fecha_entrada"]).days
            total = self._calcular_total(
                habitacion["precio"], noches, factor_temporada, descuento_porcentaje
            )
            monto_pagado = Decimal(str(reserva["monto_pagado"] or 0))
            if total < monto_pagado:
                cursor.close()
                return False, (
                    f"El nuevo total ({self._importe(total, moneda)}) sería inferior a lo ya "
                    f"pagado ({self._importe(monto_pagado, moneda)}). No se puede extender con "
                    "un total menor a lo cobrado."
                )

            cursor.execute(
                """
                UPDATE Reserva
                SET fecha_salida = %s, noches = %s, total = %s, empleado_id = %s
                WHERE id = %s AND estado = 'Iniciada'
                """,
                (nueva_salida, noches, total, empleado_id, reserva_id),
            )
            conexion.commit()
            cursor.close()
            return True, (
                f"Estadía extendida hasta el {nueva_salida.strftime('%d/%m/%Y')}. "
                f"Nuevo total: {self._importe(total, moneda)}."
            )
        except Error as err:
            conexion.rollback()
            print(f"Error al extender la estadía: {err}")
            return False, "No se pudo extender la estadía."
        finally:
            self.db.desconectar()

    def obtener_pendientes(self):
        """Todas las reservas pendientes de ingreso, sea cual sea su fecha.

        Incluye también las reservas futuras, para que la mesa «Reservas
        pendientes» muestre todo lo reservado y todavía sin ingresar.
        """
        return self._listar("AND r.estado = 'Pendiente'")

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

    def obtener_todas(self, estricto=False):
        """Reservas de cualquier fecha y cualquier estado, incluidas las canceladas.

        Es el listado completo del hotel. Antes la interfaz solo consultaba las
        llegadas del día, así que una reserva para dentro de un mes no aparecía
        en ninguna parte del sistema y parecía no existir.

        El orden jerárquico por estado lo impone la propia consulta, de modo que
        quien llama siempre recibe la mesa igual y ordenada sin tener que
        reacomodar los datos en Python.
        """
        try:
            with SessionLocal() as session:
                prioridad_estado = case(
                    (Reserva.estado == "Pendiente", 1),
                    (Reserva.estado == "Iniciada", 2),
                    (Reserva.estado == "No presentada", 3),
                    (Reserva.estado == "Cancelada", 4),
                    (Reserva.estado == "Finalizada", 5),
                    else_=99,
                )
                consulta = (
                    select(Reserva)
                    .join(Reserva.habitacion)
                    .options(
                        joinedload(Reserva.habitacion),
                        joinedload(Reserva.empleado_registro),
                        joinedload(Reserva.empleado_checkin),
                        joinedload(Reserva.empleado_salida),
                    )
                    .order_by(
                        prioridad_estado,
                        Reserva.fecha_entrada,
                        Habitacion.no_habitacion,
                        Reserva.id,
                    )
                )
                reservas = session.scalars(consulta).all()
                return [
                    {
                        "id": reserva.id,
                        "cliente": reserva.cliente,
                        "identificacion": reserva.identificacion,
                        "contacto": reserva.contacto,
                        "numero_huespedes": reserva.numero_huespedes,
                        "noches": reserva.noches,
                        "fecha_entrada": reserva.fecha_entrada,
                        "fecha_salida": reserva.fecha_salida,
                        "metodo_pago": reserva.metodo_pago,
                        "total": reserva.total,
                        "monto_pagado": reserva.monto_pagado,
                        "saldo": reserva.total - reserva.monto_pagado,
                        "estado": reserva.estado,
                        "habitacion_id": reserva.habitacion_id,
                        "empleado_id": reserva.empleado_id,
                        "creado_en": reserva.creado_en,
                        "habitacion_nombre": reserva.habitacion.nombre,
                        "habitacion_numero": reserva.habitacion.no_habitacion,
                        "empleado_nombre": reserva.empleado_registro.nombre_completo,
                        "checkin_empleado": (
                            reserva.empleado_checkin.nombre_completo
                            if reserva.empleado_checkin
                            else None
                        ),
                        "salida_empleado": (
                            reserva.empleado_salida.nombre_completo
                            if reserva.empleado_salida
                            else None
                        ),
                    }
                    for reserva in reservas
                ]
        except SQLAlchemyError as err:
            print(f"Error al obtener las reservas: {err}")
            if estricto:
                raise
            return []

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
        base = "" if incluir_canceladas else "r.estado NOT IN ('Cancelada', 'No presentada')"
        condiciones = " ".join(parte for parte in (base, filtro) if parte)

        sql = f"""
            SELECT r.id, r.cliente, r.identificacion, r.contacto,
                r.numero_huespedes, r.noches, r.fecha_entrada, r.fecha_salida, r.metodo_pago, r.total,
                r.monto_pagado, (r.total - r.monto_pagado) AS saldo,
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

    # ------------------------------------------------------------------
    # PAGOS Y SALDOS
    # ------------------------------------------------------------------
    def obtener_cuenta(self, reserva_id):
        """Estado de cuenta de una reserva concreta, o None si no existe.

        Es la validación previa (sin transacción) que usa el servicio para dar
        de inmediato el motivo del rechazo. La salida vuelve a validar con la
        fila bloqueada, por lo que un falso negativo aquí nunca colaría una
        liberación con deuda.
        """
        conexion = self.db.conectar()
        if not conexion:
            return None

        sql = """
            SELECT r.id, r.total, r.monto_pagado, r.numero_huespedes,
                (r.total - r.monto_pagado) AS saldo, r.estado,
                CASE
                    WHEN r.monto_pagado <= 0 THEN 'Pendiente'
                    WHEN r.monto_pagado < r.total THEN 'Parcial'
                    ELSE 'Pagado'
                END AS estado_pago
            FROM Reserva r
            WHERE r.id = %s
        """

        try:
            cursor = conexion.cursor(dictionary=True)
            cursor.execute(sql, (reserva_id,))
            cuenta = cursor.fetchone()
            cursor.close()
            return cuenta
        except Error as err:
            print(f"Error al obtener la cuenta: {err}")
            return None
        finally:
            self.db.desconectar()

    def obtener_cuentas(self):
        """Estado de cuenta de cada reserva vigente.

        Incluye el total, lo cobrado, el saldo y el estado de pago (calculado,
        no almacenado: así no puede quedar desincronizado con monto_pagado).
        Las canceladas se excluyen: no hay nada que cobrar en ellas.
        """
        conexion = self.db.conectar()
        if not conexion:
            return []

        sql = """
            SELECT r.id, r.cliente, r.identificacion, r.contacto,
                r.numero_huespedes, r.noches,
                r.fecha_entrada, r.fecha_salida, r.metodo_pago, r.total,
                r.monto_pagado, (r.total - r.monto_pagado) AS saldo,
                r.estado, r.habitacion_id,
                h.no_habitacion AS habitacion_numero, h.nombre AS habitacion_nombre,
                CASE
                    WHEN r.monto_pagado <= 0 THEN 'Pendiente'
                    WHEN r.monto_pagado < r.total THEN 'Parcial'
                    ELSE 'Pagado'
                END AS estado_pago
            FROM Reserva r
            JOIN registro_habitacion h ON h.id = r.habitacion_id
            WHERE r.estado NOT IN ('Cancelada', 'No presentada')
            ORDER BY
                CASE WHEN r.monto_pagado >= r.total THEN 1 ELSE 0 END,
                r.fecha_entrada, h.no_habitacion, r.id
        """

        try:
            cursor = conexion.cursor(dictionary=True)
            cursor.execute(sql)
            cuentas = cursor.fetchall()
            cursor.close()
            return cuentas
        except Error as err:
            print(f"Error al obtener las cuentas: {err}")
            return []
        finally:
            self.db.desconectar()

    def obtener_estadias_vencidas(self, fecha):
        """Estancias ya iniciadas cuya fecha de salida ya pasó.

        Son los huéspedes que siguen en la habitación pese a tener el egreso
        cumplido: la habitación no se libera sola, así que hay que avisarlas al
        personal. La habitación sigue marcada como ocupada hasta que se registre
        la salida, de modo que estas filas coinciden con el catálogo.
        """
        conexion = self.db.conectar()
        if not conexion:
            return []

        sql = """
            SELECT r.id, r.cliente, r.identificacion, r.numero_huespedes,
                r.noches, r.fecha_entrada, r.fecha_salida, r.total, r.monto_pagado,
                (r.total - r.monto_pagado) AS saldo,
                h.no_habitacion AS habitacion_numero, h.nombre AS habitacion_nombre,
                DATEDIFF(%s, r.fecha_salida) AS dias_excedidos
            FROM Reserva r
            JOIN registro_habitacion h ON h.id = r.habitacion_id
            WHERE r.estado = 'Iniciada'
              AND r.fecha_entrada <= %s
              AND r.fecha_salida < %s
            ORDER BY r.fecha_salida, h.no_habitacion, r.id
        """

        try:
            cursor = conexion.cursor(dictionary=True)
            cursor.execute(sql, (fecha, fecha, fecha))
            vencidas = cursor.fetchall()
            cursor.close()
            return vencidas
        except Error as err:
            print(f"Error al obtener las estadías vencidas: {err}")
            return []
        finally:
            self.db.desconectar()

    def obtener_cuentas_alojados(self):
        """Cuentas con saldo pendiente de los huéspedes que siguen alojados.

        Son las reservas Iniciadas cuya cuenta todavía no está saldada. Se usa
        para la tarjeta de «cuentas por cobrar» del tablero: a diferencia de
        `obtener_cuentas` aquí solo aparece quien ocupa la habitación ahora.
        """
        conexion = self.db.conectar()
        if not conexion:
            return []

        sql = """
            SELECT r.id, r.cliente, r.identificacion, r.numero_huespedes, r.noches,
                r.fecha_entrada, r.fecha_salida, r.total, r.monto_pagado,
                (r.total - r.monto_pagado) AS saldo,
                h.no_habitacion AS habitacion_numero, h.nombre AS habitacion_nombre,
                CASE
                    WHEN r.monto_pagado <= 0 THEN 'Pendiente'
                    WHEN r.monto_pagado < r.total THEN 'Parcial'
                    ELSE 'Pagado'
                END AS estado_pago
            FROM Reserva r
            JOIN registro_habitacion h ON h.id = r.habitacion_id
            WHERE r.estado = 'Iniciada'
              AND r.monto_pagado < r.total
            ORDER BY (r.total - r.monto_pagado) DESC, h.no_habitacion, r.id
        """

        try:
            cursor = conexion.cursor(dictionary=True)
            cursor.execute(sql)
            cuentas = cursor.fetchall()
            cursor.close()
            return cuentas
        except Error as err:
            print(f"Error al obtener las cuentas de los alojados: {err}")
            return []
        finally:
            self.db.desconectar()

    def registrar_pago(self, reserva_id, monto, metodo_pago, empleado_id, moneda="NIO"):
        """Registra un cobro (total o parcial) y actualiza el saldo de la reserva."""
        conexion = self.db.conectar()
        if not conexion:
            return False, "No hay conexión con el servidor de base de datos."

        try:
            cursor = conexion.cursor(dictionary=True)
            cursor.execute(
                "SELECT total, monto_pagado, estado FROM Reserva WHERE id = %s FOR UPDATE",
                (reserva_id,),
            )
            reserva = cursor.fetchone()
            if not reserva:
                cursor.close()
                return False, "La reserva no existe."
            if reserva["estado"] in ("Cancelada", "No presentada"):
                cursor.close()
                return False, "No se puede cobrar una reserva cancelada o no presentada."

            total = Decimal(str(reserva["total"]))
            pagado = Decimal(str(reserva["monto_pagado"]))
            monto = Decimal(str(monto))
            saldo = total - pagado

            if monto <= 0:
                cursor.close()
                return False, "El monto a cobrar debe ser mayor a cero."
            if monto > saldo:
                cursor.close()
                return False, f"El monto supera el saldo pendiente ({self._importe(saldo, moneda)})."

            cursor.execute(
                """
                INSERT INTO Pago (reserva_id, monto, metodo_pago, empleado_id)
                VALUES (%s, %s, %s, %s)
                """,
                (reserva_id, monto, metodo_pago, empleado_id),
            )
            nuevo_pagado = pagado + monto
            cursor.execute(
                "UPDATE Reserva SET monto_pagado = %s WHERE id = %s",
                (nuevo_pagado, reserva_id),
            )
            conexion.commit()
            cursor.close()

            nuevo_saldo = total - nuevo_pagado
            if nuevo_saldo <= 0:
                return True, "Pago registrado. La cuenta quedó saldada."
            return True, (
                f"Pago registrado. Saldo pendiente: {self._importe(nuevo_saldo, moneda)}."
            )
        except Error as err:
            conexion.rollback()
            print(f"Error al registrar el pago: {err}")
            return False, "No se pudo registrar el pago."
        finally:
            self.db.desconectar()

    @staticmethod
    def _importe(monto, moneda):
        simbolo = "C$" if moneda == "NIO" else "$"
        return f"{simbolo} {monto:,.2f}"

    def obtener_pagos(self, reserva_id):
        """Historial de cobros y devoluciones de una reserva."""
        conexion = self.db.conectar()
        if not conexion:
            return []

        try:
            cursor = conexion.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT movimiento.id, movimiento.monto, movimiento.metodo_pago,
                    movimiento.creado_en, movimiento.empleado
                FROM (
                    SELECT p.id, p.monto, p.metodo_pago, p.creado_en,
                        u.nombre_completo AS empleado
                    FROM Pago p
                    JOIN Usuario u ON u.id = p.empleado_id
                    WHERE p.reserva_id = %s
                    UNION ALL
                    SELECT -d.id AS id, -d.monto AS monto, 'Devolución' AS metodo_pago,
                        d.creado_en, u.nombre_completo AS empleado
                    FROM Devolucion d
                    JOIN Usuario u ON u.id = d.empleado_id
                    WHERE d.reserva_id = %s
                ) AS movimiento
                ORDER BY movimiento.creado_en DESC, ABS(movimiento.id) DESC
                """,
                (reserva_id, reserva_id),
            )
            pagos = cursor.fetchall()
            cursor.close()
            return pagos
        except Error as err:
            print(f"Error al obtener los pagos: {err}")
            return []
        finally:
            self.db.desconectar()

    def crear_comprobante_pago(self, pago_id, prefijo="COMP"):
        """Crea (una sola vez) el número consecutivo y devuelve los datos del recibo."""
        conexion = self.db.conectar()
        if not conexion:
            return False, "No hay conexión con el servidor de base de datos."

        try:
            cursor = conexion.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT p.id AS pago_id, p.reserva_id, p.monto, p.metodo_pago, p.creado_en,
                    r.cliente, r.identificacion, r.fecha_entrada, r.fecha_salida,
                    h.no_habitacion AS habitacion_numero,
                    u.nombre_completo AS empleado
                FROM Pago p
                JOIN Reserva r ON r.id = p.reserva_id
                JOIN registro_habitacion h ON h.id = r.habitacion_id
                JOIN Usuario u ON u.id = p.empleado_id
                WHERE p.id = %s
                """,
                (pago_id,),
            )
            comprobante = cursor.fetchone()
            if not comprobante:
                cursor.close()
                return False, "El pago ya no existe."

            cursor.execute(
                "SELECT numero FROM Comprobante WHERE pago_id = %s",
                (pago_id,),
            )
            existente = cursor.fetchone()
            if existente:
                numero = existente["numero"]
            else:
                cursor.execute(
                    "SELECT siguiente FROM ControlComprobante WHERE id = 1 FOR UPDATE"
                )
                control = cursor.fetchone()
                if not control:
                    cursor.close()
                    return False, "No está inicializado el contador de comprobantes."
                cursor.execute(
                    "SELECT numero FROM Comprobante WHERE pago_id = %s",
                    (pago_id,),
                )
                existente = cursor.fetchone()
                if existente:
                    numero = existente["numero"]
                else:
                    consecutivo = int(control["siguiente"])
                    numero = f"{prefijo}-{consecutivo:06d}"
                    cursor.execute(
                        "INSERT INTO Comprobante (pago_id, numero) VALUES (%s, %s)",
                        (pago_id, numero),
                    )
                    cursor.execute(
                        "UPDATE ControlComprobante SET siguiente = %s WHERE id = 1",
                        (consecutivo + 1,),
                    )
            conexion.commit()
            cursor.close()

            configuracion = self.obtener_configuracion()
            comprobante.update({
                "numero": numero,
                "hotel_nombre": configuracion.get("hotel_nombre", "Allogi Hotel"),
                "hotel_direccion": configuracion.get("hotel_direccion", ""),
                "hotel_telefono": configuracion.get("hotel_telefono", ""),
                "hotel_correo": configuracion.get("hotel_correo", ""),
                "comprobante_mensaje": configuracion.get("comprobante_mensaje", ""),
                "moneda": configuracion.get("moneda", "NIO"),
            })
            return True, comprobante
        except Error as err:
            conexion.rollback()
            print(f"Error al generar comprobante: {err}")
            return False, "No se pudo generar el comprobante."
        finally:
            self.db.desconectar()

    # ------------------------------------------------------------------
    # PARAMETROS DEL HOTEL (tabla Configuracion)
    # ------------------------------------------------------------------
    def obtener_configuracion(self):
        """Devuelve todos los parámetros del hotel como un diccionario clave→valor."""
        try:
            with SessionLocal() as session:
                filas = session.scalars(select(Configuracion)).all()
                return {fila.clave: fila.valor for fila in filas}
        except SQLAlchemyError as err:
            print(f"Error al obtener la configuración: {err}")
            return {}

    def guardar_configuracion(self, pares: dict):
        """Guarda varios parámetros a la vez (upsert por clave)."""
        if not pares:
            return False, "No hay parámetros para guardar."

        try:
            with SessionLocal.begin() as session:
                for clave, valor in pares.items():
                    parametro = session.get(Configuracion, clave)
                    if parametro is None:
                        session.add(Configuracion(clave=clave, valor=str(valor)))
                    else:
                        parametro.valor = str(valor)
            return True, "Parámetros guardados correctamente."
        except OperationalError as err:
            print(f"Error al guardar la configuración: {err}")
            return False, "No hay conexión con el servidor de base de datos."
        except SQLAlchemyError as err:
            print(f"Error al guardar la configuración: {err}")
            return False, "No se pudieron guardar los parámetros."

    # ------------------------------------------------------------------
    # REPORTES
    # ------------------------------------------------------------------
    def ingresos_por_dia(self, fecha_inicio, fecha_fin):
        """Suma de cobros por día dentro del rango pedido."""
        conexion = self.db.conectar()
        if not conexion:
            return []

        try:
            cursor = conexion.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT movimiento.fecha, SUM(movimiento.monto) AS total
                FROM (
                    SELECT DATE(creado_en) AS fecha, monto
                    FROM Pago
                    WHERE DATE(creado_en) BETWEEN %s AND %s
                    UNION ALL
                    SELECT DATE(creado_en) AS fecha, -monto AS monto
                    FROM Devolucion
                    WHERE DATE(creado_en) BETWEEN %s AND %s
                ) AS movimiento
                GROUP BY movimiento.fecha
                ORDER BY fecha
                """,
                (fecha_inicio, fecha_fin, fecha_inicio, fecha_fin),
            )
            filas = cursor.fetchall()
            cursor.close()
            return filas
        except Error as err:
            print(f"Error al obtener los ingresos: {err}")
            return []
        finally:
            self.db.desconectar()

    def resumen_periodo(self, fecha_inicio, fecha_fin):
        """Indicadores agregados del período para el panel de reportes."""
        conexion = self.db.conectar()
        if not conexion:
            return {}

        try:
            cursor = conexion.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT
                    (SELECT COALESCE(SUM(monto), 0) FROM Pago
                     WHERE DATE(creado_en) BETWEEN %s AND %s)
                    - (SELECT COALESCE(SUM(monto), 0) FROM Devolucion
                     WHERE DATE(creado_en) BETWEEN %s AND %s) AS ingresos,
                    (SELECT COUNT(*) FROM Reserva
                     WHERE DATE(creado_en) BETWEEN %s AND %s) AS reservas,
                    (SELECT COUNT(*) FROM Reserva
                     WHERE estado = 'Cancelada'
                     AND DATE(actualizado_en) BETWEEN %s AND %s) AS canceladas,
                    (SELECT COUNT(*) FROM Reserva
                     WHERE estado = 'No presentada'
                     AND DATE(actualizado_en) BETWEEN %s AND %s) AS no_presentadas
                """,
                (fecha_inicio, fecha_fin, fecha_inicio, fecha_fin,
                 fecha_inicio, fecha_fin, fecha_inicio, fecha_fin, fecha_inicio, fecha_fin),
            )
            resumen = cursor.fetchone() or {}
            cursor.close()
            return resumen
        except Error as err:
            print(f"Error al obtener el resumen del período: {err}")
            return {}
        finally:
            self.db.desconectar()

    def reservas_canceladas(self, fecha_inicio, fecha_fin):
        """Reservas canceladas registradas en el rango, para el detalle del reporte."""
        conexion = self.db.conectar()
        if not conexion:
            return []

        try:
            cursor = conexion.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT r.id, r.cliente, r.fecha_entrada, r.fecha_salida,
                    r.total, h.no_habitacion AS habitacion_numero
                FROM Reserva r
                JOIN registro_habitacion h ON h.id = r.habitacion_id
                WHERE r.estado = 'Cancelada'
                AND DATE(r.actualizado_en) BETWEEN %s AND %s
                ORDER BY r.creado_en DESC, r.id DESC
                """,
                (fecha_inicio, fecha_fin),
            )
            filas = cursor.fetchall()
            cursor.close()
            return filas
        except Error as err:
            print(f"Error al obtener las reservas canceladas: {err}")
            return []
        finally:
            self.db.desconectar()

    def pagos_en_periodo(self, fecha_inicio, fecha_fin):
        """Devuelve los pagos realizados en el período con huésped y empleado."""
        conexion = self.db.conectar()
        if not conexion:
            raise ConnectionError("No hay conexión con el servidor de base de datos.")

        try:
            cursor = conexion.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT movimientos.pago_id, movimientos.reserva_id, movimientos.creado_en,
                    movimientos.monto, movimientos.metodo_pago, movimientos.cliente,
                    movimientos.identificacion, movimientos.habitacion_numero,
                    movimientos.empleado_nombre
                FROM (
                    SELECT p.id AS pago_id, p.reserva_id, p.creado_en, p.monto,
                        p.metodo_pago, r.cliente, r.identificacion,
                        h.no_habitacion AS habitacion_numero,
                        u.nombre_completo AS empleado_nombre
                    FROM Pago p
                    JOIN Reserva r ON r.id = p.reserva_id
                    JOIN registro_habitacion h ON h.id = r.habitacion_id
                    JOIN Usuario u ON u.id = p.empleado_id
                    WHERE DATE(p.creado_en) BETWEEN %s AND %s
                    UNION ALL
                    SELECT -d.id AS pago_id, d.reserva_id, d.creado_en, -d.monto,
                        'Devolución' AS metodo_pago, r.cliente, r.identificacion,
                        h.no_habitacion AS habitacion_numero,
                        u.nombre_completo AS empleado_nombre
                    FROM Devolucion d
                    JOIN Reserva r ON r.id = d.reserva_id
                    JOIN registro_habitacion h ON h.id = r.habitacion_id
                    JOIN Usuario u ON u.id = d.empleado_id
                    WHERE DATE(d.creado_en) BETWEEN %s AND %s
                ) AS movimientos
                ORDER BY movimientos.creado_en, movimientos.pago_id
                """,
                (fecha_inicio, fecha_fin, fecha_inicio, fecha_fin),
            )
            pagos = cursor.fetchall()
            cursor.close()
            return pagos
        except Error as err:
            print(f"Error al obtener los pagos del período: {err}")
            raise
        finally:
            self.db.desconectar()

    def ingresos_por_metodo(self, fecha_inicio, fecha_fin):
        """Agrupa cantidad e importe de pagos por método en el período."""
        conexion = self.db.conectar()
        if not conexion:
            raise ConnectionError("No hay conexión con el servidor de base de datos.")

        try:
            cursor = conexion.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT movimiento.metodo_pago, COUNT(*) AS cantidad,
                    SUM(movimiento.monto) AS total
                FROM (
                    SELECT metodo_pago, monto, creado_en
                    FROM Pago
                    WHERE DATE(creado_en) BETWEEN %s AND %s
                    UNION ALL
                    SELECT 'Devolución' AS metodo_pago, -monto AS monto, creado_en
                    FROM Devolucion
                    WHERE DATE(creado_en) BETWEEN %s AND %s
                ) AS movimiento
                GROUP BY movimiento.metodo_pago
                ORDER BY metodo_pago
                """,
                (fecha_inicio, fecha_fin, fecha_inicio, fecha_fin),
            )
            filas = cursor.fetchall()
            cursor.close()
            return filas
        except Error as err:
            print(f"Error al agrupar los pagos por método: {err}")
            raise
        finally:
            self.db.desconectar()
