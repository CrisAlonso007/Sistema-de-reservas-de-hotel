from datetime import date, datetime, timedelta
from decimal import Decimal

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ui.components import TarjetaKpi
from utils.seguridad import es_administrador
from utils.stylesheets import COLORES_ESTATUS, ESTILO_PANEL


class PanelDashboard(QWidget):
    """Inicio orientado al flujo diario de recepción."""

    navegar_a = Signal(str)
    registro_solicitado = Signal()
    historial_solicitado = Signal()
    ocupacion_cambiada = Signal()
    editar_reserva_solicitada = Signal(dict)
    cobro_solicitado = Signal(dict)
    detalle_reserva_solicitado = Signal(dict)

    DIAS_LLEGADAS = 7

    def __init__(
        self,
        usuario_actual: dict = None,
        habitacion_service=None,
        reserva_service=None,
        parent=None,
    ):
        super().__init__(parent)
        self.usuario_actual = usuario_actual or {}
        self.habitacion_service = habitacion_service
        self.reserva_service = reserva_service
        self._listas_operacion = {}
        self._mensajes_vacios = {}

        self.setObjectName("panelRaiz")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(ESTILO_PANEL)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(14)
        layout.addWidget(self._crear_encabezado())
        layout.addLayout(self._crear_fila_kpis())

        self.lbl_ocupacion = QLabel("Estado del hotel")
        self.lbl_ocupacion.setObjectName("resumenOcupacion")
        layout.addWidget(self.lbl_ocupacion)

        layout.addWidget(self._crear_operacion(), stretch=1)

    def _crear_encabezado(self):
        contenedor = QWidget()
        layout = QHBoxLayout(contenedor)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        textos = QVBoxLayout()
        textos.setSpacing(3)
        self.lbl_bienvenida = QLabel("Bienvenido a Allogi Hotel")
        self.lbl_bienvenida.setObjectName("panelTitulo")
        textos.addWidget(self.lbl_bienvenida)

        nombre = (
            self.usuario_actual.get("nombre_completo")
            or self.usuario_actual.get("nombre", "")
        )
        self.lbl_subtitulo = QLabel(
            f"{self._saludo()}, {nombre}. "
            f"{datetime.now().strftime('%d/%m/%Y · %H:%M')}"
        )
        self.lbl_subtitulo.setObjectName("panelSubtitulo")
        textos.addWidget(self.lbl_subtitulo)
        layout.addLayout(textos)
        layout.addStretch()

        self.btn_historial = QPushButton("Historial")
        self.btn_historial.setObjectName("accionSecundaria")
        self.btn_historial.setCursor(Qt.PointingHandCursor)
        self.btn_historial.setFixedHeight(38)
        self.btn_historial.setToolTip("Consultar el historial completo de huéspedes.")
        self.btn_historial.clicked.connect(self.historial_solicitado.emit)
        layout.addWidget(self.btn_historial)

        self.btn_registrar = QPushButton("+  Nueva reserva")
        self.btn_registrar.setObjectName("accionPrimaria")
        self.btn_registrar.setCursor(Qt.PointingHandCursor)
        self.btn_registrar.setFixedHeight(38)
        self.btn_registrar.setMinimumWidth(155)
        self.btn_registrar.setToolTip("Registrar un huésped y crear su reserva.")
        self.btn_registrar.clicked.connect(self.registro_solicitado.emit)
        layout.addWidget(self.btn_registrar)
        return contenedor

    def set_hotel_name(self, nombre):
        self.lbl_bienvenida.setText(f"Bienvenido a {nombre or 'Allogi Hotel'}")

    def _crear_fila_kpis(self):
        layout = QHBoxLayout()
        layout.setSpacing(12)

        self.kpi_llegadas = TarjetaKpi("LLEGADAS HOY", COLORES_ESTATUS["Reservado"])
        self.kpi_alojados = TarjetaKpi("HUÉSPEDES ALOJADOS", COLORES_ESTATUS["Ocupado"])
        self.kpi_salidas = TarjetaKpi("SALIDAS POR ATENDER", "#1d7488")
        self.kpi_cobros = TarjetaKpi("SALDO POR COBRAR", "#c0392b")
        for tarjeta in (
            self.kpi_llegadas,
            self.kpi_alojados,
            self.kpi_salidas,
            self.kpi_cobros,
        ):
            layout.addWidget(tarjeta)
        return layout

    def _crear_operacion(self):
        seccion = QFrame()
        seccion.setObjectName("seccionOperacion")
        layout = QVBoxLayout(seccion)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        encabezado = QHBoxLayout()
        titulos = QVBoxLayout()
        titulos.setSpacing(2)
        titulo = QLabel("Operación de recepción")
        titulo.setObjectName("operacionTitulo")
        subtitulo = QLabel("Sigue cada estancia desde la llegada hasta la salida.")
        subtitulo.setObjectName("panelSubtitulo")
        titulos.addWidget(titulo)
        titulos.addWidget(subtitulo)
        encabezado.addLayout(titulos)
        encabezado.addStretch()
        layout.addLayout(encabezado)

        self.tabs_operacion = QTabWidget()
        self.tabs_operacion.setObjectName("operacionTabs")
        self._agregar_pestana("llegadas", "Llegadas")
        self._agregar_pestana("alojados", "Alojados")
        self._agregar_pestana("salidas", "Salidas")
        self._agregar_pestana("cobros", "Cobros pendientes")
        layout.addWidget(self.tabs_operacion, stretch=1)
        return seccion

    def _agregar_pestana(self, clave, titulo):
        pagina = QWidget()
        pagina_layout = QVBoxLayout(pagina)
        pagina_layout.setContentsMargins(4, 10, 4, 4)
        pagina_layout.setSpacing(8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        contenido = QWidget()
        lista = QVBoxLayout(contenido)
        lista.setContentsMargins(2, 2, 6, 2)
        lista.setSpacing(8)

        vacio = QLabel()
        vacio.setObjectName("operacionVacia")
        vacio.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vacio.setMinimumHeight(100)
        vacio.hide()
        lista.addWidget(vacio)
        lista.addStretch()
        scroll.setWidget(contenido)
        pagina_layout.addWidget(scroll)
        self._listas_operacion[clave] = lista
        self._mensajes_vacios[clave] = vacio
        self.tabs_operacion.addTab(pagina, titulo)

    def refrescar(self):
        if not self.habitacion_service or not self.reserva_service:
            return
        self.aplicar_datos({
            "resumen": self.habitacion_service.obtener_resumen_ocupacion(),
            "cuentas": self.reserva_service.obtener_cuentas(),
            "pendientes": self.reserva_service.obtener_reservas_pendientes(),
            "alojados": self.reserva_service.obtener_en_casa(),
        })

    def aplicar_datos(self, datos):
        resumen = datos["resumen"]
        pendientes = datos["pendientes"]
        alojados = datos["alojados"]
        cuentas = datos["cuentas"]
        hoy = date.today()

        llegadas = [
            reserva for reserva in pendientes
            if hoy <= self._a_date(reserva["fecha_entrada"])
            <= hoy + timedelta(days=self.DIAS_LLEGADAS)
        ]
        llegadas.sort(
            key=lambda reserva: (
                self._a_date(reserva["fecha_entrada"]),
                reserva["habitacion_numero"],
            )
        )
        salidas = [
            reserva for reserva in alojados
            if self._a_date(reserva["fecha_salida"]) <= hoy
        ]
        salidas.sort(
            key=lambda reserva: (
                self._a_date(reserva["fecha_salida"]),
                reserva["habitacion_numero"],
            )
        )
        cobros = [
            cuenta for cuenta in cuentas
            if Decimal(str(cuenta.get("saldo") or 0)) > 0
        ]

        llegadas_hoy = sum(
            1 for reserva in llegadas
            if self._a_date(reserva["fecha_entrada"]) == hoy
        )
        self.kpi_llegadas.set_valor(llegadas_hoy)
        self.kpi_alojados.set_valor(len(alojados))
        self.kpi_salidas.set_valor(len(salidas))
        self.kpi_cobros.set_valor(
            self.reserva_service.formato_dinero(
                sum(
                    (Decimal(str(cuenta.get("saldo") or 0)) for cuenta in cobros),
                    Decimal("0.00"),
                )
            )
        )
        self.lbl_ocupacion.setText(
            f"{resumen['total']} habitaciones  ·  "
            f"{resumen['disponibles']} disponibles  ·  "
            f"{resumen['ocupadas']} ocupadas  ·  "
            f"{resumen['reservadas']} reservadas  ·  "
            f"{resumen['mantenimiento']} en mantenimiento"
        )

        self._mostrar_registros("llegadas", llegadas, "No hay llegadas en los próximos días.")
        self._mostrar_registros("alojados", alojados, "No hay huéspedes alojados actualmente.")
        self._mostrar_registros("salidas", salidas, "No hay salidas pendientes para hoy.")
        self._mostrar_registros("cobros", cobros, "No hay saldos pendientes.")
        self.tabs_operacion.setTabText(0, f"Llegadas · {len(llegadas)}")
        self.tabs_operacion.setTabText(1, f"Alojados · {len(alojados)}")
        self.tabs_operacion.setTabText(2, f"Salidas · {len(salidas)}")
        self.tabs_operacion.setTabText(3, f"Cobros · {len(cobros)}")

    def _mostrar_registros(self, clave, registros, mensaje_vacio):
        lista = self._listas_operacion[clave]
        vacio = self._mensajes_vacios[clave]

        while lista.count() > 2:
            elemento = lista.takeAt(1)
            widget = elemento.widget()
            if widget is not None and widget is not vacio:
                widget.deleteLater()

        vacio.setText(mensaje_vacio)
        vacio.setVisible(not registros)
        for registro in registros:
            lista.insertWidget(lista.count() - 1, self._crear_tarjeta(clave, registro))

    def _crear_tarjeta(self, clave, reserva):
        tarjeta = TarjetaOperacion(reserva)
        tarjeta.setObjectName("operacionCard")
        tarjeta.setCursor(Qt.CursorShape.PointingHandCursor)
        tarjeta.setToolTip("Haz clic para ver los detalles de la reserva.")
        tarjeta.detalle_solicitado.connect(self.detalle_reserva_solicitado.emit)
        layout = QHBoxLayout(tarjeta)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(14)

        datos = QVBoxLayout()
        datos.setSpacing(3)
        encabezado = QHBoxLayout()
        habitacion = QLabel(
            f"Habitación {reserva.get('habitacion_numero', '—')}"
        )
        habitacion.setObjectName("operacionHabitacion")
        habitacion.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        encabezado.addWidget(habitacion)

        cliente = QLabel(str(reserva.get("cliente", "Huésped")))
        cliente.setObjectName("operacionHuesped")
        cliente.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        encabezado.addWidget(cliente)
        encabezado.addStretch()

        situacion, estado_objeto = self._situacion(clave, reserva)
        estado = QLabel(situacion)
        estado.setObjectName(estado_objeto)
        estado.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        encabezado.addWidget(estado)
        datos.addLayout(encabezado)

        entrada = self._a_date(reserva["fecha_entrada"])
        salida = self._a_date(reserva["fecha_salida"])
        huespedes = int(reserva.get("numero_huespedes") or 1)
        texto_huespedes = f"{huespedes} huésped" if huespedes == 1 else f"{huespedes} huéspedes"
        detalle = QLabel(
            f"{texto_huespedes}  ·  Entrada {entrada.strftime('%d/%m/%Y')}  ·  "
            f"Salida {salida.strftime('%d/%m/%Y')}"
        )
        detalle.setObjectName("operacionDetalle")
        detalle.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        datos.addWidget(detalle)

        saldo = Decimal(str(reserva.get("saldo") or 0))
        pago = QLabel(
            "Cuenta al día"
            if saldo <= 0
            else f"Saldo pendiente: {self.reserva_service.formato_dinero(saldo)}"
        )
        pago.setObjectName("operacionSaldo" if saldo > 0 else "operacionCuentaAlDia")
        pago.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        datos.addWidget(pago)
        layout.addLayout(datos, stretch=1)

        acciones = self._crear_acciones(clave, reserva, saldo)
        if acciones:
            botones = QVBoxLayout()
            botones.setSpacing(6)
            for texto, callback, primario, habilitado in acciones:
                boton = QPushButton(texto)
                boton.setObjectName(
                    "accionPrimaria" if primario else "accionSecundaria"
                )
                boton.setCursor(Qt.PointingHandCursor)
                boton.setMinimumWidth(132)
                boton.setFixedHeight(34)
                boton.setEnabled(habilitado)
                boton.clicked.connect(
                    lambda _=False, accion=callback, r=reserva: accion(r)
                )
                botones.addWidget(boton)
            layout.addLayout(botones)
        return tarjeta

    def _crear_acciones(self, clave, reserva, saldo):
        if clave == "llegadas":
            if self._a_date(reserva["fecha_entrada"]) <= date.today():
                return [("Registrar ingreso", self._registrar_ingreso, True, True)]
            return []

        if clave == "cobros":
            return [("Registrar cobro", self._solicitar_cobro, True, True)]

        if clave == "salidas":
            if saldo > 0:
                acciones = [("Cobrar cuenta", self._solicitar_cobro, True, True)]
                if es_administrador(self.usuario_actual):
                    acciones.append(("Forzar salida", self._forzar_salida, False, True))
                return acciones
            return [("Registrar salida", self._registrar_salida, True, True)]

        fecha_salida = self._a_date(reserva["fecha_salida"])
        if saldo > 0:
            return [("Cobrar cuenta", self._solicitar_cobro, True, True)]
        if fecha_salida <= date.today():
            return [("Registrar salida", self._registrar_salida, True, True)]
        return []

    @staticmethod
    def _situacion(clave, reserva):
        hoy = date.today()
        if clave == "llegadas":
            entrada = PanelDashboard._a_date(reserva["fecha_entrada"])
            if entrada == hoy:
                return "Llega hoy", "operacionEstadoHoy"
            return f"Llega {entrada.strftime('%d/%m')}", "operacionEstadoProximo"
        if clave == "salidas":
            salida = PanelDashboard._a_date(reserva["fecha_salida"])
            if salida < hoy:
                return "Salida vencida", "operacionEstadoAlerta"
            return "Salida de hoy", "operacionEstadoHoy"
        return "Alojado", "operacionEstadoAlojado"

    def _solicitar_cobro(self, reserva):
        self.cobro_solicitado.emit(reserva)

    def _registrar_ingreso(self, reserva):
        respuesta = QMessageBox.question(
            self,
            "Registrar ingreso",
            f"¿Confirmas el ingreso de {reserva['cliente']} a la habitación "
            f"{reserva['habitacion_numero']}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if respuesta != QMessageBox.StandardButton.Yes:
            return

        exito, mensaje = self.reserva_service.registrar_checkin(
            self.usuario_actual, reserva["id"]
        )
        self._informar_resultado(exito, mensaje)

    def _registrar_salida(self, reserva):
        respuesta = QMessageBox.question(
            self,
            "Registrar salida",
            f"¿Confirmas la salida de {reserva['cliente']} de la habitación "
            f"{reserva['habitacion_numero']}?\n\n"
            "La habitación quedará pendiente de limpieza.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if respuesta != QMessageBox.StandardButton.Yes:
            return

        exito, mensaje = self.reserva_service.registrar_salida(
            self.usuario_actual, reserva["id"]
        )
        self._informar_resultado(exito, mensaje)

    def _forzar_salida(self, reserva):
        saldo = Decimal(str(reserva.get("saldo") or 0))
        respuesta = QMessageBox.question(
            self,
            "Forzar salida",
            f"La cuenta de {reserva['cliente']} tiene un saldo pendiente de "
            f"{self.reserva_service.formato_dinero(saldo)}.\n\n"
            "¿Registrar la salida de todas formas? Esta acción es exclusiva "
            "del administrador.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if respuesta != QMessageBox.StandardButton.Yes:
            return

        exito, mensaje = self.reserva_service.registrar_salida(
            self.usuario_actual, reserva["id"], forzar=True
        )
        self._informar_resultado(exito, mensaje)

    def _informar_resultado(self, exito, mensaje):
        if exito:
            QMessageBox.information(self, "Operación registrada", mensaje)
            self.ocupacion_cambiada.emit()
        else:
            QMessageBox.warning(self, "No se pudo completar", mensaje)

    @staticmethod
    def _a_date(valor):
        if isinstance(valor, datetime):
            return valor.date()
        if isinstance(valor, date):
            return valor
        return datetime.strptime(str(valor).strip()[:10], "%Y-%m-%d").date()

    @staticmethod
    def _saludo():
        hora = datetime.now().hour
        if hora < 12:
            return "Buenos días"
        if hora < 19:
            return "Buenas tardes"
        return "Buenas noches"


class TarjetaOperacion(QFrame):
    detalle_solicitado = Signal(dict)

    def __init__(self, reserva, parent=None):
        super().__init__(parent)
        self.reserva = reserva

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.detalle_solicitado.emit(self.reserva)
        super().mousePressEvent(event)
