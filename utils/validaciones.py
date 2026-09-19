# utils/validaciones.py
import re
from datetime import datetime

# ----------------------------------------------------------------------
# VALIDACIÓN BASE / GENÉRICA DE TEXTO
# ----------------------------------------------------------------------
def es_texto_valido(texto: str, longitud_minima: int = 1, longitud_maxima: int | None = None) -> bool:
    """Verifica que la cadena no sea None, no esté vacía ni contenga solo espacios."""
    if texto is None:
        return False

    texto_limpio = str(texto).strip()
    if len(texto_limpio) < longitud_minima:
        return False

    if longitud_maxima is not None and len(texto_limpio) > longitud_maxima:
        return False

    return True


# ----------------------------------------------------------------------
# VALIDACIONES INDIVIDUALES PARA PUBLICACIÓN DE HABITACIÓN
# ----------------------------------------------------------------------
def nombre_habitacion_valido(nombre: str) -> bool:
    """Valida un nombre de habitación (3-50 caracteres alfanuméricos con acentos y espacios)."""
    if not isinstance(nombre, str):
        return False
    nombre_limpio = nombre.strip()
    if not (3 <= len(nombre_limpio) <= 50):
        return False
    return bool(re.fullmatch(r"[A-Za-z0-9ÁÉÍÓÚáéíóúÑñ\s]+", nombre_limpio))


def precio_habitacion_valido(precio: str | float | int) -> bool:
    """Valida que el precio sea un número positivo entre 0.01 y 10000."""
    return es_precio_valido(precio)


def descripcion_habitacion_valida(descripcion: str) -> bool:
    """Valida la descripción de la habitación (10-500 caracteres)."""
    if not isinstance(descripcion, str):
        return False
    desc_limpia = descripcion.strip()
    return 10 <= len(desc_limpia) <= 500


# ----------------------------------------------------------------------
# VALIDACIONES INDIVIDUALES PARA REGISTRO DE USUARIOS Y CONTACTO
# ----------------------------------------------------------------------
def validar_correo(correo: str) -> bool:
    """Valida un correo electrónico independiente de otras reglas."""
    if not isinstance(correo, str):
        return False
    correo_limpio = correo.strip()
    if not (5 <= len(correo_limpio) <= 100):
        return False
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", correo_limpio))


def es_usuario_valido(usuario: str) -> bool:
    """Valida un nombre de usuario (3-20 caracteres: letras, números o guion bajo)."""
    if not isinstance(usuario, str):
        return False
    usr_limpio = usuario.strip()
    if not (3 <= len(usr_limpio) <= 20):
        return False
    return bool(re.fullmatch(r"[A-Za-z0-9_]+", usr_limpio))


def es_password_valido(password: str) -> bool:
    """Valida una contraseña (4-30 caracteres, sin espacios en blanco)."""
    if not isinstance(password, str):
        return False
    if not (4 <= len(password) <= 30):
        return False
    return not any(caracter.isspace() for caracter in password)


def es_identificacion_valida(valor: str) -> bool:
    """Valida número de cédula o pasaporte (5-20 caracteres alfanuméricos con guiones)."""
    if valor is None:
        return False
    val_limpio = str(valor).strip()
    if not (5 <= len(val_limpio) <= 20):
        return False
    return bool(re.fullmatch(r"[A-Za-z0-9-]+", val_limpio))


def validar_nombre_completo(nombre: str) -> bool:
    """Valida un nombre personal (2-100 caracteres: letras, espacios, guiones o apóstrofes)."""
    if not isinstance(nombre, str):
        return False
    nom_limpio = nombre.strip()
    if not (2 <= len(nom_limpio) <= 100):
        return False
    return bool(re.fullmatch(r"[A-Za-zÁÉÍÓÚáéíóúÑñ]+(?:[ '\-][A-Za-zÁÉÍÓÚáéíóúÑñ]+)*", nom_limpio))


def validar_telefono(telefono: str) -> bool:
    """Valida número telefónico nacional e internacional con formato amplio."""
    if telefono is None:
        return False
    tel_limpio = str(telefono).strip()
    if not (5 <= len(tel_limpio) <= 100):
        return False
    return bool(re.fullmatch(r"\+?[0-9][0-9 ()-]{5,18}[0-9]", tel_limpio))


# ----------------------------------------------------------------------
# VALIDACIONES INDIVIDUALES PARA RESERVAS Y PRECIOS
# ----------------------------------------------------------------------
def es_fecha_valida(fecha: str) -> bool:
    """Valida formato YYYY-MM-DD y que no sea una fecha pasada."""
    if not isinstance(fecha, str):
        return False

    try:
        fecha_obj = datetime.strptime(fecha.strip(), "%Y-%m-%d")
        fecha_actual = datetime.now()
        return fecha_obj.date() >= fecha_actual.date()
    except (ValueError, AttributeError):
        return False


def es_noches_valida(valor: str | int) -> bool:
    """Valida que la cantidad de noches sea un entero mayor a cero."""
    if valor is None:
        return False

    try:
        cantidad = int(str(valor).strip())
        return cantidad > 0
    except (TypeError, ValueError):
        return False


def es_precio_valido(valor: str | float | int) -> bool:
    """Verifica que el valor sea un número positivo menor o igual a 10000."""
    if valor is None:
        return False

    try:
        valor_limpio = str(valor).replace("$", "").replace(",", "").strip()
        precio = float(valor_limpio)
        return 0 < precio <= 10000
    except (TypeError, ValueError):
        return False