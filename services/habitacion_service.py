import os
from DATABASE.registro import RegistroDAO

class HabitacionService:
    def __init__(self):
        self.dao = RegistroDAO()

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.ruta_foto_defecto = os.path.join(base_dir, "recursos", "habitacion1.jpg")

    def realizar_reserva(self, **datos) -> tuple[bool, str]:
        """Registra una reserva con todos sus datos de estancia y pago."""
        return self.dao.realizar_reserva(**datos)

    @staticmethod
    def _convertir_numero(numero):
        if numero in (None, ""):
            return None
        try:
            return int(numero)
        except (TypeError, ValueError):
            raise ValueError("El número de habitación debe ser un entero válido.")

    @staticmethod
    def tipo_para_presentacion(tipo):
        """Convierte el valor persistido al nombre mostrado en la interfaz."""
        return "Presidencial" if tipo == "Presencial" else tipo

    def obtener_todas(self) -> list[dict]:
        """Llama al DAO para traer las habitaciones y les asigna la imagen por defecto."""
        habitaciones = self.dao.obtener_habitaciones()

        for hab in habitaciones:
            tipo = hab.get("tipo")
            hab["tipo"] = self.tipo_para_presentacion(tipo)
            if "imagen" not in hab or not hab["imagen"]:
                hab["imagen"] = self.ruta_foto_defecto

        return habitaciones

    def agregar_habitacion(
        self,
        nombre: str,
        numero: int,
        tipo: str,
        precio: float,
        capacidad: str = "",
        descripcion: str = "",
        imagen: str = ""
    ) -> tuple[bool, str]:
        """Guarda la habitación a través del DAO."""
        try:
            numero = self._convertir_numero(numero)
        except ValueError as exc:
            return False, str(exc)

        exito, mensaje = self.dao.registrar_habitacion(
            nombre=nombre,
            no_habitacion=numero,
            tipo=tipo,
            precio=precio,
            capacidad=capacidad,
            descripcion=descripcion
        )
        return exito, mensaje

    def editar_habitacion(
        self,
        habitacion_id=None,
        nombre: str = "",
        numero: int = None,
        tipo: str = "",
        precio: float = 0.0,
        capacidad: str = "",
        descripcion: str = "",
        imagen: str = ""
    ) -> tuple[bool, str]:
        """Actualiza una habitación existente en la base de datos."""
        if habitacion_id is None and numero is None:
            return False, "Debe indicarse el ID o el número de la habitación a editar."

        try:
            numero = self._convertir_numero(numero) if numero is not None else None
        except ValueError as exc:
            return False, str(exc)

        exito, mensaje = self.dao.actualizar_habitacion(
            id=habitacion_id,
            nombre=nombre,
            no_habitacion=numero,
            tipo=tipo,
            precio=precio,
            capacidad=capacidad,
            descripcion=descripcion
        )
        return exito, mensaje

    def eliminar_habitacion(self, numero=None, habitacion_id=None) -> tuple[bool, str]:
        """Elimina una habitación por ID o por su número."""
        if habitacion_id is None and numero is None:
            return False, "Debe indicarse el ID o el número de la habitación a eliminar."

        try:
            numero = self._convertir_numero(numero) if numero is not None else None
        except ValueError as exc:
            return False, str(exc)

        return self.dao.eliminar_habitacion(id=habitacion_id, no_habitacion=numero)