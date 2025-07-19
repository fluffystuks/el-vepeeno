# scheduler.py
import datetime
import pytz
from telegram.ext import Application
from utils import refresh_session_key_once
from scheduler_tasks import check_keys_once

async def start_scheduler(application: Application):
    # Проверка ключей раз в сутки, в 00:00 по Москве
    application.job_queue.run_daily(
        callback=check_keys_once,
        time=datetime.time(hour=0, minute=0, tzinfo=pytz.timezone("Europe/Moscow")),
        days=(0, 1, 2, 3, 4, 5, 6)
    )

    application.job_queue.run_repeating(
        refresh_session_key_once,
        interval=12 * 60 * 60,
        first=0
    )