# utils/validaciones.py
import re
from decimal import Decimal, InvalidOperation

# Límites alineados con el esquema MySQL (ver DATABASE/BD_Registro.sql)
MAX_NOMBRE_HABITACION = 100
MAX_DESCRIPCION_HABITACION = 255
MAX_NOMBRE_HUESPED = 100
MAX_TELEFONO = 50

# ----------------------------------------------------------------------
# PATRONES REUTILIZABLES
# ----------------------------------------------------------------------
EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
SOLO_LETRAS_ESPACIOS_RE = re.compile(r"^[A-Za-zÁÉÍÓÚáéíóúÑñ]+(?:[ '\-][A-Za-zÁÉÍÓÚáéíóúÑñ]+)*$")
USUARIO_RE = re.compile(r"^[A-Za-z0-9_]{3,20}$")
IDENTIFICACION_RE = re.compile(r"^[A-Za-z0-9\-]{5,20}$")
TELEFONO_RE = re.compile(r"^\+?[0-9][0-9 ()\-]{4,18}[0-9]$")
NUMEROS_SOLO_RE = re.compile(r"^[0-9]+$")
NUMEROS_ENTEROS_RE = re.compile(r"^-?[0-9]+$")
DECIMAL_RE = re.compile(r"^-?[0-9]+([.,][0-9]+)?$")


def normalizar(texto):
    """Normaliza texto quitando espacios al inicio/fin."""
    if texto is None:
        return ""
    return str(texto).strip()


def normalizar_mayusculas(texto):
    """Normaliza texto quitando espacios y pasando a mayúsculas."""
    return normalizar(texto).upper()


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
# VALIDACIONES INMEDIATAS PARA UI
# ----------------------------------------------------------------------
def filtrar_solo_letras(texto: str) -> str:
    """Filtra solo letras, espacios, guiones y apóstrofes."""
    return re.sub(r"[^A-Za-zÁÉÍÓÚáéíóúÑñ '\-]", "", texto)


def filtrar_solo_numeros(texto: str) -> str:
    """Filtra solo números."""
    return re.sub(r"[^0-9]", "", texto)


def filtrar_telefono(texto: str) -> str:
    """Filtra caracteres válidos para teléfono."""
    return re.sub(r"[^0-9+\-\s()]", "", texto)


def filtrar_identificacion(texto: str) -> str:
    """Filtra caracteres válidos para identificación."""
    return re.sub(r"[^A-Za-z0-9\-]", "", texto)


def filtrar_usuario(texto: str) -> str:
    """Filtra caracteres válidos para usuario."""
    return re.sub(r"[^A-Za-z0-9_]", "", texto)


def filtrar_precio(texto: str) -> str:
    """Filtra caracteres válidos para precio."""
    return re.sub(r"[^0-9.,]", "", texto)


# ----------------------------------------------------------------------
# VALIDACIONES DEL CATALOGO DE HABITACIONES
# ----------------------------------------------------------------------
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


def es_precio_positivo_valido(valor: str | float | int) -> bool:
    """Verifica que el precio sea mayor a 0 y válido."""
    return es_precio_valido(valor)


def es_capacidad_valida(valor: str | int) -> bool:
    """Verifica que la capacidad sea un entero entre 1 y 10."""
    if valor is None:
        return False
    try:
        cantidad = int(str(valor).strip())
        return 1 <= cantidad <= 10
    except (TypeError, ValueError):
        return False


def es_numero_habitacion_valido(valor: str | int) -> bool:
    """Verifica que el número de habitación sea un entero positivo."""
    if valor is None:
        return False
    try:
        numero = int(str(valor).strip())
        return 1 <= numero <= 9999
    except (TypeError, ValueError):
        return False


