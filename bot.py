import asyncio
import os
import json
import random
import string
import threading
from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

BOT_TOKEN = os.getenv("BOT_TOKEN")

STAFF_GROUP_ID = -1004332150226

USERS_FILE = "users.json"

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher(storage=MemoryStorage())

TICKETS = {}
REPLY_MODE = {}
USERS = set()

# ---------- KEEP ALIVE ----------

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot Online"

def run():
    port = int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0",port=port)

def keep_alive():
    threading.Thread(target=run).start()

# ---------- USERS ----------

def load_users():
    global USERS
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE,"r") as f:
            USERS = set(json.load(f))

def save_users():
    with open(USERS_FILE,"w") as f:
        json.dump(list(USERS),f)

def add_user(uid):
    USERS.add(uid)
    save_users()

# ---------- TOOLS ----------

def ticket_id():
    return "TK-" + "".join(random.choices(string.ascii_uppercase+string.digits,k=6))

def main_menu():
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="🚫 Punishment Appeal")],
            [types.KeyboardButton(text="✅ Whitelist Request")],
            [types.KeyboardButton(text="👨‍💻 Contact Staff")],
            [types.KeyboardButton(text="🛒 Server Shop")]
        ],
        resize_keyboard=True
    )

def shop_menu():
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="👑 Rank",callback_data="rank")],
            [types.InlineKeyboardButton(text="🪙 Coin",callback_data="coin")]
        ]
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

# ---------- STATES ----------

class Punish(StatesGroup):
    username = State()
    pid = State()
    reason = State()
    message = State()

class Whitelist(StatesGroup):
    username = State()
    message = State()

class Contact(StatesGroup):
    subject = State()
    message = State()

class Shop(StatesGroup):
    category = State()
    message = State()

# ---------- START ----------

@dp.message(Command("start"))
async def start(message:types.Message):

    add_user(message.from_user.id)

    text = """
👋 Welcome to <b>TheFellOmen Support Center</b>

If you need help, want to appeal a punishment, request whitelist, 
or contact the staff team, you can easily do it here.

Please choose one of the options below.
"""

    await message.answer(text,reply_markup=main_menu())

# ---------- PUNISHMENT ----------

@dp.message(F.text=="🚫 Punishment Appeal")
async def punish_start(message:types.Message,state:FSMContext):

    await state.set_state(Punish.username)

    await message.answer(
        "🚫 <b>Punishment Appeal</b>\n\n"
        "Please send your Minecraft username so we can locate your punishment record."
    )

@dp.message(Punish.username)
async def punish_user(message:types.Message,state:FSMContext):

    await state.update_data(username=message.text)

    await state.set_state(Punish.pid)

    await message.answer(
        "🆔 Please send the <b>Punishment ID</b> you received from the server."
    )

@dp.message(Punish.pid)
async def punish_pid(message:types.Message,state:FSMContext):

    await state.update_data(pid=message.text)

    await state.set_state(Punish.reason)

    await message.answer(
        "📄 What was the reason of the punishment?"
    )

@dp.message(Punish.reason)
async def punish_reason(message:types.Message,state:FSMContext):

    await state.update_data(reason=message.text)

    await state.set_state(Punish.message)

    await message.answer(
        "✏️ Please explain why you think the punishment should be removed."
    )

@dp.message(Punish.message)
async def punish_finish(message:types.Message,state:FSMContext):

    data = await state.get_data()

    ticket = ticket_id()

    TICKETS[ticket]={"user":message.from_user.id}

    text=f"""
🚫 <b>Punishment Appeal Ticket</b>

🎫 Ticket ID: {ticket}

🎮 Minecraft Username:
{data['username']}

🆔 Punishment ID:
{data['pid']}

📄 Reason:
{data['reason']}

💬 Player Explanation:
{message.text}

👤 Telegram:
@{message.from_user.username}
"""

    await bot.send_message(STAFF_GROUP_ID,text,reply_markup=staff_buttons(ticket))

    await message.answer(
        "✅ Your appeal has been successfully submitted.\n\n"
        "Our staff team will review your request and respond as soon as possible."
    )

    await state.clear()

# ---------- WHITELIST ----------

@dp.message(F.text=="✅ Whitelist Request")
async def wl_start(message:types.Message,state:FSMContext):

    await state.set_state(Whitelist.username)

    await message.answer(
        "✅ <b>Whitelist Request</b>\n\n"
        "Please send your Minecraft username."
    )

@dp.message(Whitelist.username)
async def wl_user(message:types.Message,state:FSMContext):

    await state.update_data(username=message.text)

    await state.set_state(Whitelist.message)

    await message.answer(
        "💬 If you want, write a short message for the staff team."
    )

@dp.message(Whitelist.message)
async def wl_finish(message:types.Message,state:FSMContext):

    data=await state.get_data()

    ticket=ticket_id()

    TICKETS[ticket]={"user":message.from_user.id}

    text=f"""
✅ <b>Whitelist Request</b>

🎫 Ticket ID: {ticket}

🎮 Minecraft Username:
{data['username']}

💬 Message:
{message.text}

👤 Telegram:
@{message.from_user.username}
"""

    await bot.send_message(STAFF_GROUP_ID,text,reply_markup=staff_buttons(ticket))

    await message.answer(
        "✅ Your whitelist request has been sent to the staff team."
    )

    await state.clear()

