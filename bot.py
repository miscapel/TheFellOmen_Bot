import asyncio
import os
import logging
import random
import string
from datetime import datetime
import threading
from flask import Flask

from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

# ================= CONFIG =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
STAFF_GROUP_ID = -1004332150226

logging.basicConfig(level=logging.INFO)

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher(storage=MemoryStorage())

# ================= RENDER KEEP ALIVE =================

app = Flask("")

@app.route("/")
def home():
    return "TheFellOmen Bot Running"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    thread = threading.Thread(target=run)
    thread.start()

# ================= DATA =================

TICKETS = {}
REPLY_MODE = {}

def make_ticket_id():
    return "TK-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))

# ================= MENUS =================

def main_menu():
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="⚖️ Punishment Appeal")],
            [types.KeyboardButton(text="📜 Whitelist")],
            [types.KeyboardButton(text="🆘 Contact Staff")],
            [types.KeyboardButton(text="💎 Shop")]
        ],
        resize_keyboard=True
    )

def inline_main():
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="⚖️ Punishment Appeal", callback_data="punish")],
            [types.InlineKeyboardButton(text="📜 Whitelist", callback_data="whitelist")],
            [types.InlineKeyboardButton(text="🆘 Contact Staff", callback_data="contact")],
            [types.InlineKeyboardButton(text="💎 Shop", callback_data="shop")]
        ]
    )

def shop_keyboard():
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="👑 Rank", callback_data="rank")],
            [types.InlineKeyboardButton(text="🪙 Coin", callback_data="coin")],
            [types.InlineKeyboardButton(text="🔙 Back", callback_data="back")]
        ]
    )

def whitelist_keyboard():
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="📜 Register Whitelist", callback_data="wl_start")],
            [types.InlineKeyboardButton(text="🔙 Back", callback_data="back")]
        ]
    )

def staff_buttons(ticket):
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="✅ Accept", callback_data=f"accept:{ticket}"),
                types.InlineKeyboardButton(text="❌ Deny", callback_data=f"deny:{ticket}")
            ],
            [
                types.InlineKeyboardButton(text="💬 Reply", callback_data=f"reply:{ticket}")
            ]
        ]
    )

# ================= STATES =================

class Punishment(StatesGroup):
    username = State()
    pid = State()
    reason = State()
    message = State()

class Whitelist(StatesGroup):
    username = State()
    message = State()

class Contact(StatesGroup):
    reason = State()
    message = State()

# ================= START =================

@dp.message(Command("start"))
async def start(message: types.Message):

    text = """
🔥 <b>TheFellOmen Support Center</b>

به سیستم رسمی پشتیبانی سرور خوش آمدید.

از منوی زیر یا دکمه‌های شیشه‌ای استفاده کنید.
"""

    await message.answer(text, reply_markup=main_menu())
    await message.answer("Quick Menu:", reply_markup=inline_main())

# ================= SHOP =================

@dp.message(F.text == "💎 Shop")
async def shop(message: types.Message):

    text = """
💎 <b>TheFellOmen Server Shop</b>

از دکمه‌های زیر انتخاب کنید.
"""

    await message.answer(text, reply_markup=shop_keyboard())

@dp.callback_query(F.data == "shop")
async def shop_inline(callback: types.CallbackQuery):

    await callback.message.edit_text(
        "💎 <b>Server Shop</b>",
        reply_markup=shop_keyboard()
    )

@dp.callback_query(F.data == "rank")
async def rank(callback: types.CallbackQuery):

    text = """
👑 <b>Rank Shop</b>

Vip » 49,000 Toman
Elite » 100,000 Toman
TheFellOmen » 190,000 Toman
Sponsor » 250,000 Toman
Lover » 400,000 Toman

برای خرید کیت رنک،
نام کیت را در چت بنویسید.
"""

    await callback.message.edit_text(text, reply_markup=shop_keyboard())

@dp.callback_query(F.data == "coin")
async def coin(callback: types.CallbackQuery):

    text = """
🪙 <b>Coin Shop</b>

50 Coin » 15,000 Toman
100 Coins » 30,000 Toman
150 Coins » 55,000 Toman
200 Coins » 80,000 Toman
250 Coins » 150,000 Toman

اگر مقدار بیشتری می‌خواهید،
در چت بنویسید.
"""

    await callback.message.edit_text(text, reply_markup=shop_keyboard())

# ================= WHITELIST =================

