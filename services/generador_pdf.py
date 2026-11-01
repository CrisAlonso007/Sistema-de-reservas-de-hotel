from datetime import datetime
from decimal import Decimal
from pathlib import Path

import reportlab
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    LongTable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from xml.sax.saxutils import escape


COLOR_PRINCIPAL = colors.HexColor("#234A72")
COLOR_SECUNDARIO = colors.HexColor("#EAF0F6")
COLOR_BORDE = colors.HexColor("#C9D3DE")
FUENTES_REPORTLAB = Path(reportlab.__file__).resolve().parent / "fonts"
pdfmetrics.registerFont(TTFont("HotelVera", str(FUENTES_REPORTLAB / "Vera.ttf")))
pdfmetrics.registerFont(TTFont("HotelVera-Bold", str(FUENTES_REPORTLAB / "VeraBd.ttf")))


def _pie_pagina(canvas, documento):
    canvas.saveState()
    canvas.setFont("HotelVera", 8)
    canvas.setFillColor(colors.HexColor("#596879"))
    canvas.drawString(
        15 * mm,
        10 * mm,
        f"Sistema de Reservas de Hotel | Emitido: {datetime.now():%d/%m/%Y %H:%M}",
    )
    canvas.drawRightString(
        documento.pagesize[0] - 15 * mm,
        10 * mm,
        f"Página {documento.page}",
    )
    canvas.restoreState()


def generar_reporte_pagos_pdf(ruta, datos):
    """Genera un PDF con el resumen y el detalle de pagos del período."""
    simbolo = "C$" if datos.get("moneda") == "NIO" else "$"
    documento = SimpleDocTemplate(
        str(ruta),
        pagesize=landscape(letter),
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=18 * mm,
        title="Reporte de pagos del hotel",
        author="Sistema de Reservas de Hotel",
    )

    estilos = getSampleStyleSheet()
    titulo = ParagraphStyle(
        "TituloReportePagos",
        parent=estilos["Title"],
        fontName="HotelVera-Bold",
        fontSize=16,
        leading=20,
        textColor=COLOR_PRINCIPAL,
        alignment=1,
        spaceAfter=5,
    )
    texto_celda = ParagraphStyle(
        "TextoCeldaPagos",
        parent=estilos["BodyText"],
        fontName="HotelVera",
        fontSize=7,
        leading=9,
        spaceAfter=0,
    )
    encabezado_celda = ParagraphStyle(
        "EncabezadoCeldaPagos",
        parent=texto_celda,
        fontName="HotelVera-Bold",
        textColor=colors.white,
        alignment=1,
    )

    contenido = []
    contenido.extend(
        [
            Paragraph("REPORTE DE PAGOS", titulo),
            Paragraph(
                f"Período: {datos['fecha_inicio']:%d/%m/%Y} al "
                f"{datos['fecha_fin']:%d/%m/%Y}",
                ParagraphStyle(
                    "SubtituloReportePagos",
                    parent=estilos["Normal"],
                    fontName="HotelVera",
                ),
            ),
            Spacer(1, 5 * mm),
        ]
    )

    resumen = Table(
        [
            ["Cantidad de pagos", "Total recibido"],
            [str(datos["cantidad_pagos"]), f"{simbolo} {datos['total']:,.2f}"],
        ],
        colWidths=[60 * mm, 60 * mm],
        hAlign="LEFT",
    )
    resumen.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), COLOR_PRINCIPAL),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "HotelVera-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "HotelVera"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("BOX", (0, 0), (-1, -1), 0.7, COLOR_BORDE),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, COLOR_BORDE),
                ("BACKGROUND", (0, 1), (-1, 1), COLOR_SECUNDARIO),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    contenido.extend([resumen, Spacer(1, 6 * mm)])

    if datos["por_dia"]:
        filas_resumen = [[
            Paragraph("Resumen diario", encabezado_celda),
            Paragraph("Pagos", encabezado_celda),
            Paragraph("Total recibido", encabezado_celda),
        ]]
        filas_resumen.extend(
            [
                [
                    str(fila["fecha"].strftime("%d/%m/%Y")),
                    str(fila["cantidad"]),
                    f"{simbolo} {fila['total']:,.2f}",
                ]
                for fila in datos["por_dia"]
            ]
        )
        tabla_resumen = Table(filas_resumen, colWidths=[45 * mm, 30 * mm, 45 * mm])
        tabla_resumen.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), COLOR_PRINCIPAL),
                    ("GRID", (0, 0), (-1, -1), 0.4, COLOR_BORDE),
                    ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "HotelVera-Bold"),
                    ("FONTNAME", (0, 1), (-1, -1), "HotelVera"),
                    ("BOX", (0, 0), (-1, -1), 0.7, COLOR_BORDE),
                    ("INNERGRID", (0, 0), (-1, -1), 0.35, COLOR_BORDE),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_SECUNDARIO]),
                    ("FONTSIZE", (0, 1), (-1, -1), 8),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        contenido.extend(
            [
                Paragraph("Totales por día", estilos["Heading2"]),
                tabla_resumen,
                Spacer(1, 6 * mm),
            ]
        )

    filas_metodos = [[
        Paragraph("Método de pago", encabezado_celda),
        Paragraph("Pagos", encabezado_celda),
        Paragraph("Total recibido", encabezado_celda),
    ]]
    filas_metodos.extend(
        [
            [
                Paragraph(escape(fila["metodo_pago"]), texto_celda),
                str(fila["cantidad"]),
                f"{simbolo} {fila['total']:,.2f}",
            ]
            for fila in datos["por_metodo"]
        ]
    )
    tabla_metodos = Table(
        filas_metodos,
        colWidths=[72 * mm, 30 * mm, 45 * mm],
        hAlign="LEFT",
    )
    tabla_metodos.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), COLOR_PRINCIPAL),
                ("GRID", (0, 0), (-1, -1), 0.4, COLOR_BORDE),
                ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "HotelVera-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "HotelVera"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_SECUNDARIO]),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    contenido.extend(
        [
            Paragraph("Ingresos por método de pago", estilos["Heading2"]),
            tabla_metodos,
            Spacer(1, 6 * mm),
        ]
    )

    encabezados = [
        "ID pago",
        "Fecha y hora",
        "Huésped",
        "Documento",
        "Habitación",
        "ID reserva",
        "Monto",
        "Método",
        "Registrado por",
    ]
    filas_pagos = [[Paragraph(escape(valor), encabezado_celda) for valor in encabezados]]
    for pago in datos["pagos"]:
        fecha = pago["creado_en"]
        if isinstance(fecha, datetime):
            fecha = fecha.strftime("%d/%m/%Y %H:%M")
        else:
            fecha = str(fecha)
        filas_pagos.append(
            [
                str(pago["pago_id"]),
                escape(fecha),
                Paragraph(escape(str(pago["cliente"])), texto_celda),
                escape(str(pago["identificacion"])),
                str(pago["habitacion_numero"]),
                str(pago["reserva_id"]),
                f"{simbolo} {pago['monto']:,.2f}",
                Paragraph(escape(str(pago["metodo_pago"])), texto_celda),
                Paragraph(escape(str(pago["empleado_nombre"])), texto_celda),
            ]
        )

    tabla_pagos = LongTable(
        filas_pagos,
        colWidths=[40, 75, 105, 82, 45, 52, 68, 115, 110],
        repeatRows=1,
        hAlign="LEFT",
    )
    tabla_pagos.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), COLOR_PRINCIPAL),
                ("BOX", (0, 0), (-1, -1), 0.7, COLOR_BORDE),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, COLOR_BORDE),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("ALIGN", (2, 1), (2, -1), "LEFT"),
                ("ALIGN", (7, 1), (8, -1), "LEFT"),
                ("ALIGN", (6, 1), (6, -1), "RIGHT"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_SECUNDARIO]),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    contenido.extend(
        [
            Paragraph("Detalle de pagos", estilos["Heading2"]),
            tabla_pagos,
        ]
    )
    documento.build(contenido, onFirstPage=_pie_pagina, onLaterPages=_pie_pagina)


