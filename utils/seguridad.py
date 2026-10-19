# utils/seguridad.py
"""Seguridad del personal: hash de contraseñas y control de acceso por rol.

La interfaz oculta los controles no autorizados, pero eso no es una barrera: la
verificación real vive aquí y se aplica en la capa de servicios, que es la
frontera por la que toda operación pasa. Un recepcionista no debe poder
administrar el catálogo aunque llame al servicio directamente.
"""
import hashlib
import hmac
import os

# ----------------------------------------------------------------------
# CONTRASEÑAS
# ----------------------------------------------------------------------
ALGORITMO = "pbkdf2_sha256"
ITERACIONES = 200_000
LONGITUD_SAL = 16


def generar_hash(password: str) -> str:
    """Genera un hash PBKDF2-SHA256 con sal aleatoria por usuario."""
    sal = os.urandom(LONGITUD_SAL)
    derivado = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), sal, ITERACIONES)
    return f"{ALGORITMO}${ITERACIONES}${sal.hex()}${derivado.hex()}"


def verificar_password(password: str, hash_guardado: str) -> bool:
    """Compara la contrasena en texto plano contra el hash almacenado."""
    if not password or not hash_guardado:
        return False

    try:
        algoritmo, iteraciones, sal_hex, hash_hex = hash_guardado.split("$")
        if algoritmo != ALGORITMO:
            return False

        esperado = bytes.fromhex(hash_hex)
        calculado = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(sal_hex), int(iteraciones)
        )
        return hmac.compare_digest(calculado, esperado)
    except (ValueError, AttributeError):
        return False


# ----------------------------------------------------------------------
# CONTROL DE ACCESO POR ROL
# ----------------------------------------------------------------------
ROL_ADMINISTRADOR = "administrador"
ROL_RECEPCIONISTA = "recepcionista"

ROLES_VALIDOS = (ROL_ADMINISTRADOR, ROL_RECEPCIONISTA)

# Operaciones reservadas al administrador del hotel.
ACCIONES_EXCLUSIVAS_DE_ADMIN = (
    "publicar habitación",
    "editar habitación",
    "eliminar habitación",
    "cambiar mantenimiento",
    "gestionar personal",
    "editar parámetros del hotel",
    "ajustar tarifas",
    "ver reportes",
    "editar reserva",
    "forzar salida con deuda",
    "reactivar reserva",
    "cancelar estancia iniciada",
)


MENSAJE_SIN_PERMISO = (
    "No tiene permisos para realizar esta operación. "
    "Solo un administrador puede modificar el catálogo de habitaciones."
)

MENSAJE_SOLO_ADMIN = (
    "No tiene permisos para realizar esta operación. "
    "Es una acción exclusiva del administrador del hotel."
)


def rol_de(usuario) -> str:
    """Extrae el rol de un diccionario de sesion, sin confiar en su formato."""
    if not isinstance(usuario, dict):
        return ""
    return str(usuario.get("rol") or "").strip().lower()


def es_administrador(usuario) -> bool:
    return rol_de(usuario) == ROL_ADMINISTRADOR


def es_recepcionista(usuario) -> bool:
    return rol_de(usuario) == ROL_RECEPCIONISTA


def sesion_valida(usuario) -> bool:
    """Una sesión utilizable debe traer identificación, nombre y un rol conocido.

    Se exige la sesión completa (y no solo un `id`) para que el servicio nunca
    acepte un fragmento de datos armado a mano por un llamante cualquiera.
    """
    if not isinstance(usuario, dict):
        return False
    if usuario.get("id") in (None, ""):
        return False
    if not str(usuario.get("nombre") or "").strip():
        return False
    return rol_de(usuario) in ROLES_VALIDOS


def puede_administrar_catalogo(usuario) -> bool:
    return es_administrador(usuario)
