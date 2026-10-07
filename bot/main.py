import asyncio
import logging
from bot.config import get_settings
from bot.db import Database
from bot.engine.router import ModelRouter
from bot.skills import SKILLS, get_skill_names
from bot.transport.telegram import TelegramTransport

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class SkillRouter:
    def __init__(self):
        self.config = get_settings()
        self.db = Database()
        self.engine = ModelRouter()
        self.transport = None
        self.skills = {}
        self._init_skills()

    def _init_skills(self):
        for name, cls in SKILLS.items():
            self.skills[name] = cls(self)

    async def initialize(self):
        self.db.init_db()
        self.transport = TelegramTransport(self)
        await self.transport.start()
        logger.info("All systems initialized")

    async def shutdown(self):
        if self.transport:
            await self.transport.stop()
        logger.info("Shutdown complete")

    async def handle_registration(self, telegram_id: int, username: str, chat_id: int):
        user = self.db.get_user(telegram_id)
        if user:
            await self.transport.send_message(
                OutgoingMessage(
                    chat_id=chat_id,
                    text=f"✅ Bienvenido de nuevo, {user['nombre']}!",
                )
            )
        else:
            await self.transport.send_message(
                OutgoingMessage(
                    chat_id=chat_id,
                    text=(
                        "👋 Bienvenido a Clinic AI Assistant.\n"
                        "Para registrarse, contacte a Talento Humano con su cédula.\n"
                        "Ellos vincularán su Telegram ID a su perfil."
                    ),
                )
            )

    async def handle_pin_change(self, user_id: int, new_pin: str):
        if len(new_pin) != 4 or not new_pin.isdigit():
            return "El PIN debe ser de 4 dígitos."
        from bot.utils.pin import set_pin
        if set_pin(self.db, user_id, new_pin):
            return "✅ PIN actualizado correctamente."
        return "❌ Error al actualizar PIN."

    async def route_message(self, msg):
        user = self.db.get_user(msg.user_id)
        if not user:
            await self.transport.send_message(OutgoingMessage(
                chat_id=msg.chat_id,
                text="❌ No está registrado. Contacte a Talento Humano.",
            ))
            return

        intent_result = await self.engine.parse_intent(
            msg.text, user["role"], get_skill_names()
        )
        intent = intent_result.get("intent", "unknown")
        args = intent_result.get("args", {})
        confidence = intent_result.get("confidence", "LOW")

        if confidence == "LOW":
            await self.transport.send_message(OutgoingMessage(
                chat_id=msg.chat_id,
                text="🤔 No entendí su solicitud. ¿Podría reformularla?\n"
                     "Ejemplos: 'Necesito certificado laboral', "
                     "'Quiero vacaciones del 5 al 9 de octubre', "
                     "'¿Cuántos días me quedan?'",
            ))
            return

        if intent == "unknown":
            await self.transport.send_message(OutgoingMessage(
                chat_id=msg.chat_id,
                text="❓ No reconozco esa acción. Use /ayuda para ver opciones.",
            ))
            return

        skill_name = self._intent_to_skill(intent)
        if not skill_name:
            await self.transport.send_message(OutgoingMessage(
                chat_id=msg.chat_id,
                text=f"❌ Intención '{intent}' no mapeada a ninguna habilidad.",
            ))
            return

        skill = self.skills.get(skill_name)
        if not skill:
            await self.transport.send_message(OutgoingMessage(
                chat_id=msg.chat_id,
                text=f"❌ Habilidad '{skill_name}' no implementada.",
            ))
            return

        result = await skill.execute(msg.user_id, intent, args)

        if result.files:
            for f in result.files:
                await self.transport.send_file(OutgoingFile(
                    chat_id=msg.chat_id, file_path=f, caption=result.message,
                ))
        else:
            await self.transport.send_message(OutgoingMessage(
                chat_id=msg.chat_id, text=result.message,
            ))

    async def handle_callback(self, callback):
        data = callback.data
        if data.startswith("approve:") or data.startswith("reject:"):
            from bot.utils.approval import handle_approval_callback
            result = await handle_approval_callback(self.db, data, callback.user_id, self.transport)
            await self.transport.answer_callback(callback.data, result, show_alert=True)
        else:
            await self.transport.answer_callback(callback.data, "Acción no reconocida.")

    async def handle_skill(self, user_id: int, intent: str, args: Dict) -> str:
        skill_name = self._intent_to_skill(intent)
        if not skill_name:
            return "Intención no reconocida."
        skill = self.skills.get(skill_name)
        if not skill:
            return "Habilidad no disponible."
        result = await skill.execute(user_id, intent, args)
        return result.message

    def _intent_to_skill(self, intent: str) -> str:
        mapping = {
            "certificado_laboral": "certificados",
            "certificado_tiempos": "certificados",
            "certificado_salario": "certificados",
            "solicitar_vacaciones": "vacaciones",
            "cancelar_vacaciones": "vacaciones",
            "saldo_vacaciones": "consulta",
            "mi_horario": "consulta",
            "mi_perfil": "consulta",
            "equipo_vacaciones": "consulta",
            "certificados_mes": "consulta",
            "reglamento": "consulta",
        }
        return mapping.get(intent)


from bot.transport.base import OutgoingMessage, OutgoingFile


async def main():
    router = SkillRouter()
    await router.initialize()

    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        await router.shutdown()


if __name__ == "__main__":
    asyncio.run(main())