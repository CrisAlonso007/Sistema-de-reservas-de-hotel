import os
from DATABASE.registro import RegistroDAO

class HabitacionService:
    def __init__(self):
        self.dao = RegistroDAO()
        
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.ruta_foto_defecto = os.path.join(base_dir, "recursos", "habitacion1.jpg")

    def obtener_todas(self) -> list[dict]:
        """Llama al DAO para traer las habitaciones y les asigna la imagen por defecto."""
        habitaciones = self.dao.obtener_habitaciones()
        
        for hab in habitaciones:
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
        exito, mensaje = self.dao.registrar_habitacion(
            nombre=nombre,
            no_habitacion=numero,
            tipo=tipo,
            precio=precio,
            capacidad=capacidad,
            descripcion=descripcion
        )
        return exito, mensaje