# ----------------------------------------------------------------------
# VALIDACIONES DEL PERSONAL Y DEL CONTACTO DEL HUESPED
# ----------------------------------------------------------------------
def es_usuario_valido(usuario: str) -> bool:
    """Valida un nombre de usuario (3-20 caracteres: letras, números o guion bajo)."""
    if not isinstance(usuario, str):
        return False
    usr_limpio = usuario.strip()
    if not (3 <= len(usr_limpio) <= 20):
        return False
    return bool(re.fullmatch(r"[A-Za-z0-9_]+", usr_limpio))


def es_usuario_valido_inmediato(usuario: str) -> tuple[bool, str]:
    """Validación inmediata para usuario con mensaje de error."""
    usr = normalizar(usuario)
    if not usr:
        return False, "El usuario es obligatorio."
    if len(usr) < 3:
        return False, "El usuario debe tener al menos 3 caracteres."
    if len(usr) > 20:
        return False, "El usuario no puede tener más de 20 caracteres."
    if not re.fullmatch(r"[A-Za-z0-9_]+", usr):
        return False, "Solo se permiten letras, números y guion bajo."
    return True, ""


def es_password_valido(password: str) -> bool:
    """Valida una contraseña (4-30 caracteres, sin espacios en blanco)."""
    if not isinstance(password, str):
        return False
    if not (4 <= len(password) <= 30):
        return False
    return not any(caracter.isspace() for caracter in password)


def es_password_valido_inmediato(password: str) -> tuple[bool, str]:
    """Validación inmediata para contraseña con mensaje de error."""
    pwd = str(password) if password is not None else ""
    if not pwd.strip():
        return False, "La contraseña es obligatoria."
    if " " in pwd:
        return False, "La contraseña no puede contener espacios."
    if len(pwd) < 4:
        return False, "La contraseña debe tener al menos 4 caracteres."
    if len(pwd) > 30:
        return False, "La contraseña no puede tener más de 30 caracteres."
    return True, ""


def es_identificacion_valida(valor: str) -> bool:
    """Valida número de cédula o pasaporte (5-20 caracteres alfanuméricos con guiones)."""
    if valor is None:
        return False
    val_limpio = str(valor).strip()
    if not (5 <= len(val_limpio) <= 20):
        return False
    return bool(re.fullmatch(r"[A-Za-z0-9-]+", val_limpio))


def es_identificacion_valida_inmediato(valor: str) -> tuple[bool, str]:
    """Validación inmediata para identificación con mensaje de error."""
    ident = normalizar(valor).upper()
    if not ident:
        return False, "El documento de identidad es obligatorio."
    if len(ident) < 5:
        return False, "El documento debe tener al menos 5 caracteres."
    if len(ident) > 20:
        return False, "El documento no puede tener más de 20 caracteres."
    if not IDENTIFICACION_RE.match(ident):
        return False, "Solo se permiten letras, números y guiones."
    return True, ""


def validar_nombre_completo(nombre: str) -> bool:
    """Valida un nombre personal (2-100 caracteres: letras, espacios, guiones o apóstrofes)."""
    if not isinstance(nombre, str):
        return False
    nom_limpio = nombre.strip()
    if not (2 <= len(nom_limpio) <= MAX_NOMBRE_HUESPED):
        return False
    return bool(re.fullmatch(r"[A-Za-zÁÉÍÓÚáéíóúÑñ]+(?:[ '\-][A-Za-zÁÉÍÓÚáéíóúÑñ]+)*", nom_limpio))


def validar_nombre_completo_inmediato(nombre: str) -> tuple[bool, str]:
    """Validación inmediata para nombre completo con mensaje de error."""
    nom = normalizar(nombre)
    if not nom:
        return False, "El nombre completo es obligatorio."
    if len(nom) < 2:
        return False, "El nombre debe tener al menos 2 caracteres."
    if len(nom) > MAX_NOMBRE_HUESPED:
        return False, f"El nombre no puede tener más de {MAX_NOMBRE_HUESPED} caracteres."
    if not SOLO_LETRAS_ESPACIOS_RE.match(nom):
        return False, "Solo se permiten letras, espacios, guiones y apóstrofes."
    return True, ""


