import asyncio
import os
import logging
from datetime import datetime
import threading
from flask import Flask

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

BOT_TOKEN = os.getenv("BOT_TOKEN")
STAFF_GROUP_ID = -1004332150226

logging.basicConfig(level=logging.INFO)

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher(storage=MemoryStorage())

# ---------------- KEEP ALIVE ----------------

app = Flask("")

@app.route("/")
def home():
    return "Bot Running"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    t = threading.Thread(target=run)
    t.start()

# ---------------- STATES ----------------

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

# ---------------- MENU ----------------

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

# ---------------- START ----------------

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "به سیستم پشتیبانی سرور TheFellOmen خوش آمدید.",
        reply_markup=main_menu()
    )

# ---------------- PUNISHMENT ----------------

@dp.message(F.text == "⚖️ Punishment Appeal")
async def punishment_start(message: types.Message, state: FSMContext):

    await state.set_state(Punishment.username)

    await message.answer(
        "لطفا یوزرنیم ماینکرفت خود را بنویسید."
    )

@dp.message(Punishment.username)
async def punishment_username(message: types.Message, state: FSMContext):

    await state.update_data(username=message.text)
    await state.set_state(Punishment.pid)

    await message.answer("لطفا Punishment ID را بنویسید.")

@dp.message(Punishment.pid)
async def punishment_pid(message: types.Message, state: FSMContext):

    await state.update_data(pid=message.text)
    await state.set_state(Punishment.reason)

    await message.answer("لطفا دلیل درخواست آنبن یا آنمیوت را بنویسید.")

@dp.message(Punishment.reason)
async def punishment_reason(message: types.Message, state: FSMContext):

    await state.update_data(reason=message.text)
    await state.set_state(Punishment.message)

    await message.answer("توضیحات کامل خود را بنویسید.")

@dp.message(Punishment.message)
async def punishment_finish(message: types.Message, state: FSMContext):

    data = await state.get_data()

    text = f"""
<b>Punishment Appeal</b>

Username: {data['username']}
Reason: {data['reason']}
Message: {message.text}
Time: {datetime.now().strftime("%Y-%m-%d %H:%M")}
Punishment id: {data['pid']}
"""

    await bot.send_message(STAFF_GROUP_ID, text)

    await message.answer("✅ درخواست شما ارسال شد.", reply_markup=main_menu())

    await state.clear()

# ---------------- WHITELIST ----------------

@dp.message(F.text == "📜 Whitelist")
async def whitelist_start(message: types.Message, state: FSMContext):

    await state.set_state(Whitelist.username)

    await message.answer(
        "لطفا یوزر ای که میخواهید وایت لیست شود را در چت بنویسید."
    )

@dp.message(Whitelist.username)
async def whitelist_finish(message: types.Message, state: FSMContext):

    text = f"""
<b>Whitelist</b>

Username: {message.text}
Time: {datetime.now().strftime("%Y-%m-%d %H:%M")}
Messages: درخواست وایت لیست
"""

    buttons = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="✅ Accept", callback_data="w_accept"),
                types.InlineKeyboardButton(text="❌ Deny", callback_data="w_deny")
            ]
        ]
    )

    await bot.send_message(STAFF_GROUP_ID, text, reply_markup=buttons)

    await message.answer("✅ درخواست شما ارسال شد.", reply_markup=main_menu())

    await state.clear()

# ---------------- CONTACT STAFF ----------------

@dp.message(F.text == "🆘 Contact Staff")
async def contact_start(message: types.Message, state: FSMContext):

    await state.set_state(Contact.reason)

    await message.answer("لطفا دلیل تیکت خود را بنویسید.")

@dp.message(Contact.reason)
async def contact_reason(message: types.Message, state: FSMContext):

    await state.update_data(reason=message.text)

    await state.set_state(Contact.message)

    await message.answer("پیام خود را بنویسید.")

@dp.message(Contact.message)
async def contact_finish(message: types.Message, state: FSMContext):

    data = await state.get_data()

    text = f"""
<b>Contact Staff</b>

Usename: {message.from_user.full_name}
Reason: {data['reason']}
Time: {datetime.now().strftime("%Y-%m-%d %H:%M")}
Messages: {message.text}
"""

    buttons = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="✅ Accept", callback_data="c_accept"),
                types.InlineKeyboardButton(text="❌ Deny", callback_data="c_deny")
            ],
            [
                types.InlineKeyboardButton(text="💬 Reply", callback_data="c_reply")
            ]
        ]
    )

    await bot.send_message(STAFF_GROUP_ID, text, reply_markup=buttons)

    await message.answer("✅ تیکت شما ارسال شد.", reply_markup=main_menu())

    await state.clear()

# ---------------- SHOP ----------------

@dp.message(F.text == "💎 Shop")
async def shop(message: types.Message):

    buttons = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="Rank", callback_data="rank")],
            [types.InlineKeyboardButton(text="Coin", callback_data="coin")]
        ]
    )

    await message.answer(
        "رنک ها و کوین ها در سرور",
        reply_markup=buttons
    )

@dp.callback_query(F.data == "rank")
async def rank_shop(callback: types.CallbackQuery):

    text = """
<b>Rank Shop</b>

Vip » 49,000 Toman
Elite » 100,000 Toman
TheFellOmen » 190,000 Toman
Sponsor » 250,000 Toman
Lover » 400,000 Toman

اگر فقط نیاز به کیت رنک دارید رنک مورد نظر و کیت مورد نظر را بنویسید.
مثال:
کیت رنک الایت
"""

    await callback.message.answer(text)

@dp.callback_query(F.data == "coin")
async def coin_shop(callback: types.CallbackQuery):

    text = """
<b>Coin Shop</b>

50 Coin » 15,000 Toman
100 Coins » 30,000 Toman
150 Coins » 55,000 Toman
200 Coins » 80,000 Toman
250 Coins » 150,000 Toman

اگر مقدار کوین مورد نظر بیشتر از این هاست مقدار مورد نظر خود را در چت بنویسید.
"""

    await callback.message.answer(text)

# ---------------- MAIN ----------------

async def main():

    keep_alive()

    await bot.delete_webhook(drop_pending_updates=True)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
