# utils/stylesheets.py
from PySide6.QtGui import QColor, QPalette


def configurar_tema_aplicacion(app):
    """Aplica una paleta clara uniforme en todos los equipos."""
    app.setStyle("Fusion")

    palette = QPalette()
    colores = {
        QPalette.ColorRole.Window: "#f4f6f8",
        QPalette.ColorRole.WindowText: "#1f2d3d",
        QPalette.ColorRole.Base: "#ffffff",
        QPalette.ColorRole.AlternateBase: "#eef2f6",
        QPalette.ColorRole.ToolTipBase: "#1f2d3d",
        QPalette.ColorRole.ToolTipText: "#ffffff",
        QPalette.ColorRole.Text: "#1f2d3d",
        QPalette.ColorRole.Button: "#ffffff",
        QPalette.ColorRole.ButtonText: "#1f2d3d",
        QPalette.ColorRole.BrightText: "#b42318",
        QPalette.ColorRole.Link: "#1d7488",
        QPalette.ColorRole.Highlight: "#d9eeee",
        QPalette.ColorRole.HighlightedText: "#1f2d3d",
        QPalette.ColorRole.PlaceholderText: "#6b7c8f",
        QPalette.ColorRole.Light: "#ffffff",
        QPalette.ColorRole.Midlight: "#e4e9ef",
        QPalette.ColorRole.Dark: "#9eacba",
        QPalette.ColorRole.Mid: "#c3ccd6",
        QPalette.ColorRole.Shadow: "#6b7c8f",
    }

    for role, color in colores.items():
        palette.setColor(QPalette.ColorGroup.Active, role, QColor(color))
        palette.setColor(QPalette.ColorGroup.Inactive, role, QColor(color))

    colores_deshabilitados = {
        QPalette.ColorRole.WindowText: "#7b8998",
        QPalette.ColorRole.Base: "#f1f3f5",
        QPalette.ColorRole.Text: "#7b8998",
        QPalette.ColorRole.Button: "#eef2f6",
        QPalette.ColorRole.ButtonText: "#7b8998",
        QPalette.ColorRole.PlaceholderText: "#8a97a6",
    }
    for role, color in colores_deshabilitados.items():
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor(color))

    app.setPalette(palette)


ESTILO_SELECTOR_IMAGEN = """
    QLabel {
        border: 2px dashed #aaa;
        border-radius: 8px;
        background-color: #f9f9f9;
        color: #555;
    }
"""

TARJETAS_ESTILO = """
    QLabel {
        border: 1px solid #ccc; 
        background-color: #f2f2f2; 
        border-radius: 6px;
    }
"""

ESTILO_CAMPO_VALIDO = """
    border: 1px solid #5cb85c;
    background-color: #f1fff5;
"""

ESTILO_CAMPO_INVALIDO = """
    border: 1px solid #d9534f;
    background-color: #fff1f1;
"""

ESTILO_PRECIO_VALIDO = """
    border: 1px solid #5cb85c;
    background-color: #f1fff5;
"""

ESTILO_PRECIO_INVALIDO = """
    border: 1px solid #d9534f;
    background-color: #fff1f1;
"""

# ----------------------------------------------------------------------
# BANNER SUPERIOR Y NAVEGACION
# ----------------------------------------------------------------------
ESTILO_BANNER = """
    QWidget#bannerContenedor {
        background-color: #1f2d3d;
        border-bottom: 2px solid #61b7b7;
    }
    QLabel#bannerMarca {
        background-color: #ffffff;
        border: 1px solid #d5e5e8;
        border-radius: 8px;
    }
    QLabel#bannerTitulo {
        color: #71c2bd;
        font-size: 18px;
        font-weight: bold;
    }
    QLabel#bannerSubtitulo {
        color: #a8bac8;
        font-size: 11px;
    }

    /* Navegacion */
    QPushButton#bannerBoton {
        color: #cfd8e3;
        background-color: transparent;
        border: 1px solid transparent;
        border-radius: 6px;
        padding: 7px 16px;
        font-size: 13px;
    }
    QPushButton#bannerBoton:hover {
        background-color: #2b3d52;
        color: #ffffff;
    }
    QPushButton#bannerBoton:checked {
        background-color: #1d7488;
        color: #ffffff;
        font-weight: bold;
    }

    /* Sesion y notificaciones */
    QPushButton#bannerUsuario {
        color: #ffffff;
        background-color: #2b3d52;
        border: 1px solid #46596e;
        border-radius: 6px;
        padding: 7px 14px;
        font-size: 13px;
    }
    QPushButton#bannerUsuario:hover {
        background-color: #3a4f68;
    }
    QPushButton#campanaNotificaciones {
        color: #cfd8e3;
        background-color: transparent;
        border: 1px solid #46596e;
        border-radius: 6px;
        padding: 7px 12px;
        font-size: 12px;
    }
    QPushButton#campanaNotificaciones:hover {
        background-color: #2b3d52;
        color: #ffffff;
    }
    /* Cuando hay avisos pendientes la campana se pinta en rojo para llamar la
       atención sin recurrir a un ícono externo. */
    QPushButton#campanaNotificaciones[conAvisos="true"] {
        color: #ffffff;
        background-color: #c0392b;
        border: 1px solid #c0392b;
        font-weight: bold;
    }
"""

