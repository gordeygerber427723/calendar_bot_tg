import asyncio
import os

from datetime import date, time, datetime
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher, F
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from dotenv import load_dotenv

from database import (
    init_db,
    save_event,
    get_user_events,
    get_user_event,
    delete_user_event,
    set_daily_reminder,
    get_reminder_events,
    get_event_reminder_events,
    mark_event_reminder_sent,
    save_user_timezone,
    get_user_timezone,
    has_user_timezone,
    get_last_reminder_date,
    set_last_reminder_date,
)


load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
PROXY_URL = os.getenv("TELEGRAM_PROXY")

if not TOKEN or TOKEN == "PASTE_YOUR_TELEGRAM_BOT_TOKEN_HERE":
    raise RuntimeError("Set your real BOT_TOKEN in .env")

if not PROXY_URL:
    raise RuntimeError("Set your TELEGRAM_PROXY in .env")


dp = Dispatcher()


class AddEvent(StatesGroup):
    waiting_for_title = State()
    waiting_for_date = State()
    waiting_for_time = State()


class TimezoneState(StatesGroup):
    waiting_for_timezone = State()


main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="➕ Добавить событие"),
            KeyboardButton(text="📅 Мои события"),
        ],
        [
            KeyboardButton(text="🌍 Часовой пояс"),
            KeyboardButton(text="❓ Помощь"),
        ],
    ],
    resize_keyboard=True,
    input_field_placeholder="Выбери действие...",
)


def event_list_keyboard(events: list[dict]) -> InlineKeyboardMarkup:
    buttons = []

    for event in events:
        title = event["title"]
        if len(title) > 55:
            title = title[:52] + "..."

        buttons.append([
            InlineKeyboardButton(
                text=f"📅 {title}",
                callback_data=f"evt:view:{event['id']}",
            )
        ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def event_detail_keyboard(
    event_id: int,
    reminder_enabled: bool = False,
) -> InlineKeyboardMarkup:
    reminder_text = (
        "🔕 Выключить ежедневные напоминания"
        if reminder_enabled
        else "🔔 Включить ежедневные напоминания"
    )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⏳ Сколько дней осталось?",
                    callback_data=f"evt:countdown:{event_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=reminder_text,
                    callback_data=f"evt:reminder:{event_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑️ Удалить",
                    callback_data=f"evt:delete:{event_id}",
                ),
                InlineKeyboardButton(
                    text="⬅️ Назад к списку",
                    callback_data="evt:list",
                ),
            ],
        ]
    )


def event_list_text(events: list[dict], prefix: str = "") -> str:
    if not events:
        return (
            f"{prefix}"
            "📋 Список событий\n\n"
            "У тебя пока нет событий.\n"
            "Нажми «➕ Добавить событие», чтобы создать первое."
        )

    return (
        f"{prefix}"
        "📋 Список событий\n\n"
        "Выбери событие, чтобы посмотреть подробности:"
    )


async def send_event_list(
    message: Message,
    user_id: int,
    prefix: str = "",
):
    events = get_user_events(user_id)

    await message.answer(
        event_list_text(events, prefix),
        reply_markup=event_list_keyboard(events) if events else None,
    )


@dp.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    await state.clear()

    user_id = message.from_user.id

    if has_user_timezone(user_id):
        await message.answer(
            "Привет! 📅\n\n"
            "Я твой календарный бот.\n"
            "Добавляй события и просматривай их в удобном списке.",
            reply_markup=main_keyboard,
        )
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🇷🇺 Москва",
                    callback_data="timezone:Europe/Moscow",
                ),
                InlineKeyboardButton(
                    text="🇦🇪 Дубай",
                    callback_data="timezone:Asia/Dubai",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🇫🇷 Париж",
                    callback_data="timezone:Europe/Paris",
                ),
                InlineKeyboardButton(
                    text="🇫🇮 Хельсинки",
                    callback_data="timezone:Europe/Helsinki",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🇬🇧 Лондон",
                    callback_data="timezone:Europe/London",
                ),
                InlineKeyboardButton(
                    text="🇹🇷 Стамбул",
                    callback_data="timezone:Europe/Istanbul",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🇺🇸 Нью-Йорк",
                    callback_data="timezone:America/New_York",
                ),
                InlineKeyboardButton(
                    text="🌐 Указать вручную",
                    callback_data="timezone:manual",
                ),
            ],
        ]
    )

    await message.answer(
        "Привет! 📅\n\n"
        "Перед началом выбери свой часовой пояс, "
        "чтобы напоминания приходили вовремя.",
        reply_markup=keyboard,
    )


