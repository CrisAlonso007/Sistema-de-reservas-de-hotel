# utils/seguridad.py
import hashlib
import hmac
import os

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
