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

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
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
            [
                types.InlineKeyboardButton(text="Rank",callback_data="shop_rank"),
                types.InlineKeyboardButton(text="Coin",callback_data="shop_coin")
            ]
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

# ---------------- STATES ----------------

class Punish(StatesGroup):
    username = State()
    pid = State()
    reason = State()
    explain = State()

class SimpleTicket(StatesGroup):
    message = State()

class ShopState(StatesGroup):
    message = State()

# ---------------- START ----------------

@dp.message(Command("start"))
async def start(message:types.Message):

    text = """
Welcome to TheFellOmen Support Center.

Please choose one of the options below.
"""

    await message.answer(text,reply_markup=main_menu())

# ---------------- PUNISHMENT ----------------

@dp.message(F.text == "🚫 Punishment Appeal")
async def punish_start(message:types.Message,state:FSMContext):

    await state.set_state(Punish.username)
    await message.answer("Step 1/4\nSend your Minecraft username.")

@dp.message(Punish.username)
async def punish_user(message:types.Message,state:FSMContext):

    await state.update_data(username=message.text)
    await state.set_state(Punish.pid)

    await message.answer("Step 2/4\nSend your Punishment ID.")

@dp.message(Punish.pid)
async def punish_pid(message:types.Message,state:FSMContext):

    await state.update_data(pid=message.text)
    await state.set_state(Punish.reason)

    await message.answer("Step 3/4\nWhat was the reason of the punishment?")

@dp.message(Punish.reason)
async def punish_reason(message:types.Message,state:FSMContext):

    await state.update_data(reason=message.text)
    await state.set_state(Punish.explain)

    await message.answer("Step 4/4\nExplain why the punishment should be removed.")

@dp.message(Punish.explain)
async def punish_finish(message:types.Message,state:FSMContext):

    data = await state.get_data()
    ticket = ticket_id()

    TICKETS[ticket] = {"user": message.from_user.id, "status": "open"}

    text = f"""
🚫 Punishment Appeal

Ticket ID: {ticket}

Username:
{data['username']}

Punishment ID:
{data['pid']}

Reason:
{data['reason']}

Explanation:
{message.text}

User:
@{message.from_user.username}
"""

    await bot.send_message(STAFF_GROUP_ID,text,reply_markup=staff_buttons(ticket))

    await message.answer("✅ Your appeal has been sent to staff.")

    await state.clear()

# ---------------- WHITELIST ----------------

@dp.message(F.text == "✅ Whitelist Request")
async def whitelist(message:types.Message,state:FSMContext):

    await state.update_data(type="Whitelist Request")
    await state.set_state(SimpleTicket.message)

    await message.answer("Send your Minecraft username and a short message.")

# ---------------- CONTACT ----------------

@dp.message(F.text == "👨‍💻 Contact Staff")
async def contact(message:types.Message,state:FSMContext):

    await state.update_data(type="Contact Staff")
    await state.set_state(SimpleTicket.message)

    await message.answer("Send your message for staff.")

# ---------------- SHOP ----------------

@dp.message(F.text == "🛒 Server Shop")
async def shop(message:types.Message):

    await message.answer(
        "Server Shop\nChoose a category.",
        reply_markup=shop_menu()
    )

# ---------------- SHOP RANK ----------------

@dp.callback_query(F.data == "shop_rank")
async def shop_rank(callback:types.CallbackQuery,state:FSMContext):

    text = """
Rank Shop

Vip » 49,000 Toman
Elite » 100,000 Toman
TheFellOmen » 190,000 Toman
Sponsor » 250,000 Toman
Lover » 400,000 Toman

If you only need the rank kit, write the rank and kit you want.
Example: Elite rank kit
"""

    await callback.message.edit_text(text)

    await state.update_data(type="Rank Shop")
    await state.set_state(ShopState.message)

# ---------------- SHOP COIN ----------------

@dp.callback_query(F.data == "shop_coin")
async def shop_coin(callback:types.CallbackQuery,state:FSMContext):

    text = """
Coin Shop

50 Coin » 15,000 Toman
100 Coins » 30,000 Toman
150 Coins » 55,000 Toman
200 Coins » 80,000 Toman
250 Coins » 150,000 Toman

If you want more coins than these amounts, write the amount you want in chat.
"""

    await callback.message.edit_text(text)

    await state.update_data(type="Coin Shop")
    await state.set_state(ShopState.message)

# ---------------- SHOP MESSAGE ----------------

@dp.message(ShopState.message)
async def shop_message(message:types.Message,state:FSMContext):

    data = await state.get_data()
    ticket = ticket_id()

    TICKETS[ticket] = {"user": message.from_user.id,"status":"open"}

    text = f"""
🛒 Shop Order

Ticket ID: {ticket}

Type:
{data['type']}

User:
@{message.from_user.username}

Order:
{message.text}
"""

    await bot.send_message(STAFF_GROUP_ID,text,reply_markup=staff_buttons(ticket))

    await message.answer("✅ Your order has been sent to staff.")

    await state.clear()

# ---------------- ACCEPT ----------------

@dp.callback_query(F.data.startswith("accept:"))
async def accept_ticket(callback:types.CallbackQuery):

    ticket = callback.data.split(":")[1]

    if TICKETS[ticket]["status"] == "accepted":
        await callback.answer("Already accepted",show_alert=True)
        return

    if TICKETS[ticket]["status"] == "denied":
        await callback.answer("Already denied",show_alert=True)
        return

    TICKETS[ticket]["status"] = "accepted"

    user = TICKETS[ticket]["user"]

    await bot.send_message(user,f"✅ Your ticket {ticket} has been accepted.")

    await callback.answer("Ticket accepted")

# ---------------- DENY ----------------

@dp.callback_query(F.data.startswith("deny:"))
async def deny_ticket(callback:types.CallbackQuery):

    ticket = callback.data.split(":")[1]

    if TICKETS[ticket]["status"] == "denied":
        await callback.answer("Already denied",show_alert=True)
        return

    if TICKETS[ticket]["status"] == "accepted":
        await callback.answer("Already accepted",show_alert=True)
        return

    TICKETS[ticket]["status"] = "denied"

    user = TICKETS[ticket]["user"]

    await bot.send_message(user,f"❌ Your ticket {ticket} was denied.")

    await callback.answer("Ticket denied")

# ---------------- REPLY ----------------

@dp.callback_query(F.data.startswith("reply:"))
async def reply_ticket(callback:types.CallbackQuery):

    ticket = callback.data.split(":")[1]

    user = TICKETS[ticket]["user"]

    REPLY_MODE[callback.from_user.id] = user

    await callback.message.reply("Send your reply for the player.")

@dp.message(F.chat.id == STAFF_GROUP_ID)
async def staff_reply(message:types.Message):

    if message.from_user.id not in REPLY_MODE:
        return

    user = REPLY_MODE[message.from_user.id]

    await bot.send_message(user,f"💬 Staff Reply:\n\n{message.text}")

    await message.reply("✅ Sent")

    del REPLY_MODE[message.from_user.id]

# ---------------- MAIN ----------------

async def main():

    keep_alive()

    await bot.delete_webhook(drop_pending_updates=True)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
