from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    InputFile, BotCommand
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from bot.transport.base import (
    TransportAdapter, IncomingMessage, OutgoingMessage,
    OutgoingFile, CallbackQuery
)
from bot.config import get_settings
import logging

logger = logging.getLogger(__name__)


class TelegramTransport(TransportAdapter):
    def __init__(self, router):
        self.router = router
        self.settings = get_settings()
        self.app: Application = None

    async def start(self) -> None:
        self.app = Application.builder().token(
            self.settings.telegram_bot_token
        ).build()

        self.app.add_handler(CommandHandler("start", self._cmd_start))
        self.app.add_handler(CommandHandler("pin", self._cmd_pin))
        self.app.add_handler(CommandHandler("perfil", self._cmd_perfil))
        self.app.add_handler(CommandHandler("ayuda", self._cmd_ayuda))
        self.app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, self._on_message
        ))
        self.app.add_handler(CallbackQueryHandler(self._on_callback))

        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()

        await self._set_commands()
        logger.info("Telegram bot started")

    async def stop(self) -> None:
        if self.app:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()

    async def _set_commands(self) -> None:
        commands = [
            BotCommand("start", "Registrarse / iniciar"),
            BotCommand("pin", "Cambiar PIN de seguridad"),
            BotCommand("perfil", "Ver mi perfil"),
            BotCommand("ayuda", "Comandos disponibles"),
        ]
        await self.app.bot.set_my_commands(commands)

    async def send_message(self, msg: OutgoingMessage) -> None:
        await self.app.bot.send_message(
            chat_id=msg.chat_id,
            text=msg.text,
            reply_markup=msg.reply_markup,
            parse_mode=msg.parse_mode,
        )

    async def send_file(self, file: OutgoingFile) -> None:
        with open(file.file_path, "rb") as f:
            await self.app.bot.send_document(
                chat_id=file.chat_id,
                document=InputFile(f, filename=file.file_path.split("/")[-1]),
                caption=file.caption,
            )

    async def answer_callback(self, callback_id: str, text: str, show_alert: bool = False) -> None:
        await self.app.bot.answer_callback_query(
            callback_query_id=callback_id,
            text=text,
            show_alert=show_alert,
        )

    def register_handlers(self, router) -> None:
        self.router = router

    async def _cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        await self.router.handle_registration(
            telegram_id=user.id,
            username=user.username,
            chat_id=update.effective_chat.id,
        )

    async def _cmd_pin(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if context.args:
            new_pin = context.args[0]
            await self.router.handle_pin_change(user.id, new_pin)
        else:
            await update.message.reply_text(
                "Uso: /pin <nuevo_pin_de_4_digitos>"
            )

    async def _cmd_perfil(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        result = await self.router.handle_skill(
            user_id=user.id,
            intent="perfil",
            args={},
        )
        await self.send_message(OutgoingMessage(
            chat_id=update.effective_chat.id,
            text=result,
        ))

    async def _cmd_ayuda(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        help_text = (
            "🤖 <b>Clinic AI Assistant</b>\n\n"
            "<b>Comandos:</b>\n"
            "• /start — Registrarse en el sistema\n"
            "• /pin <pin> — Cambiar PIN de seguridad\n"
            "• /perfil — Ver mi perfil y saldos\n"
            "• /ayuda — Esta ayuda\n\n"
            "<b>Ejemplos:</b>\n"
            '• "Necesito certificado laboral"\n'
            '• "Quiero vacaciones del 5 al 9 de octubre"\n'
            '• "¿Cuántos días de vacaciones me quedan?"\n'
            '• "¿Cuándo trabajo esta semana?"'
        )
        await update.message.reply_text(help_text, parse_mode="HTML")

    async def _on_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        msg = IncomingMessage(
            user_id=user.id,
            username=user.username,
            text=update.message.text,
            chat_id=update.effective_chat.id,
            message_id=update.message.message_id,
        )
        await self.router.route_message(msg)

    async def _on_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        await query.answer()
        cb = CallbackQuery(
            user_id=query.from_user.id,
            data=query.data,
            message_chat_id=query.message.chat_id,
            message_id=query.message.message_id,
        )
        await self.router.handle_callback(cb)