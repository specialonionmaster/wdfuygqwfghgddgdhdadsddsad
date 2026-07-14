import asyncio
import os
import json
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

# Загружаем переменные из .env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
RENDER_URL = os.getenv("RENDER_URL", "")  # URL твоего сервиса на Render

if not BOT_TOKEN or not ADMIN_ID:
    raise ValueError("Проверь .env файл! Нужны BOT_TOKEN и ADMIN_ID")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Файл для хранения тем
TOPICS_FILE = "topics.json"


# Загрузка тем из JSON файла
def load_topics():
    try:
        with open(TOPICS_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        default_topics = {
            "topic_1": {
                "title": "Темка 1",
                "text": "уаывраырва\nувраврыа"
            }
        }
        save_topics(default_topics)
        return default_topics


# Сохранение тем в JSON файл
def save_topics(topics_data):
    with open(TOPICS_FILE, "w", encoding="utf-8") as file:
        json.dump(topics_data, file, ensure_ascii=False, indent=2)


# Загружаем темы при старте
topics = load_topics()


# Состояния для FSM
class AddTopic(StatesGroup):
    waiting_for_title = State()
    waiting_for_text = State()
    waiting_for_callback = State()


# Проверка на админа
def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


# Главное меню
def get_main_keyboard(user_id: int):
    buttons = []

    buttons.append([InlineKeyboardButton(
        text="🔥 Получить темку бесплатно",
        callback_data="start_main",
        style="success"
    )])

    buttons.append([InlineKeyboardButton(
        text="📢 Канал воркеров",
        url="https://t.me/ly_team",
        style="danger"
    )])

    if is_admin(user_id):
        buttons.append([InlineKeyboardButton(
            text="⚙️ Админ панель",
            callback_data="admin_panel",
            style="primary"
        )])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


# Меню с темами
def get_topics_keyboard():
    buttons = []

    for topic_id, topic_data in topics.items():
        buttons.append([InlineKeyboardButton(
            text=topic_data["title"],
            callback_data=topic_id,
            style="primary"
        )])

    buttons.append([InlineKeyboardButton(
        text="🔙 Назад в меню",
        callback_data="back_to_main",
        style="danger"
    )])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


# Админ панель
def get_admin_keyboard():
    buttons = [
        [InlineKeyboardButton(
            text="➕ Добавить тему",
            callback_data="add_topic",
            style="success"
        )],
        [InlineKeyboardButton(
            text="📋 Список тем",
            callback_data="list_topics",
            style="primary"
        )],
        [InlineKeyboardButton(
            text="❌ Удалить тему",
            callback_data="delete_topic",
            style="danger"
        )],
        [InlineKeyboardButton(
            text="🔙 Назад в меню",
            callback_data="back_to_main"
        )]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# Клавиатура для удаления тем
def get_delete_topics_keyboard():
    buttons = []

    for topic_id, topic_data in topics.items():
        buttons.append([InlineKeyboardButton(
            text=f"❌ {topic_data['title']}",
            callback_data=f"del_{topic_id}",
            style="danger"
        )])

    buttons.append([InlineKeyboardButton(
        text="🔙 Назад",
        callback_data="admin_panel"
    )])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


# Команда /start
@dp.message(Command("start"))
async def start_command(message: types.Message):
    caption_text = (
        "👋 <b>Привет, работяга!</b>\n\n"
        "Тут ты можешь получить темку <b>абсолютно бесплатно!</b>\n\n"
        "🎯 Жми на кнопку ниже чтобы забрать темку\n"
        "📢 А в нашем канале еще больше полезного!"
    )

    try:
        photo = FSInputFile("photo.png")
        await message.answer_photo(
            photo=photo,
            caption=caption_text,
            parse_mode="HTML",
            reply_markup=get_main_keyboard(message.from_user.id)
        )
    except FileNotFoundError:
        await message.answer(
            caption_text,
            parse_mode="HTML",
            reply_markup=get_main_keyboard(message.from_user.id)
        )


# Главное меню (для callback)
@dp.callback_query(lambda c: c.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery):
    caption_text = (
        "👋 <b>Привет, работяга!</b>\n\n"
        "Тут ты можешь получить темку <b>абсолютно бесплатно!</b>\n\n"
        "🎯 Жми на кнопку ниже чтобы забрать темку\n"
        "📢 А в нашем канале еще больше полезного!"
    )

    try:
        await callback.message.delete()
    except:
        pass

    try:
        photo = FSInputFile("photo.png")
        await callback.message.answer_photo(
            photo=photo,
            caption=caption_text,
            parse_mode="HTML",
            reply_markup=get_main_keyboard(callback.from_user.id)
        )
    except FileNotFoundError:
        await callback.message.answer(
            caption_text,
            parse_mode="HTML",
            reply_markup=get_main_keyboard(callback.from_user.id)
        )
    await callback.answer()


# Показать темы
@dp.callback_query(lambda c: c.data == "start_main")
async def show_topics(callback: types.CallbackQuery):
    try:
        await callback.message.delete()
    except:
        pass

    if not topics:
        await callback.message.answer(
            "😔 Пока нет доступных тем, загляни позже!",
            reply_markup=get_main_keyboard(callback.from_user.id)
        )
        await callback.answer("Темы не найдены")
        return

    await callback.message.answer(
        "🎯 <b>Доступные темки:</b>\n\nВыбирай любую!",
        parse_mode="HTML",
        reply_markup=get_topics_keyboard()
    )
    await callback.answer()


# Показать конкретную тему
@dp.callback_query(lambda c: c.data in topics)
async def show_topic(callback: types.CallbackQuery):
    topic = topics[callback.data]

    topic_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🔙 Назад к темкам",
            callback_data="start_main",
            style="danger"
        )]
    ])

    await callback.message.answer(
        f"<b>{topic['title']}</b>\n\n{topic['text']}",
        parse_mode="HTML",
        reply_markup=topic_kb
    )
    await callback.answer()


