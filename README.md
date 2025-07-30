100% GPT README Made
---

````markdown
# 🛰️ Telegram VPN Bot — Pien VPN

Телеграм-бот для продажи VPN-ключей с автогенерацией, оплатой через ЮKassa и встроенной реферальной системой.

## 🚀 Возможности

- 🎁 Бесплатный пробный ключ (1 раз на пользователя)
- 🔑 Генерация и продление VPN-ключей через панель `3x-ui`
- 💳 Пополнение баланса через YooKassa
- ⏰ Автоуведомления о скором истечении ключей и бонусов
- 👥 Реферальная программа:
  - +3 дня за приглашённого друга
  - +20% дней от покупок реферала
  - +10 дней за 3 платящих реферала
  - +15 дней за 5 платящих
  - Реферал получает +3 дня и до +7 за оплату

## 🛠 Установка

1. Клонируй репозиторий:
   ```bash
   git clone https://github.com/yourname/telegram-vpn-bot.git
   cd telegram-vpn-bot
````

2. Установи зависимости:

   ```bash
   pip install -r requirements.txt
   ```

3. Создай `.env` файл:

   ```env
   TELEGRAM_TOKEN=your_bot_token
   API_URL=https://your.3x-ui.host
   PANEL_USERNAME=admin
   PANEL_PASSWORD=password
   YOOKASSA_ACCOUNT_ID=your_account_id
   YOOKASSA_SECRET_KEY=your_secret
   ADMIN_TG_ID=123456789
   ```

4. Запусти бота:

   ```bash
   python bot.py
   ```

## 📁 Структура

* `bot.py` — запуск и маршрутизация команд
* `handlers/` — логика взаимодействия с пользователем
* `services/` — работа с 3x-ui и YooKassa
* `db.py` — SQLite-хранилище данных
* `scheduler.py` — регулярные задачи (истечение ключей, бонусы)
* `start.py` — обработка `/start` и приглашений
* `referral.py` — логика бонусов и ссылок

## 💼 Зависимости

Создай `requirements.txt`, например:

```txt
python-telegram-bot==20.3
requests
python-dotenv
yookassa
pytz
```

Установи через:

```bash
pip install -r requirements.txt
```

## 👨‍💻 Авторы

Разработано с любовью:

* [24.txt](https://github.com/fluffystuks)
* [phtea](https://github.com/phtea)

## 🛡 Безопасность

* Telegram ID используется как уникальный идентификатор
* Ключи и платежи хранятся локально
* SESSION\_KEY обновляется каждые 12 часов

## 📄 Лицензия

MIT © 24.txt & phtea

## ⚙ Обновление базы

При переходе на новый inbound необходимо добавить колонку `inbound_id` в таблицу `keys` и отметить существующие ключи как созданные во 2 инбаунде:

```sql
ALTER TABLE keys ADD COLUMN inbound_id INTEGER DEFAULT 1;
UPDATE keys SET inbound_id = 2;
```

### 🛠 Массовый перенос ключей

После обновления структуры запустите скрипт `migrate_old_keys.py`, который
создаст новые ключи в inbound 1 и сократит срок старых ключей до 3 дней.
