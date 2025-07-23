import asyncio
from services.key_service import login
from telegram.ext import CallbackContext
from config import ADMIN_TG_ID


async def notify_admin(bot, text: str) -> None:
    """Send a log message to the admin if ADMIN_TG_ID is set."""
    if not ADMIN_TG_ID:
        return
    try:
        await bot.send_message(chat_id=ADMIN_TG_ID, text=text)
    except Exception as e:
        print(f"❌ Не удалось отправить админу: {e}")

async def refresh_session_key_once(context: CallbackContext) -> None:
    bot = context.bot

    print("🔑 Пробуем обновить SESSION_KEY...")
    await notify_admin(bot, "🔑 Пробуем обновить SESSION_KEY...")

    success = login()

    if success:
        msg = "✅ SESSION_KEY обновлён!"
    else:
        msg = "❌ Не удалось обновить SESSION_KEY."

    print(msg)
    await notify_admin(bot, msg)

