import os

class HabitacionService:
    def __init__(self):
        # 1. Obtenemos la ruta raíz del proyecto (subiendo un nivel desde 'services')
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # 2. Construimos la ruta dinámica hacia la carpeta de recursos
        ruta_foto_defecto = os.path.join(base_dir, "recursos", "habitacion1.jpg")

        self.habitaciones = [
            {
                "nombre": "Suite Presidencial Vista al Mar",
                "numero": "101",
                "tipo": "Suite",
                "precio": 150.00,
                "capacidad": "2 Personas",
                "descripcion": "Incluye cama King Size, jacuzzi privado, vista panorámica al mar y servicio a la habitación 24/7.",
                "estado": "Disponible",
                "imagen": ruta_foto_defecto  # <--- Ruta dinámica y portable
            }
        ]
    def obtener_todas(self) -> list[dict]:
        return self.habitaciones

    def agregar_habitacion(
        self, 
        nombre: str, 
        numero: str, 
        tipo: str, 
        precio: float, 
        capacidad: str = "", 
        descripcion: str = "", 
        imagen: str = ""
    ) -> bool:
        nueva = {
            "nombre": nombre,
            "numero": numero,
            "tipo": tipo,
            "precio": precio,
            "capacidad": capacidad,
            "descripcion": descripcion,
            "estado": "Disponible",
            "imagen": imagen
        }
        self.habitaciones.append(nueva)
        return True