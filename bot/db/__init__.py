from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from bot.db.models import Base, Empleado, Solicitud, CertificadoLog, CuadroTurno, AuditLog, Documento
from bot.config import get_settings
from datetime import datetime, date
from typing import List, Dict, Any, Optional
import json
import hashlib


class Database:
    def __init__(self):
        self.config = get_settings()
        self.engine = create_engine(
            f"sqlite:///{self.config.database.path}",
            connect_args={"check_same_thread": False},
        )
        self.SessionLocal = sessionmaker(bind=self.engine)

    def init_db(self):
        Base.metadata.create_all(self.engine)
        self._seed_mock_data()

    def get_session(self) -> Session:
        return self.SessionLocal()

    def _seed_mock_data(self):
        session = self.get_session()
        try:
            if session.query(Empleado).count() == 0:
                mock_users = [
                    {
                        "nombre": "Juan Pérez", "cedula": "12345678", "cargo": "Ingeniero",
                        "area": "TI", "telegram_id": 999999999, "role": "empleado",
                        "saldo_vacaciones_dias": 15, "fecha_ingreso": date(2023, 1, 15),
                    },
                    {
                        "nombre": "María García", "cedula": "87654321", "cargo": "Enfermera",
                        "area": "UCI", "telegram_id": 888888888, "role": "empleado",
                        "saldo_vacaciones_dias": 12, "fecha_ingreso": date(2022, 3, 10),
                    },
                    {
                        "nombre": "Carlos López", "cedula": "11223344", "cargo": "Líder TI",
                        "area": "TI", "telegram_id": 777777777, "role": "lider",
                        "saldo_vacaciones_dias": 20, "fecha_ingreso": date(2021, 6, 1),
                    },
                    {
                        "nombre": "Ana Martínez", "cedula": "44332211", "cargo": "RRHH",
                        "area": "Talento Humano", "telegram_id": 666666666, "role": "rrhh",
                        "saldo_vacaciones_dias": 18, "fecha_ingreso": date(2020, 1, 15),
                    },
                ]
                for u in mock_users:
                    emp = Empleado(**u)
                    session.add(emp)
                session.commit()
        finally:
            session.close()

    def get_user(self, telegram_id: int) -> Optional[Dict]:
        session = self.get_session()
        try:
            emp = session.query(Empleado).filter(Empleado.telegram_id == telegram_id).first()
            if emp:
                return {
                    "id": emp.id, "nombre": emp.nombre, "cedula": emp.cedula,
                    "cargo": emp.cargo, "area": emp.area, "telegram_id": emp.telegram_id,
                    "role": emp.role.value, "saldo_vacaciones_dias": emp.saldo_vacaciones_dias,
                    "fecha_ingreso": emp.fecha_ingreso.isoformat() if emp.fecha_ingreso else None,
                }
            return None
        finally:
            session.close()

    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        session = self.get_session()
        try:
            emp = session.query(Empleado).filter(Empleado.id == user_id).first()
            if emp:
                return {
                    "id": emp.id, "nombre": emp.nombre, "cedula": emp.cedula,
                    "cargo": emp.cargo, "area": emp.area, "telegram_id": emp.telegram_id,
                    "role": emp.role.value, "saldo_vacaciones_dias": emp.saldo_vacaciones_dias,
                    "fecha_ingreso": emp.fecha_ingreso.isoformat() if emp.fecha_ingreso else None,
                }
            return None
        finally:
            session.close()

    def get_user_role(self, telegram_id: int) -> str:
        session = self.get_session()
        try:
            emp = session.query(Empleado).filter(Empleado.telegram_id == telegram_id).first()
            return emp.role.value if emp else "empleado"
        finally:
            session.close()

    def register_user(self, telegram_id: int, user_id: int) -> bool:
        session = self.get_session()
        try:
            emp = session.query(Empleado).filter(Empleado.id == user_id).first()
            if emp and emp.telegram_id is None:
                emp.telegram_id = telegram_id
                session.commit()
                return True
            return False
        finally:
            session.close()

    def verify_pin(self, user_id: int, pin: str) -> bool:
        import bcrypt
        session = self.get_session()
        try:
            emp = session.query(Empleado).filter(Empleado.id == user_id).first()
            if not emp or not emp.pin_hash:
                return False
            if emp.pin_locked_until and emp.pin_locked_until > datetime.utcnow():
                return False
            if bcrypt.checkpw(pin.encode(), emp.pin_hash.encode()):
                emp.pin_attempts = 0
                emp.pin_locked_until = None
                session.commit()
                return True
            else:
                emp.pin_attempts += 1
                config = get_settings()
                if emp.pin_attempts >= config.telegram.pin_attempts:
                    emp.pin_locked_until = datetime.utcnow().timestamp() + config.telegram.pin_cooldown_seconds
                session.commit()
                return False
        finally:
            session.close()

    def set_pin(self, user_id: int, pin: str) -> bool:
        import bcrypt
        session = self.get_session()
        try:
            emp = session.query(Empleado).filter(Empleado.id == user_id).first()
            if emp:
                emp.pin_hash = bcrypt.hashpw(pin.encode(), bcrypt.gensalt()).decode()
                emp.pin_attempts = 0
                emp.pin_locked_until = None
                session.commit()
                return True
            return False
        finally:
            session.close()

    def get_certificate_data(self, user_id: int, tipo: str) -> Optional[Dict]:
        session = self.get_session()
        try:
            emp = session.query(Empleado).filter(Empleado.id == user_id).first()
            if not emp:
                return None
            return {
                "id": emp.id, "nombre": emp.nombre, "cedula": emp.cedula,
                "cargo": emp.cargo, "area": emp.area,
                "fecha_ingreso": emp.fecha_ingreso,
                "tipo": tipo,
            }
        finally:
            session.close()

    def log_certificate(self, user_id: int, tipo: str, destino: str, pdf_path: str, qr_hash: str):
        session = self.get_session()
        try:
            log = CertificadoLog(
                empleado_id=user_id, tipo=tipo, destino=destino,
                pdf_path=pdf_path, qr_hash=qr_hash,
            )
            session.add(log)
            session.commit()
        finally:
            session.close()

    def log_audit(self, actor_id: int, action: str, entity: str, entity_id: int, payload: Dict):
        session = self.get_session()
        try:
            log = AuditLog(
                actor_id=actor_id, action=action, entity=entity,
                entity_id=entity_id, payload=json.dumps(payload),
            )
            session.add(log)
            session.commit()
        finally:
            session.close()

    def create_vacation_request(self, user_id: int, inicio: date, fin: date, dias: int) -> int:
        session = self.get_session()
        try:
            sol = Solicitud(
                empleado_id=user_id, tipo="vacaciones",
                fecha_inicio=inicio, fecha_fin=fin, dias=dias,
                estado="pending",
            )
            session.add(sol)
            session.commit()
            return sol.id
        finally:
            session.close()

    def check_schedule_conflict(self, user_id: int, inicio: date, fin: date) -> Optional[str]:
        session = self.get_session()
        try:
            conflict = session.query(CuadroTurno).filter(
                CuadroTurno.empleado_id == user_id,
                CuadroTurno.fecha >= inicio,
                CuadroTurno.fecha <= fin,
                CuadroTurno.estado != "ausencia",
            ).first()
            if conflict:
                return f"Turno {conflict.turno_id} el {conflict.fecha}"
            return None
        finally:
            session.close()

    def get_pending_vacations_for_leader(self, leader_id: int) -> List[Dict]:
        session = self.get_session()
        try:
            solicitudes = session.query(Solicitud).join(Empleado).filter(
                Solicitud.estado == "pending",
                Solicitud.tipo == "vacaciones",
            ).all()
            result = []
            for s in solicitudes:
                emp = s.empleado
                if leader_id and emp.area != session.query(Empleado).filter(Empleado.id == leader_id).first().area:
                    continue
                result.append({
                    "id": s.id, "empleado": emp.nombre, "fecha_inicio": s.fecha_inicio.isoformat(),
                    "fecha_fin": s.fecha_fin.isoformat(), "dias": s.dias,
                    "saldo_restante": emp.saldo_vacaciones_dias - s.dias,
                })
            return result
        finally:
            session.close()

    def approve_vacation(self, solicitud_id: int, leader_id: int) -> bool:
        session = self.get_session()
        try:
            sol = session.query(Solicitud).filter(Solicitud.id == solicitud_id).first()
            if not sol or sol.estado != "pending":
                return False
            sol.estado = "approved"
            sol.aprobado_por = leader_id
            sol.decided_at = datetime.utcnow()
            emp = session.query(Empleado).filter(Empleado.id == sol.empleado_id).first()
            if emp:
                emp.saldo_vacaciones_dias -= sol.dias
            session.commit()
            return True
        finally:
            session.close()

    def reject_vacation(self, solicitud_id: int, leader_id: int) -> bool:
        session = self.get_session()
        try:
            sol = session.query(Solicitud).filter(Solicitud.id == solicitud_id).first()
            if not sol or sol.estado != "pending":
                return False
            sol.estado = "rejected"
            sol.aprobado_por = leader_id
            sol.decided_at = datetime.utcnow()
            session.commit()
            return True
        finally:
            session.close()

    def get_schedule_week(self, user_id: int) -> List[Dict]:
        session = self.get_session()
        try:
            hoy = date.today()
            inicio_semana = hoy - timedelta(days=hoy.weekday())
            fin_semana = inicio_semana + timedelta(days=6)
            turnos = session.query(CuadroTurno).filter(
                CuadroTurno.empleado_id == user_id,
                CuadroTurno.fecha >= inicio_semana,
                CuadroTurno.fecha <= fin_semana,
            ).order_by(CuadroTurno.fecha).all()
            return [{
                "fecha": t.fecha.isoformat(), "turno": t.turno_id,
                "hora_inicio": t.hora_inicio, "hora_fin": t.hora_fin,
                "recargo_calculado": float(t.recargo_calculado) if t.recargo_calculado else 0,
            } for t in turnos]
        finally:
            session.close()

    def get_team_vacations(self, leader_id: int, role: str) -> List[Dict]:
        session = self.get_session()
        try:
            query = session.query(Solicitud).join(Empleado).filter(Solicitud.tipo == "vacaciones")
            if role == "lider":
                leader_area = session.query(Empleado).filter(Empleado.id == leader_id).first().area
                query = query.filter(Empleado.area == leader_area)
            solicitudes = query.all()
            return [{
                "id": s.id, "empleado": s.empleado.nombre,
                "fecha_inicio": s.fecha_inicio.isoformat(),
                "fecha_fin": s.fecha_fin.isoformat(),
                "dias": s.dias, "estado": s.estado,
            } for s in solicitudes]
        finally:
            session.close()

    def count_certificates_this_month(self) -> int:
        session = self.get_session()
        try:
            hoy = date.today()
            inicio_mes = date(hoy.year, hoy.month, 1)
            return session.query(CertificadoLog).filter(
                CertificadoLog.emitted_at >= inicio_mes
            ).count()
        finally:
            session.close()

    def search_docs(self, query: str) -> List[Dict]:
        session = self.get_session()
        try:
            docs = session.query(Documento).filter(
                Documento.titulo.ilike(f"%{query}%") |
                Documento.contenido.ilike(f"%{query}%")
            ).limit(10).all()
            return [{
                "titulo": d.titulo, "area": d.area, "path": d.path
            } for d in docs]
        finally:
            session.close()

    def cancel_vacation_request(self, user_id: int, solicitud_id: int) -> bool:
        session = self.get_session()
        try:
            sol = session.query(Solicitud).filter(
                Solicitud.id == solicitud_id,
                Solicitud.empleado_id == user_id,
                Solicitud.estado == "pending",
            ).first()
            if sol:
                session.delete(sol)
                session.commit()
                return True
            return False
        finally:
            session.close()


from datetime import timedelta