# utils/validaciones.py
import re
from decimal import Decimal, InvalidOperation
from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import QLabel
from utils.stylesheets import ESTILO_CAMPO_INVALIDO, ESTILO_CAMPO_VALIDO

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
        return cantidad > 0
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


class ValidadorCampo:
    """Valida un campo Qt y actualiza sus indicadores visuales."""

    def __init__(self, campo, etiqueta_error=None, funcion_validar=None, filtro=None,
                 bloquear=True, estilos=None):
        self.campo = campo
        self.etiqueta_error = etiqueta_error
        self.funcion_validar = funcion_validar
        self.filtro = filtro
        self.bloquear = bloquear
        self.estilos = estilos or (ESTILO_CAMPO_VALIDO, ESTILO_CAMPO_INVALIDO)

        self._conectado = False
        self._validando = False

    def conectar(self):
        if self._conectado:
            return
        self.campo.textChanged.connect(self._on_text_changed)
        self.campo.editingFinished.connect(self._on_editing_finished)
        self._conectado = True
        self.validar()

    def _on_text_changed(self, texto):
        if self._validando:
            return
        if self.bloquear and self.filtro:
            self._validando = True
            limpio = self.filtro(texto)
            if limpio != texto:
                cursor = self.campo.cursorPosition()
                self.campo.setText(limpio)
                self.campo.setCursorPosition(min(cursor, len(limpio)))
            self._validando = False
        self.validar()

    def _on_editing_finished(self):
        self.validar(forzar=True)

    def validar(self, forzar=False):
        """Valida el campo y devuelve su estado, actualizando su indicador visual."""
        texto = self.campo.text()
        if self.funcion_validar:
            resultado = self.funcion_validar(texto)
            if isinstance(resultado, tuple):
                valido, mensaje = resultado
            else:
                valido = bool(resultado)
                mensaje = "" if valido else "Campo inválido."
        else:
            valido = es_texto_valido(texto)
            mensaje = "" if valido else "Campo obligatorio."

        if not texto.strip() and not forzar:
            self.campo.setStyleSheet("")
            if self.etiqueta_error:
                self.etiqueta_error.setText("")
                self.etiqueta_error.hide()
            return False

        if valido:
            self.campo.setStyleSheet(self.estilos[0])
            if self.etiqueta_error:
                self.etiqueta_error.setText("")
                self.etiqueta_error.hide()
        else:
            self.campo.setStyleSheet(self.estilos[1])
            if self.etiqueta_error and mensaje:
                self.etiqueta_error.setText(mensaje)
                self.etiqueta_error.show()
        return valido


def aplicar_validador(campo, etiqueta_error=None, funcion_validar=None, filtro=None,
                     bloquear=True):
    validador = ValidadorCampo(campo, etiqueta_error, funcion_validar, filtro, bloquear)
    validador.conectar()
    return validador


def crear_etiqueta_error(parent=None):
    lbl = QLabel(parent)
    lbl.setStyleSheet("color: #d9534f; font-size: 11px;")
    lbl.setWordWrap(True)
    lbl.hide()
    return lbl


def aplicar_regex_bloqueo(campo, patron):
    validador_regex = QRegularExpressionValidator(QRegularExpression(patron), campo)
    campo.setValidator(validador_regex)
    return validador_regex


def habilitar_validacion_boton(campo_validadores, boton):
    """Habilita o deshabilita un botón según los validadores de sus campos."""
    def revisar():
        todo_ok = True
        for validador in campo_validadores:
            texto = validador.campo.text()
            if validador.funcion_validar:
                resultado = validador.funcion_validar(texto)
                if isinstance(resultado, tuple):
                    valido, _ = resultado
                else:
                    valido = bool(resultado)
            else:
                valido = es_texto_valido(texto)
            if not valido or not texto.strip():
                todo_ok = False
                break
        boton.setEnabled(todo_ok)

    for validador in campo_validadores:
        validador.campo.textChanged.connect(revisar)
        validador.campo.editingFinished.connect(revisar)
    revisar()
    return revisar
