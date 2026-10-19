# ui/panel_reportes.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox,
    QDateEdit, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QAbstractItemView,
)
from PySide6.QtCore import Qt, QDate
from services.reserva_service import ReservaService
from services.habitacion_service import HabitacionService
from ui.components import TarjetaKpi
from utils.stylesheets import COLORES_ESTATUS, ESTILO_PANEL, ESTILO_TABLA

class PanelReportes(QWidget):
    """Reportes de ocupación e ingresos del período. Solo administradores."""

    def __init__(self, usuario_actual: dict = None, reserva_service=None,
                 habitacion_service=None, parent=None):
        super().__init__(parent)
        self.usuario_actual = usuario_actual or {}
        self.reserva_service = reserva_service or ReservaService()
        self.habitacion_service = habitacion_service or HabitacionService()

        self.setObjectName("panelRaiz")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(ESTILO_PANEL)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)

        layout.addWidget(self._crear_encabezado())
        layout.addLayout(self._crear_fila_kpis())
        layout.addLayout(self._crear_detalles(), stretch=1)

    # ------------------------------------------------------------------
    # CONSTRUCCIÓN
    # ------------------------------------------------------------------
    def _crear_encabezado(self):
        contenedor = QWidget()
        layout = QHBoxLayout(contenedor)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        textos = QVBoxLayout()
        textos.setSpacing(2)
        lbl_titulo = QLabel("Reportes")
        lbl_titulo.setObjectName("panelTitulo")
        textos.addWidget(lbl_titulo)
        lbl_sub = QLabel("Ocupación, ingresos y reservas canceladas por período")
        lbl_sub.setObjectName("panelSubtitulo")
        textos.addWidget(lbl_sub)
        layout.addLayout(textos)
        layout.addStretch()

        layout.addWidget(QLabel("Desde:"))
        self.dt_inicio = QDateEdit()
        self.dt_inicio.setCalendarPopup(True)
        self.dt_inicio.setDisplayFormat("yyyy-MM-dd")
        self.dt_inicio.setFixedHeight(32)
        hoy = QDate.currentDate()
        self.dt_inicio.setDate(QDate(hoy.year(), hoy.month(), 1))
        layout.addWidget(self.dt_inicio)

        layout.addWidget(QLabel("Hasta:"))
        self.dt_fin = QDateEdit()
        self.dt_fin.setCalendarPopup(True)
        self.dt_fin.setDisplayFormat("yyyy-MM-dd")
        self.dt_fin.setFixedHeight(32)
        self.dt_fin.setDate(hoy)
        layout.addWidget(self.dt_fin)

        btn_generar = QPushButton("Generar")
        btn_generar.setObjectName("accionPrimaria")
        btn_generar.setCursor(Qt.PointingHandCursor)
        btn_generar.setFixedHeight(34)
        btn_generar.clicked.connect(self.refrescar)
        layout.addWidget(btn_generar)

        return contenedor

    def _crear_fila_kpis(self):
        layout = QHBoxLayout()
        layout.setSpacing(12)

        self.kpi_ocupacion = TarjetaKpi("OCUPACIÓN ACTUAL", COLORES_ESTATUS["Ocupado"])
        self.kpi_ingresos = TarjetaKpi("INGRESOS DEL PERÍODO", COLORES_ESTATUS["Disponible"])
        self.kpi_reservas = TarjetaKpi("RESERVAS DEL PERÍODO", "#2f6fb0")
        self.kpi_canceladas = TarjetaKpi("CANCELADAS DEL PERÍODO", COLORES_ESTATUS["Cancelada"])

        for kpi in (self.kpi_ocupacion, self.kpi_ingresos, self.kpi_reservas, self.kpi_canceladas):
            layout.addWidget(kpi)
        return layout

    def _crear_detalles(self):
        layout = QHBoxLayout()
        layout.setSpacing(12)
        layout.addWidget(self._crear_tabla_ingresos(), stretch=1)
        layout.addWidget(self._crear_tabla_canceladas(), stretch=1)
        return layout

    def _crear_tabla_ingresos(self):
        grupo = QGroupBox("Ingresos por día")
        grupo.setObjectName("seccion")
        contenedor = QVBoxLayout(grupo)
        contenedor.setContentsMargins(14, 18, 14, 14)

        self.tabla_ingresos = self._crear_tabla(["Fecha", "Ingresos"])
        contenedor.addWidget(self.tabla_ingresos)
        return grupo

    def _crear_tabla_canceladas(self):
        grupo = QGroupBox("Reservas canceladas")
        grupo.setObjectName("seccion")
        contenedor = QVBoxLayout(grupo)
        contenedor.setContentsMargins(14, 18, 14, 14)

        self.tabla_canceladas = self._crear_tabla(["Hab.", "Huésped", "Entrada", "Total"])
        contenedor.addWidget(self.tabla_canceladas)
        return grupo

    def _crear_tabla(self, encabezados):
        tabla = QTableWidget(0, len(encabezados))
        tabla.setHorizontalHeaderLabels(encabezados)
        tabla.setStyleSheet(ESTILO_TABLA)
        tabla.verticalHeader().setVisible(False)
        tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        tabla.setMinimumHeight(260)
        return tabla

    # ------------------------------------------------------------------
    # DATOS
    # ------------------------------------------------------------------
    def refrescar(self):
        inicio = self.dt_inicio.date().toString("yyyy-MM-dd")
        fin = self.dt_fin.date().toString("yyyy-MM-dd")

        exito, resultado = self.reserva_service.obtener_reporte(
            self.usuario_actual, inicio, fin
        )
        if not exito:
            QMessageBox.warning(self, "No se pudo generar el reporte", resultado)
            return

        resumen = self.habitacion_service.obtener_resumen_ocupacion()
        self.kpi_ocupacion.set_valor(f"{resumen['porcentaje_ocupacion']}%")
        self.kpi_ingresos.set_valor(
            f"${self.reserva_service.formato_monto(resultado['ingresos'])}"
        )
        self.kpi_reservas.set_valor(resultado["reservas"])
        self.kpi_canceladas.set_valor(resultado["canceladas_total"])

        self._llenar_ingresos(resultado["por_dia"])
        self._llenar_canceladas(resultado["canceladas"])

    def _llenar_ingresos(self, filas):
        self.tabla_ingresos.setRowCount(0)
        for registro in filas:
            fila = self.tabla_ingresos.rowCount()
            self.tabla_ingresos.insertRow(fila)
            self.tabla_ingresos.setItem(
                fila, 0, QTableWidgetItem(self.reserva_service.formato_fecha(registro["fecha"]))
            )
            self.tabla_ingresos.setItem(
                fila, 1,
                QTableWidgetItem(f"${self.reserva_service.formato_monto(registro['total'])}"),
            )

    def _llenar_canceladas(self, filas):
        self.tabla_canceladas.setRowCount(0)
        for registro in filas:
            fila = self.tabla_canceladas.rowCount()
            self.tabla_canceladas.insertRow(fila)
            valores = [
                str(registro["habitacion_numero"]),
                registro["cliente"],
                self.reserva_service.formato_fecha(registro["fecha_entrada"]),
                f"${self.reserva_service.formato_monto(registro['total'])}",
            ]
            for columna, valor in enumerate(valores):
                self.tabla_canceladas.setItem(fila, columna, QTableWidgetItem(str(valor)))
