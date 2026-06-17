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
STAFF_GROUP_ID = -100XXXXXXXXXX

bot = Bot(token=BOT_TOKEN,default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# ---------- DATA ----------

tickets = {}
user_ticket = {}

# ---------- KEEP ALIVE ----------

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot Online"

def run():
    port=int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0",port=port)

def keep_alive():
    threading.Thread(target=run).start()

# ---------- TOOLS ----------

def ticket_id():
    return "TK-"+''.join(random.choices(string.ascii_uppercase+string.digits,k=6))

def menu():
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="🚫 Punishment Appeal")],
            [types.KeyboardButton(text="👨‍💻 Contact Staff")],
            [types.KeyboardButton(text="💎 Server Shop")],
            [types.KeyboardButton(text="📜 Whitelist Request")]
        ],
        resize_keyboard=True
    )

def staff_panel(ticket):
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="Close",callback_data=f"close:{ticket}")
            ]
        ]
    )

# ---------- STATES ----------

class Punish(StatesGroup):
    username=State()
    pid=State()
    reason=State()
    explain=State()

class Contact(StatesGroup):
    message=State()

# ---------- START ----------

@dp.message(Command("start"))
async def start(message:types.Message):

    await message.answer(
"""
🎮 به ربات پشتیبانی سرور خوش آمدید

برای صحبت با استف از دکمه‌ها استفاده کنید
""",
reply_markup=menu()
)

# ---------- CONTACT ----------

@dp.message(F.text=="👨‍💻 Contact Staff")
async def contact_start(message:types.Message,state:FSMContext):

    if message.from_user.id in user_ticket:
        await message.answer("شما یک تیکت باز دارید.")
        return

    await state.set_state(Contact.message)

    await message.answer("پیام خود را ارسال کنید")

@dp.message(Contact.message)
async def create_contact(message:types.Message,state:FSMContext):

    ticket=ticket_id()

    tickets[ticket]={
        "user":message.from_user.id,
        "status":"open"
    }

    user_ticket[message.from_user.id]=ticket

    text=f"""
🎫 CONTACT TICKET

Ticket: {ticket}

User:
@{message.from_user.username}
"""

    msg=await bot.send_message(
        STAFF_GROUP_ID,
        text,
        reply_markup=staff_panel(ticket)
    )

    tickets[ticket]["staff_msg"]=msg.message_id

    await message.answer("✅ تیکت ساخته شد")

    await state.clear()

# ---------- PUNISH ----------

@dp.message(F.text=="🚫 Punishment Appeal")
async def punish_start(message:types.Message,state:FSMContext):

    if message.from_user.id in user_ticket:
        await message.answer("شما یک تیکت باز دارید.")
        return

    await state.set_state(Punish.username)

    await message.answer("Minecraft Username را ارسال کنید")

@dp.message(Punish.username)
async def p1(message:types.Message,state:FSMContext):

    await state.update_data(username=message.text)
    await state.set_state(Punish.pid)

    await message.answer("Punishment ID")

@dp.message(Punish.pid)
async def p2(message:types.Message,state:FSMContext):

    await state.update_data(pid=message.text)
    await state.set_state(Punish.reason)

    await message.answer("Reason")

@dp.message(Punish.reason)
async def p3(message:types.Message,state:FSMContext):

    await state.update_data(reason=message.text)
    await state.set_state(Punish.explain)

    await message.answer("Explain")

@dp.message(Punish.explain)
async def p4(message:types.Message,state:FSMContext):

    data=await state.get_data()

    ticket=ticket_id()

    tickets[ticket]={
        "user":message.from_user.id,
        "status":"open"
    }

    user_ticket[message.from_user.id]=ticket

    text=f"""
🚫 PUNISHMENT APPEAL

Ticket: {ticket}

Username:
{data['username']}

Punishment ID:
{data['pid']}

Reason:
{data['reason']}

Explain:
{message.text}

User:
@{message.from_user.username}
"""

    msg=await bot.send_message(
        STAFF_GROUP_ID,
        text,
        reply_markup=staff_panel(ticket)
    )

    tickets[ticket]["staff_msg"]=msg.message_id

    await message.answer("✅ تیکت ارسال شد")

    await state.clear()

# ---------- USER → STAFF ----------

@dp.message(F.chat.type=="private")
async def user_messages(message:types.Message):

    uid=message.from_user.id

    if uid not in user_ticket:
        return

    ticket=user_ticket[uid]

    if tickets[ticket]["status"]!="open":
        return

    header=f"👤 {ticket}\n"

    if message.text:
        await bot.send_message(STAFF_GROUP_ID,header+message.text)

    elif message.photo:
        await bot.send_photo(STAFF_GROUP_ID,message.photo[-1].file_id,caption=header)

    elif message.video:
        await bot.send_video(STAFF_GROUP_ID,message.video.file_id,caption=header)

    elif message.document:
        await bot.send_document(STAFF_GROUP_ID,message.document.file_id,caption=header)

# ---------- STAFF → USER ----------

@dp.message(F.chat.id==STAFF_GROUP_ID)
async def staff_messages(message:types.Message):

    if not message.reply_to_message:
        return

    text=message.reply_to_message.text

    if "Ticket:" not in text:
        return

    ticket=text.split("Ticket: ")[1].split("\n")[0]

    if ticket not in tickets:
        return

    user=tickets[ticket]["user"]

    if message.text:
        await bot.send_message(user,message.text)

    elif message.photo:
        await bot.send_photo(user,message.photo[-1].file_id,caption=message.caption)

    elif message.video:
        await bot.send_video(user,message.video.file_id,caption=message.caption)

    elif message.document:
        await bot.send_document(user,message.document.file_id,caption=message.caption)

# ---------- CLOSE ----------

@dp.callback_query(F.data.startswith("close:"))
async def close(callback:types.CallbackQuery):

    ticket=callback.data.split(":")[1]

    if tickets[ticket]["status"]=="closed":
        await callback.answer("already closed")
        return

    tickets[ticket]["status"]="closed"

    user=tickets[ticket]["user"]

    user_ticket.pop(user,None)

    await bot.send_message(user,"🔒 تیکت بسته شد")

    await callback.answer("closed")

# ---------- MAIN ----------

async def main():

    keep_alive()

    await bot.delete_webhook(drop_pending_updates=True)

    await dp.start_polling(bot)

if __name__=="__main__":
    asyncio.run(main())