# АДМИН ПАНЕЛЬ
@dp.callback_query(lambda c: c.data == "admin_panel")
async def admin_panel(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа!", show_alert=True)
        return

    try:
        await callback.message.delete()
    except:
        pass

    await callback.message.answer(
        "⚙️ <b>Админ панель:</b>",
        parse_mode="HTML",
        reply_markup=get_admin_keyboard()
    )
    await callback.answer()


# Добавление темы (шаг 1)
@dp.callback_query(lambda c: c.data == "add_topic")
async def add_topic_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа!", show_alert=True)
        return

    try:
        await callback.message.delete()
    except:
        pass

    await callback.message.answer("📝 Введите название темы:")
    await state.set_state(AddTopic.waiting_for_title)
    await callback.answer()


# Добавление темы (шаг 2)
@dp.message(AddTopic.waiting_for_title)
async def add_topic_title(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа!")
        return

    await state.update_data(title=message.text)
    await message.answer("📄 Теперь введите текст темы:")
    await state.set_state(AddTopic.waiting_for_text)


# Добавление темы (шаг 3)
@dp.message(AddTopic.waiting_for_text)
async def add_topic_text(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа!")
        return

    await state.update_data(text=message.text)
    await message.answer("🔑 Введите callback_data для темы (латиница, без пробелов, например: topic_3):")
    await state.set_state(AddTopic.waiting_for_callback)


# Добавление темы (шаг 4 - сохраняем)
@dp.message(AddTopic.waiting_for_callback)
async def add_topic_callback(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа!")
        return

    callback_data = message.text.strip()

    if callback_data in topics:
        await message.answer("⚠️ Такая тема уже существует! Введите другой callback_data:")
        return

    data = await state.get_data()
    topics[callback_data] = {
        "title": data["title"],
        "text": data["text"]
    }

    save_topics(topics)

    await state.clear()
    await message.answer("✅ Тема успешно добавлена и сохранена!", reply_markup=get_admin_keyboard())


# Показать список тем (админка)
@dp.callback_query(lambda c: c.data == "list_topics")
async def list_topics(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа!", show_alert=True)
        return

    try:
        await callback.message.delete()
    except:
        pass

    if not topics:
        await callback.message.answer("📋 Список тем пуст.", reply_markup=get_admin_keyboard())
        await callback.answer()
        return

    text = "📋 <b>Список тем:</b>\n\n"
    for i, (topic_id, topic_data) in enumerate(topics.items(), 1):
        text += f"{i}. {topic_data['title']}\n"
        text += f"   ID: <code>{topic_id}</code>\n\n"

    await callback.message.answer(text, parse_mode="HTML", reply_markup=get_admin_keyboard())
    await callback.answer()


# Удаление темы
@dp.callback_query(lambda c: c.data == "delete_topic")
async def delete_topic_list(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа!", show_alert=True)
        return

    try:
        await callback.message.delete()
    except:
        pass

    if not topics:
        await callback.message.answer("🗑 Нечего удалять.", reply_markup=get_admin_keyboard())
        await callback.answer()
        return

    await callback.message.answer("🗑 Выберите тему для удаления:", reply_markup=get_delete_topics_keyboard())
    await callback.answer()


# Подтверждение удаления
@dp.callback_query(lambda c: c.data.startswith("del_"))
async def confirm_delete_topic(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа!", show_alert=True)
        return

    topic_id = callback.data.replace("del_", "")

    if topic_id in topics:
        topic_title = topics[topic_id]["title"]
        del topics[topic_id]

        save_topics(topics)

        try:
            await callback.message.delete()
        except:
            pass

        await callback.message.answer("✅ Тема успешно удалена!", reply_markup=get_admin_keyboard())
        await callback.answer(f"Тема '{topic_title}' удалена")
    else:
        await callback.answer("❌ Тема не найдена!", show_alert=True)


# Запуск бота
async def main():
    print("🤖 Бот запущен!")
    print(f"👑 Админ ID: {ADMIN_ID}")
    print(f"📚 Загружено тем: {len(topics)}")

    # Используем Webhook для Render
    if RENDER_URL:
        await bot.set_webhook(f"{RENDER_URL}/webhook")
        app = web.Application()
        webhook_requests_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
        webhook_requests_handler.register(app, path="/webhook")
        setup_application(app, dp, bot=bot)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
        await site.start()
        print("Webhook установлен!")
    else:
        # Long polling для локальной разработки
        await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())