# ----------------------------------------------------------------------
# PANEL / TABLERO
# ----------------------------------------------------------------------
ESTILO_PANEL = """
    QWidget#panelRaiz {
        background-color: #f4f6f8;
    }
    QLabel#panelTitulo {
        color: #1f2d3d;
        font-size: 19px;
        font-weight: bold;
    }
    QLabel#panelSubtitulo {
        color: #6b7c8f;
        font-size: 12px;
    }
    QFrame#tarjetaKpi {
        background-color: #ffffff;
        border: 1px solid #dfe4ea;
        border-radius: 10px;
    }
    QLabel#kpiValor {
        font-size: 28px;
        font-weight: bold;
        color: #1f2d3d;
    }
    QLabel#kpiTitulo {
        font-size: 11px;
        color: #6b7c8f;
    }
    QFrame#tarjetaDeuda {
        background-color: #ffffff;
        border: 1px solid #dfe4ea;
        border-radius: 10px;
    }
    QLabel#deudaTitulo {
        font-size: 11px;
        color: #6b7c8f;
        font-weight: bold;
    }
    QLabel#deudaMonto {
        color: #c0392b;
        font-size: 22px;
        font-weight: bold;
    }
    QLabel#deudaItem {
        font-size: 12px;
        color: #1f2d3d;
    }
    QLabel#deudaMontoItem {
        font-size: 12px;
        color: #c0392b;
        font-weight: bold;
    }
    QLabel#resumenOcupacion {
        color: #526579;
        font-size: 12px;
        font-weight: 600;
        padding: 2px 4px;
    }
    QFrame#seccionOperacion {
        background-color: #ffffff;
        border: 1px solid #dfe4ea;
        border-radius: 12px;
    }
    QLabel#operacionTitulo {
        color: #1f2d3d;
        font-size: 16px;
        font-weight: bold;
    }
    QTabWidget#operacionTabs::pane {
        border: none;
        border-top: 1px solid #e6ebf0;
        top: -1px;
    }
    QTabWidget#operacionTabs QTabBar::tab {
        color: #617386;
        background: transparent;
        border: none;
        border-bottom: 3px solid transparent;
        padding: 10px 14px;
        margin-right: 4px;
        font-size: 12px;
        font-weight: 600;
    }
    QTabWidget#operacionTabs QTabBar::tab:selected {
        color: #1d7488;
        border-bottom-color: #1d7488;
    }
    QTabWidget#operacionTabs QTabBar::tab:hover:!selected {
        color: #258a99;
        background: #f3f8f9;
    }
    QScrollArea {
        background: transparent;
    }
    QFrame#operacionCard {
        background-color: #ffffff;
        border: 1px solid #e1e7ed;
        border-left: 4px solid #1d7488;
        border-radius: 8px;
    }
    QFrame#operacionCard:hover {
        background-color: #f9fbfc;
        border-color: #c5d6dc;
        border-left-color: #1d7488;
    }
    QLabel#operacionHabitacion {
        color: #1d7488;
        font-size: 14px;
        font-weight: bold;
    }
    QLabel#operacionHuesped {
        color: #1f2d3d;
        font-size: 14px;
        font-weight: 600;
    }
    QLabel#operacionDetalle {
        color: #718196;
        font-size: 11px;
    }
    QLabel#operacionSaldo {
        color: #bd3b32;
        font-size: 11px;
        font-weight: bold;
    }
    QLabel#operacionCuentaAlDia {
        color: #2e8b57;
        font-size: 11px;
        font-weight: 600;
    }
    QLabel#operacionEstadoHoy,
    QLabel#operacionEstadoAlojado {
        color: #1d7488;
        background: #e8f4f6;
        border-radius: 10px;
        padding: 4px 9px;
        font-size: 10px;
        font-weight: bold;
    }
    QLabel#operacionEstadoProximo {
        color: #53677d;
        background: #edf1f5;
        border-radius: 10px;
        padding: 4px 9px;
        font-size: 10px;
        font-weight: bold;
    }
    QLabel#operacionEstadoAlerta {
        color: #a93226;
        background: #fbeceb;
        border-radius: 10px;
        padding: 4px 9px;
        font-size: 10px;
        font-weight: bold;
    }
    QLabel#operacionVacia {
        color: #718196;
        background: #f7f9fb;
        border: 1px dashed #d5dde5;
        border-radius: 8px;
        font-size: 12px;
    }
    QPushButton#accionPrimaria {
        background-color: #1d7488;
        color: #ffffff;
        border: none;
        border-radius: 6px;
        padding: 9px 18px;
        font-size: 13px;
        font-weight: bold;
    }
    QPushButton#accionPrimaria:hover {
        background-color: #258a99;
    }
    QPushButton#accionSecundaria {
        background-color: #ffffff;
        color: #1f2d3d;
        border: 1px solid #c3ccd6;
        border-radius: 6px;
        padding: 9px 18px;
        font-size: 13px;
    }
    QPushButton#accionSecundaria:hover {
        background-color: #eef2f6;
    }
    QPushButton#accionPeligro {
        background-color: #ffffff;
        color: #c0392b;
        border: 1px solid #e0b4ae;
        border-radius: 6px;
        padding: 9px 18px;
        font-size: 13px;
        font-weight: bold;
    }
    QPushButton#accionPeligro:hover {
        background-color: #fdf1f0;
    }
    QPushButton#botonTarjeta {
        background-color: #ffffff;
        color: #1f2d3d;
        border: 1px solid #c3ccd6;
        border-radius: 5px;
        padding: 0 10px;
        font-size: 12px;
    }
    QPushButton#botonTarjeta:hover {
        background-color: #eef2f6;
    }
    QPushButton#botonTarjetaPeligro {
        background-color: #ffffff;
        color: #c0392b;
        border: 1px solid #e0b4ae;
        border-radius: 5px;
        padding: 0 10px;
        font-size: 12px;
    }
    QPushButton#botonTarjetaPeligro:hover {
        background-color: #fdf1f0;
    }
    /* Acciones dentro de las tablas: el relleno de las variantes grandes
       (18px por lado) dejaba el boton sin espacio para su texto y lo
       recortaba dentro de la celda. */
    QPushButton#accionTablaPrimaria {
        background-color: #1d7488;
        color: #ffffff;
        border: none;
        border-radius: 5px;
        padding: 5px 9px;
        font-size: 12px;
        font-weight: bold;
    }
    QPushButton#accionTablaPrimaria:hover {
        background-color: #258a99;
    }
    QPushButton#accionTablaSecundaria {
        background-color: #ffffff;
        color: #1f2d3d;
        border: 1px solid #c3ccd6;
        border-radius: 5px;
        padding: 5px 9px;
        font-size: 12px;
    }
    QPushButton#accionTablaSecundaria:hover {
        background-color: #eef2f6;
    }
    QPushButton#accionTablaPeligro {
        background-color: #fff7f6;
        color: #b83227;
        border: 1px solid #e4b7b2;
        border-radius: 5px;
        padding: 5px 9px;
        font-size: 12px;
        font-weight: bold;
    }
    QPushButton#accionTablaPeligro:hover {
        background-color: #fce9e7;
    }
    QToolButton#accionTablaMenu {
        background-color: #ffffff;
        color: #34495e;
        border: 1px solid #c3ccd6;
        border-radius: 5px;
        padding: 0;
        font-size: 22px;
        font-weight: bold;
    }
    QToolButton#accionTablaMenu::menu-indicator {
        image: none;
    }
    QToolButton#accionTablaMenu:hover {
        background-color: #eef2f6;
        border-color: #9eacba;
    }
    QMenu {
        background-color: #ffffff;
        border: 1px solid #dfe4ea;
        padding: 5px;
    }
    QMenu::item {
        padding: 7px 22px 7px 12px;
        color: #1f2d3d;
    }
    QMenu::item:selected {
        background-color: #eef2f6;
    }
    QGroupBox#seccion {
        background-color: #ffffff;
        border: 1px solid #dfe4ea;
        border-radius: 10px;
        margin-top: 12px;
        padding-top: 10px;
        font-size: 13px;
        font-weight: bold;
    }
    QGroupBox#seccion::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 14px;
        padding: 0 6px;
        color: #1f2d3d;
    }
    /* Buscador y filtro de las mesas de trabajo. Sin estilo propio los campos
       heredan el aspecto del sistema y rompen el azul de la barra. */
    QLineEdit#campoFiltro {
        background-color: #ffffff;
        color: #1f2d3d;
        border: 1px solid #c3ccd6;
        border-radius: 6px;
        padding: 4px 10px;
        font-size: 12px;
    }
    QLineEdit#campoFiltro:focus {
        border: 1px solid #1d7488;
    }
    QComboBox#campoFiltro {
        background-color: #ffffff;
        color: #1f2d3d;
        border: 1px solid #c3ccd6;
        border-radius: 6px;
        padding: 4px 10px;
        font-size: 12px;
    }
    QComboBox#campoFiltro:hover {
        background-color: #eef2f6;
    }
    QComboBox#campoFiltro::drop-down {
        border: none;
    }
    QComboBox#campoFiltro QAbstractItemView {
        background-color: #ffffff;
        border: 1px solid #c3ccd6;
        selection-background-color: #d9eeee;
        selection-color: #1f2d3d;
        font-size: 12px;
    }
"""