@dp.message(F.text == "🌍 Часовой пояс")
async def timezone_button_handler(message: Message, state: FSMContext):
    await state.clear()

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🇷🇺 Москва",
                    callback_data="timezone:Europe/Moscow",
                ),
                InlineKeyboardButton(
                    text="🇦🇪 Дубай",
                    callback_data="timezone:Asia/Dubai",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🇫🇷 Париж",
                    callback_data="timezone:Europe/Paris",
                ),
                InlineKeyboardButton(
                    text="🇫🇮 Хельсинки",
                    callback_data="timezone:Europe/Helsinki",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🇬🇧 Лондон",
                    callback_data="timezone:Europe/London",
                ),
                InlineKeyboardButton(
                    text="🇹🇷 Стамбул",
                    callback_data="timezone:Europe/Istanbul",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🇺🇸 Нью-Йорк",
                    callback_data="timezone:America/New_York",
                ),
                InlineKeyboardButton(
                    text="🌐 Указать вручную",
                    callback_data="timezone:manual",
                ),
            ],
        ]
    )

    await message.answer(
        "🌍 Выбери свой часовой пояс:",
        reply_markup=keyboard,
    )


@dp.callback_query(F.data.startswith("timezone:"))
async def timezone_callback(callback: CallbackQuery, state: FSMContext):
    timezone = callback.data.split(":", 1)[1]

    if timezone == "manual":
        await callback.message.answer(
            "Введи свой часовой пояс в формате IANA.\n\n"
            "Например: Europe/Paris, Europe/Moscow, Asia/Tokyo"
        )
        await state.set_state(TimezoneState.waiting_for_timezone)
        await callback.answer()
        return

    try:
        ZoneInfo(timezone)
    except (KeyError, ValueError):
        await callback.answer(
            "Не удалось распознать часовой пояс.",
            show_alert=True,
        )
        return

    save_user_timezone(callback.from_user.id, timezone)

    await callback.message.edit_text(
        f"✅ Часовой пояс сохранён: {timezone}"
    )
    await callback.message.answer(
        "Теперь можно пользоваться календарём!",
        reply_markup=main_keyboard,
    )
    await callback.answer()


@dp.message(TimezoneState.waiting_for_timezone)
async def manual_timezone_handler(message: Message, state: FSMContext):
    timezone = message.text.strip() if message.text else ""

    try:
        ZoneInfo(timezone)
    except (KeyError, ValueError):
        await message.answer(
            "Не удалось распознать часовой пояс.\n"
            "Попробуй, например: Europe/Paris или Asia/Tokyo"
        )
        return

    save_user_timezone(message.from_user.id, timezone)
    await state.clear()

    await message.answer(
        f"✅ Часовой пояс сохранён: {timezone}",
        reply_markup=main_keyboard,
    )


