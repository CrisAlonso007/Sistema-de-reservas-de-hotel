# ui/validacion_helpers.py
from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtCore import QRegularExpression

from utils.stylesheets import ESTILO_CAMPO_VALIDO, ESTILO_CAMPO_INVALIDO
from utils import validaciones as v


class ValidadorCampo:
    """Ayudante para validación inmediata en formularios."""

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
        self._on_editing_finished()

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
        self._validar_mostrar()

    def _on_editing_finished(self):
        self._validar_mostrar(forzar=True)

    def _validar_mostrar(self, forzar=False):
        texto = self.campo.text()
        if self.funcion_validar:
            resultado = self.funcion_validar(texto)
            if isinstance(resultado, tuple):
                valido, mensaje = resultado
            else:
                valido = bool(resultado)
                mensaje = "" if valido else "Campo inválido."
        else:
            valido = v.es_texto_valido(texto)
            mensaje = "" if valido else "Campo obligatorio."

        if not texto.strip() and not forzar:
            self.campo.setStyleSheet("")
            if self.etiqueta_error:
                self.etiqueta_error.setText("")
                self.etiqueta_error.hide()
            return

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
    """Habilita/deshabilita botón según validaciones."""
    def revisar():
        todo_ok = True
        for validador in campo_validadores:
            texto = validador.campo.text()
            if validador.funcion_validar:
                res = validador.funcion_validar(texto)
                if isinstance(res, tuple):
                    valido, _ = res
                else:
                    valido = bool(res)
            else:
                valido = v.es_texto_valido(texto)
            if not valido or not texto.strip():
                todo_ok = False
                break
        boton.setEnabled(todo_ok)
    for validador in campo_validadores:
        validador.campo.textChanged.connect(revisar)
        validador.campo.editingFinished.connect(revisar)
    revisar()
    return revisar
