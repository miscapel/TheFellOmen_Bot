import asyncio
import html
import json
import logging
import os
import re
import threading
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path

from aiogram import Bot, Dispatcher, F, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ChatType, ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    BotCommand,
    BotCommandScopeChat,
    BotCommandScopeDefault,
    ChatPermissions,
)
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from dotenv import load_dotenv
from flask import Flask

# -------------------- CONFIG --------------------

logging.basicConfig(level=logging.INFO)
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
STAFF_GROUP_ID = int(os.getenv("STAFF_GROUP_ID"))
ADMIN_ID = int(os.getenv("ADMIN_ID"))
PORT = int(os.getenv("PORT", 10000))

if not BOT_TOKEN or not STAFF_GROUP_ID:
    raise RuntimeError("Missing BOT_TOKEN or STAFF_GROUP_ID")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
app = Flask(__name__)

# -------------------- STATES --------------------

class UserState(StatesGroup):
    punishment = State()
    whitelist = State()
    support = State()

class StaffState(StatesGroup):
    replying = State()

# -------------------- DATABASE --------------------

USERS_FILE = Path("users.json")
WARNS_FILE = Path("warns.json")

USERS = set()
WARNS = {}
TICKETS = {}

def load_users():
    global USERS
    if USERS_FILE.exists():
        USERS = set(json.loads(USERS_FILE.read_text()))

def save_users():
    USERS_FILE.write_text(json.dumps(list(USERS)))

def remember_user(user):
    if user.id not in USERS:
        USERS.add(user.id)
        save_users()

def load_warns():
    global WARNS
    if WARNS_FILE.exists():
        WARNS = json.loads(WARNS_FILE.read_text())

def save_warns():
    WARNS_FILE.write_text(json.dumps(WARNS))

def warn_key(chat_id, user_id):
    return f"{chat_id}:{user_id}"

def add_warn(chat_id, user_id):
    key = warn_key(chat_id, user_id)
    WARNS[key] = WARNS.get(key, 0) + 1
    save_warns()
    return WARNS[key]

def clear_warn(chat_id, user_id):
    key = warn_key(chat_id, user_id)
    if key in WARNS:
        del WARNS[key]
        save_warns()

def get_warn(chat_id, user_id):
    return WARNS.get(warn_key(chat_id, user_id), 0)

# -------------------- KEYBOARDS --------------------

def main_menu():
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="⚖️ Punishment", callback_data="menu_punishment")],
        [types.InlineKeyboardButton(text="✅ Whitelist", callback_data="menu_whitelist")],
        [types.InlineKeyboardButton(text="🎧 Support", callback_data="menu_support")],
        [types.InlineKeyboardButton(text="🛒 Shop", callback_data="menu_shop")]
    ])

def shop_menu():
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="👑 Rank Shop", callback_data="shop_rank")],
        [types.InlineKeyboardButton(text="🪙 Coin Shop", callback_data="shop_coin")],
        [types.InlineKeyboardButton(text="🔙 Back", callback_data="menu_back")]
    ])
# -------------------- COMMAND MENU --------------------

async def set_commands():
    user_cmds = [
        BotCommand(command="start", description="Main Menu"),
        BotCommand(command="punishment", description="Appeal"),
        BotCommand(command="whitelist", description="Whitelist"),
        BotCommand(command="support", description="Support"),
        BotCommand(command="shop", description="Shop"),
    ]

    await bot.set_my_commands(user_cmds, scope=BotCommandScopeDefault())

    admin_cmds = user_cmds + [
        BotCommand(command="broadcast", description="Broadcast"),
        BotCommand(command="warns", description="Check warns"),
        BotCommand(command="clearwarn", description="Clear warns"),
        BotCommand(command="mute", description="Mute"),
        BotCommand(command="unmute", description="Unmute"),
    ]

    await bot.set_my_commands(admin_cmds, scope=BotCommandScopeChat(chat_id=ADMIN_ID))


# -------------------- START --------------------

@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    remember_user(message.from_user)
    await state.clear()
    await message.answer("🌙 Welcome to TheFellOmen", reply_markup=main_menu())

@dp.callback_query(F.data == "menu_back")
async def back_menu(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("🌙 Main Menu", reply_markup=main_menu())

@dp.callback_query(F.data == "menu_punishment")
async def open_punishment(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(UserState.punishment)
    await call.message.edit_text("⚖️ Send your appeal message.")

@dp.callback_query(F.data == "menu_whitelist")
async def open_whitelist(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(UserState.whitelist)
    await call.message.edit_text("✅ Send your Minecraft username.")

@dp.callback_query(F.data == "menu_support")
async def open_support(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(UserState.support)
    await call.message.edit_text("🎧 Send your support message.")

@dp.callback_query(F.data == "menu_shop")
async def open_shop(call: types.CallbackQuery):
    await call.message.edit_text("🛒 Shop Menu", reply_markup=shop_menu())
    # -------------------- TICKETS --------------------

async def send_ticket(message: types.Message, category: str):

    ticket_id = str(uuid.uuid4())[:8]

    TICKETS[ticket_id] = message.from_user.id

    user = message.from_user

    text = (
        f"🎫 <b>New Ticket</b>\n\n"
        f"ID: <code>{ticket_id}</code>\n"
       f"User: {html.escape(user.full_name)}\n"
        f"UserID: <code>{user.id}</code>\n"
        f"Type: {category}"
    )

    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="✅ Accept", callback_data=f"accept_{ticket_id}"),
                types.InlineKeyboardButton(text="❌ Deny", callback_data=f"deny_{ticket_id}")
            ],
            [
                types.InlineKeyboardButton(text="💬 Reply", callback_data=f"reply_{ticket_id}")
            ]
        ]
    )

    await message.copy_to(STAFF_GROUP_I, caption=text, reply_markup=keyboard)

    await message.answer("✅ Your ticket was sent to staff.")
@dp.message(UserState.punishment)
async def punishment_ticket(message: types.Message, state: FSMContext):

    await send_ticket(message, "Punishment Appeal")

    await state.clear()


@dp.message(UserState.whitelist)
async def whitelist_ticket(message: types.Message, state: FSMContext):

    await send_ticket(message, "Whitelist")

    await state.clear()


@dp.message(UserState.support)
async def support_ticket(message: types.Message, state: FSMContext):

    await send_ticket(message, "Support")

    await state.clear()
@dp.callback_query(F.data.startswith("accept_"))
async def accept_ticket(call: types.CallbackQuery):

    ticket_id = call.data.split("_")[1]

    user_id = TICKETS.get(ticket_id)

    if not user_id:
        return

    await bot.send_message(user_id, "✅ Your request was accepted.")

    await call.answer("Accepted")


@dp.callback_query(F.data.startswith("deny_"))
async def deny_ticket(call: types.CallbackQuery):

    ticket_id = call.data.split("_")[1]

    user_id = TICKETS.get(ticket_id)

    if not user_id:
        return

    await bot.send_message(user_id, "❌ Your request was denied.")

    await call.answer("Denied")


@dp.callback_query(F.data.startswith("reply_"))
async def reply_ticket(call: types.CallbackQuery, state: FSMContext):

    ticket_id = call.data.split("_")[1]

    await state.update_data(ticket=ticket_id)

    await state.set_state(StaffState.replying)

    await call.message.reply("Send reply message to user.")