def validar_telefono(telefono: str) -> bool:
    """Valida número telefónico nacional e internacional con formato amplio."""
    if telefono is None:
        return False
    tel_limpio = str(telefono).strip()
    if not (5 <= len(tel_limpio) <= MAX_TELEFONO):
        return False
    return bool(re.fullmatch(r"\+?[0-9][0-9 ()-]{5,18}[0-9]", tel_limpio))


def validar_telefono_inmediato(telefono: str) -> tuple[bool, str]:
    """Validación inmediata para teléfono con mensaje de error."""
    tel = normalizar(telefono)
    if not tel:
        return False, "El teléfono es obligatorio."
    if len(tel) < 7:
        return False, "El teléfono debe tener al menos 7 caracteres."
    if len(tel) > MAX_TELEFONO:
        return False, f"El teléfono no puede tener más de {MAX_TELEFONO} caracteres."
    if not re.match(r"^[0-9+\-\s()]+$", tel):
        return False, "Solo se permiten números, +, -, espacios y paréntesis."
    if not any(c.isdigit() for c in tel):
        return False, "El teléfono debe contener al menos un número."
    if not TELEFONO_RE.match(tel.replace(" ", "").replace("(", "").replace(")", "")) and not re.fullmatch(r"\+?[0-9][0-9 ()-]{5,18}[0-9]", tel):
        return False, "Formato de teléfono inválido."
    return True, ""


def es_correo_valido(correo: str) -> bool:
    """Valida un correo electrónico con formato básico (usuario@dominio.tld)."""
    if not isinstance(correo, str):
        return False
    correo_limpio = correo.strip()
    if not (5 <= len(correo_limpio) <= 255):
        return False
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", correo_limpio))


def es_correo_valido_inmediato(correo: str) -> tuple[bool, str]:
    """Validación inmediata para correo con mensaje de error."""
    mail = normalizar(correo)
    if not mail:
        return False, "El correo electrónico es obligatorio."
    if len(mail) > 255:
        return False, "El correo es demasiado largo."
    if " " in mail:
        return False, "El correo no puede contener espacios."
    if "@" not in mail:
        return False, "El correo debe contener @."
    if not EMAIL_RE.match(mail):
        return False, "Formato de correo electrónico inválido."
    partes = mail.split("@")
    if len(partes) != 2 or not partes[0] or not partes[1]:
        return False, "Formato de correo electrónico inválido."
    if "." not in partes[1]:
        return False, "El dominio debe contener un punto."
    return True, ""


# ----------------------------------------------------------------------
# VALIDACIONES DE LAS ESTANCIAS
# ----------------------------------------------------------------------
def es_id_valido(valor) -> bool:
    """Valida un identificador de base de datos: entero positivo."""
    if valor is None or isinstance(valor, bool):
        return False
    try:
        return int(valor) > 0
    except (TypeError, ValueError):
        return False


def es_noches_valida(valor: str | int) -> bool:
    """Valida que la cantidad de noches sea un entero mayor a cero."""
    if valor is None:
        return False

    try:
        cantidad = int(str(valor).strip())
        return 0 < cantidad <= 365
    except (TypeError, ValueError):
        return False


def es_monto_cobro_valido(monto, saldo_pendiente) -> tuple[bool, str]:
    """Valida que el monto a cobrar sea mayor a 0 y no supere el saldo."""
    try:
        m_str = str(monto).replace(",", ".").strip()
        s_str = str(saldo_pendiente or 0).replace(",", ".").strip()
        if not m_str:
            return False, "El monto es obligatorio."
        monto_dec = Decimal(m_str)
        saldo_dec = Decimal(s_str)
        if monto_dec <= 0:
            return False, "El monto debe ser mayor a 0."
        if monto_dec > saldo_dec + Decimal("0.01"):
            return False, "El monto no puede superar el saldo pendiente."
        return True, ""
    except (InvalidOperation, TypeError):
        return False, "Monto inválido."

