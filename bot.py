from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters
)
import datetime
from config import TELEGRAM_TOKEN
from db import init_db
from handlers.start import start
from handlers.payment import (
    pay_handler,
    process_payment_amount,
    check_payment_handler,
    cancel_payment_handler
)
from handlers.keys import connect_handler, tariff_handler
from handlers.account import account_handler, show_key_handler
from handlers.extend import extend_key_handler
from handlers.misc import help_handler, instruction_handler, rules_handler
from scheduler import start_scheduler
from services.key_service import login
from utils import refresh_session_key_once

from telegram import BotCommand, MenuButtonCommands

PAYMENT_AMOUNT = 1

payment_conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("pay", pay_handler),
        CallbackQueryHandler(pay_handler, pattern="^top_up$")
    ],
    states={
        PAYMENT_AMOUNT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, process_payment_amount)
        ]
    },
    fallbacks=[],
    allow_reentry=True
)

async def post_init(application):
    
    application.job_queue.run_daily(
        start_scheduler,
        time=datetime.time(hour=0, minute=0)
    )

    
    application.job_queue.run_repeating(
        refresh_session_key_once,
        interval=12*60*60
    )

    
    await application.bot.set_my_commands([
        BotCommand("start", "Запустить бота"),
        BotCommand("pay", "Пополнить баланс"),
        BotCommand("check_payment", "Проверить платёж")
    ])
    await application.bot.set_chat_menu_button(menu_button=MenuButtonCommands())

def main():
    init_db()
    login()  

    application = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .post_init(post_init)  
        .build()
    )

    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(payment_conv_handler)
    application.add_handler(CommandHandler("check_payment", check_payment_handler))
    application.add_handler(CommandHandler("cancel_payment", cancel_payment_handler))

    application.add_handler(CallbackQueryHandler(account_handler, pattern="^account$"))
    application.add_handler(CallbackQueryHandler(rules_handler, pattern="^rules$"))
    application.add_handler(CallbackQueryHandler(extend_key_handler, pattern="^extend_"))
    application.add_handler(CallbackQueryHandler(show_key_handler, pattern="^key_"))
    application.add_handler(CallbackQueryHandler(check_payment_handler, pattern="^check_payment$"))
    application.add_handler(CallbackQueryHandler(cancel_payment_handler, pattern="^cancel_payment$"))
    application.add_handler(CallbackQueryHandler(connect_handler, pattern="^connect$"))
    application.add_handler(CallbackQueryHandler(tariff_handler, pattern="^(trial|100rub|250rub|500rub|back)$"))
    application.add_handler(CallbackQueryHandler(help_handler, pattern="^help$"))
    application.add_handler(CallbackQueryHandler(instruction_handler, pattern="^instruction$"))

    application.run_polling()

if __name__ == "__main__":
    main()
