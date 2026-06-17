import asyncio
import os
import random
import string
import threading
from datetime import datetime

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

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

tickets = {}
user_ticket = {}

# ---------------- KEEP ALIVE ----------------

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot Online"

def run():
    port=int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0",port=port)

def keep_alive():
    threading.Thread(target=run).start()

# ---------------- TOOLS ----------------

def ticket_id():
    return "TK-"+''.join(random.choices(string.ascii_uppercase+string.digits,k=6))

def time():
    return datetime.now().strftime("%Y-%m-%d %H:%M")

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

# ---------------- STATES ----------------

class Contact(StatesGroup):
    reason = State()

class Whitelist(StatesGroup):
    username = State()

class ShopRank(StatesGroup):
    text = State()

class ShopCoin(StatesGroup):
    text = State()

# ---------------- START ----------------

@dp.message(Command("start"))
async def start(message:types.Message):

    await message.answer(
"""
🎮 به ربات پشتیبانی سرور خوش آمدید

برای صحبت با استف از دکمه‌ها استفاده کنید
""",
reply_markup=menu()
)

# ---------------- WHITELIST ----------------

@dp.message(F.text=="📜 Whitelist Request")
async def wl_start(message:types.Message,state:FSMContext):

    await state.set_state(Whitelist.username)

    await message.answer("لطفا یوزر ای که میخواهید وایت لیست شود را در چت بنویسید.")

@dp.message(Whitelist.username)
async def wl_send(message:types.Message,state:FSMContext):

    username=message.text

    text=f"""
Whitelist
Username: {username}
Time: {time()}
Messages: 0
"""

    kb=types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="Accept",callback_data=f"wl_accept:{message.from_user.id}"),
                types.InlineKeyboardButton(text="Deny",callback_data=f"wl_deny:{message.from_user.id}")
            ]
        ]
    )

    await bot.send_message(STAFF_GROUP_ID,text,reply_markup=kb)

    await message.answer("✅ درخواست شما ارسال شد")

    await state.clear()

# ---------------- CONTACT ----------------

@dp.message(F.text=="👨‍💻 Contact Staff")
async def contact_start(message:types.Message,state:FSMContext):

    if message.from_user.id in user_ticket:
        await message.answer("شما یک تیکت باز دارید.")
        return

    await state.set_state(Contact.reason)

    await message.answer("Reason را بنویسید")

@dp.message(Contact.reason)
async def contact_send(message:types.Message,state:FSMContext):

    reason=message.text

    ticket=ticket_id()

    tickets[ticket]={
        "user":message.from_user.id,
        "messages":0,
        "status":"open"
    }

    user_ticket[message.from_user.id]=ticket

    text=f"""
Contact Staff
Username: @{message.from_user.username}
Reason: {reason}
Time: {time()}
Messages: 0
Ticket: {ticket}
"""

    kb=types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="Accept",callback_data=f"accept:{ticket}"),
                types.InlineKeyboardButton(text="Deny",callback_data=f"deny:{ticket}")
            ],
            [
                types.InlineKeyboardButton(text="Reply",callback_data=f"reply:{ticket}")
            ]
        ]
    )

    await bot.send_message(STAFF_GROUP_ID,text,reply_markup=kb)

    await message.answer("✅ تیکت ساخته شد")

    await state.clear()

# ---------------- SHOP ----------------

@dp.message(F.text=="💎 Server Shop")
async def shop(message:types.Message):

    kb=types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="Rank",callback_data="shop_rank")],
            [types.InlineKeyboardButton(text="Coin",callback_data="shop_coin")]
        ]
    )

    await message.answer("رنک ها و کوین ها در سرور",reply_markup=kb)

# ---------- RANK ----------

@dp.callback_query(F.data=="shop_rank")
async def rank_shop(callback:types.CallbackQuery,state:FSMContext):

    await callback.message.answer(
"""
Rank Shop

Vip » 49,000 Toman
Elite » 100,000 Toman
TheFellOmen » 190,000 Toman
Sponsor » 250,000 Toman
Lover » 400,000 Toman

اگر فقط نیاز به کیت رنک دارید رنک مورد نظر و کیت ای که میخواهید را بنویسید
مثلا: کیت رنک الایت
"""
)

    await state.set_state(ShopRank.text)

# ---------- COIN ----------

@dp.callback_query(F.data=="shop_coin")
async def coin_shop(callback:types.CallbackQuery,state:FSMContext):

    await callback.message.answer(
"""
Coin Shop

50 Coin » 15,000 Toman
100 Coins » 30,000 Toman
150 Coins » 55,000 Toman
200 Coins » 80,000 Toman
250 Coins » 150,000 Toman

اگر مقدار کوین ای که میخواهید بیشتر از این هاست مقدار مورد نظر خودتون رو تو چت بنویسید
"""
)

    await state.set_state(ShopCoin.text)

# ---------------- USER MESSAGES ----------------

@dp.message(F.chat.type=="private")
async def user_messages(message:types.Message):

    uid=message.from_user.id

    if uid not in user_ticket:
        return

    ticket=user_ticket[uid]

    if tickets[ticket]["status"]!="open":
        return

    tickets[ticket]["messages"]+=1

    header=f"Ticket {ticket}\n"

    if message.text:
        await bot.send_message(STAFF_GROUP_ID,header+message.text)

    elif message.photo:
        await bot.send_photo(STAFF_GROUP_ID,message.photo[-1].file_id,caption=header)

    elif message.video:
        await bot.send_video(STAFF_GROUP_ID,message.video.file_id,caption=header)

# ---------------- STAFF REPLY ----------------

@dp.message(F.chat.id==STAFF_GROUP_ID)
async def staff_reply(message:types.Message):

    if not message.reply_to_message:
        return

    txt=message.reply_to_message.text

    if not txt or "Ticket:" not in txt:
        return

    ticket=txt.split("Ticket: ")[1].split("\n")[0]

    user=tickets[ticket]["user"]

    if message.text:
        await bot.send_message(user,"👮 پاسخ استف\n\n"+message.text)

# ---------------- ACCEPT / DENY ----------------

@dp.callback_query(F.data.startswith("wl_accept"))
async def wl_accept(callback:types.CallbackQuery):

    uid=int(callback.data.split(":")[1])

    await bot.send_message(uid,"✅ شما وایت لیست شدید")

    await callback.answer("Accepted")

@dp.callback_query(F.data.startswith("wl_deny"))
async def wl_deny(callback:types.CallbackQuery):

    uid=int(callback.data.split(":")[1])

    await bot.send_message(uid,"❌ درخواست وایت لیست رد شد")

    await callback.answer("Denied")

# ---------------- MAIN ----------------

async def main():

    keep_alive()

    await bot.delete_webhook(drop_pending_updates=True)

    await dp.start_polling(bot)

if __name__=="__main__":
    asyncio.run(main())
