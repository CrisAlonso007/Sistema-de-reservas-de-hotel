"""Configuración de SQLAlchemy: motor compartido y fábrica de sesiones."""

from sqlalchemy import URL, create_engine
from sqlalchemy.orm import sessionmaker

from DATABASE.conexion import ConexionBD

configuracion = ConexionBD()
DATABASE_URL = URL.create(
    drivername="mysql+pymysql",
    username=configuracion.user,
    password=configuracion.password,
    host=configuracion.host,
    port=configuracion.port,
    database=configuracion.database,
    query={"charset": "utf8mb4"},
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
