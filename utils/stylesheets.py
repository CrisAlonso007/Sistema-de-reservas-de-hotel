# utils/stylesheets.py
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
    }
    QLabel#bannerTitulo {
        color: #ffffff;
        font-size: 17px;
        font-weight: bold;
    }
    QLabel#bannerSubtitulo {
        color: #9fb3c8;
        font-size: 11px;
    }
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
        background-color: #2f6fb0;
        color: #ffffff;
        font-weight: bold;
    }
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
    QPushButton#accionPrimaria {
        background-color: #2f6fb0;
        color: #ffffff;
        border: none;
        border-radius: 6px;
        padding: 9px 18px;
        font-size: 13px;
        font-weight: bold;
    }
    QPushButton#accionPrimaria:hover {
        background-color: #3d82c7;
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
        background-color: #2f6fb0;
        color: #ffffff;
        border: none;
        border-radius: 5px;
        padding: 5px 9px;
        font-size: 12px;
        font-weight: bold;
    }
    QPushButton#accionTablaPrimaria:hover {
        background-color: #3d82c7;
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
"""

ESTILO_TABLA = """
    QTableWidget {
        background-color: #ffffff;
        border: 1px solid #dfe4ea;
        border-radius: 8px;
        gridline-color: #eceff3;
        font-size: 12px;
        selection-background-color: #d6e6f7;
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
    "Pendiente": "#d68910",
    "Confirmada": "#2f6fb0",
    "Iniciada": "#2e9e5b",
    "Finalizada": "#5d6d7e",
    "Cancelada": "#c0392b",
}

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
        background-color: #2f6fb0;
        color: #ffffff;
        border: none;
        border-radius: 7px;
        padding: 11px;
        font-size: 14px;
        font-weight: bold;
    }
    QPushButton#loginBoton:hover {
        background-color: #3d82c7;
    }
    QPushButton#loginBoton:pressed {
        background-color: #2a629b;
    }
    QLabel#loginPie {
        color: #9fb3c8;
        font-size: 11px;
    }
"""
