import bcrypt
from datetime import datetime
from bot.config import get_settings


def set_pin(db, user_id: int, pin: str) -> bool:
    hash_bytes = bcrypt.hashpw(pin.encode(), bcrypt.gensalt())
    return db.set_pin(user_id, hash_bytes.decode())


def verify_pin(user_id: int, db, config) -> bool:
    session = db.get_session()
    try:
        from bot.db.models import Empleado
        emp = session.query(Empleado).filter(Empleado.id == user_id).first()
        if not emp or not emp.pin_hash:
            return False
        if emp.pin_locked_until and emp.pin_locked_until > datetime.utcnow():
            return False
        if bcrypt.checkpw(config.telegram.pin_attempts, emp.pin_hash.encode()):
            return True
        return False
    finally:
        session.close()