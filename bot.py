import asyncio
import os
import json
import random
import string
import html
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
TRANSCRIPTS = {}
REPLY_MODE = {}
USERS = set()

# ---------------- KEEP ALIVE (Render) ----------------

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot Running"

def run():
    port = int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0",port=port)

def keep_alive():
    threading.Thread(target=run).start()

# ---------------- USERS ----------------

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

# ---------------- TOOLS ----------------

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
            [types.InlineKeyboardButton(text="Rank",callback_data="rank")],
            [types.InlineKeyboardButton(text="Coin",callback_data="coin")]
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

# ---------------- TRANSCRIPT ----------------

def create_transcript(ticket):

    messages = TRANSCRIPTS.get(ticket,[])

    html_content = "<html><body>"
    html_content += f"<h2>Transcript {ticket}</h2><hr>"

    for m in messages:
        html_content += f"<p><b>{html.escape(m['author'])}</b>: {html.escape(m['text'])}</p>"

    html_content += "</body></html>"

    filename = f"transcript_{ticket}.html"

    with open(filename,"w",encoding="utf-8") as f:
        f.write(html_content)

    return filename

# ---------------- STATES ----------------

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

# ---------------- START ----------------

@dp.message(Command("start"))
async def start(message:types.Message):

    add_user(message.from_user.id)

    text = """
👋 Welcome to TheFellOmen Support Center

Please choose an option below
"""

    await message.answer(text,reply_markup=main_menu())

# ---------------- PUNISHMENT ----------------

@dp.message(F.text=="🚫 Punishment Appeal")
async def punish_start(message:types.Message,state:FSMContext):

    await state.set_state(Punish.username)
    await message.answer("🎮 Minecraft username?")

@dp.message(Punish.username)
async def punish_user(message:types.Message,state:FSMContext):

    await state.update_data(username=message.text)

    await state.set_state(Punish.pid)

    await message.answer("🆔 Punishment ID?")

@dp.message(Punish.pid)
async def punish_pid(message:types.Message,state:FSMContext):

    await state.update_data(pid=message.text)

    await state.set_state(Punish.reason)

    await message.answer("📄 Reason?")

@dp.message(Punish.reason)
async def punish_reason(message:types.Message,state:FSMContext):

    await state.update_data(reason=message.text)

    await state.set_state(Punish.message)

    await message.answer("✏️ Full explanation")

@dp.message(Punish.message)
async def punish_finish(message:types.Message,state:FSMContext):

    data = await state.get_data()

    ticket = ticket_id()

    TICKETS[ticket]={"user":message.from_user.id}

    TRANSCRIPTS[ticket]=[]

    text=f"""
🚫 Punishment Appeal

🎮 {data['username']}
🆔 {data['pid']}

📄 {data['reason']}

💬 {message.text}

👤 @{message.from_user.username}

🎫 {ticket}
"""

    await bot.send_message(STAFF_GROUP_ID,text,reply_markup=staff_buttons(ticket))

    await message.answer("✅ Ticket sent to staff",reply_markup=main_menu())

    await state.clear()

# ---------------- WHITELIST ----------------

@dp.message(F.text=="✅ Whitelist Request")
async def wl_start(message:types.Message,state:FSMContext):

    await state.set_state(Whitelist.username)

    await message.answer("🎮 Minecraft username")

@dp.message(Whitelist.username)
async def wl_user(message:types.Message,state:FSMContext):

    await state.update_data(username=message.text)

    await state.set_state(Whitelist.message)

    await message.answer("💬 Message")

@dp.message(Whitelist.message)
async def wl_finish(message:types.Message,state:FSMContext):

    data=await state.get_data()

    ticket=ticket_id()

    TICKETS[ticket]={"user":message.from_user.id}

    TRANSCRIPTS[ticket]=[]

    text=f"""
✅ Whitelist Request

🎮 {data['username']}

💬 {message.text}

👤 @{message.from_user.username}

🎫 {ticket}
"""

    await bot.send_message(STAFF_GROUP_ID,text,reply_markup=staff_buttons(ticket))

    await message.answer("✅ Request sent",reply_markup=main_menu())

    await state.clear()

# ---------------- CONTACT ----------------

@dp.message(F.text=="👨‍💻 Contact Staff")
async def contact_start(message:types.Message,state:FSMContext):

    await state.set_state(Contact.subject)

    await message.answer("📌 Subject")

@dp.message(Contact.subject)
async def contact_subject(message:types.Message,state:FSMContext):

    await state.update_data(subject=message.text)

    await state.set_state(Contact.message)

    await message.answer("💬 Message")