ESTILO_TABLA = """
    QTableWidget {
        background-color: #ffffff;
        border: 1px solid #dfe4ea;
        border-radius: 8px;
        gridline-color: #eceff3;
        font-size: 12px;
        selection-background-color: #d9eeee;
        selection-color: #1f2d3d;
    }
    QHeaderView::section {
        background-color: #eef2f6;
        border: none;
        border-bottom: 1px solid #dfe4ea;
        padding: 7px;
        font-weight: bold;
        color: #1f2d3d;
    }
"""

COLORES_ESTATUS = {
    "Disponible": "#2e9e5b",
    "Ocupado": "#c0392b",
    "Reservado": "#d68910",
    "Mantenimiento": "#5d6d7e",
    "Pendiente de limpieza": "#7d5ba6",
    "Pendiente": "#d68910",
    "Iniciada": "#2e9e5b",
    "Finalizada": "#5d6d7e",
    "Cancelada": "#c0392b",
    "No presentada": "#7d5ba6",
}

# Colores del estado de la cuenta de una reserva (calculado a partir del saldo).
COLORES_ESTADO_PAGO = {
    "Pendiente": "#c0392b",
    "Parcial": "#d68910",
    "Pagado": "#2e9e5b",
}

# ----------------------------------------------------------------------
# PANEL DE NOTIFICACIONES (campana de avisos)
# ----------------------------------------------------------------------
ESTILO_NOTIFICACIONES = """
    QFrame#popupNotificaciones {
        background-color: #ffffff;
        border: 1px solid #c3ccd6;
        border-radius: 10px;
    }
    QLabel#popupTitulo {
        color: #1f2d3d;
        font-size: 14px;
        font-weight: bold;
    }
    QLabel#popupSubtitulo {
        color: #6b7c8f;
        font-size: 11px;
    }
    QFrame#avisoItemVencida, QFrame#avisoItemHoy, QFrame#avisoItemProxima {
        background-color: #ffffff;
        border: 1px solid #dfe4ea;
        border-radius: 8px;
    }
    QFrame#avisoItemVencida {
        border-left: 4px solid #c0392b;
    }
    QFrame#avisoItemHoy {
        border-left: 4px solid #d68910;
    }
    QFrame#avisoItemProxima {
        border-left: 4px solid #1d7488;
    }
    QLabel#avisoSeccion {
        color: #6b7c8f;
        font-size: 11px;
        font-weight: bold;
        padding-top: 4px;
    }
    QLabel#avisoTitulo {
        color: #1f2d3d;
        font-size: 12px;
        font-weight: bold;
    }
    QLabel#avisoTexto {
        color: #1f2d3d;
        font-size: 12px;
    }
    QLabel#avisoVacio {
        color: #6b7c8f;
        font-size: 12px;
        font-style: italic;
    }
"""

