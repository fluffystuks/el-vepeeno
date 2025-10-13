import warnings
from telegram.warnings import PTBUserWarning

warnings.filterwarnings(
    action="ignore",
    message=r".*CallbackQueryHandler.*",
    category=PTBUserWarning
)
import logging
logging.getLogger("telegram").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.WARNING)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters
)
from config import TELEGRAM_TOKEN
from db import init_db
from handlers.start import start
from handlers.payment import (
    pay_handler,
    process_payment_amount,
    check_payment_handler,
    cancel_payment_handler,
    cancel_handler,
    timeout_handler
)
from handlers.keys import connect_handler, tariff_handler
from handlers.account import (
    account_handler,
    show_key_handler,
    delete_key_prompt,
    delete_key_confirm,
    transfer_key_handler,
)
from handlers.extend import extend_key_handler
from handlers.misc import help_handler, instruction_handler, rules_handler
from handlers.referral import (
    list_bonuses,
    referral_menu,
    show_bonuses,
    choose_bonus_key,
    apply_bonus_button,
)
from handlers.admin import (
    admin_panel,
    admin_choose_audience,
    admin_broadcast_message,
    admin_cancel,
    admin_cancel_callback,
    SELECT_ACTION,
    WAITING_MESSAGE,
)
from services.key_service import login
from scheduler import start_scheduler

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
        ],
        ConversationHandler.TIMEOUT: [
            MessageHandler(filters.ALL, timeout_handler)
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_handler)
    ],
    allow_reentry=True,
    conversation_timeout=60  
)


admin_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("admin", admin_panel)],
    states={
        SELECT_ACTION: [
            CallbackQueryHandler(admin_choose_audience, pattern="^admin_broadcast_(all|active)$"),
            CallbackQueryHandler(admin_cancel_callback, pattern="^admin_cancel$"),
        ],
        WAITING_MESSAGE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, admin_broadcast_message)
        ],
    },
    fallbacks=[CommandHandler("cancel", admin_cancel)],
    per_message=False,
)


async def post_init(application):
    await start_scheduler(application)

    await application.bot.set_my_commands([
        BotCommand("start", "Запустить бота"),
        BotCommand("pay", "Пополнить баланс"),
        BotCommand("check_payment", "Проверить платёж"),
        BotCommand("bonuses", "Список бонусов")
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
    application.add_handler(admin_conv_handler)
    application.add_handler(CommandHandler("bonuses", list_bonuses))
    application.add_handler(payment_conv_handler)
    application.add_handler(CommandHandler("check_payment", check_payment_handler))
    application.add_handler(CommandHandler("cancel_payment", cancel_payment_handler))

    application.add_handler(CallbackQueryHandler(account_handler, pattern="^account$"))
    application.add_handler(CallbackQueryHandler(rules_handler, pattern="^rules$"))
    application.add_handler(CallbackQueryHandler(extend_key_handler, pattern="^extend_"))
    application.add_handler(CallbackQueryHandler(show_key_handler, pattern="^key_"))
    application.add_handler(CallbackQueryHandler(transfer_key_handler, pattern="^transfer_"))
    application.add_handler(CallbackQueryHandler(delete_key_prompt, pattern="^delete_"))
    application.add_handler(CallbackQueryHandler(delete_key_confirm, pattern="^confirm_delete_"))
    application.add_handler(CallbackQueryHandler(check_payment_handler, pattern="^check_payment$"))
    application.add_handler(CallbackQueryHandler(cancel_payment_handler, pattern="^cancel_payment$"))
    application.add_handler(CallbackQueryHandler(connect_handler, pattern="^connect$"))
    application.add_handler(CallbackQueryHandler(tariff_handler, pattern="^(trial|100rub|250rub|500rub|back)$"))
    application.add_handler(CallbackQueryHandler(referral_menu, pattern="^referral$"))
    application.add_handler(CallbackQueryHandler(show_bonuses, pattern="^show_bonuses$"))
    application.add_handler(CallbackQueryHandler(choose_bonus_key, pattern="^use_bonus$"))
    application.add_handler(CallbackQueryHandler(apply_bonus_button, pattern="^apply_bonus_"))
    application.add_handler(CallbackQueryHandler(help_handler, pattern="^help$"))
    application.add_handler(CallbackQueryHandler(instruction_handler, pattern="^instruction$"))

    application.run_polling()

if __name__ == "__main__":
    main()
