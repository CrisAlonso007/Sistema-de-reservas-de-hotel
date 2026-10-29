from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Usuario(Base):
    __tablename__ = "Usuario"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    passwrd: Mapped[str] = mapped_column(String(255), nullable=False)
    rol: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'recepcionista'")
    )
    nombre_completo: Mapped[str] = mapped_column(String(150), nullable=False)
    numero_identificacion: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    correo_electronico: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    numero_telefono: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("1"))
    creado_en: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )

    reservas_registradas: Mapped[list["Reserva"]] = relationship(
        back_populates="empleado_registro",
        foreign_keys="Reserva.empleado_id",
    )
    ingresos_registrados: Mapped[list["Reserva"]] = relationship(
        back_populates="empleado_checkin",
        foreign_keys="Reserva.checkin_empleado_id",
    )
    salidas_registradas: Mapped[list["Reserva"]] = relationship(
        back_populates="empleado_salida",
        foreign_keys="Reserva.salida_empleado_id",
    )
    pagos_registrados: Mapped[list["Pago"]] = relationship(back_populates="empleado")


class Habitacion(Base):
    __tablename__ = "registro_habitacion"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    no_habitacion: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'Simple'"))
    precio: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    capacidad: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("2"))
    descripcion: Mapped[str] = mapped_column(String(255), nullable=False)
    imagen: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        server_default=text("'recursos/placeholder-image.jpg'"),
    )
    mantenimiento: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("0"))
    creado_en: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=datetime.now,
    )

    reservas: Mapped[list["Reserva"]] = relationship(back_populates="habitacion")


class Reserva(Base):
    __tablename__ = "Reserva"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cliente: Mapped[str] = mapped_column(String(100), nullable=False)
    identificacion: Mapped[str] = mapped_column(String(50), nullable=False)
    contacto: Mapped[str] = mapped_column(String(50), nullable=False)
    noches: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha_entrada: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_salida: Mapped[date] = mapped_column(Date, nullable=False)
    metodo_pago: Mapped[str] = mapped_column(String(40), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    monto_pagado: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, server_default=text("0.00")
    )
    estado: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'Pendiente'")
    )
    habitacion_id: Mapped[int] = mapped_column(
        ForeignKey("registro_habitacion.id", ondelete="RESTRICT"), nullable=False
    )
    empleado_id: Mapped[int] = mapped_column(
        ForeignKey("Usuario.id", ondelete="RESTRICT"), nullable=False
    )
    checkin_empleado_id: Mapped[int | None] = mapped_column(
        ForeignKey("Usuario.id", ondelete="SET NULL")
    )
    salida_empleado_id: Mapped[int | None] = mapped_column(
        ForeignKey("Usuario.id", ondelete="SET NULL")
    )
    creado_en: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=datetime.now,
    )

    habitacion: Mapped[Habitacion] = relationship(back_populates="reservas")
    empleado_registro: Mapped[Usuario] = relationship(
        back_populates="reservas_registradas",
        foreign_keys=[empleado_id],
    )
    empleado_checkin: Mapped[Usuario | None] = relationship(
        back_populates="ingresos_registrados",
        foreign_keys=[checkin_empleado_id],
    )
    empleado_salida: Mapped[Usuario | None] = relationship(
        back_populates="salidas_registradas",
        foreign_keys=[salida_empleado_id],
    )
    pagos: Mapped[list["Pago"]] = relationship(back_populates="reserva")


class Pago(Base):
    __tablename__ = "Pago"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reserva_id: Mapped[int] = mapped_column(
        ForeignKey("Reserva.id", ondelete="CASCADE"), nullable=False
    )
    monto: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    metodo_pago: Mapped[str] = mapped_column(String(40), nullable=False)
    empleado_id: Mapped[int] = mapped_column(
        ForeignKey("Usuario.id", ondelete="RESTRICT"), nullable=False
    )
    creado_en: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )

    reserva: Mapped[Reserva] = relationship(back_populates="pagos")
    empleado: Mapped[Usuario] = relationship(back_populates="pagos_registrados")


class Configuracion(Base):
    __tablename__ = "Configuracion"

    clave: Mapped[str] = mapped_column(String(60), primary_key=True)
    valor: Mapped[str] = mapped_column(String(255), nullable=False)
    descripcion: Mapped[str] = mapped_column(
        String(255), nullable=False, server_default=text("''")
    )
