# ui/tabla_reservas.py
from datetime import date
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QAbstractItemView,
    QLineEdit, QComboBox,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from services.reserva_service import ReservaService
from utils.stylesheets import COLORES_ESTATUS, ESTILO_TABLA

class TablaReservas(QWidget):
    """Mesa de reservas reutilizable.

    La usan el tablero (llegadas pendientes y huéspedes alojados) y la ventana
    de historial. Arma la tabla, la rellena y, si se pide, agrega los botones de
    ingreso, salida y cancelación.

    El ancho de la columna de acciones no se reparte con el resto: al
    estrecharse, Qt recorta el texto de los botones y quedan ilegibles.
    """

    ocupacion_cambiada = Signal()

    ANCHO_COLUMNA_ACCIONES = 210

    ENCABEZADOS = {
        "habitacion": "Hab.",
        "cliente": "Huésped",
        "documento": "Documento",
        "entrada": "Entrada",
        "salida": "Salida",
        "pago": "Método",
        "total": "Total",
        "saldo": "Saldo",
        "estado": "Estado",
    }

    def __init__(
        self,
        usuario_actual: dict = None,
        reserva_service=None,
        columnas=None,
        con_acciones=True,
        con_filtros=False,
        titulo=None,
        alto=220,
        parent=None,
    ):
        super().__init__(parent)
        self.usuario_actual = usuario_actual or {}
        self.reserva_service = reserva_service
        self.columnas = list(columnas or ["habitacion", "cliente", "entrada", "salida"])
        self.con_acciones = con_acciones
        self.con_filtros = con_filtros

        self.setObjectName("panelRaiz")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        if titulo:
            grupo = QGroupBox(titulo)
            grupo.setObjectName("seccion")
            contenedor = QVBoxLayout(grupo)
            contenedor.setContentsMargins(14, 18, 14, 14)
            contenedor.setSpacing(10)
            layout.addWidget(grupo)
        else:
            contenedor = layout

        if con_filtros:
            contenedor.addWidget(self._crear_barra())

        encabezados = [self.ENCABEZADOS[c] for c in self.columnas]
        if con_acciones:
            encabezados.append("")
        self.tabla = self._crear_tabla(encabezados)
        self.tabla.setMinimumHeight(alto)
        contenedor.addWidget(self.tabla)

    # ------------------------------------------------------------------
    # CONSTRUCCIÓN
    # ------------------------------------------------------------------
    def _crear_barra(self):
        """Buscador y filtro de estado, resueltos sobre las filas ya cargadas."""
        barra = QWidget()
        layout = QHBoxLayout(barra)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.txt_buscar = QLineEdit()
        self.txt_buscar.setObjectName("campoFiltro")
        self.txt_buscar.setPlaceholderText("Buscar por huésped, habitación o documento...")
        self.txt_buscar.setClearButtonEnabled(True)
        self.txt_buscar.setFixedHeight(30)
        self.txt_buscar.textChanged.connect(self.filtrar)
        layout.addWidget(self.txt_buscar, stretch=1)

        self.cmb_filtro_estado = QComboBox()
        self.cmb_filtro_estado.setObjectName("campoFiltro")
        self.cmb_filtro_estado.addItem("Todos los estados", "")
        for estado in ReservaService.ESTADOS_RESERVA:
            self.cmb_filtro_estado.addItem(ReservaService.etiqueta_estado(estado), estado)
        self.cmb_filtro_estado.setFixedHeight(30)
        self.cmb_filtro_estado.currentIndexChanged.connect(self.filtrar)
        layout.addWidget(self.cmb_filtro_estado)

        self.lbl_conteo = QLabel("")
        self.lbl_conteo.setObjectName("panelSubtitulo")
        self.lbl_conteo.setMinimumWidth(150)
        self.lbl_conteo.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.lbl_conteo)

        return barra

    def _crear_tabla(self, encabezados):
        tabla = QTableWidget(0, len(encabezados))
        tabla.setHorizontalHeaderLabels(encabezados)
        tabla.setStyleSheet(ESTILO_TABLA)
        tabla.verticalHeader().setVisible(False)
        tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        tabla.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        tabla.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        if self.con_acciones:
            tabla.horizontalHeader().setSectionResizeMode(
                len(encabezados) - 1, QHeaderView.ResizeMode.Fixed
            )
            tabla.setColumnWidth(len(encabezados) - 1, self.ANCHO_COLUMNA_ACCIONES)
        return tabla

    # ------------------------------------------------------------------
    # CONTENIDO
    # ------------------------------------------------------------------
    def llenar(self, reservas):
        """Carga las reservas y reconstruye la tabla."""
        self.tabla.setRowCount(0)
        self.tabla.clearSpans()

        if not reservas:
            item = QTableWidgetItem("Sin registros para mostrar.")
            item.setForeground(QColor("#8a97a6"))
            self.tabla.setRowCount(1)
            self.tabla.setItem(0, 0, item)
            self.tabla.setSpan(0, 0, 1, self.tabla.columnCount())
            if self.con_filtros:
                self.lbl_conteo.setText("")
            return

        for reserva in reservas:
            fila = self.tabla.rowCount()
            self.tabla.insertRow(fila)

            for columna, nombre in enumerate(self.columnas):
                texto, color = self._celda(nombre, reserva)
                item = QTableWidgetItem(str(texto))
                if color:
                    item.setForeground(QColor(color))
                if columna == 0:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    fuente = item.font()
                    fuente.setBold(True)
                    item.setFont(fuente)
                    # La fila guarda su estado y su texto buscable: el filtro
                    # decide qué esconder sin volver a consultar MySQL.
                    item.setData(Qt.ItemDataRole.UserRole, {
                        "estado": reserva["estado"],
                        "texto": self._texto_buscable(reserva),
                    })
                self.tabla.setItem(fila, columna, item)

            if self.con_acciones:
                self._agregar_acciones(fila, reserva)

        if self.con_filtros:
            self.filtrar()

    def _celda(self, nombre, reserva):
        servicio = self.reserva_service
        if nombre == "habitacion":
            return str(reserva["habitacion_numero"]), None
        if nombre == "cliente":
            return reserva["cliente"], None
        if nombre == "documento":
            return reserva["identificacion"], None
        if nombre == "entrada":
            return servicio.formato_fecha(reserva["fecha_entrada"]), None
        if nombre == "salida":
            return servicio.formato_fecha(reserva["fecha_salida"]), None
        if nombre == "pago":
            return reserva["metodo_pago"], None
        if nombre == "total":
            return f"${servicio.formato_monto(reserva['total'])}", None
        if nombre == "saldo":
            return f"${servicio.formato_monto(reserva.get('saldo', 0))}", self._color_saldo(reserva)
        if nombre == "estado":
            return (
                ReservaService.etiqueta_estado(reserva["estado"]),
                COLORES_ESTATUS.get(reserva["estado"]),
            )
        return "", None

    @staticmethod
    def _color_saldo(reserva):
        try:
            saldo = float(reserva.get("saldo", 0) or 0)
        except (TypeError, ValueError):
            return None
        return COLORES_ESTATUS["Pendiente"] if saldo > 0 else COLORES_ESTATUS["Iniciada"]

    def _texto_buscable(self, reserva) -> str:
        partes = [
            str(reserva.get("habitacion_numero", "")),
            reserva.get("cliente", ""),
            reserva.get("identificacion", ""),
            reserva.get("contacto", ""),
            reserva.get("metodo_pago", ""),
            reserva.get("estado", ""),
        ]
        return " ".join(partes).lower()

    def filtrar(self, *_):
        """Muestra u oculta filas según la búsqueda y el estado elegido."""
        if not self.con_filtros:
            return

        texto = self.txt_buscar.text().strip().lower()
        estado = self.cmb_filtro_estado.currentData()

        total = 0
        visibles = 0
        for fila in range(self.tabla.rowCount()):
            celda = self.tabla.item(fila, 0)
            if celda is None:
                continue

            datos = celda.data(Qt.ItemDataRole.UserRole)
            if not isinstance(datos, dict):
                continue

            total += 1
            coincide_texto = not texto or texto in datos["texto"]
            coincide_estado = not estado or datos["estado"] == estado
            coincide = coincide_texto and coincide_estado

            self.tabla.setRowHidden(fila, not coincide)
            if coincide:
                visibles += 1

        if total == 0:
            self.lbl_conteo.setText("")
        else:
            self.lbl_conteo.setText(f"{visibles} de {total} reservas")

    # ------------------------------------------------------------------
    # ACCIONES
    # ------------------------------------------------------------------
    def _agregar_acciones(self, fila, reserva):
        acciones = self._acciones(reserva)
        if not acciones:
            return

        contenedor = QWidget()
        layout = QVBoxLayout(contenedor)
        layout.setContentsMargins(2, 3, 2, 3)
        layout.setSpacing(4)

        for texto, ranura, ayuda in acciones:
            btn = QPushButton(texto)
            btn.setObjectName("accionTablaPrimaria")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(28)
            btn.setToolTip(ayuda)
            # `ranura` se fija como valor por defecto: si el cierre la leyera del
            # ámbito compartido, los botones acabarían ejecutando la última
            # acción asignada (cancelar en vez de alojar, por ejemplo).
            btn.clicked.connect(lambda _=False, r=reserva, accion=ranura: accion(r))
            layout.addWidget(btn)

        if len(acciones) > 1:
            self.tabla.setRowHeight(fila, 68)
        self.tabla.setCellWidget(fila, len(self.columnas), contenedor)

    def _acciones(self, reserva):
        """Acciones que admite una reserva según su estado y su fecha."""
        estado = reserva["estado"]
        acciones = []

        if estado == "Pendiente":
            if reserva["fecha_entrada"] <= date.today():
                acciones.append((
                    "Marcar como ocupada",
                    self._registrar_checkin,
                    "Registrar la llegada del huésped y ocupar la habitación.",
                ))
            acciones.append((
                "Cancelar reserva",
                self._cancelar_reserva,
                "Anular la reserva y liberar la habitación.",
            ))
        elif estado == "Iniciada":
            acciones.append((
                "Registrar salida",
                self._registrar_salida,
                "Registrar la salida del huésped y liberar la habitación.",
            ))

        # «Finalizada» y «Cancelada» son estados cerrados: no admiten acciones.
        return acciones

    def _registrar_checkin(self, reserva):
        if not self._confirmar(
            "Registrar ingreso",
            f"¿Registrar el ingreso de {reserva['cliente']} en la habitación {reserva['habitacion_numero']}?",
        ):
            return
        self._ejecutar(self.reserva_service.registrar_checkin, reserva)

    def _registrar_salida(self, reserva):
        if not self._confirmar(
            "Registrar salida",
            f"¿Registrar la salida de {reserva['cliente']} de la habitación {reserva['habitacion_numero']}?",
        ):
            return
        self._ejecutar(self.reserva_service.registrar_salida, reserva)

    def _cancelar_reserva(self, reserva):
        if not self._confirmar(
            "Cancelar reserva",
            f"¿Cancelar la reserva de {reserva['cliente']} en la habitación {reserva['habitacion_numero']}?\n\nLas fechas quedarán disponibles.",
        ):
            return
        self._ejecutar(self.reserva_service.cancelar_reserva, reserva)

    def _ejecutar(self, operacion, reserva):
        # El servicio toma la sesión completa para validar el rol y obtener el
        # identificador del empleado responsable de la operación.
        exito, mensaje = operacion(usuario_actual=self.usuario_actual, reserva_id=reserva["id"])
        if exito:
            QMessageBox.information(self, "Operación registrada", mensaje)
        else:
            QMessageBox.warning(self, "No se pudo completar", mensaje)
        if exito:
            self.ocupacion_cambiada.emit()

    def _confirmar(self, titulo, mensaje):
        respuesta = QMessageBox.question(
            self,
            titulo,
            mensaje,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        return respuesta == QMessageBox.StandardButton.Yes
