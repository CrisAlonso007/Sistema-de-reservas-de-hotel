# utils/validaciones.py
import re


def es_texto_valido(texto: str, longitud_minima: int = 1, longitud_maxima: int | None = None) -> bool:
    """
    Verifica que la cadena no sea None, no esté vacía, no contenga
    únicamente espacios y cumpla la longitud mínima/máxima indicada.
    """
    if texto is None:
        return False

    texto_limpio = str(texto).strip()
    if len(texto_limpio) < longitud_minima:
        return False

    if longitud_maxima is not None and len(texto_limpio) > longitud_maxima:
        return False

    return True


def es_usuario_valido(usuario: str) -> bool:
    """Valida un nombre de usuario simple."""
    if not es_texto_valido(usuario, longitud_minima=3, longitud_maxima=20):
        return False
    return bool(re.fullmatch(r"[A-Za-z0-9_]+", usuario.strip()))


def es_password_valido(password: str) -> bool:
    """Valida una contraseña con longitud mínima y sin espacios."""
    if not es_texto_valido(password, longitud_minima=4, longitud_maxima=30):
        return False
    return not any(caracter.isspace() for caracter in password)


def es_numero_habitacion_valido(valor: str) -> bool:
    """Valida que el número de habitación sea numérico y positivo."""
    if not es_texto_valido(valor, longitud_minima=1, longitud_maxima=6):
        return False
    return bool(re.fullmatch(r"\d{1,6}", str(valor).strip()))


def es_capacidad_valida(valor: str) -> bool:
    """Valida que la capacidad contenga un número entero positivo."""
    if not es_texto_valido(valor):
        return False

    coincidencia = re.search(r"\d+", str(valor).strip())
    if not coincidencia:
        return False

    return int(coincidencia.group()) > 0


def es_identificacion_valida(valor: str) -> bool:
    """Valida una identificación con formato alfanumérico simple."""
    if not es_texto_valido(valor, longitud_minima=5, longitud_maxima=20):
        return False
    return bool(re.fullmatch(r"[A-Za-z0-9-]+", str(valor).strip()))


def es_noches_valida(valor: str) -> bool:
    """Valida que la cantidad de noches sea un entero positivo."""
    if not es_texto_valido(valor):
        return False

    try:
        cantidad = int(str(valor).strip())
    except (TypeError, ValueError):
        return False

    return cantidad > 0


def es_precio_valido(valor: str) -> bool:
    """
    Verifica que el valor sea un número positivo y mayor a cero.
    Limpiando prefijos como el símbolo '$'.
    """
    try:
        valor_limpio = str(valor).replace("$", "").strip()
        precio = float(valor_limpio)
        return 0 < precio <= 10000
    except (ValueError, TypeError):
        return False