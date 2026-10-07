from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from bot.config import get_settings


async def send_approval_request(transport, group_id: int, solicitud_id: int,
                                empleado: str, inicio, fin, dias: int, saldo_restante: int):
    text = (
        f"📋 <b>Solicitud de vacaciones</b>\n"
        f"Empleado: {empleado}\n"
        f"Fechas: {inicio} al {fin} ({dias} días)\n"
        f"Saldo restante: {saldo_restante} días\n"
    )
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Aprobar", callback_data=f"approve:{solicitud_id}"),
        InlineKeyboardButton("❌ Rechazar", callback_data=f"reject:{solicitud_id}"),
    ]])
    await transport.send_message(OutgoingMessage(
        chat_id=group_id, text=text, reply_markup=keyboard
    ))


async def handle_approval_callback(db, callback_data: str, leader_id: int, transport) -> str:
    action, solicitud_id = callback_data.split(":")
    solicitud_id = int(solicitud_id)

    if action == "approve":
        ok = db.approve_vacation(solicitud_id, leader_id)
        return "✅ Solicitud aprobada." if ok else "❌ No se pudo aprobar."
    elif action == "reject":
        ok = db.reject_vacation(solicitud_id, leader_id)
        return "✅ Solicitud rechazada." if ok else "❌ No se pudo rechazar."
    return "Acción no reconocida."