from bot.skills.base import BaseSkill, SkillResult
from bot.utils.approval import send_approval_request
from datetime import datetime, timedelta
import re


class VacacionesSkill(BaseSkill):
    name = "vacaciones"
    description = "Solicitud de vacaciones con flujo de aprobación por botones"
    allowed_intents = ["solicitar_vacaciones", "cancelar_vacaciones"]
    permission = "empleado"
    tools = ["sqlite", "approval"]
    input_schema = {
        "fecha_inicio": {"type": "string", "format": "date"},
        "fecha_fin": {"type": "string", "format": "date"},
    }
    validation = {
        "fecha_inicio": "required",
        "fecha_fin": "required",
    }

    def _parse_dates(self, text: str) -> tuple:
        patterns = [
            r"(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})",
            r"(\d{1,2})\s+de\s+(\w+)\s+(\d{4})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.groups()
        return None

    async def execute(self, user_id: int, intent: str, args: Dict) -> SkillResult:
        if intent == "cancelar_vacaciones":
            return await self._cancel(user_id, args)

        user = self.db.get_user(user_id)
        if not user:
            return SkillResult(False, "Usuario no encontrado.")

        inicio_str = args.get("fecha_inicio")
        fin_str = args.get("fecha_fin")

        if not inicio_str or not fin_str:
            return SkillResult(False, "Debe indicar fecha de inicio y fin (ej: 5 al 9 de octubre).")

        try:
            inicio = datetime.strptime(inicio_str, "%Y-%m-%d").date()
            fin = datetime.strptime(fin_str, "%Y-%m-%d").date()
        except ValueError:
            return SkillResult(False, "Formato de fecha inválido. Use YYYY-MM-DD.")

        if inicio > fin:
            return SkillResult(False, "La fecha de inicio debe ser anterior a la de fin.")

        dias = (fin - inicio).days + 1
        saldo = user.get("saldo_vacaciones_dias", 0)

        if saldo < dias:
            return SkillResult(False, f"Saldo insuficiente. Tiene {saldo} días, solicitó {dias}.")

        anticipacion = (inicio - datetime.now().date()).days
        if anticipacion < 15:
            return SkillResult(False, f"Debe solicitar con ≥15 días de anticipación. Faltan {15 - anticipacion} días.")

        conflict = self.db.check_schedule_conflict(user_id, inicio, fin)
        if conflict:
            return SkillResult(False, f"Conflicto con turno programado: {conflict}")

        solicitud_id = self.db.create_vacation_request(user_id, inicio, fin, dias)

        await send_approval_request(
            self.router.transport,
            self.config.telegram.th_group_id,
            solicitud_id,
            user["nombre"],
            inicio,
            fin,
            dias,
            saldo - dias,
        )

        return SkillResult(
            success=True,
            message=(
                f"📋 Solicitud de vacaciones creada ({inicio} al {fin}, {dias} días).\n"
                f"Queda pendiente de aprobación por su líder."
            ),
            data={"solicitud_id": solicitud_id, "estado": "pending"},
            requires_approval=True,
            approval_data={"solicitud_id": solicitud_id},
        )

    async def _cancel(self, user_id: int, args: Dict) -> SkillResult:
        solicitud_id = args.get("solicitud_id")
        if not solicitud_id:
            return SkillResult(False, "Debe indicar el ID de la solicitud a cancelar.")
        ok = self.db.cancel_vacation_request(user_id, solicitud_id)
        if ok:
            return SkillResult(True, "Solicitud cancelada.")
        return SkillResult(False, "No se pudo cancelar (ya decidida o no existe).")