# utils/permisos.py
"""Control de acceso por rol.

La interfaz oculta los botones no autorizados, pero eso no es una barrera: la
verificacion real vive aqui y se aplica en la capa de servicios, que es la
frontera por la que toda operacion pasa. Un recepcionista no debe poder
administrar el catalogo aunque llame al servicio directamente.
"""

ROL_ADMINISTRADOR = "administrador"
ROL_RECEPCIONISTA = "recepcionista"

ROLES_VALIDOS = (ROL_ADMINISTRADOR, ROL_RECEPCIONISTA)

# Operaciones reservadas al administrador del hotel.
ACCIONES_EXCLUSIVAS_DE_ADMIN = (
    "publicar habitación",
    "editar habitación",
    "eliminar habitación",
    "cambiar mantenimiento",
)

MENSAJE_SIN_PERMISO = (
    "No tiene permisos para realizar esta operación. "
    "Solo un administrador puede modificar el catálogo de habitaciones."
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
