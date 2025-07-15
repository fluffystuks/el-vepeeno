import asyncio
from datetime import datetime, timedelta
import pytz

from db import get_expiring_keys, deactivate_key
import math

async def start_scheduler(bot):
    while True:
        
        tz = pytz.timezone('Europe/Moscow')
        now = datetime.now(tz)

        
        next_run = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        seconds_until_next_run = (next_run - now).total_seconds()

        print(f"⏳ Следующая проверка ключей будет через {seconds_until_next_run:.2f} секунд (по МСК)")

        await asyncio.sleep(seconds_until_next_run)

        print("🔄 Наступило 00:00 по МСК — выполняем проверку ключей!")

        keys = get_expiring_keys()

        for key in keys:
            remaining_sec = key['remaining_seconds']
            days_left = math.ceil(remaining_sec / 86400)

            tg_id = key['tg_id']
            email = key['email']

            try:
                if days_left == 7:
                    await bot.send_message(
                        chat_id=tg_id,
                        text=f"🔔 Напоминание: Ваш ключ {email} истекает через 7 дней!"
                    )
                elif days_left == 3:
                    await bot.send_message(
                        chat_id=tg_id,
                        text=f"🔔 Напоминание: Ваш ключ {email} истекает через 3 дня!"
                    )
                elif days_left == 1:
                    await bot.send_message(
                        chat_id=tg_id,
                        text=f"🔔 Напоминание: Ваш ключ {email} истекает завтра!"
                    )
                elif days_left <= 0:
                    await bot.send_message(
                        chat_id=tg_id,
                        text=f"⏰ Ваш ключ {email} истёк! Продлите или купите новый."
                    )
                    deactivate_key(key['key_id'])

            except Exception as e:
                print(f"❌ Ошибка отправки уведомления: {e}")

        print("✅ Проверка завершена.")