# ---------- CONTACT ----------

@dp.message(F.text=="👨‍💻 Contact Staff")
async def contact_start(message:types.Message,state:FSMContext):

    await state.set_state(Contact.subject)

    await message.answer(
        "👨‍💻 <b>Contact Staff</b>\n\n"
        "Please send the subject of your message."
    )

@dp.message(Contact.subject)
async def contact_subject(message:types.Message,state:FSMContext):

    await state.update_data(subject=message.text)

    await state.set_state(Contact.message)

    await message.answer(
        "💬 Now write the message you want to send to the staff team."
    )

@dp.message(Contact.message)
async def contact_finish(message:types.Message,state:FSMContext):

    data=await state.get_data()

    ticket=ticket_id()

    TICKETS[ticket]={"user":message.from_user.id}

    text=f"""
👨‍💻 <b>Support Ticket</b>

🎫 Ticket ID: {ticket}

📌 Subject:
{data['subject']}

💬 Message:
{message.text}

👤 Telegram:
@{message.from_user.username}
"""

    await bot.send_message(STAFF_GROUP_ID,text,reply_markup=staff_buttons(ticket))

    await message.answer(
        "✅ Your support message has been delivered to the staff team."
    )

    await state.clear()

# ---------- SHOP ----------

@dp.message(F.text=="🛒 Server Shop")
async def shop(message:types.Message):

    await message.answer(
        "🛒 <b>TheFellOmen Server Shop</b>\n\n"
        "Choose the category you want to buy from."
        ,reply_markup=shop_menu()
    )

@dp.callback_query(F.data=="rank")
async def rank(callback:types.CallbackQuery,state:FSMContext):

    await state.update_data(category="Rank")
    await state.set_state(Shop.message)

    text="""
👑 <b>Rank Shop</b>

Vip » 49,000
Elite » 100,000
TheFellOmen » 190,000
Sponsor » 250,000
Lover » 400,000

Write the rank you want to buy.
"""

    await callback.message.edit_text(text)

@dp.callback_query(F.data=="coin")
async def coin(callback:types.CallbackQuery,state:FSMContext):

    await state.update_data(category="Coin")
    await state.set_state(Shop.message)

    text="""
🪙 <b>Coin Shop</b>

50 Coin » 15,000
100 Coin » 30,000
150 Coin » 55,000
200 Coin » 80,000
250 Coin » 150,000

Write how many coins you want.
"""

    await callback.message.edit_text(text)

@dp.message(Shop.message)
async def shop_finish(message:types.Message,state:FSMContext):

    data=await state.get_data()

    ticket=ticket_id()

    TICKETS[ticket]={"user":message.from_user.id}

    text=f"""
🛒 <b>Shop Order</b>

🎫 Ticket ID: {ticket}

📦 Category:
{data['category']}

💬 Order Details:
{message.text}

👤 Telegram:
@{message.from_user.username}
"""

    await bot.send_message(STAFF_GROUP_ID,text,reply_markup=staff_buttons(ticket))

    await message.answer(
        "✅ Your order request has been sent to the staff team."
    )

    await state.clear()

# ---------- STAFF BUTTONS ----------

@dp.callback_query(F.data.startswith("accept:"))
async def accept_ticket(callback:types.CallbackQuery):

    ticket = callback.data.split(":")[1]

    user = TICKETS.get(ticket,{}).get("user")

    if user:
        await bot.send_message(
            user,
            f"✅ Your ticket {ticket} has been accepted by the staff team."
        )

    await callback.message.edit_reply_markup()

@dp.callback_query(F.data.startswith("deny:"))
async def deny_ticket(callback:types.CallbackQuery):

    ticket = callback.data.split(":")[1]

    user = TICKETS.get(ticket,{}).get("user")

    if user:
        await bot.send_message(
            user,
            f"❌ Your ticket {ticket} has been denied by the staff team."
        )

    await callback.message.edit_reply_markup()

@dp.callback_query(F.data.startswith("reply:"))
async def reply_ticket(callback:types.CallbackQuery):

    ticket = callback.data.split(":")[1]

    user = TICKETS.get(ticket,{}).get("user")

    REPLY_MODE[callback.from_user.id]={"ticket":ticket,"user":user}

    await callback.message.reply(
        "💬 Please send the message you want to deliver to the player."
    )

@dp.message(F.chat.id==STAFF_GROUP_ID)
async def staff_reply(message:types.Message):

    if message.from_user.id not in REPLY_MODE:
        return

    data=REPLY_MODE[message.from_user.id]

    await bot.send_message(
        data["user"],
        f"💬 <b>Message From Staff</b>\n\n{message.text}"
    )

    await message.reply("✅ Reply sent to player.")

    del REPLY_MODE[message.from_user.id]

# ---------- MAIN ----------

async def main():

    load_users()

    keep_alive()

    await bot.delete_webhook(drop_pending_updates=True)

    await dp.start_polling(bot)

if __name__=="__main__":
    asyncio.run(main())
