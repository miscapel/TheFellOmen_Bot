import asyncio
import os
import logging
import random
import string
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

# ================= CONFIG =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
STAFF_GROUP_ID = -1004332150226

COOLDOWN_SECONDS = 30

# ================= LOGGING =================

logging.basicConfig(level=logging.INFO)

# ================= BOT INIT =================

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher(storage=MemoryStorage())

# ================= DATABASE (Memory) =================

active_tickets = {}
cooldowns = {}

# ================= UTILITIES =================

def generate_ticket_id(prefix="T"):
    return prefix + ''.join(random.choices(string.digits, k=5))

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M")

def is_on_cooldown(user_id):
    if user_id not in cooldowns:
        return False
    return datetime.now() < cooldowns[user_id]

def set_cooldown(user_id):
    cooldowns[user_id] = datetime.now() + timedelta(seconds=COOLDOWN_SECONDS)

async def is_staff(user_id):
    member = await bot.get_chat_member(STAFF_GROUP_ID, user_id)
    return member.status in ["administrator", "creator"]

def main_menu():
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="⚖️ Punishment Appeal")],
            [types.KeyboardButton(text="📜 Whitelist")],
            [types.KeyboardButton(text="🆘 Contact Staff")],
            [types.KeyboardButton(text="💎 Shop")]
        ],
        resize_keyboard=True
    )

def staff_buttons(ticket_id, user_id):
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="✅ Accept", callback_data=f"accept|{ticket_id}|{user_id}"),
                types.InlineKeyboardButton(text="❌ Deny", callback_data=f"deny|{ticket_id}|{user_id}")
            ],
            [
                types.InlineKeyboardButton(text="💬 Reply", callback_data=f"reply|{ticket_id}|{user_id}"),
                types.InlineKeyboardButton(text="🔒 Close", callback_data=f"close|{ticket_id}|{user_id}")
            ]
        ]
    )

# ================= STATES =================

class Appeal(StatesGroup):
    username = State()
    pid = State()
    reason = State()
    message = State()

class Whitelist(StatesGroup):
    username = State()
    message = State()

class Contact(StatesGroup):
    reason = State()
    message = State()

# ================= START =================

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "🔥 Welcome to TheFellOmen Ultimate Staff Bot\n\n"
        "از منوی زیر انتخاب کنید.",
        reply_markup=main_menu()
    )

# ================= ANTI MULTI TICKET =================

def has_active_ticket(user_id):
    return user_id in active_tickets

def create_ticket(user_id, ticket_id):
    active_tickets[user_id] = ticket_id

def close_ticket(user_id):
    if user_id in active_tickets:
        del active_tickets[user_id]

# ================= PUNISHMENT APPEAL =================

@dp.message(F.text == "⚖️ Punishment Appeal")
async def appeal_start(message: types.Message, state: FSMContext):

    if has_active_ticket(message.from_user.id):
        await message.answer("❌ شما یک تیکت باز دارید.")
        return

    await state.set_state(Appeal.username)
    await message.answer("🎮 یوزرنیم ماینکرفت خود را وارد کنید.")

@dp.message(Appeal.username)
async def appeal_username(message: types.Message, state: FSMContext):
    await state.update_data(username=message.text)
    await state.set_state(Appeal.pid)
    await message.answer("🆔 Punishment ID را وارد کنید.")

@dp.message(Appeal.pid)
async def appeal_pid(message: types.Message, state: FSMContext):
    await state.update_data(pid=message.text)
    await state.set_state(Appeal.reason)
    await message.answer("📄 دلیل درخواست را بنویسید.")

@dp.message(Appeal.reason)
async def appeal_reason(message: types.Message, state: FSMContext):
    await state.update_data(reason=message.text)
    await state.set_state(Appeal.message)
    await message.answer("✍️ توضیحات کامل را ارسال کنید (متن/عکس/ویدیو).")

@dp.message(Appeal.message)
async def appeal_finish(message: types.Message, state: FSMContext):

    if is_on_cooldown(message.from_user.id):
        await message.answer("⏳ لطفا کمی صبر کنید.")
        return

    data = await state.get_data()

    ticket_id = generate_ticket_id("A")
    create_ticket(message.from_user.id, ticket_id)
    set_cooldown(message.from_user.id)

    text = f"""
━━━━━━━━━━━━━━━━━━
⚖️ <b>Punishment Appeal</b>

👤 Username: {data['username']}
🆔 User ID: {message.from_user.id}

📌 Punishment ID: {data['pid']}
📄 Reason: {data['reason']}

🕒 Time: {now()}
🎫 Ticket: #{ticket_id}
━━━━━━━━━━━━━━━━━━
"""

    if message.photo:
        await bot.send_photo(STAFF_GROUP_ID, message.photo[-1].file_id,
                             caption=text + f"\n💬 Message:\n{message.caption}",
                             reply_markup=staff_buttons(ticket_id, message.from_user.id))
    elif message.video:
        await bot.send_video(STAFF_GROUP_ID, message.video.file_id,
                             caption=text + f"\n💬 Message:\n{message.caption}",
                             reply_markup=staff_buttons(ticket_id, message.from_user.id))
    else:
        await bot.send_message(STAFF_GROUP_ID,
                               text + f"\n💬 Message:\n{message.text}",
                               reply_markup=staff_buttons(ticket_id, message.from_user.id))

    await message.answer("✅ درخواست شما ارسال شد.", reply_markup=main_menu())
    await state.clear()

# ================= STAFF ACTIONS =================

@dp.callback_query(F.data.startswith(("accept","deny","close")))
async def staff_action(callback: types.CallbackQuery):

    action, ticket_id, user_id = callback.data.split("|")
    user_id = int(user_id)

    if not await is_staff(callback.from_user.id):
        await callback.answer("⛔ شما ادمین نیستید.", show_alert=True)
        return

    if action == "accept":
        await bot.send_message(user_id, f"✅ تیکت #{ticket_id} تایید شد.")
    elif action == "deny":
        await bot.send_message(user_id, f"❌ تیکت #{ticket_id} رد شد.")
    elif action == "close":
        close_ticket(user_id)
        await bot.send_message(user_id, f"🔒 تیکت #{ticket_id} بسته شد.")

    await callback.answer("✅ انجام شد.")

# ================= RUN =================

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