@dp.message(F.text == "📜 Whitelist")
async def whitelist_menu(message: types.Message):

    text = """
📜 <b>Whitelist Request</b>

برای ثبت درخواست وایت‌لیست
روی دکمه زیر بزنید.
"""

    await message.answer(text, reply_markup=whitelist_keyboard())

@dp.callback_query(F.data == "wl_start")
async def wl_start(callback: types.CallbackQuery, state: FSMContext):

    await state.set_state(Whitelist.username)

    await callback.message.answer(
        "یوزرنیم ماینکرفت خود را ارسال کنید."
    )

@dp.message(Whitelist.username)
async def wl_user(message: types.Message, state: FSMContext):

    await state.update_data(username=message.text)
    await state.set_state(Whitelist.message)

    await message.answer("اگر توضیحی دارید بنویسید.")

@dp.message(Whitelist.message)
async def wl_finish(message: types.Message, state: FSMContext):

    data = await state.get_data()

    ticket = make_ticket_id()

    TICKETS[ticket] = {
        "user_id": message.from_user.id
    }

    text = f"""
📜 <b>Whitelist</b>

Username: {data['username']}

Messages:
{message.text}

Time: {datetime.now().strftime("%Y-%m-%d %H:%M")}

User ID: {message.from_user.id}
Ticket: {ticket}
"""

    await bot.send_message(
        STAFF_GROUP_ID,
        text,
        reply_markup=staff_buttons(ticket)
    )

    await message.answer(
        "✅ درخواست شما ارسال شد.",
        reply_markup=main_menu()
    )

    await state.clear()

# ================= CONTACT =================

@dp.message(F.text == "🆘 Contact Staff")
async def contact_start(message: types.Message, state: FSMContext):

    await state.set_state(Contact.reason)

    await message.answer("دلیل تیکت را بنویسید.")

@dp.message(Contact.reason)
async def contact_reason(message: types.Message, state: FSMContext):

    await state.update_data(reason=message.text)
    await state.set_state(Contact.message)

    await message.answer("پیام خود را ارسال کنید.")

@dp.message(Contact.message)
async def contact_finish(message: types.Message, state: FSMContext):

    data = await state.get_data()

    ticket = make_ticket_id()

    TICKETS[ticket] = {
        "user_id": message.from_user.id
    }

    text = f"""
📩 <b>Contact Staff</b>

Reason: {data['reason']}

Message:
{message.text}

Time: {datetime.now().strftime("%Y-%m-%d %H:%M")}
Ticket: {ticket}
"""

    await bot.send_message(
        STAFF_GROUP_ID,
        text,
        reply_markup=staff_buttons(ticket)
    )

    await message.answer(
        "✅ تیکت شما ارسال شد.",
        reply_markup=main_menu()
    )

    await state.clear()

# ================= STAFF ACTIONS =================

@dp.callback_query(F.data.startswith("accept:"))
async def accept(callback: types.CallbackQuery):

    ticket = callback.data.split(":")[1]

    user = TICKETS[ticket]["user_id"]

    await bot.send_message(
        user,
        "✅ درخواست شما تایید شد."
    )

    await callback.answer("Accepted")

@dp.callback_query(F.data.startswith("deny:"))
async def deny(callback: types.CallbackQuery):

    ticket = callback.data.split(":")[1]

    user = TICKETS[ticket]["user_id"]

    await bot.send_message(
        user,
        "❌ درخواست شما رد شد."
    )

    await callback.answer("Denied")

@dp.callback_query(F.data.startswith("reply:"))
async def reply(callback: types.CallbackQuery):

    ticket = callback.data.split(":")[1]

    REPLY_MODE[callback.from_user.id] = ticket

    await callback.message.reply(
        "پیام خود را ارسال کنید."
    )

# ================= STAFF MESSAGE =================

@dp.message()
async def staff_reply(message: types.Message):

    if message.from_user.id not in REPLY_MODE:
        return

    ticket = REPLY_MODE[message.from_user.id]

    user = TICKETS[ticket]["user_id"]

    if message.photo:

        await bot.send_photo(
            user,
            message.photo[-1].file_id,
            caption="💬 پاسخ استاف"
        )

    elif message.video:

        await bot.send_video(
            user,
            message.video.file_id,
            caption="💬 پاسخ استاف"
        )

    else:

        await bot.send_message(
            user,
            f"💬 پاسخ استاف:\n\n{message.text}"
        )

    del REPLY_MODE[message.from_user.id]

# ================= MAIN =================

async def main():

    keep_alive()

    await bot.delete_webhook(drop_pending_updates=True)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
