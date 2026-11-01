# services/habitacion_service.py
import os
from DATABASE.habitacion_dao import HabitacionDAO
from utils.seguridad import (
    MENSAJE_SIN_PERMISO,
    MENSAJE_SOLO_ADMIN,
    es_administrador,
    puede_administrar_catalogo,
    sesion_valida,
)
from utils.validaciones import es_id_valido, es_precio_valido

class HabitacionService:
    """Reglas de negocio del catálogo de habitaciones y su estado de ocupación.

    Las operaciones de escritura exigen una sesión de administrador. La interfaz
    ya oculta esos controles, pero la comprobación se repite aquí para que la
    autorización no dependa de la capa de presentación.
    """

    TIPOS_HABITACION = ["Simple", "Doble", "Matrimonial", "Suite", "Deluxe", "Presidencial"]

    def __init__(self):
        self.dao = HabitacionDAO()

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.ruta_foto_defecto = os.path.join(
            base_dir, "recursos", "placeholder-image.jpg"
        )

    @staticmethod
    def _convertir_numero(numero, campo="valor"):
        if numero in (None, ""):
            return None
        try:
            return int(numero)
        except (TypeError, ValueError):
            raise ValueError(f"El {campo} debe ser un número entero válido.")

    def obtener_todas(self) -> list[dict]:
        """Trae el catálogo con la imagen por defecto aplicada y la capacidad formateada."""
        habitaciones = self.dao.obtener_habitaciones()

        for hab in habitaciones:
            if not hab.get("imagen"):
                hab["imagen"] = self.ruta_foto_defecto
            hab["capacidad_texto"] = self._formatear_capacidad(hab.get("capacidad"))
            hab["precio"] = float(hab.get("precio") or 0)
            hab["mantenimiento"] = bool(hab.get("mantenimiento"))
            hab["reserva_activa"] = bool(hab.get("reserva_activa"))

        return habitaciones

    def obtener_resumen_ocupacion(self) -> dict:
        """Conteos del panel: base para el tablero de occupancy en tiempo real."""
        habitaciones = self.obtener_todas()

        resumen = {
            "total": len(habitaciones),
            "ocupadas": 0,
            "reservadas": 0,
            "disponibles": 0,
            "limpieza": 0,
            "mantenimiento": 0,
        }
        for hab in habitaciones:
            estatus = hab.get("estatus", "Disponible")
            if estatus == "Ocupado":
                resumen["ocupadas"] += 1
            elif estatus == "Reservado":
                resumen["reservadas"] += 1
            elif estatus == "Mantenimiento":
                resumen["mantenimiento"] += 1
            elif estatus == "Pendiente de limpieza":
                resumen["limpieza"] += 1
            else:
                resumen["disponibles"] += 1

        resumen["porcentaje_ocupacion"] = (
            round((resumen["ocupadas"] / resumen["total"]) * 100) if resumen["total"] else 0
        )
        return resumen

    def _sin_permiso(self, usuario_actual) -> tuple[bool, str] | None:
        """Devuelve el rechazo si la sesión no autoriza a modificar el catálogo."""
        if not sesion_valida(usuario_actual):
            return False, "Debe iniciar sesión para modificar el catálogo."
        if not puede_administrar_catalogo(usuario_actual):
            return False, MENSAJE_SIN_PERMISO
        return None

    def obtener_disponibles(self, fecha_entrada, fecha_salida) -> list[dict]:
        """Habitaciones libres para el tramo pedido, ya formateadas para la interfaz.

        `fecha_entrada` y `fecha_salida` se reciben como texto `YYYY-MM-DD`.
        """
        if not fecha_entrada or not fecha_salida:
            return []

        disponibles = self.dao.obtener_disponibles(fecha_entrada, fecha_salida)
        for hab in disponibles:
            if not hab.get("imagen"):
                hab["imagen"] = self.ruta_foto_defecto
            hab["precio"] = float(hab.get("precio") or 0)
            hab["capacidad_texto"] = self._formatear_capacidad(hab.get("capacidad"))
        return disponibles

    def agregar_habitacion(
        self,
        usuario_actual: dict,
        nombre: str,
        numero: int,
        tipo: str,
        precio: float,
        capacidad: int = 2,
        descripcion: str = "",
        imagen: str = ""
    ) -> tuple[bool, str]:
        """Publica una habitación nueva en el catálogo."""
        rechazo = self._sin_permiso(usuario_actual)
        if rechazo:
            return rechazo

        try:
            numero = self._convertir_numero(numero, "número de habitación")
            capacidad = self._convertir_numero(capacidad, "número de capacidad")
        except ValueError as exc:
            return False, str(exc)

        if tipo not in self.TIPOS_HABITACION:
            return False, "El tipo de habitación seleccionado no es válido."

        return self.dao.registrar_habitacion(
            nombre=nombre,
            no_habitacion=numero,
            tipo=tipo,
            precio=precio,
            capacidad=capacidad,
            descripcion=descripcion,
            imagen=imagen,
        )

    def editar_habitacion(
        self,
        usuario_actual: dict,
        habitacion_id,
        nombre: str,
        numero: int,
        tipo: str,
        precio: float,
        capacidad: int = 2,
        descripcion: str = "",
        imagen: str = ""
    ) -> tuple[bool, str]:
        """Actualiza los datos de una habitación existente."""
        rechazo = self._sin_permiso(usuario_actual)
        if rechazo:
            return rechazo

        if habitacion_id is None:
            return False, "Debe indicarse la habitación a editar."

        try:
            numero = self._convertir_numero(numero, "número de habitación")
            capacidad = self._convertir_numero(capacidad, "número de capacidad")
        except ValueError as exc:
            return False, str(exc)

        if tipo not in self.TIPOS_HABITACION:
            return False, "El tipo de habitación seleccionado no es válido."

        return self.dao.actualizar_habitacion(
            id=habitacion_id,
            nombre=nombre,
            no_habitacion=numero,
            tipo=tipo,
            precio=precio,
            capacidad=capacidad,
            descripcion=descripcion,
            imagen=imagen,
        )

    def eliminar_habitacion(self, usuario_actual: dict, habitacion_id) -> tuple[bool, str]:
        """Elimina una habitación del catálogo. Rechaza el borrado si tiene reservas."""
        rechazo = self._sin_permiso(usuario_actual)
        if rechazo:
            return rechazo

        if habitacion_id is None:
            return False, "Debe indicarse la habitación a eliminar."

        return self.dao.eliminar_habitacion(id=habitacion_id)

    def alternar_mantenimiento(self, usuario_actual: dict, habitacion_id) -> tuple[bool, str]:
        """Pone la habitación fuera de servicio o la devuelve a operación."""
        rechazo = self._sin_permiso(usuario_actual)
        if rechazo:
            return rechazo

        if habitacion_id is None:
            return False, "Debe indicarse la habitación."

        return self.dao.alternar_mantenimiento(
            id=habitacion_id,
            empleado_id=usuario_actual.get("id"),
        )

    def obtener_tareas_habitacion(self, fecha) -> list[dict]:
        """Tareas de limpieza y mantenimiento programadas para una fecha."""
        return self.dao.obtener_tareas_habitacion(fecha)

    def actualizar_tarea_habitacion(
        self, usuario_actual: dict, tarea_id, finalizar=False
    ) -> tuple[bool, str]:
        """Inicia o finaliza una tarea, validando sesión y permisos."""
        if not sesion_valida(usuario_actual):
            return False, "Debe iniciar sesión para gestionar tareas de habitaciones."
        if not es_id_valido(tarea_id):
            return False, "La tarea indicada no es válida."
        if finalizar and not es_administrador(usuario_actual):
            tarea = self.dao.obtener_tarea_habitacion(tarea_id)
            if tarea is None:
                return False, "La tarea ya no existe."
            if tarea.get("tipo") == "Mantenimiento técnico":
                return False, MENSAJE_SOLO_ADMIN

        return self.dao.actualizar_tarea_habitacion(
            tarea_id=tarea_id,
            empleado_id=usuario_actual["id"],
            finalizar=bool(finalizar),
        )

    def actualizar_precio_por_tipo(self, usuario_actual: dict, tipo, precio) -> tuple[bool, str]:
        """Ajusta de una vez el precio por noche de todas las habitaciones de un tipo."""
        rechazo = self._sin_permiso(usuario_actual)
        if rechazo:
            return rechazo

        if tipo not in self.TIPOS_HABITACION:
            return False, "El tipo de habitación seleccionado no es válido."
        if not es_precio_valido(precio):
            return False, "El precio debe ser un número mayor a cero."

        return self.dao.actualizar_precio_por_tipo(tipo=tipo, precio=precio)

    @staticmethod
    def _formatear_capacidad(capacidad) -> str:
        try:
            personas = int(capacidad)
        except (TypeError, ValueError):
            personas = 0
        return f"{personas} persona" if personas == 1 else f"{personas} personas"
