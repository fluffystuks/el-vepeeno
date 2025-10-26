from db import get_key_by_id

EXTEND_DISABLED_NOTICE = (
    "🚧 Продление подписки временно недоступно.\n"
    "Мы сообщим, как только сервис возобновит работу."
)


async def extend_key_handler(update, context):
    query = update.callback_query
    data = query.data
    print("🔍 query.data:", data)

    parts = data.split("_")
    key_id = int(parts[1]) if len(parts) > 1 else None

    if key_id is None or not get_key_by_id(key_id):
        await query.answer("❌ Ключ не найден!", show_alert=True)
        return

    await query.answer(EXTEND_DISABLED_NOTICE, show_alert=True)
