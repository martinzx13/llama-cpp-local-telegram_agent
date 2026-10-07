from sqlalchemy import (
    Column, Integer, String, Date, DateTime, Text, Enum, ForeignKey, Numeric, Boolean
)
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
import enum

Base = declarative_base()


class UserRole(str, enum.Enum):
    empleado = "empleado"
    lider = "lider"
    rrhh = "rrhh"
    admin = "admin"


class UserStatus(str, enum.Enum):
    activo = "activo"
    retirado = "retirado"
    incapacitado = "incapacitado"


class RequestStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class CertificateType(str, enum.Enum):
    laboral = "laboral"
    tiempos = "tiempos"
    salario = "salario"


class Empleado(Base):
    __tablename__ = "empleados"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(200), nullable=False)
    cedula = Column(String(20), unique=True, nullable=False, index=True)
    cargo = Column(String(100))
    area = Column(String(100))
    telegram_id = Column(Integer, unique=True, index=True)
    role = Column(Enum(UserRole), default=UserRole.empleado, nullable=False)
    saldo_vacaciones_dias = Column(Integer, default=15)
    fecha_ingreso = Column(Date)
    pin_hash = Column(String(255))
    pin_attempts = Column(Integer, default=0)
    pin_locked_until = Column(DateTime)
    estado = Column(Enum(UserStatus), default=UserStatus.activo)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    solicitudes = relationship("Solicitud", back_populates="empleado")
    certificados = relationship("CertificadoLog", back_populates="empleado")


class Solicitud(Base):
    __tablename__ = "solicitudes"

    id = Column(Integer, primary_key=True)
    empleado_id = Column(Integer, ForeignKey("empleados.id"), nullable=False, index=True)
    tipo = Column(String(50), default="vacaciones")
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date, nullable=False)
    dias = Column(Integer, nullable=False)
    estado = Column(Enum(RequestStatus), default=RequestStatus.pending, index=True)
    aprobado_por = Column(Integer, ForeignKey("empleados.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    decided_at = Column(DateTime)

    empleado = relationship("Empleado", back_populates="solicitudes", foreign_keys=[empleado_id])
    aprobador = relationship("Empleado", foreign_keys=[aprobado_por])


class CertificadoLog(Base):
    __tablename__ = "certificados_log"

    id = Column(Integer, primary_key=True)
    empleado_id = Column(Integer, ForeignKey("empleados.id"), nullable=False, index=True)
    tipo = Column(Enum(CertificateType), nullable=False)
    destino = Column(String(200))
    pdf_path = Column(String(500))
    qr_hash = Column(String(64))
    emitted_at = Column(DateTime, default=datetime.utcnow)

    empleado = relationship("Empleado", back_populates="certificados")


class CuadroTurno(Base):
    __tablename__ = "cuadro_turnos"

    id = Column(Integer, primary_key=True)
    empleado_id = Column(Integer, ForeignKey("empleados.id"), nullable=False, index=True)
    fecha = Column(Date, nullable=False, index=True)
    turno_id = Column(Integer)
    hora_inicio = Column(String(5))
    hora_fin = Column(String(5))
    horas_diurnas = Column(Numeric(5, 2))
    horas_nocturnas = Column(Numeric(5, 2))
    recargo_calculado = Column(Numeric(12, 2))
    estado = Column(String(20), default="programado")
    registrado_por = Column(Integer, ForeignKey("empleados.id"))
    motivo = Column(Text)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True)
    actor_id = Column(Integer, ForeignKey("empleados.id"), nullable=False, index=True)
    action = Column(String(50), nullable=False)
    entity = Column(String(50), nullable=False)
    entity_id = Column(Integer)
    payload = Column(Text)
    ts = Column(DateTime, default=datetime.utcnow, index=True)


class Documento(Base):
    __tablename__ = "documentos"

    id = Column(Integer, primary_key=True)
    path = Column(String(500))
    titulo = Column(String(200))
    area = Column(String(100))
    contenido = Column(Text)
    indexed_at = Column(DateTime, default=datetime.utcnow)