def generar_comprobante_pdf(ruta, datos):
    """Genera un comprobante individual para un pago ya registrado."""
    documento = SimpleDocTemplate(
        str(ruta),
        pagesize=letter,
        rightMargin=22 * mm,
        leftMargin=22 * mm,
        topMargin=18 * mm,
        bottomMargin=20 * mm,
        title=f"Comprobante {datos['numero']}",
        author=str(datos.get("hotel_nombre") or "Allogi Hotel"),
    )
    estilos = getSampleStyleSheet()
    titulo = ParagraphStyle(
        "TituloComprobante",
        parent=estilos["Title"],
        fontName="HotelVera-Bold",
        fontSize=17,
        leading=21,
        textColor=COLOR_PRINCIPAL,
        alignment=1,
        spaceAfter=8,
    )
    normal = ParagraphStyle(
        "TextoComprobante",
        parent=estilos["BodyText"],
        fontName="HotelVera",
        fontSize=10,
        leading=14,
    )
    negrita = ParagraphStyle(
        "TextoComprobanteNegrita",
        parent=normal,
        fontName="HotelVera-Bold",
    )

    contenido = []
    contacto = [
        str(datos.get("hotel_direccion") or ""),
        str(datos.get("hotel_telefono") or ""),
        str(datos.get("hotel_correo") or ""),
    ]
    contacto = [escape(valor) for valor in contacto if valor]
    contenido.extend([
        Paragraph(escape(str(datos.get("hotel_nombre") or "Allogi Hotel")), titulo),
        Paragraph(" · ".join(contacto), normal) if contacto else Spacer(1, 1 * mm),
        Spacer(1, 7 * mm),
        Paragraph("COMPROBANTE DE PAGO", titulo),
        Paragraph(f"Número: <b>{escape(str(datos['numero']))}</b>", normal),
    ])

    fecha = datos.get("creado_en")
    if isinstance(fecha, datetime):
        fecha = fecha.strftime("%d/%m/%Y %H:%M")
    simbolo = "C$" if datos.get("moneda") == "NIO" else "$"
    filas = [
        ["Huésped", str(datos["cliente"])],
        ["Documento", str(datos["identificacion"])],
        ["Habitación", str(datos["habitacion_numero"])],
        ["Reserva", str(datos["reserva_id"])],
        ["Estadía", f"{datos['fecha_entrada']} al {datos['fecha_salida']}"],
        ["Fecha del pago", str(fecha)],
        ["Método de pago", str(datos["metodo_pago"])],
        ["Registrado por", str(datos["empleado"])],
        ["Monto recibido", f"{simbolo} {Decimal(str(datos['monto'])):,.2f}"],
    ]
    tabla = Table(
        [[Paragraph(escape(clave), negrita), Paragraph(escape(valor), normal)]
         for clave, valor in filas],
        colWidths=[48 * mm, 112 * mm],
        hAlign="LEFT",
    )
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), COLOR_SECUNDARIO),
        ("GRID", (0, 0), (-1, -1), 0.4, COLOR_BORDE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    contenido.extend([Spacer(1, 5 * mm), tabla, Spacer(1, 8 * mm)])
    mensaje = str(datos.get("comprobante_mensaje") or "")
    if mensaje:
        contenido.append(Paragraph(escape(mensaje), normal))

    documento.build(contenido, onFirstPage=_pie_pagina, onLaterPages=_pie_pagina)
