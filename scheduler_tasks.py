# scheduler_tasks.py
from config import ADMIN_TG_ID
import math
from datetime import datetime
from pathlib import Path
import shutil
from db import (
    get_expiring_keys,
    deactivate_key,
    update_notified_level,
    get_all_active_bonuses,
    expire_bonus,
)

async def check_keys_once(context):
    bot = context.bot
    start_msg = f"[{datetime.now().strftime('%H:%M:%S')}] 🔄 Проверка ключей"
    print(start_msg)
    if ADMIN_TG_ID:
        try:
            await bot.send_message(chat_id=ADMIN_TG_ID, text=start_msg)
        except Exception as e:
            print(f"❌ Не удалось отправить админу: {e}")

    keys = get_expiring_keys()
    for key in keys:
        try:
            await handle_key_notification(bot, key)
        except Exception as e:
            print(f"❌ Ошибка при уведомлении TG ID {key['tg_id']}: {e}")

async def handle_key_notification(bot, key):
    remaining_sec = key['remaining_seconds']
    days_left = math.ceil(remaining_sec / 86400)
    tg_id = key['tg_id']
    email = key['email']
    key_id = key['key_id']
    notified_level = key.get("notified_level", 0)

    messages = {
        7: (
            "🔔 *Напоминание:*\n\n"
            "Ваш ключ *{email}* истекает через *7 дней*.\n"
            "Продлите его заранее, чтобы не потерять доступ к VPN! 🔐\n\n"
            "Вы всегда можете продлить ключ в разделе «Аккаунт / Ключи».",
            1
        ),
        3: (
            "⚠️ *Осталось 3 дня!*\n\n"
            "Срок действия ключа *{email}* почти подошёл к концу.\n"
            "Продлите его сейчас, чтобы всё продолжало работать без перебоев. 🔄\n\n"
            "Если возникнут вопросы — раздел «Помощь» всегда рядом.",
            2
        ),
        1: (
            "⏳ *Последний день!*\n\n"
            "Завтра истекает срок действия ключа *{email}*.\n"
            "Успейте продлить, чтобы не потерять подключение. ⚡️\n\n"
            "Это можно сделать всего в пару нажатий в разделе «Аккаунт / Ключи».",
            3
        ),
        0: (
            "❌ *Ключ деактивирован*\n\n"
            "Срок действия ключа *{email}* завершился.\n"
            "Вы можете продлить его или купить новый прямо в боте. 🔁\n\n"
            "Спасибо, что пользуетесь нашим VPN — мы всегда рядом! ❤️",
            4
        )
    }


    for day, (text, level) in messages.items():
        if (days_left == day or (day == 0 and days_left <= 0)) and notified_level < level:
            if day == 0:
                deactivate_key(key_id)
            message = text.format(email=email)
            await bot.send_message(chat_id=tg_id, text=message, parse_mode="Markdown")
            update_notified_level(key_id, level)
            log_message = f"[📨] TG ID {tg_id} — {message}"
            if ADMIN_TG_ID:
                try:
                    await bot.send_message(chat_id=ADMIN_TG_ID, text=log_message)
                except Exception as e:
                    print(f"❌ Не удалось отправить админу: {e}")
            break


async def check_bonuses_once(context):
    bot = context.bot
    bonuses = get_all_active_bonuses()
    now = int(datetime.now().timestamp())
    for bonus in bonuses:
        days_left = math.ceil((bonus["expiry_time"] - now) / 86400)
        if bonus["expiry_time"] <= now:
            expire_bonus(bonus["id"])
            continue
        if bonus["days"] <= 0:
            continue
        if days_left in (7, 1):
            message = (
                f"🎁 Ваш бонус +{bonus['days']} дн. истекает через {days_left} дн."
            )
            try:
                await bot.send_message(chat_id=bonus["tg_id"], text=message)
                if ADMIN_TG_ID:
                    await bot.send_message(chat_id=ADMIN_TG_ID, text=f"[Бонус] TG ID {bonus['tg_id']} — {message}")
            except Exception:
                pass


async def backup_db_once(context):
    bot = context.bot
    now = datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] 💾 Создание бэкапа базы данных")
    if ADMIN_TG_ID:
        try:
            await bot.send_message(chat_id=ADMIN_TG_ID, text="💾 Создание бэкапа базы данных")
        except Exception as e:
            print(f"❌ Не удалось отправить админу: {e}")

    base_dir = Path(__file__).parent
    db_path = base_dir / "vpn_bot.db"
    backups_dir = base_dir / "backups"
    backups_dir.mkdir(exist_ok=True)

    if db_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backups_dir / f"vpn_bot_{timestamp}.db"
        shutil.copy2(db_path, backup_file)
        msg = f"📁 Бэкап сохранён: {backup_file}"
        print(msg)
        if ADMIN_TG_ID:
            try:
                await bot.send_message(chat_id=ADMIN_TG_ID, text=msg)
            except Exception as e:
                print(f"❌ Не удалось отправить админу: {e}")
    else:
        msg = f"❌ База данных не найдена: {db_path}"
        print(msg)
        if ADMIN_TG_ID:
            try:
                await bot.send_message(chat_id=ADMIN_TG_ID, text=msg)
            except Exception as e:
                print(f"❌ Не удалось отправить админу: {e}")
