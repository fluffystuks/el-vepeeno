import asyncio
from services.key_service import login
from telegram.ext import CallbackContext

async def refresh_session_key_once(context: CallbackContext) -> None:
    print("🔑 Пробуем обновить SESSION_KEY...")
    success = login()
    if success:
        print("✅ SESSION_KEY обновлён!")
    else:
        print("❌ Не удалось обновить SESSION_KEY.")

async def schedule_session_refresh():
    await refresh_session_key_once()

    loop = asyncio.get_event_loop()

    loop.call_later(
        12 * 60 * 60,
        lambda: asyncio.create_task(schedule_session_refresh())
    )
