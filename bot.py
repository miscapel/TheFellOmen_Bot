import asyncio
import html
import os
import uuid
import logging
import threading
from flask import Flask
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    BotCommand,
    BotCommandScopeDefault,
    BotCommandScopeChat
)

# ---------- CONFIG ----------

logging.basicConfig(level=logging.INFO)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
STAFF_GROUP_ID = int(os.getenv("STAFF_GROUP_ID"))
ADMIN_ID = int(os.getenv("ADMIN_ID"))
PORT = int(os.getenv("PORT", 10000))

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher(storage=MemoryStorage())
app = Flask(__name__)

# ---------- DATABASE ----------

USERS = set()
TICKETS = {}

# ---------- STATES ----------

class PunishmentForm(StatesGroup):
    username = State()
    punish_id = State()
    message = State()

class WhitelistForm(StatesGroup):
    username = State()

class SupportForm(StatesGroup):
    message = State()

class StaffReply(StatesGroup):
    replying = State()

# ---------- MENUS ----------

def main_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⚖️ Punishment Appeal", callback_data="punishment")],
            [InlineKeyboardButton(text="✅ Whitelist", callback_data="whitelist")],
            [InlineKeyboardButton(text="🎧 Contact Staff", callback_data="support")],
            [InlineKeyboardButton(text="🛒 Shop", callback_data="shop")]
        ]
    )

def shop_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👑 Rank Shop", callback_data="rank_shop")],
            [InlineKeyboardButton(text="🪙 Coin Shop", callback_data="coin_shop")],
            [InlineKeyboardButton(text="⬅ Back", callback_data="back")]
        ]
    )

# ---------- COMMAND MENU ----------

async def set_commands():

    user_commands = [
        BotCommand(command="start", description="Start bot"),
        BotCommand(command="punishment", description="Punishment appeal"),
        BotCommand(command="whitelist", description="Whitelist request"),
        BotCommand(command="support", description="Contact staff"),
        BotCommand(command="shop", description="Open shop")
    ]

    await bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())

    admin_commands = user_commands + [
        BotCommand(command="broadcast", description="Send broadcast")
    ]

    await bot.set_my_commands(
        admin_commands,
        scope=BotCommandScopeChat(chat_id=ADMIN_ID)
    )

# ---------- START ----------

@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):

    USERS.add(message.from_user.id)

    await state.clear()

    await message.answer(
        "🌙 Welcome to TheFellOmen Bot",
        reply_markup=main_menu()
    )

# ---------- MENU BUTTONS ----------

@dp.callback_query(F.data == "back")
async def back_menu(call: types.CallbackQuery):

    await call.message.edit_text(
        "Main Menu",
        reply_markup=main_menu()
    )

@dp.callback_query(F.data == "shop")
async def shop_menu_open(call: types.CallbackQuery):

    await call.message.edit_text(
        "🛒 Shop Menu",
        reply_markup=shop_menu()
    )

# ---------- PUNISHMENT SYSTEM ----------

@dp.callback_query(F.data == "punishment")
async def punishment_start(call: types.CallbackQuery, state: FSMContext):

    await state.set_state(PunishmentForm.username)

    await call.message.edit_text(
        "⚖️ Punishment Appeal\n\nSend your Minecraft username."
    )

@dp.message(PunishmentForm.username)
async def punishment_username(message: types.Message, state: FSMContext):

    await state.update_data(username=message.text)

    await state.set_state(PunishmentForm.punish_id)

    await message.answer("Send your punishment ID.")

@dp.message(PunishmentForm.punish_id)
async def punishment_id(message: types.Message, state: FSMContext):

    await state.update_data(punish_id=message.text)

    await state.set_state(PunishmentForm.message)

    await message.answer("Explain why you should be unbanned.")

@dp.message(PunishmentForm.message)
async def punishment_finish(message: types.Message, state: FSMContext):

    data = await state.get_data()

    username = data["username"]
    punish_id = data["punish_id"]
    user_message = message.text

    ticket_id = str(uuid.uuid4())[:8]

    TICKETS[ticket_id] = message.from_user.id

    staff_text = (

        f"🎫 <b>Punishment Appeal</b>\n\n"

        f"User: {html.escape(message.from_user.full_name)}\n"
        f"UserID: <code>{message.from_user.id}</code>\n\n"

        f"Username: <b>{html.escape(username)}</b>\n"
        f"Punishment ID: <code>{html.escape(punish_id)}</code>\n\n"

        f"Message:\n{html.escape(user_message)}"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Accept", callback_data=f"accept_{ticket_id}"),
                InlineKeyboardButton(text="❌ Deny", callback_data=f"deny_{ticket_id}")
            ],
            [
                InlineKeyboardButton(text="💬 Reply", callback_data=f"reply_{ticket_id}")
            ]
        ]
    )

    await bot.send_message(
        STAFF_GROUP_ID,
        staff_text,
        reply_markup=keyboard
    )

    await message.answer("✅ Your appeal has been sent to staff.")

    await state.clear()

