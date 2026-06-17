import asyncio
import os
import random
import string
import threading

from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

BOT_TOKEN = os.getenv("BOT_TOKEN")

STAFF_GROUP_ID = -1004332150226

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher(storage=MemoryStorage())

TICKETS = {}
REPLY_MODE = {}

# ---------------- KEEP ALIVE ----------------

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot Online"

def run():
    port = int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0",port=port)

def keep_alive():
    threading.Thread(target=run).start()

# ---------------- TOOLS ----------------

def ticket_id():
    return "TK-" + "".join(random.choices(string.ascii_uppercase+string.digits,k=6))

def main_menu():
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="🚫 اعتراض به مجازات")],
            [types.KeyboardButton(text="✅ درخواست وایت لیست")],
            [types.KeyboardButton(text="👨‍💻 ارتباط با استاف")],
            [types.KeyboardButton(text="🛒 فروشگاه سرور")]
        ],
        resize_keyboard=True
    )

def staff_buttons(ticket):
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="✅ Accept",callback_data=f"accept:{ticket}"),
                types.InlineKeyboardButton(text="❌ Deny",callback_data=f"deny:{ticket}")
            ],
            [
                types.InlineKeyboardButton(text="💬 Reply",callback_data=f"reply:{ticket}")
            ]
        ]
    )

# ---------------- STATES ----------------

class TicketState(StatesGroup):
    waiting_message = State()

# ---------------- START ----------------

@dp.message(Command("start"))
async def start(message:types.Message):

    text = """
👋 به مرکز پشتیبانی TheFellOmen خوش آمدید

برای ارسال تیکت یکی از گزینه‌های زیر را انتخاب کنید.
"""

    await message.answer(text,reply_markup=main_menu())

# ---------------- MENU ----------------

@dp.message(F.text == "🚫 اعتراض به مجازات")
async def punish(message:types.Message,state:FSMContext):

    await state.update_data(type="Punishment Appeal")
    await state.set_state(TicketState.waiting_message)

    await message.answer("لطفاً توضیحات اعتراض خود را ارسال کنید.")

@dp.message(F.text == "✅ درخواست وایت لیست")
async def whitelist(message:types.Message,state:FSMContext):

    await state.update_data(type="Whitelist Request")
    await state.set_state(TicketState.waiting_message)

    await message.answer("نام کاربری ماینکرفت و توضیحات خود را ارسال کنید.")

@dp.message(F.text == "👨‍💻 ارتباط با استاف")
async def contact(message:types.Message,state:FSMContext):

    await state.update_data(type="Contact Staff")
    await state.set_state(TicketState.waiting_message)

    await message.answer("پیام خود را برای تیم استاف ارسال کنید.")

@dp.message(F.text == "🛒 فروشگاه سرور")
async def shop(message:types.Message,state:FSMContext):

    await state.update_data(type="Shop Order")
    await state.set_state(TicketState.waiting_message)

    await message.answer("سفارش خود را بنویسید.")

# ---------------- TEXT TICKET ----------------

@dp.message(TicketState.waiting_message, F.text)
async def ticket_text(message:types.Message,state:FSMContext):

    data = await state.get_data()

    ticket = ticket_id()

    TICKETS[ticket] = {
        "user": message.from_user.id,
        "status": "open"
    }

    text = f"""
📨 تیکت جدید

🎫 Ticket ID: {ticket}

📌 نوع تیکت:
{data['type']}

👤 کاربر:
@{message.from_user.username}

💬 پیام:
{message.text}
"""

    await bot.send_message(
        STAFF_GROUP_ID,
        text,
        reply_markup=staff_buttons(ticket)
    )

    await message.answer("✅ تیکت شما برای استاف ارسال شد.")

    await state.clear()

# ---------------- MEDIA TICKET ----------------

@dp.message(TicketState.waiting_message, F.photo | F.video | F.document)
async def ticket_media(message:types.Message,state:FSMContext):

    data = await state.get_data()

    ticket = ticket_id()

    TICKETS[ticket] = {
        "user": message.from_user.id,
        "status": "open"
    }

    caption = f"""
📨 تیکت جدید

🎫 Ticket ID: {ticket}

📌 نوع تیکت:
{data['type']}

👤 کاربر:
@{message.from_user.username}
"""

    if message.photo:
        await bot.send_photo(
            STAFF_GROUP_ID,
            message.photo[-1].file_id,
            caption=caption,
            reply_markup=staff_buttons(ticket)
        )

    elif message.video:
        await bot.send_video(
            STAFF_GROUP_ID,
            message.video.file_id,
            caption=caption,
            reply_markup=staff_buttons(ticket)
        )

    elif message.document:
        await bot.send_document(
            STAFF_GROUP_ID,
            message.document.file_id,
            caption=caption,
            reply_markup=staff_buttons(ticket)
        )

    await message.answer("✅ فایل شما برای استاف ارسال شد.")

    await state.clear()

# ---------------- ACCEPT ----------------

@dp.callback_query(F.data.startswith("accept:"))
async def accept_ticket(callback:types.CallbackQuery):

    ticket = callback.data.split(":")[1]

    if TICKETS[ticket]["status"] == "accepted":
        await callback.answer("قبلاً Accept شده",show_alert=True)
        return

    if TICKETS[ticket]["status"] == "denied":
        await callback.answer("قبلاً Deny شده",show_alert=True)
        return

    TICKETS[ticket]["status"] = "accepted"

    user = TICKETS[ticket]["user"]

    await bot.send_message(
        user,
        f"✅ تیکت {ticket} توسط استاف پذیرفته شد."
    )

    await callback.answer("Accept شد")

# ---------------- DENY ----------------

@dp.callback_query(F.data.startswith("deny:"))
async def deny_ticket(callback:types.CallbackQuery):

    ticket = callback.data.split(":")[1]

    if TICKETS[ticket]["status"] == "denied":
        await callback.answer("قبلاً Deny شده",show_alert=True)
        return

    if TICKETS[ticket]["status"] == "accepted":
        await callback.answer("قبلاً Accept شده",show_alert=True)
        return

    TICKETS[ticket]["status"] = "denied"

    user = TICKETS[ticket]["user"]

    await bot.send_message(
        user,
        f"❌ تیکت {ticket} رد شد."
    )

    await callback.answer("Deny شد")

# ---------------- REPLY ----------------

@dp.callback_query(F.data.startswith("reply:"))
async def reply_ticket(callback:types.CallbackQuery):

    ticket = callback.data.split(":")[1]

    user = TICKETS[ticket]["user"]

    REPLY_MODE[callback.from_user.id] = user

    await callback.message.reply("پیام خود را برای بازیکن ارسال کنید.")

@dp.message(F.chat.id == STAFF_GROUP_ID)
async def staff_reply(message:types.Message):

    if message.from_user.id not in REPLY_MODE:
        return

    user = REPLY_MODE[message.from_user.id]

    await bot.send_message(
        user,
        f"💬 پیام از طرف استاف:\n\n{message.text}"
    )

    await message.reply("✅ ارسال شد")

    del REPLY_MODE[message.from_user.id]

# ---------------- MAIN ----------------

async def main():

    keep_alive()

    await bot.delete_webhook(drop_pending_updates=True)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
