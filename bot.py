import os
import uuid
import asyncio
import threading

from flask import Flask
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

BOT_TOKEN = os.getenv("BOT_TOKEN")
STAFF_GROUP_ID = int(os.getenv("STAFF_GROUP_ID"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

TICKETS = {}

# ---------------- KEEP ALIVE ----------------

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running"

def run_web():
    app.run(host="0.0.0.0", port=10000)

# ---------------- STATES ----------------

class Punishment(StatesGroup):
    username = State()
    punish_id = State()
    reason = State()
    message = State()

class Whitelist(StatesGroup):
    username = State()

class Support(StatesGroup):
    message = State()

class StaffReply(StatesGroup):
    message = State()

# ---------------- MENU ----------------

def menu():

    return InlineKeyboardMarkup(inline_keyboard=[

        [InlineKeyboardButton(text="⚖️ Punishment Appeal", callback_data="punishment")],

        [InlineKeyboardButton(text="✅ Whitelist Request", callback_data="whitelist")],

        [InlineKeyboardButton(text="🎧 Contact Staff", callback_data="support")],

        [InlineKeyboardButton(text="🛒 Shop", callback_data="shop")]

    ])

# ---------------- START ----------------

@dp.message(Command("start"))
async def start(message: types.Message):

    await message.answer(

        "🌙 Welcome to TheFellOmen server bot\n\n"
        "Select one option below.",

        reply_markup=menu()

    )

# ---------------- PUNISHMENT ----------------

@dp.callback_query(F.data == "punishment")
async def punishment(call: types.CallbackQuery, state: FSMContext):

    await call.message.edit_text(

        "Punishment Appeal\n\n"
        "Send information like this:\n\n"
        "Username\n"
        "Punishment ID\n"
        "Reason\n"
        "Message\n\n"
        "First send your Minecraft username."

    )

    await state.set_state(Punishment.username)
    await call.answer()

@dp.message(Punishment.username)
async def p_user(message: types.Message, state: FSMContext):

    await state.update_data(username=message.text)

    await message.answer("Now send Punishment ID")

    await state.set_state(Punishment.punish_id)

@dp.message(Punishment.punish_id)
async def p_id(message: types.Message, state: FSMContext):

    await state.update_data(punish_id=message.text)

    await message.answer("Send reason of punishment")

    await state.set_state(Punishment.reason)

@dp.message(Punishment.reason)
async def p_reason(message: types.Message, state: FSMContext):

    await state.update_data(reason=message.text)

    await message.answer("Send your appeal message")

    await state.set_state(Punishment.message)

@dp.message(Punishment.message)
async def p_finish(message: types.Message, state: FSMContext):

    data = await state.get_data()

    ticket_id = str(uuid.uuid4())[:8]

    TICKETS[ticket_id] = message.from_user.id

    text = (

        "New Punishment Appeal\n\n"

        f"User: {message.from_user.full_name}\n"
        f"UserID: {message.from_user.id}\n\n"

        f"Username: {data['username']}\n"
        f"PunishID: {data['punish_id']}\n"
        f"Reason: {data['reason']}\n\n"

        f"Message:\n{message.text}"

    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[

        [
            InlineKeyboardButton(text="✅ Accept", callback_data=f"accept_{ticket_id}"),
            InlineKeyboardButton(text="❌ Deny", callback_data=f"deny_{ticket_id}")
        ],

        [
            InlineKeyboardButton(text="💬 Reply", callback_data=f"reply_{ticket_id}")
        ]

    ])

    await bot.send_message(STAFF_GROUP_ID, text, reply_markup=keyboard)

    await message.answer("Your request was sent to staff.")

    await state.clear()

# ---------------- WHITELIST ----------------

@dp.callback_query(F.data == "whitelist")
async def whitelist(call: types.CallbackQuery, state: FSMContext):

    await call.message.edit_text(

        "Whitelist Request\n\n"
        "Send your Minecraft username."

    )

    await state.set_state(Whitelist.username)

@dp.message(Whitelist.username)
async def whitelist_finish(message: types.Message, state: FSMContext):

    ticket_id = str(uuid.uuid4())[:8]

    TICKETS[ticket_id] = message.from_user.id

    text = (

        "Whitelist Request\n\n"

        f"User: {message.from_user.full_name}\n"
        f"UserID: {message.from_user.id}\n"
        f"Username: {message.text}"

    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[

        [
            InlineKeyboardButton(text="✅ Accept", callback_data=f"accept_{ticket_id}"),
            InlineKeyboardButton(text="❌ Deny", callback_data=f"deny_{ticket_id}")
        ],

        [
            InlineKeyboardButton(text="💬 Reply", callback_data=f"reply_{ticket_id}")
        ]

    ])

    await bot.send_message(STAFF_GROUP_ID, text, reply_markup=keyboard)

    await message.answer("Whitelist request sent.")

    await state.clear()

# ---------------- SUPPORT ----------------

@dp.callback_query(F.data == "support")
async def support(call: types.CallbackQuery, state: FSMContext):

    await call.message.edit_text(

        "Support\n\n"
        "Send your problem or question."

    )

    await state.set_state(Support.message)

@dp.message(Support.message)
async def support_finish(message: types.Message, state: FSMContext):

    ticket_id = str(uuid.uuid4())[:8]

    TICKETS[ticket_id] = message.from_user.id

    text = (

        "Support Ticket\n\n"

        f"User: {message.from_user.full_name}\n"
        f"UserID: {message.from_user.id}\n\n"

        f"Message:\n{message.text}"

    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[

        [
            InlineKeyboardButton(text="✅ Accept", callback_data=f"accept_{ticket_id}"),
            InlineKeyboardButton(text="❌ Deny", callback_data=f"deny_{ticket_id}")
        ],

        [
            InlineKeyboardButton(text="💬 Reply", callback_data=f"reply_{ticket_id}")
        ]

    ])

    await bot.send_message(STAFF_GROUP_ID, text, reply_markup=keyboard)

    await message.answer("Support ticket sent.")

    await state.clear()

# ---------------- SHOP ----------------

@dp.callback_query(F.data == "shop")
async def shop(call: types.CallbackQuery):

    await call.message.edit_text(

        "Server Shop\n\n"
        "Visit our store:\n"
        "your-store-link"

    )

# ---------------- STAFF ACTIONS ----------------

@dp.callback_query(F.data.startswith("accept_"))
async def accept(call: types.CallbackQuery):

    ticket_id = call.data.split("_")[1]

    user_id = TICKETS.get(ticket_id)

    if user_id:
        await bot.send_message(user_id, "✅ Your request was accepted.")

    await call.answer("Accepted")

@dp.callback_query(F.data.startswith("deny_"))
async def deny(call: types.CallbackQuery):

    ticket_id = call.data.split("_")[1]

    user_id = TICKETS.get(ticket_id)

    if user_id:
        await bot.send_message(user_id, "❌ Your request was denied.")

    await call.answer("Denied")

@dp.callback_query(F.data.startswith("reply_"))
async def reply(call: types.CallbackQuery, state: FSMContext):

    ticket_id = call.data.split("_")[1]

    await state.update_data(ticket=ticket_id)

    await state.set_state(StaffReply.message)

    await call.message.reply("Send your reply")

@dp.message(StaffReply.message)
async def reply_send(message: types.Message, state: FSMContext):

    data = await state.get_data()

    ticket_id = data["ticket"]

    user_id = TICKETS.get(ticket_id)

    if user_id:
        await bot.send_message(user_id, f"Staff reply:\n\n{message.text}")

    await message.answer("Reply sent.")

    await state.clear()

# ---------------- MAIN ----------------

async def main():

    await bot.set_my_commands([

        BotCommand(command="start", description="Start bot")

    ])

    await dp.start_polling(bot)

if __name__ == "__main__":

    threading.Thread(target=run_web).start()

    asyncio.run(main())
