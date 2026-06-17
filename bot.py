import asyncio
import os
import logging
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

BOT_TOKEN = os.getenv("BOT_TOKEN")
STAFF_GROUP_ID = -1004332150226

logging.basicConfig(level=logging.INFO)

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher(storage=MemoryStorage())

# ---------------- RENDER KEEP ALIVE ----------------

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

# ---------------- DATA ----------------

TICKETS = {}
REPLY_MODE = {}

# ---------------- MENU ----------------

def menu():
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="⚖️ Punishment Appeal")],
            [types.KeyboardButton(text="📜 Whitelist")],
            [types.KeyboardButton(text="🆘 Contact Staff")],
            [types.KeyboardButton(text="💎 Shop")]
        ],
        resize_keyboard=True
    )

# ---------------- BUTTONS ----------------

def staff_buttons(ticket):

    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="✅ Accept",
                    callback_data=f"accept:{ticket}"
                ),
                types.InlineKeyboardButton(
                    text="❌ Deny",
                    callback_data=f"deny:{ticket}"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="💬 Reply",
                    callback_data=f"reply:{ticket}"
                )
            ]
        ]
    )

# ---------------- STATES ----------------

class Punishment(StatesGroup):
    username = State()
    pid = State()
    reason = State()
    message = State()

class Whitelist(StatesGroup):
    username = State()

class Contact(StatesGroup):
    reason = State()
    message = State()

# ---------------- START ----------------

@dp.message(Command("start"))
async def start(message: types.Message):

    text = """
🔥 <b>TheFellOmen Support System</b>

به سیستم پشتیبانی سرور خوش آمدید.

از منوی زیر بخش مورد نظر خود را انتخاب کنید.
"""

    await message.answer(text, reply_markup=menu())

# ---------------- PUNISHMENT ----------------

@dp.message(F.text == "⚖️ Punishment Appeal")
async def punish_start(message: types.Message, state: FSMContext):

    await state.set_state(Punishment.username)

    await message.answer(
        "⚖️ <b>Punishment Appeal</b>\n\n"
        "لطفا یوزرنیم ماینکرفت خود را ارسال کنید."
    )

@dp.message(Punishment.username)
async def punish_user(message: types.Message, state: FSMContext):

    await state.update_data(username=message.text)

    await state.set_state(Punishment.pid)

    await message.answer("🆔 Punishment ID خود را ارسال کنید.")

@dp.message(Punishment.pid)
async def punish_pid(message: types.Message, state: FSMContext):

    await state.update_data(pid=message.text)

    await state.set_state(Punishment.reason)

    await message.answer("📄 دلیل درخواست Unban / Unmute را بنویسید.")

@dp.message(Punishment.reason)
async def punish_reason(message: types.Message, state: FSMContext):

    await state.update_data(reason=message.text)

    await state.set_state(Punishment.message)

    await message.answer(
        "💬 توضیحات کامل خود را ارسال کنید.\n"
        "می‌توانید متن، عکس یا ویدیو ارسال کنید."
    )

@dp.message(Punishment.message)
async def punish_finish(message: types.Message, state: FSMContext):

    data = await state.get_data()

    ticket = message.from_user.id

    TICKETS[ticket] = message.from_user.id

    text = f"""
🚨 <b>Punishment Appeal</b>

👤 Username: {data['username']}
🆔 Punishment ID: {data['pid']}

📄 Reason:
{data['reason']}

💬 Message:
{message.caption or message.text}

🕒 Time: {datetime.now().strftime("%Y-%m-%d %H:%M")}
"""

    if message.photo:
        msg = await bot.send_photo(
            STAFF_GROUP_ID,
            message.photo[-1].file_id,
            caption=text,
            reply_markup=staff_buttons(ticket)
        )

    elif message.video:
        msg = await bot.send_video(
            STAFF_GROUP_ID,
            message.video.file_id,
            caption=text,
            reply_markup=staff_buttons(ticket)
        )

    else:
        msg = await bot.send_message(
            STAFF_GROUP_ID,
            text,
            reply_markup=staff_buttons(ticket)
        )

    await message.answer(
        "✅ درخواست شما برای تیم استاف ارسال شد.",
        reply_markup=menu()
    )

    await state.clear()

# ---------------- CONTACT STAFF ----------------

@dp.message(F.text == "🆘 Contact Staff")
async def contact_start(message: types.Message, state: FSMContext):

    await state.set_state(Contact.reason)

    await message.answer(
        "🆘 <b>Support Ticket</b>\n\n"
        "لطفا دلیل تیکت خود را بنویسید."
    )

@dp.message(Contact.reason)
async def contact_reason(message: types.Message, state: FSMContext):

    await state.update_data(reason=message.text)

    await state.set_state(Contact.message)

    await message.answer(
        "💬 پیام خود را ارسال کنید.\n"
        "می‌توانید عکس یا ویدیو هم ارسال کنید."
    )

@dp.message(Contact.message)
async def contact_finish(message: types.Message, state: FSMContext):

    data = await state.get_data()

    ticket = message.from_user.id

    TICKETS[ticket] = message.from_user.id

    text = f"""
📩 <b>Contact Staff</b>

👤 Username: {message.from_user.full_name}

📄 Reason:
{data['reason']}

💬 Message:
{message.caption or message.text}

🕒 Time: {datetime.now().strftime("%Y-%m-%d %H:%M")}
"""

    if message.photo:
        await bot.send_photo(
            STAFF_GROUP_ID,
            message.photo[-1].file_id,
            caption=text,
            reply_markup=staff_buttons(ticket)
        )

    elif message.video:
        await bot.send_video(
            STAFF_GROUP_ID,
            message.video.file_id,
            caption=text,
            reply_markup=staff_buttons(ticket)
        )

    else:
        await bot.send_message(
            STAFF_GROUP_ID,
            text,
            reply_markup=staff_buttons(ticket)
        )

    await message.answer(
        "✅ تیکت شما برای تیم پشتیبانی ارسال شد.",
        reply_markup=menu()
    )

    await state.clear()

# ---------------- STAFF ACTIONS ----------------

@dp.callback_query(F.data.startswith("accept"))
async def accept(callback: types.CallbackQuery):

    ticket = int(callback.data.split(":")[1])

    user = TICKETS.get(ticket)

    if user:
        await bot.send_message(user, "✅ درخواست شما توسط استاف تایید شد.")

    await callback.answer("Accepted")

@dp.callback_query(F.data.startswith("deny"))
async def deny(callback: types.CallbackQuery):

    ticket = int(callback.data.split(":")[1])

    user = TICKETS.get(ticket)

    if user:
        await bot.send_message(user, "❌ درخواست شما رد شد.")

    await callback.answer("Denied")

@dp.callback_query(F.data.startswith("reply"))
async def reply(callback: types.CallbackQuery):

    ticket = int(callback.data.split(":")[1])

    REPLY_MODE[callback.from_user.id] = ticket

    await callback.message.reply(
        "پیام خود را ارسال کنید تا برای پلیر فرستاده شود."
    )

    await callback.answer()

# ---------------- STAFF MESSAGE ----------------

@dp.message()
async def staff_reply(message: types.Message):

    if message.from_user.id in REPLY_MODE:

        ticket = REPLY_MODE[message.from_user.id]

        user = TICKETS.get(ticket)

        if user:

            await bot.send_message(
                user,
                f"💬 پاسخ استاف:\n\n{message.text}"
            )

        del REPLY_MODE[message.from_user.id]

# ---------------- MAIN ----------------

async def main():

    keep_alive()

    await bot.delete_webhook(drop_pending_updates=True)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