# ---------- WHITELIST ----------

@dp.callback_query(F.data == "whitelist")
async def whitelist_start(call: types.CallbackQuery, state: FSMContext):

    await state.set_state(WhitelistForm.username)

    await call.message.edit_text("Send your Minecraft username for whitelist.")

@dp.message(WhitelistForm.username)
async def whitelist_finish(message: types.Message, state: FSMContext):

    ticket_id = str(uuid.uuid4())[:8]

    TICKETS[ticket_id] = message.from_user.id

    text = (

        f"✅ <b>Whitelist Request</b>\n\n"

        f"User: {html.escape(message.from_user.full_name)}\n"

        f"UserID: <code>{message.from_user.id}</code>\n\n"

        f"Username: <b>{html.escape(message.text)}</b>"
    )

    await bot.send_message(STAFF_GROUP_ID, text)

    await message.answer("✅ Whitelist request sent.")

    await state.clear()

# ---------- SUPPORT ----------

@dp.callback_query(F.data == "support")
async def support_start(call: types.CallbackQuery, state: FSMContext):

    await state.set_state(SupportForm.message)

    await call.message.edit_text("Send your message to staff.")

@dp.message(SupportForm.message)
async def support_finish(message: types.Message, state: FSMContext):

    ticket_id = str(uuid.uuid4())[:8]

    TICKETS[ticket_id] = message.from_user.id

    text = (

        f"🎧 <b>Support Ticket</b>\n\n"

        f"User: {html.escape(message.from_user.full_name)}\n"

        f"UserID: <code>{message.from_user.id}</code>\n\n"

        f"Message:\n{html.escape(message.text)}"
    )

    await bot.send_message(STAFF_GROUP_ID, text)

    await message.answer("✅ Support message sent.")

    await state.clear()

# ---------- STAFF ACTIONS ----------

@dp.callback_query(F.data.startswith("accept_"))
async def accept_ticket(call: types.CallbackQuery):

    ticket_id = call.data.sp1]

    user_id = TICKETS.get(ticket_id)

    if user_id:
        await bot.send_message(user_id, "✅ Your request was accepted.")

@dp.callback_query(F.data.startswith("deny_"))
async def deny_ticket(call: types.CallbackQuery):

    ticket_id = call.data.split("_")[1]

    user_id = TICKETS.get(ticket_id)

    if user_id:
        await bot.send_message(user_id, "❌ Your request was denied.")

@dp.callback_query(F.data.startswith("reply_"))
async def reply_ticket(call: types.CallbackQuery, state: FSMContext):

    ticket_id = call.data.split("_")[1]

    await state.update_data(ticket=ticket_id)

    await state.set_state(StaffReply.replying)

    await call.message.reply("Send your reply to the user.")

# ---------- STAFF REPLY ----------

@dp.message(StaffReply.replying)
async def staff_reply(message: types.Message, state: FSMContext):

    data = await state.get_data()

    ticket_id = data["ticket"]

    user_id = TICKETS.get(ticket_id)

    if user_id:

        await message.copy_to(user_id)

        await message.reply("✅ Reply sent.")

    await state.clear()

# ---------- BROADCAST ----------

@dp.message(Command("broadcast"))
async def broadcast(message: types.Message):

    if message.from_user.id != ADMIN_ID:
        return

    if not message.reply_to_message:
        await message.reply("Reply to a message to broadcast.")
        return

    sent = 0

    for user in USERS:

        try:
            await message.reply_to_message.copy_to(user)
            sent += 1
        except:
            pass

    await message.reply(f"✅ Broadcast sent to {sent} users.")

# ---------- KEEP ALIVE ----------

@app.route("/")
def home():
    return "Bot running"

# ---------- MAIN ----------

async def main():

    await set_commands()

    threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=PORT),
        daemon=True
    ).start()

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
