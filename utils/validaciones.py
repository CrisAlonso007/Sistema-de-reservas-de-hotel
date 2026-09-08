# utils/validaciones.py

def es_texto_valido(texto: str) -> bool:
    """
    Verifica que la cadena no sea None, no esté vacía 
    y no contenga únicamente espacios en blanco.
    """
    if texto is None:
        return False
    return len(texto.strip()) > 0


def es_precio_valido(valor: str) -> bool:
    """
    Verifica que el valor sea un número positivo y mayor a cero.
    Limpiando prefijos como el símbolo '$'.
    """
    try:
        # Elimina espacios y el signo de dólar si vienen en el string
        valor_limpio = str(valor).replace("$", "").strip()
        precio = float(valor_limpio)
        return precio > 0
    except (ValueError, TypeError):
        return False