# ui/panel_recepcion.py
from datetime import date
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QAbstractItemView,
    QLineEdit, QComboBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from services.reserva_service import ReservaService
from utils.stylesheets import COLORES_ESTATUS, ESTILO_PANEL, ESTILO_TABLA

class PanelRecepcion(QWidget):
    """Mesa de trabajo de recepción: altas, ingresos, salidas y cancelaciones."""

    # Acción principal: llega un cliente y hay que registrarlo.
    registro_solicitado = Signal()

    # Un ingreso o una salida cambian la ocupación real de la habitación, así
    # que catálogo y tablero deben renovarse también, no solo estas dos mesas.
    ocupacion_cambiada = Signal()

    # Ancho reservado para la celda de acciones. Los botones van apilados, asi
    # que basta con que quepa el mas largo ("Registrar ingreso") sin recortarlo.
    ANCHO_COLUMNA_ACCIONES = 232

    # Nombres claros para el personal: la base guarda estados tecnicos que aqui
    # se muestran con palabras del dia a dia.
    ETIQUETAS_ESTADO = {
        "Pendiente": "Reservada",
        "Confirmada": "Confirmada",
        "Iniciada": "Alojado",
        "Finalizada": "Finalizada",
        "Cancelada": "Cancelada",
    }

    def __init__(self, usuario_actual: dict = None, reserva_service=None, parent=None):
        super().__init__(parent)
        self.usuario_actual = usuario_actual or {}
        self.reserva_service = reserva_service

        self.setObjectName("panelRaiz")
        # Necesario para que Qt dibuje el fondo de la hoja de estilos: en un
        # QWidget propio no lo hace por defecto.
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(ESTILO_PANEL)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)

        layout.addWidget(self._crear_encabezado())
        layout.addLayout(self._crear_tablas())

        layout.addStretch()

    def _crear_encabezado(self):
        contenedor = QWidget()
        layout = QHBoxLayout(contenedor)
        layout.setContentsMargins(0, 0, 0, 0)

        textos = QVBoxLayout()
        textos.setSpacing(2)

        lbl_titulo = QLabel("Recepción")
        lbl_titulo.setObjectName("panelTitulo")
        textos.addWidget(lbl_titulo)

        lbl_subtitulo = QLabel("Ingresos, egresos y gestión de reservas del día")
        lbl_subtitulo.setObjectName("panelSubtitulo")
        textos.addWidget(lbl_subtitulo)

        layout.addLayout(textos)
        layout.addStretch()

        self.btn_registrar = QPushButton("+  Registrar Huésped")
        self.btn_registrar.setObjectName("accionPrimaria")
        self.btn_registrar.setCursor(Qt.PointingHandCursor)
        self.btn_registrar.setFixedHeight(38)
        self.btn_registrar.setMinimumWidth(180)
        self.btn_registrar.setToolTip(
            "Registra al cliente que acaba de llegar y abre su reserva."
        )
        self.btn_registrar.clicked.connect(self._solicitar_registro)
        layout.addWidget(self.btn_registrar)

        btn_actualizar = QPushButton("Actualizar")
        btn_actualizar.setObjectName("accionSecundaria")
        btn_actualizar.setCursor(Qt.PointingHandCursor)
        btn_actualizar.clicked.connect(self.refrescar)
        layout.addWidget(btn_actualizar)

        return contenedor

    def _solicitar_registro(self):
        self.registro_solicitado.emit()

    def _crear_tablas(self):
        layout = QHBoxLayout()
        layout.setSpacing(14)

        # --------------------------------------------------
        # RESERVAS (cualquier fecha y cualquier estado)
        # --------------------------------------------------
        grupo_reservas = QGroupBox("Reservas del hotel")
        grupo_reservas.setObjectName("seccion")
        layout_reservas = QVBoxLayout(grupo_reservas)
        layout_reservas.setContentsMargins(14, 18, 14, 14)
        layout_reservas.setSpacing(10)

        # La barra va sobre la tabla: es la mesa que más filas maneja, así que
        # es la que necesita poder recortarse sin volver a preguntar a MySQL.
        layout_reservas.addWidget(self._crear_barra_reservas())

        self.tabla_reservas = self._crear_tabla(
            ["Hab.", "Huésped", "Entrada", "Salida", "Pago", "Total", "Estado", ""]
        )
        layout_reservas.addWidget(self.tabla_reservas)

        # --------------------------------------------------
        # HUÉSPEDES ALOJADOS
        # --------------------------------------------------
        grupo_casa = QGroupBox("Huéspedes alojados")
        grupo_casa.setObjectName("seccion")
        layout_casa = QVBoxLayout(grupo_casa)
        layout_casa.setContentsMargins(14, 18, 14, 14)

        self.tabla_en_casa = self._crear_tabla(
            ["Hab.", "Huésped", "Entrada", "Salida", "Pago", "Total", "Estado", ""]
        )
        layout_casa.addWidget(self.tabla_en_casa)

        layout.addWidget(grupo_reservas, stretch=1)
        layout.addWidget(grupo_casa, stretch=1)
        return layout

    def _crear_barra_reservas(self):
        """Barra de búsqueda y filtro de la mesa de reservas.

        Los dos controles se conectan al mismo método: escribir o cambiar el
        estado esconde y muestra filas, sin volver a consultar la base de datos.
        """
        barra = QWidget()
        layout = QHBoxLayout(barra)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.txt_buscar = QLineEdit()
        self.txt_buscar.setObjectName("campoFiltro")
        self.txt_buscar.setPlaceholderText("Buscar por huésped, habitación o documento...")
        self.txt_buscar.setClearButtonEnabled(True)
        self.txt_buscar.setFixedHeight(30)
        self.txt_buscar.setToolTip("Filtra la mesa mientras escribe, sin recargar la base de datos.")
        self.txt_buscar.textChanged.connect(self.filtrar_tabla_reservas)
        layout.addWidget(self.txt_buscar, stretch=1)

        self.cmb_filtro_estado = QComboBox()
        self.cmb_filtro_estado.setObjectName("campoFiltro")
        self.cmb_filtro_estado.addItem("Todos los estados", "")
        # Los estados se piden al servicio, que es quien los conoce: así el
        # filtro no puede quedar desactualizado si la base agrega uno nuevo.
        for estado in ReservaService.ESTADOS_RESERVA:
            self.cmb_filtro_estado.addItem(
                self.ETIQUETAS_ESTADO.get(estado, estado), estado
            )
        self.cmb_filtro_estado.setFixedHeight(30)
        self.cmb_filtro_estado.setToolTip("Muestra solo las reservas del estado elegido.")
        self.cmb_filtro_estado.currentIndexChanged.connect(self.filtrar_tabla_reservas)
        layout.addWidget(self.cmb_filtro_estado)

        # Aviso de cuántas filas quedan visibles: si el filtro no arroja nada,
        # la mesa se ve vacía y sin esta etiqueta no se sabría si es un error o
        # simplemente no hay coincidencias.
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
        # La ultima columna aloja los botones de accion. No debe repartirse el
        # ancho con el resto porque al estrecharse Qt recorta el texto de los
        # botones y quedan ilegibles.
        tabla.horizontalHeader().setSectionResizeMode(
            len(encabezados) - 1, QHeaderView.ResizeMode.Fixed
        )
        tabla.setColumnWidth(len(encabezados) - 1, self.ANCHO_COLUMNA_ACCIONES)
        return tabla

    def refrescar(self):
        """Recarga las dos mesas de trabajo de recepción."""
        if not self.reserva_service:
            return

        # Listado completo: cualquier fecha y cualquier estado. Antes esta mesa
        # solo traía las llegadas del día, de modo que una reserva para dentro
        # de un mes no se veía en ninguna parte del sistema.
        self._llenar_tabla(
            self.tabla_reservas,
            self.reserva_service.obtener_reservas(),
            self._acciones_reserva,
        )
        # Aquí solo entran los huéspedes que ocupan una habitación de verdad.
        self._llenar_tabla(
            self.tabla_en_casa,
            self.reserva_service.obtener_en_casa(),
            self._acciones_huesped,
        )

        # La mesa vuelve a tener filas nuevas, así que el filtro que el usuario
        # tenía puesto se reaplica: recargar no debe borrar la búsqueda.
        self.filtrar_tabla_reservas()

    def _acciones_reserva(self, reserva):
        """Acciones que admite una reserva según su estado y su fecha.

        Cada acción es una tupla (texto, función, ayuda). Se omiten las que no
        tienen sentido: no se ofrece registrar el ingreso de una reserva
        futura, porque el servidor lo rechaza, ni cancelar una estancia ya
        empezada.
        """
        estado = reserva["estado"]
        acciones = []

        if estado in ("Pendiente", "Confirmada"):
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

    def _acciones_huesped(self, reserva):
        """En la mesa de alojados la única acción posible es la salida."""
        return [(
            "Registrar salida",
            self._registrar_salida,
            "Registrar la salida del huésped y liberar la habitación.",
        )]

    def _llenar_tabla(self, tabla, reservas, acciones_por_reserva):
        tabla.setRowCount(0)

        # Esta fila es un aviso, no una reserva: no lleva datos de búsqueda
        # asociados, y por eso el filtro la deja siempre a la vista.
        if not reservas:
            item = QTableWidgetItem("Sin registros para mostrar.")
            item.setForeground(QColor("#8a97a6"))
            tabla.setRowCount(1)
            tabla.setItem(0, 0, item)
            tabla.setSpan(0, 0, 1, tabla.columnCount())
            return

        for reserva in reservas:
            fila = tabla.rowCount()
            tabla.insertRow(fila)

            celdas = [
                str(reserva["habitacion_numero"]),
                reserva["cliente"],
                self.reserva_service.formato_fecha(reserva["fecha_entrada"]),
                self.reserva_service.formato_fecha(reserva["fecha_salida"]),
                reserva["metodo_pago"],
                f"${self.reserva_service.formato_monto(reserva['total'])}",
            ]
            for columna, texto in enumerate(celdas):
                item = QTableWidgetItem(str(texto))
                if columna == 0:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    fuente = item.font()
                    fuente.setBold(True)
                    item.setFont(fuente)
                    # La fila guarda su propia reserva: así el filtro puede
                    # decidir qué esconder sin volver a preguntarle a MySQL.
                    item.setData(Qt.ItemDataRole.UserRole, {
                        "estado": reserva["estado"],
                        "texto": self._texto_buscable(reserva),
                    })
                tabla.setItem(fila, columna, item)

            estado_item = QTableWidgetItem(
                self.ETIQUETAS_ESTADO.get(reserva["estado"], reserva["estado"])
            )
            estado_item.setForeground(QColor(COLORES_ESTATUS.get(reserva["estado"], "#1f2d3d")))
            estado_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            tabla.setItem(fila, 6, estado_item)

            acciones = acciones_por_reserva(reserva)
            if not acciones:
                continue

            # Los botones van apilados: en horizontal los dos textos largos se
            # pisan y Qt los recorta hasta hacerlos ilegibles.
            contenedor_botones = QWidget()
            layout_botones = QVBoxLayout(contenedor_botones)
            layout_botones.setContentsMargins(2, 3, 2, 3)
            layout_botones.setSpacing(4)

            for texto, ranura, ayuda in acciones:
                btn = QPushButton(texto)
                btn.setObjectName("accionTablaPrimaria")
                btn.setCursor(Qt.PointingHandCursor)
                btn.setFixedHeight(28)
                btn.setToolTip(ayuda)
                # `ranura` se fija como valor por defecto: si el cierre la
                # leyera del ambito compartido, los dos botones acabarian
                # ejecutando la ultima accion asignada y "Marcar como ocupada"
                # cancelaria la reserva en vez de alojar al huesped.
                btn.clicked.connect(lambda _=False, r=reserva, accion=ranura: accion(r))
                layout_botones.addWidget(btn)

            if len(acciones) > 1:
                tabla.setRowHeight(fila, 68)
            tabla.setCellWidget(fila, 7, contenedor_botones)

    @staticmethod
    def _texto_buscable(reserva) -> str:
        """Texto en minúsculas con todo por lo que se puede buscar una reserva.

        Se arma una sola vez por fila, al llenar la tabla, para que al escribir
        en el buscador no haya que volver a recorrer los datos de cada reserva.
        """
        partes = [
            str(reserva["habitacion_numero"]),
            reserva["cliente"],
            reserva["identificacion"],
            reserva["contacto"],
            reserva["correo_electronico"],
            reserva["metodo_pago"],
            reserva["estado"],
        ]
        return " ".join(partes).lower()

    def filtrar_tabla_reservas(self, *_):
        """Muestra u oculta filas según la búsqueda y el estado elegido.

        La mesa ya tiene cargadas todas las reservas, así que el filtro solo
        recorre las filas y les cambia la visibilidad. No vuelve a consultar la
        base de datos, y por eso responde mientras el usuario escribe.
        """
        texto = self.txt_buscar.text().strip().lower()
        estado = self.cmb_filtro_estado.currentData()

        total = 0
        visibles = 0
        for fila in range(self.tabla_reservas.rowCount()):
            celda = self.tabla_reservas.item(fila, 0)
            if celda is None:
                continue

            datos = celda.data(Qt.ItemDataRole.UserRole)
            if not isinstance(datos, dict):
                # Fila de aviso: no es una reserva, se deja como está.
                continue

            total += 1
            coincide_texto = not texto or texto in datos["texto"]
            coincide_estado = not estado or datos["estado"] == estado
            coincide = coincide_texto and coincide_estado

            self.tabla_reservas.setRowHidden(fila, not coincide)
            if coincide:
                visibles += 1

        if total == 0:
            self.lbl_conteo.setText("")
        else:
            self.lbl_conteo.setText(f"{visibles} de {total} reservas")

    # ------------------------------------------------------------------
    # ACCIONES DE RECEPCIÓN
    # ------------------------------------------------------------------
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
        self.refrescar()
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
