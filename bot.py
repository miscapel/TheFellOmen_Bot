import os
import asyncio
from datetime import datetime

from aiogram import Bot, Dispatcher, F, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

BOT_TOKEN = os.getenv("BOT_TOKEN")
STAFF_GROUP_ID = -100XXXXXXXXX

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# ---------------- STATES ----------------

class Appeal(StatesGroup):
    waiting = State()

class Whitelist(StatesGroup):
    waiting = State()

class Contact(StatesGroup):
    waiting = State()

class ShopRank(StatesGroup):
    waiting = State()

class ShopCoin(StatesGroup):
    waiting = State()

# ---------------- MENU ----------------

def main_menu():
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="⚖️ درخواست رفع مجازات")],
            [types.KeyboardButton(text="📜 درخواست وایت لیست")],
            [types.KeyboardButton(text="🆘 تماس با استاف")],
            [types.KeyboardButton(text="💎 فروشگاه سرور")]
        ],
        resize_keyboard=True
    )

# ---------------- START ----------------

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "به ربات رسمی سرور خوش آمدید.\n\n"
        "یکی از گزینه‌های زیر را انتخاب کنید.",
        reply_markup=main_menu()
    )

# ---------------- PUNISHMENT ----------------

@dp.message(F.text == "⚖️ درخواست رفع مجازات")
async def appeal_start(message: types.Message, state: FSMContext):
    await state.set_state(Appeal.waiting)

    await message.answer(
        "لطفا اطلاعات زیر را در یک پیام ارسال کنید:\n\n"
        "یوزرنیم ماینکرفت\n"
        "Punishment ID\n"
        "دلیل درخواست\n"
        "پیام شما"
    )

@dp.message(Appeal.waiting)
async def appeal_send(message: types.Message, state: FSMContext):

    time = datetime.now().strftime("%Y-%m-%d %H:%M")

    text = f"""
⚖️ <b>Punishment Appeal</b>

Username: {message.from_user.username}
Reason: درخواست رفع مجازات

Message:
{message.text}

Time: {time}
"""

    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="✅ Accept", callback_data=f"accept_{message.from_user.id}"),
                types.InlineKeyboardButton(text="❌ Deny", callback_data=f"deny_{message.from_user.id}")
            ],
            [
                types.InlineKeyboardButton(text="💬 Reply", callback_data=f"reply_{message.from_user.id}")
            ]
        ]
    )

    await bot.send_message(STAFF_GROUP_ID, text, reply_markup=keyboard)

    await message.answer("✅ درخواست شما برای استاف ارسال شد.")

    await state.clear()

# ---------------- WHITELIST ----------------

@dp.message(F.text == "📜 درخواست وایت لیست")
async def whitelist_start(message: types.Message, state: FSMContext):

    await state.set_state(Whitelist.waiting)

    await message.answer(
        "لطفا یوزری که میخواهید وایت لیست شود را در چت بنویسید."
    )

@dp.message(Whitelist.waiting)
async def whitelist_send(message: types.Message, state: FSMContext):

    time = datetime.now().strftime("%Y-%m-%d %H:%M")

    text = f"""
📜 <b>Whitelist</b>

Username: {message.text}

Time: {time}

Messages:
درخواست وایت لیست
"""

    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="✅ Accept", callback_data=f"accept_{message.from_user.id}"),
                types.InlineKeyboardButton(text="❌ Deny", callback_data=f"deny_{message.from_user.id}")
            ]
        ]
    )

    await bot.send_message(STAFF_GROUP_ID, text, reply_markup=keyboard)

    await message.answer("✅ درخواست وایت لیست ارسال شد.")

    await state.clear()

# ---------------- CONTACT ----------------

@dp.message(F.text == "🆘 تماس با استاف")
async def contact_start(message: types.Message, state: FSMContext):

    await state.set_state(Contact.waiting)

    await message.answer(
        "لطفا دلیل و پیام خود را برای استاف بنویسید."
    )

@dp.message(Contact.waiting)
async def contact_send(message: types.Message, state: FSMContext):

    time = datetime.now().strftime("%Y-%m-%d %H:%M")

    text = f"""
🆘 <b>Contact Staff</b>

Username: {message.from_user.username}

Reason: Support

Time: {time}

Messages:
{message.text}
"""

    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="✅ Accept", callback_data=f"accept_{message.from_user.id}"),
                types.InlineKeyboardButton(text="❌ Deny", callback_data=f"deny_{message.from_user.id}")
            ],
            [
                types.InlineKeyboardButton(text="💬 Reply", callback_data=f"reply_{message.from_user.id}")
            ]
        ]
    )

    await bot.send_message(STAFF_GROUP_ID, text, reply_markup=keyboard)

    await message.answer("✅ تیکت شما برای استاف ارسال شد.")

    await state.clear()

# ---------------- SHOP ----------------

def shop_menu():
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="🏆 Rank Shop", callback_data="rank")],
            [types.InlineKeyboardButton(text="🪙 Coin Shop", callback_data="coin")]
        ]
    )

@dp.message(F.text == "💎 فروشگاه سرور")
async def shop(message: types.Message):

    await message.answer(
        "رنک ها و کوین ها در سرور",
        reply_markup=shop_menu()
    )

@dp.callback_query(F.data == "rank")
async def rank_shop(callback: types.CallbackQuery):

    text = """
🏆 Rank Shop

Vip » 49,000 Toman
Elite » 100,000 Toman
TheFellOmen » 190,000 Toman
Sponsor » 250,000 Toman
Lover » 400,000 Toman

اگر فقط نیاز به کیت رنک دارید
رنک مورد نظر و کیت را بنویسید

مثال:
کیت رنک الایت
"""

    await callback.message.answer(text)

@dp.callback_query(F.data == "coin")
async def coin_shop(callback: types.CallbackQuery):

    text = """
🪙 Coin Shop

50 Coin » 15,000 Toman
100 Coins » 30,000 Toman
150 Coins » 55,000 Toman
200 Coins » 80,000 Toman
250 Coins » 150,000 Toman

اگر مقدار کوین بیشتری نیاز دارید
مقدار مورد نظر را در چت بنویسید.
"""

    await callback.message.answer(text)

# ---------------- RUN ----------------

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