# ----------------------------------------------------------------------
# AUTENTICACION
# ----------------------------------------------------------------------
ESTILO_LOGIN = """
    QWidget#loginRaiz {
        background-color: #1f2d3d;
    }
    QWidget#loginTarjeta {
        background-color: #ffffff;
        border-radius: 12px;
    }
    QLabel#loginTitulo {
        color: #1f2d3d;
        font-size: 20px;
        font-weight: bold;
    }
    QLabel#loginSubtitulo {
        color: #6b7c8f;
        font-size: 12px;
    }
    QLabel#loginAviso {
        color: #b42318;
        font-size: 12px;
        font-weight: bold;
    }
    QPushButton#loginBoton {
        background-color: #1d7488;
        color: #ffffff;
        border: none;
        border-radius: 7px;
        padding: 11px;
        font-size: 14px;
        font-weight: bold;
    }
    QPushButton#loginBoton:hover {
        background-color: #258a99;
    }
    QPushButton#loginBoton:pressed {
        background-color: #185f70;
    }
    QPushButton#loginEnlace {
        background: transparent;
        border: none;
        color: #9fb3c8;
        font-size: 12px;
        text-decoration: underline;
    }
    QPushButton#loginEnlace:hover {
        color: #dbe6f1;
    }
    QLabel#loginPie {
        color: #9fb3c8;
        font-size: 11px;
    }
"""
