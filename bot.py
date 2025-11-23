import logging
import os
from typing import Dict

from dotenv import load_dotenv
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Загружаем переменные из .env
load_dotenv()

# Логирование
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Простое хранилище состояний в памяти процесса
user_states: Dict[int, str] = {}

STATE_NEW = "new"
STATE_DOOR_SHOWN = "door_shown"
STATE_CLOSED = "closed"


# ==========================
# Хэндлеры
# ==========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Старт бота / первое сообщение от пользователя.
    Показываем текст про дверь + кнопку.
    """
    if update.message is None:
        return

    user_id = update.effective_user.id
    state = user_states.get(user_id)

    # Если дверь уже была открыта и закрыта
    if state == STATE_CLOSED:
        await update.message.reply_text(
            "🚪 Дверь уже закрыта.\n"
            "Повтор открыть невозможен."
        )
        return

    user_states[user_id] = STATE_NEW

    keyboard = [
        [InlineKeyboardButton("Открыть дверь", callback_data="open_intro")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        "На сегодня у тебя есть одна дверь.\n"
        "Она откроется только один раз.\n"
        "Если откроешь — вернуться нельзя.\n\n"
        "Готова?"
    )

    await update.message.reply_text(text, reply_markup=reply_markup)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Любое текстовое сообщение (не команда) — ведём себя как /start,
    но учитываем состояние пользователя.
    """
    if update.message is None:
        return

    user_id = update.effective_user.id
    state = user_states.get(user_id)

    if state == STATE_CLOSED:
        await update.message.reply_text(
            "🚪 Дверь уже закрыта.\n"
            "Повтор открыть невозможен."
        )
        return

    # Для новых/неопределённых состояний просто запускаем сценарий
    await start(update, context)


async def on_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработка нажатий на inline-кнопки.
    """
    query = update.callback_query
    if query is None:
        return

    await query.answer()   # убираем «часики» на кнопке

    user_id = query.from_user.id
    state = user_states.get(user_id)
    data = query.data

    # Если дверь уже была закрыта
    if state == STATE_CLOSED:
        await query.edit_message_text(
            "🚪 Дверь уже закрыта.\n"
            "Повтор открыть невозможен."
        )
        return

    # Первый шаг — показать дверь
    if data == "open_intro":
        user_states[user_id] = STATE_DOOR_SHOWN

        door_art = (
            "   ┌───────────┐\n"
            "   │     🚪     │\n"
            "   │           │\n"
            "   └───────────┘"
        )

        keyboard = [
            [InlineKeyboardButton("Открыть", callback_data="open_door")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        text = (
            f"{door_art}\n\n"
            "Она откроется, только если ты действительно хочешь.\n"
            "Это не игра и не квест.\n"
            "Это момент."
        )

        await query.edit_message_text(text, reply_markup=reply_markup)
        return

    # Второй шаг — открыть дверь (одноразовый сценарий)
    if data == "open_door" and state == STATE_DOOR_SHOWN:
        user_states[user_id] = STATE_CLOSED

        # 1. Первый текст о «пустом пространстве»
        text_1 = (
            "…Иногда за дверью ничего не бывает.\n"
            "Просто пространство.\n"
            "Пауза.\n"
            "Мгновение."
        )
        await query.edit_message_text(text_1)

        # 2. Главное сообщение
        text_2 = (
            "Но сегодня — не так.\n\n"
            "Сегодня за дверью есть одно единственное сообщение:\n"
            "ты правда заслуживаешь моменты, которые делают день теплее.\n"
            "И я захотел подарить тебе один такой момент.\n\n"
            "Спасибо, что открыла."
        )
        await query.message.reply_text(text_2)

        await query.message.reply_text("Дверь закрывается…")
        await query.message.reply_text(
            "🚪 Закрыто.\n"
            "Надеюсь, твой день пройдет ярко!"
        )
        return


# ==========================
# Запуск приложения
# ==========================

def main() -> None:
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise RuntimeError(
            "BOT_TOKEN не найден в .env файле.\n"
            "Создай рядом с bot.py файл .env со строкой:\n"
            "BOT_TOKEN=твой_токен_от_BotFather"
        )

    application = ApplicationBuilder().token(bot_token).build()

    # Команды
    application.add_handler(CommandHandler("start", start))

    # Callback-кнопки
    application.add_handler(CallbackQueryHandler(on_callback_query))

    # Обычные сообщения (текст, не команда)
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    logger.info("Бот запущен. Нажми Ctrl+C для остановки.")
    application.run_polling()


if __name__ == "__main__":
    main()