@dp.message(Command("add"))
async def add_handler(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(AddEvent.waiting_for_title)
    await message.answer("📝 Введи название события:")


@dp.message(F.text == "➕ Добавить событие")
async def start_add_event(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(AddEvent.waiting_for_title)
    await message.answer("📝 Введи название события:")


@dp.message(AddEvent.waiting_for_title)
async def process_event_title(message: Message, state: FSMContext):
    if not message.text or not message.text.strip():
        await message.answer("Пожалуйста, введи название текстом.")
        return

    await state.update_data(title=message.text.strip())
    await state.set_state(AddEvent.waiting_for_date)

    await message.answer(
        "📅 Введи дату события в формате ГГГГ-ММ-ДД.\n"
        "Например: 2026-10-25"
    )


@dp.message(AddEvent.waiting_for_date)
async def process_event_date(message: Message, state: FSMContext):
    if not message.text:
        await message.answer(
            "Введи дату текстом, например: 2026-10-25"
        )
        return

    try:
        event_date = date.fromisoformat(message.text.strip())
    except ValueError:
        await message.answer(
            "❌ Неверная дата.\n"
            "Используй формат ГГГГ-ММ-ДД, например: 2026-10-25"
        )
        return

    today = date.today()

    if event_date < today:
        await message.answer(
            "⏳ Эта дата уже прошла!\n\n"
            f"Сегодня: {today.isoformat()}\n"
            "Введи сегодняшнюю или будущую дату."
        )
        return

    await state.update_data(event_date=event_date.isoformat())
    await state.set_state(AddEvent.waiting_for_time)

    await message.answer(
        "🕒 Отлично! Теперь введи время в формате ЧЧ:ММ.\n"
        "Например: 14:30"
    )


@dp.message(AddEvent.waiting_for_time)
async def process_event_time(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Введи время, например: 14:30")
        return

    try:
        event_time = time.fromisoformat(message.text.strip())
        if event_time.second or event_time.microsecond:
            raise ValueError
    except ValueError:
        await message.answer(
            "❌ Неверное время. Используй формат ЧЧ:ММ, например 14:30."
        )
        return

    if not message.from_user:
        return

    data = await state.get_data()

    event_id = save_event(
        user_id=message.from_user.id,
        title=data["title"],
        event_date=data["event_date"],
        event_time=event_time.strftime("%H:%M"),
    )

    await state.clear()

    await message.answer(
        "✅ Событие сохранено!\n\n"
        f"📝 {data['title']}\n"
        f"📅 {data['event_date']}\n"
        f"🕒 {event_time.strftime('%H:%M')}\n"
        f"🆔 №{event_id}",
        reply_markup=main_keyboard,
    )


@dp.message(F.text == "📅 Мои события")
async def my_events_handler(message: Message, state: FSMContext):
    await state.clear()

    if not message.from_user:
        return

    await send_event_list(message, message.from_user.id)


@dp.callback_query(F.data.startswith("evt:view:"))
async def show_event_details(callback: CallbackQuery):
    if not callback.from_user or not callback.message:
        await callback.answer()
        return

    if not isinstance(callback.message, Message):
        await callback.answer("Сообщение недоступно.")
        return

    try:
        event_id = int(callback.data.rsplit(":", 1)[1])
    except (ValueError, AttributeError):
        await callback.answer("Некорректный номер события.")
        return

    event = get_user_event(callback.from_user.id, event_id)

    if not event:
        await callback.answer("Событие не найдено.", show_alert=True)
        return

    await callback.answer()

    details = (
        "📌 Подробности события\n\n"
        f"📝 Название: {event['title']}\n"
        f"📅 Дата: {event['event_date']}\n"
        f"🕒 Время: {event['event_time']}\n"
        f"🆔 Номер: {event['id']}"
    )

    if event.get("description"):
        details += f"\n📖 Описание: {event['description']}"

    await callback.message.delete()

    await callback.message.answer(
        details,
        reply_markup=event_detail_keyboard(
            event_id,
            bool(event["daily_reminder"]),
        ),
    )


@dp.callback_query(F.data.startswith("evt:countdown:"))
async def show_event_countdown(callback: CallbackQuery):
    if not callback.from_user:
        await callback.answer()
        return

    try:
        event_id = int(callback.data.rsplit(":", 1)[1])
    except (ValueError, AttributeError):
        await callback.answer("Некорректный номер события.")
        return

    event = get_user_event(callback.from_user.id, event_id)

    if not event:
        await callback.answer("Событие не найдено.", show_alert=True)
        return

    event_date = date.fromisoformat(event["event_date"])
    days_left = (event_date - date.today()).days

    if days_left < 0:
        text = "Это событие уже прошло."
    elif days_left == 0:
        text = "🎉 Это событие сегодня!"
    elif days_left == 1:
        text = "⏳ Уже завтра."
    else:
        text = f"⏳ До события осталось дней: {days_left}."

    await callback.answer(text, show_alert=True)


@dp.callback_query(F.data.startswith("evt:reminder:"))
async def toggle_daily_reminder(callback: CallbackQuery):
    if not callback.from_user or not callback.message:
        await callback.answer()
        return

    if not isinstance(callback.message, Message):
        await callback.answer("Сообщение недоступно.")
        return

    try:
        event_id = int(callback.data.rsplit(":", 1)[1])
    except (ValueError, AttributeError):
        await callback.answer("Некорректный номер события.")
        return

    event = get_user_event(callback.from_user.id, event_id)

    if not event:
        await callback.answer("Событие не найдено.", show_alert=True)
        return

    enabled = not bool(event["daily_reminder"])

    updated = set_daily_reminder(
        user_id=callback.from_user.id,
        event_id=event_id,
        enabled=enabled,
    )

    if not updated:
        await callback.answer(
            "Не удалось изменить настройку.",
            show_alert=True,
        )
        return

    await callback.answer(
        "Ежедневные напоминания включены 🔔"
        if enabled
        else "Ежедневные напоминания выключены 🔕"
    )

    await callback.message.edit_reply_markup(
        reply_markup=event_detail_keyboard(event_id, enabled)
    )


@dp.callback_query(F.data == "evt:list")
async def back_to_event_list(callback: CallbackQuery):
    if not callback.message or not callback.from_user:
        await callback.answer()
        return

    if not isinstance(callback.message, Message):
        await callback.answer("Сообщение недоступно.")
        return

    await callback.answer()
    await callback.message.delete()

    events = get_user_events(callback.from_user.id)

    await callback.message.answer(
        event_list_text(events),
        reply_markup=event_list_keyboard(events) if events else None,
    )


@dp.callback_query(F.data.startswith("evt:delete:"))
async def remove_event(callback: CallbackQuery):
    if not callback.message or not callback.from_user:
        await callback.answer()
        return

    if not isinstance(callback.message, Message):
        await callback.answer("Сообщение недоступно.")
        return

    try:
        event_id = int(callback.data.rsplit(":", 1)[1])
    except (ValueError, AttributeError):
        await callback.answer("Некорректный номер события.")
        return

    deleted = delete_user_event(callback.from_user.id, event_id)

    if not deleted:
        await callback.answer(
            "Событие уже удалено или не найдено.",
            show_alert=True,
        )
        return

    await callback.answer("Событие удалено!")
    await callback.message.delete()

    events = get_user_events(callback.from_user.id)

    await callback.message.answer(
        event_list_text(events, "✅ Событие удалено.\n\n"),
        reply_markup=event_list_keyboard(events) if events else None,
    )


@dp.message(F.text == "❓ Помощь")
async def help_handler(message: Message):
    await message.answer(
        "📖 Как пользоваться ботом:\n\n"
        "➕ Добавить событие — введи название, дату и время.\n"
        "📅 Мои события — открой список и выбери событие.\n"
        "🗑️ Удалить — кнопка внутри карточки события.\n"
        "⬅️ Назад к списку — вернись к списку событий.\n\n"
        "🔔 Ежедневные напоминания сообщают, сколько дней осталось.\n"
        "🕒 В день события я также напомню в указанное время."
    )


async def send_user_daily_reminders(
    bot: Bot,
    user_id: int,
    today: str,
):
    events = get_reminder_events()
    today_date = date.fromisoformat(today)

    for event in events:
        if event["user_id"] != user_id:
            continue

        try:
            event_date = date.fromisoformat(event["event_date"])
            days_left = (event_date - today_date).days

            if days_left < 0:
                continue

            if days_left == 0:
                remaining_text = "🎉 Это событие сегодня!"
            elif days_left == 1:
                remaining_text = "⏳ Остался 1 день."
            else:
                remaining_text = f"⏳ Осталось дней: {days_left}."

            await bot.send_message(
                chat_id=user_id,
                text=(
                    "🔔 Ежедневное напоминание\n\n"
                    f"📝 {event['title']}\n"
                    f"📅 Дата: {event['event_date']}\n"
                    f"🕒 Время: {event['event_time']}\n\n"
                    f"{remaining_text}"
                ),
            )

        except Exception as error:
            print(
                f"Не удалось отправить ежедневное напоминание "
                f"для события №{event['id']}: {error}"
            )


async def send_event_time_reminders(bot: Bot):
    """Отправляет напоминания в день события по локальному времени пользователя."""
    events = get_event_reminder_events()

    for event in events:
        try:
            user_id = event["user_id"]
            timezone_name = get_user_timezone(user_id)
            user_now = datetime.now(ZoneInfo(timezone_name))

            event_date = date.fromisoformat(event["event_date"])
            event_time = time.fromisoformat(event["event_time"])

            # Если дата уже прошла, помечаем событие обработанным,
            # не отправляя запоздалое уведомление.
            if event_date < user_now.date():
                mark_event_reminder_sent(event["id"])
                continue

            # Уведомление отправляется только в дату события.
            if event_date != user_now.date():
                continue

            # Ждём заданного времени.
            if user_now.time().replace(tzinfo=None) < event_time:
                continue

            await bot.send_message(
                chat_id=user_id,
                text=(
                    "🔔 Напоминание о событии!\n\n"
                    f"📝 {event['title']}\n"
                    f"📅 Дата: {event['event_date']}\n"
                    f"🕒 Время: {event['event_time']}\n\n"
                    "🎉 Наступило время события!"
                ),
            )

            # Помечаем только после успешной отправки.
            mark_event_reminder_sent(event["id"])

        except Exception as error:
            print(
                f"Не удалось отправить напоминание "
                f"о событии №{event['id']}: {error}"
            )


async def daily_reminder_scheduler(bot: Bot):
    while True:
        try:
            # Отдельные уведомления в указанное время события.
            # Они работают независимо от daily_reminder.
            await send_event_time_reminders(bot)

            # Сохраняем существующую логику ежедневных напоминаний.
            events = get_reminder_events()
            users = {
                event["user_id"]
                for event in events
            }

            for user_id in users:
                try:
                    timezone_name = get_user_timezone(user_id)
                    user_now = datetime.now(ZoneInfo(timezone_name))
                    today = user_now.date().isoformat()

                    last_sent = get_last_reminder_date(user_id)

                    # При первом запуске не отправляем ежедневную
                    # рассылку сразу: сначала фиксируем текущую дату.
                    if last_sent is None:
                        set_last_reminder_date(user_id, today)
                        continue

                    if last_sent != today:
                        await send_user_daily_reminders(
                            bot,
                            user_id,
                            today,
                        )
                        set_last_reminder_date(user_id, today)

                except Exception as error:
                    print(
                        f"Ошибка ежедневных напоминаний "
                        f"пользователя {user_id}: {error}"
                    )

        except Exception as error:
            print(f"Ошибка планировщика напоминаний: {error}")

        await asyncio.sleep(30)


async def main():
    init_db()

    session = AiohttpSession(proxy=PROXY_URL)
    bot = Bot(token=TOKEN, session=session)

    scheduler_task = None

    try:
        me = await bot.get_me()
        print(f"Успешное подключение @{me.username}")

        scheduler_task = asyncio.create_task(
            daily_reminder_scheduler(bot)
        )

        print(
            "Планировщик запущен: ежедневные напоминания "
            "и уведомления в день события."
        )

        await dp.start_polling(bot)

    finally:
        if scheduler_task:
            scheduler_task.cancel()
            await asyncio.gather(
                scheduler_task,
                return_exceptions=True,
            )

        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