@dp.message(Contact.message)
async def contact_finish(message:types.Message,state:FSMContext):

    data=await state.get_data()

    ticket=ticket_id()

    TICKETS[ticket]={"user":message.from_user.id}

    TRANSCRIPTS[ticket]=[]

    text=f"""
👨‍💻 Contact Staff

📌 {data['subject']}

💬 {message.text}

👤 @{message.from_user.username}

🎫 {ticket}
"""

    await bot.send_message(STAFF_GROUP_ID,text,reply_markup=staff_buttons(ticket))

    await message.answer("✅ Message sent",reply_markup=main_menu())

    await state.clear()

# ---------------- SHOP ----------------

@dp.message(F.text=="🛒 Server Shop")
async def shop(message:types.Message):

    await message.answer("🛒 Shop",reply_markup=shop_menu())

@dp.callback_query(F.data=="rank")
async def rank(callback:types.CallbackQuery,state:FSMContext):

    await state.update_data(category="Rank")
    await state.set_state(Shop.message)

    text="""
Vip » 49,000
Elite » 100,000
TheFellOmen » 190,000
Sponsor » 250,000
Lover » 400,000
"""

    await callback.message.edit_text(text)

@dp.callback_query(F.data=="coin")
async def coin(callback:types.CallbackQuery,state:FSMContext):

    await state.update_data(category="Coin")
    await state.set_state(Shop.message)

    text="""
50 Coin » 15,000
100 Coin » 30,000
150 Coin » 55,000
200 Coin » 80,000
250 Coin » 150,000
"""

    await callback.message.edit_text(text)

@dp.message(Shop.message)
async def shop_finish(message:types.Message,state:FSMContext):

    data=await state.get_data()

    ticket=ticket_id()

    TICKETS[ticket]={"user":message.from_user.id}

    text=f"""
🛒 Shop Order

📦 {data['category']}

💬 {message.text}

👤 @{message.from_user.username}

🎫 {ticket}
"""

    await bot.send_message(STAFF_GROUP_ID,text,reply_markup=staff_buttons(ticket))

    await message.answer("✅ Order sent",reply_markup=main_menu())

    await state.clear()

# ---------------- STAFF ACTIONS ----------------

@dp.callback_query(F.data.startswith("accept:"))
async def accept_ticket(callback:types.CallbackQuery):

    ticket = callback.data.split(":")[1]

    user = TICKETS.get(ticket,{}).get("user")

    if user:
        await bot.send_message(user,f"✅ Your ticket {ticket} accepted")

    file=create_transcript(ticket)

    await bot.send_document(STAFF_GROUP_ID,types.FSInputFile(file))

    await callback.message.edit_reply_markup()

@dp.callback_query(F.data.startswith("deny:"))
async def deny_ticket(callback:types.CallbackQuery):

    ticket = callback.data.split(":")[1]

    user = TICKETS.get(ticket,{}).get("user")

    if user:
        await bot.send_message(user,f"❌ Your ticket {ticket} denied")

    file=create_transcript(ticket)

    await bot.send_document(STAFF_GROUP_ID,types.FSInputFile(file))

    await callback.message.edit_reply_markup()

@dp.callback_query(F.data.startswith("reply:"))
async def reply_ticket(callback:types.CallbackQuery):

    ticket = callback.data.split(":")[1]

    user = TICKETS.get(ticket,{}).get("user")

    REPLY_MODE[callback.from_user.id]={"ticket":ticket,"user":user}

    await callback.message.reply("💬 Send reply")

@dp.message(F.chat.id==STAFF_GROUP_ID)
async def staff_reply(message:types.Message):

    if message.from_user.id not in REPLY_MODE:
        return

    data=REPLY_MODE[message.from_user.id]

    await bot.send_message(data["user"],f"💬 Staff Reply\n\n{message.text}")

    TRANSCRIPTS[data["ticket"]].append({"author":"Staff","text":message.text})

    del REPLY_MODE[message.from_user.id]

# ---------------- BROADCAST ----------------

@dp.message(Command("broadcast"))
async def broadcast(message:types.Message):

    if message.chat.id != STAFF_GROUP_ID:
        return

    if not message.reply_to_message:
        return

    msg = message.reply_to_message.text

    for u in USERS:
        try:
            await bot.send_message(u,msg)
        except:
            pass

# ---------------- MAIN ----------------

async def main():

    load_users()

    keep_alive()

    await bot.delete_webhook(drop_pending_updates=True)

    await dp.start_polling(bot)

if __name__=="__main__":
    asyncio.run(main())
