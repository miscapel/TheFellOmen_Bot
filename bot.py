import asyncio
import json
from datetime import datetime, timedelta
from collections import defaultdict

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup, ChatPermissions
from aiogram.enums import ParseMode

TOKEN = "8975820451:AAEBZjhBGdFNCjnCcvld09oItdJYnkGCsGU"

STAFF_GROUP_ID = -1004332150226
ADMINS = [1256603181]

bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()
router = Router()

# ---------------- USERS DATABASE ----------------

def load_users():
    try:
        with open("users.json", "r") as f:
            return set(json.load(f))
    except:
        return set()

def save_users(users):
    with open("users.json", "w") as f:
        json.dump(list(users), f)

users = load_users()

# ---------------- SECURITY SETTINGS ----------------

WARN_LIMIT_MUTE = 3
WARN_LIMIT_BAN = 5

SPAM_LIMIT = 4
SPAM_INTERVAL = 5

user_warnings = defaultdict(int)
user_messages = defaultdict(list)

BAD_WORDS = ["porn", "sex", "xxx"]

# ---------------- MENU ----------------

def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📜 Whitelist Request")],
            [KeyboardButton(text="💎 Server Shop")],
            [KeyboardButton(text="🆘 Support Ticket")]
        ],
        resize_keyboard=True
    )

# ---------------- START ----------------

@router.message(Command("start"))
async def start(message: Message):

    users.add(message.from_user.id)
    save_users(users)

    await message.answer(
        "<b>👋 Welcome to TheFellOmen Server</b>\n\nUse the menu below to interact with staff.",
        reply_markup=main_menu()
    )

# ---------------- WHITELIST ----------------

@router.message(lambda m: m.text == "📜 Whitelist Request")
async def whitelist(message: Message):

    await message.answer(
        "<b>📜 Whitelist Request</b>\n\nSend your Minecraft username and description."
    )

# ---------------- SHOP ----------------

@router.message(lambda m: m.text == "💎 Server Shop")
async def shop(message: Message):

    await message.answer(
        "<b>💎 Server Shop</b>\nStore link:\nhttps://your-store-link.com"
    )

# ---------------- SUPPORT ----------------

@router.message(lambda m: m.text == "🆘 Support Ticket")
async def support(message: Message):

    await message.answer(
        "<b>🆘 Support</b>\nSend your problem and staff will reply."
    )

# ---------------- TICKET SYSTEM ----------------

@router.message(lambda m: m.chat.type == "private")
async def ticket_forward(message: Message):

    if message.text and message.text.startswith("/"):
        return

    msg = (
        "<b>📩 New Ticket</b>\n\n"
        f"<b>User:</b> {message.from_user.full_name}\n"
        f"<b>ID:</b> <code>{message.from_user.id}</code>\n\n"
        f"<b>Message:</b>\n{message.text}"
    )

    await bot.send_message(STAFF_GROUP_ID, msg)

    await message.answer("✅ <b>Your ticket has been sent to staff.</b>")

# ---------------- ANNOUNCEMENT ----------------

@router.message(Command("announce"))
async def announce(message: Message):

    if message.from_user.id not in ADMINS:
        return

    text = message.text.replace("/announce", "").strip()

    if not text:
        await message.answer("Send message after command.")
        return

    sent = 0

    for user_id in users:
        try:
            await bot.send_message(
                user_id,
                f"<b>📢 Server Announcement</b>\n\n{text}"
            )
            sent += 1
        except:
            pass

    await message.answer(f"✅ Sent to {sent} users")

# ---------------- GROUP SECURITY ----------------

@router.message(lambda m: m.chat.type in ["group", "supergroup"])
async def security(message: Message):

    user_id = message.from_user.id
    now = datetime.now()

    user_messages[user_id] = [
        t for t in user_messages[user_id]
        if (now - t).seconds < SPAM_INTERVAL
    ]

    user_messages[user_id].append(now)

    if len(user_messages[user_id]) > SPAM_LIMIT:

        user_warnings[user_id] += 1

        await message.delete()

        await message.answer(
            f"⚠️ <b>{message.from_user.full_name}</b> spam detected\nWarn: {user_warnings[user_id]}"
        )

    if message.photo or message.video or message.animation:

        user_warnings[user_id] += 1

        await message.delete()

        await message.answer(
            f"🚫 Media not allowed\nWarn: {user_warnings[user_id]}"
        )

    if message.text:

        txt = message.text.lower()

        if any(word in txt for word in BAD_WORDS):

            user_warnings[user_id] += 1

            await message.delete()

            await message.answer(
                f"🚫 Inappropriate message\nWarn: {user_warnings[user_id]}"
            )

    if user_warnings[user_id] == WARN_LIMIT_MUTE:

        until = datetime.now() + timedelta(minutes=10)

        await message.chat.restrict(
            user_id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until
        )

        await message.answer(
            f"🔇 {message.from_user.full_name} muted 10 minutes"
        )

    if user_warnings[user_id] >= WARN_LIMIT_BAN:

        await bot.ban_chat_member(message.chat.id, user_id)

        await message.answer(
            f"⛔ {message.from_user.full_name} banned"
        )

# ---------------- MAIN ----------------

async def main():

    await bot.delete_webhook(drop_pending_updates=True)

    dp.include_router(router)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
