from bot.skills.base import BaseSkill, SkillResult
from bot.engine.labor_law import calculate_night_surcharge, calculate_sunday_surcharge
from datetime import datetime, timedelta
import json


class ConsultaSkill(BaseSkill):
    name = "consulta"
    description = "Consultas de saldo, horario, perfil y datos del equipo"
    allowed_intents = [
        "saldo_vacaciones", "mi_horario", "mi_perfil",
        "equipo_vacaciones", "certificados_mes", "reglamento"
    ]
    permission = "empleado"
    tools = ["sqlite", "docs_search", "labor_law_engine"]
    input_schema = {
        "tipo": {"type": "string", "enum": ["saldo", "horario", "perfil", "equipo", "certificados", "reglamento"]},
        "periodo": {"type": "string"},
    }

    async def execute(self, user_id: int, intent: str, args: Dict) -> SkillResult:
        user = self.db.get_user(user_id)
        if not user:
            return SkillResult(False, "Usuario no encontrado.")

        role = user.get("role", "empleado")

        if intent == "saldo_vacaciones":
            return self._saldo_vacaciones(user)
        elif intent == "mi_horario":
            return self._mi_horario(user)
        elif intent == "mi_perfil":
            return self._mi_perfil(user)
        elif intent == "equipo_vacaciones":
            return self._equipo_vacaciones(user, role)
        elif intent == "certificados_mes":
            return self._certificados_mes(user, role)
        elif intent == "reglamento":
            return self._reglamento(args.get("periodo", ""))

        return SkillResult(False, "Consulta no reconocida.")

    def _saldo_vacaciones(self, user: Dict) -> SkillResult:
        saldo = user.get("saldo_vacaciones_dias", 0)
        msg = f"📅 <b>Saldo de vacaciones:</b> {saldo} días disponibles."
        return SkillResult(True, msg)

    def _mi_horario(self, user: Dict) -> SkillResult:
        semana = self.db.get_schedule_week(user["id"])
        if not semana:
            return SkillResult(True, "No hay turnos programados para esta semana.")

        lines = ["📋 <b>Mi horario esta semana:</b>"]
        for dia in semana:
            turno = dia.get("turno", "Libre")
            hora_ini = dia.get("hora_inicio", "")
            hora_fin = dia.get("hora_fin", "")
            recargo = dia.get("recargo_calculado", 0)
            extra = f" (recargo: ${recargo:,.0f})" if recargo > 0 else ""
            lines.append(f"• {dia['fecha']}: {turno} {hora_ini}-{hora_fin}{extra}")

        return SkillResult(True, "\n".join(lines))

    def _mi_perfil(self, user: Dict) -> SkillResult:
        lines = [
            "👤 <b>Mi perfil</b>",
            f"• Nombre: {user.get('nombre', 'N/A')}",
            f"• Cédula: {user.get('cedula', 'N/A')}",
            f"• Cargo: {user.get('cargo', 'N/A')}",
            f"• Área: {user.get('area', 'N/A')}",
            f"• Ingreso: {user.get('fecha_ingreso', 'N/A')}",
            f"• Saldo vacaciones: {user.get('saldo_vacaciones_dias', 0)} días",
        ]
        return SkillResult(True, "\n".join(lines))

    def _equipo_vacaciones(self, user: Dict, role: str) -> SkillResult:
        if role not in ["lider", "rrhh"]:
            return SkillResult(False, "Solo líderes y RRHH pueden ver vacaciones del equipo.")

        equipo = self.db.get_team_vacations(user["id"], role)
        if not equipo:
            return SkillResult(True, "No hay solicitudes de vacaciones pendientes en su equipo.")

        lines = ["📋 <b>Vacaciones del equipo:</b>"]
        for s in equipo:
            estado_emoji = {"pending": "⏳", "approved": "✅", "rejected": "❌"}.get(s["estado"], "❓")
            lines.append(
                f"{estado_emoji} {s['empleado']} — {s['fecha_inicio']} a {s['fecha_fin']} "
                f"({s['dias']} días) — {s['estado']}"
            )
        return SkillResult(True, "\n".join(lines))

    def _certificados_mes(self, user: Dict, role: str) -> SkillResult:
        if role != "rrhh":
            return SkillResult(False, "Solo RRHH puede ver estadísticas de certificados.")

        count = self.db.count_certificates_this_month()
        return SkillResult(True, f"📄 Certificados emitidos este mes: {count}")

    def _reglamento(self, query: str) -> SkillResult:
        docs = self.db.search_docs(query) if query else []
        if not docs:
            return SkillResult(True, "No se encontraron documentos relevantes.")

        lines = ["📚 <b>Resultados:</b>"]
        for d in docs[:5]:
            lines.append(f"• {d['titulo']} ({d['area']})")
        return SkillResult(True, "\n".join(lines))