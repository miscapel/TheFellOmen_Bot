import asyncio
import os
import random
import string
import threading
import re
import html
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
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    threading.Thread(target=run).start()

# ---------------- TOOLS ----------------

def safe(text):
    if text is None:
        return "None"
    return html.escape(str(text))

def ticket_id():
    return "TK-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M")

def get_username(user: types.User):
    if user.username:
        return f"@{user.username}"
    return f"{user.full_name} | ID: {user.id}"

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

def ticket_buttons(ticket):
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="Accept", callback_data=f"accept:{ticket}"),
                types.InlineKeyboardButton(text="Deny", callback_data=f"deny:{ticket}")
            ],
            [
                types.InlineKeyboardButton(text="Close", callback_data=f"close:{ticket}")
            ]
        ]
    )

def extract_ticket_from_message(message: types.Message):
    """
    برای اینکه استف بتواند روی پیام اصلی تیکت یا پیام‌های بعدی کاربر Reply کند.
    """
    text = message.text or message.caption or ""

    if "Ticket:" in text:
        return text.split("Ticket:")[1].strip().split()[0]

    match = re.search(r"TK-[A-Z0-9]{6}", text)
    if match:
        return match.group(0)

    return None

async def send_to_staff(ticket, message: types.Message):
    header = f"👤 Ticket: {ticket}\nFrom: {safe(get_username(message.from_user))}\n\n"

    if message.text:
        await bot.send_message(STAFF_GROUP_ID, header + safe(message.text))

    elif message.photo:
        await bot.send_photo(
            STAFF_GROUP_ID,
            message.photo[-1].file_id,
            caption=header + safe(message.caption or "")
        )

    elif message.video:
        await bot.send_video(
            STAFF_GROUP_ID,
            message.video.file_id,
            caption=header + safe(message.caption or "")
        )

    elif message.document:
        await bot.send_document(
            STAFF_GROUP_ID,
            message.document.file_id,
            caption=header + safe(message.caption or "")
        )

    elif message.sticker:
        await bot.send_message(STAFF_GROUP_ID, header + "Sticker:")
        await bot.send_sticker(STAFF_GROUP_ID, message.sticker.file_id)

async def send_to_user(user_id, message: types.Message):
    prefix = "👮 پاسخ استف\n\n"

    if message.text:
        await bot.send_message(user_id, prefix + safe(message.text))

    elif message.photo:
        await bot.send_photo(
            user_id,
            message.photo[-1].file_id,
            caption=prefix + safe(message.caption or "")
        )

    elif message.video:
        await bot.send_video(
            user_id,
            message.video.file_id,
            caption=prefix + safe(message.caption or "")
        )

    elif message.document:
        await bot.send_document(
            user_id,
            message.document.file_id,
            caption=prefix + safe(message.caption or "")
        )

    elif message.sticker:
        await bot.send_message(user_id, prefix)
        await bot.send_sticker(user_id, message.sticker.file_id)

# ---------------- STATES ----------------

class Punish(StatesGroup):
    username = State()
    pid = State()
    reason = State()
    explain = State()

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
async def start(message: types.Message):
    await message.answer(
        """
🎮 به ربات پشتیبانی سرور خوش آمدید

برای ارتباط با استف از دکمه‌ها استفاده کنید.
""",
        reply_markup=menu()
    )

# ---------------- PUNISHMENT APPEAL ----------------

@dp.message(F.text == "🚫 Punishment Appeal")
async def punish_start(message: types.Message, state: FSMContext):

    if message.from_user.id in user_ticket:
        await message.answer("⚠️ شما یک تیکت باز دارید. اول باید همان تیکت بسته شود.")
        return

    await state.set_state(Punish.username)

    await message.answer(
        """
🚫 Punishment Appeal

لطفا یوزرنیم ماینکرافت خود را وارد کنید.

مثال:
Steve
"""
    )

@dp.message(Punish.username)
async def punish_username(message: types.Message, state: FSMContext):

    await state.update_data(username=message.text)

    await state.set_state(Punish.pid)

    await message.answer(
        """
لطفا Punishment ID یا همان ID بن/میوت خود را وارد کنید.

اگر ID ندارید بنویسید:
ندارم
"""
    )

@dp.message(Punish.pid)
async def punish_pid(message: types.Message, state: FSMContext):

    await state.update_data(pid=message.text)

    await state.set_state(Punish.reason)

    await message.answer(
        """
Reason بن/میوت خود را بنویسید.

مثال:
Cheating
"""
    )

@dp.message(Punish.reason)
async def punish_reason(message: types.Message, state: FSMContext):

    await state.update_data(reason=message.text)

    await state.set_state(Punish.explain)

    await message.answer(
        """
توضیحات کامل خود را بنویسید.

مثلا توضیح دهید چرا فکر می‌کنید Punishment اشتباه بوده یا چرا باید برداشته شود.
"""
    )

@dp.message(Punish.explain)
async def punish_create_ticket(message: types.Message, state: FSMContext):

    data = await state.get_data()

    ticket = ticket_id()

    tickets[ticket] = {
        "type": "Punishment Appeal",
        "user": message.from_user.id,
        "messages": 0,
        "status": "open"
    }

    user_ticket[message.from_user.id] = ticket

    text = f"""
🚫 Punishment Appeal

Telegram: {safe(get_username(message.from_user))}
Minecraft Username: {safe(data.get("username"))}
Punishment ID: {safe(data.get("pid"))}
Reason: {safe(data.get("reason"))}
Explain: {safe(message.text)}

Time: {now()}
Messages: 0
Ticket: {ticket}
"""

    await bot.send_message(
        STAFF_GROUP_ID,
        text,
        reply_markup=ticket_buttons(ticket)
    )

    await message.answer(
        """
✅ درخواست Punishment Appeal شما ارسال شد.

لطفا منتظر پاسخ استف باشید.
اگر نیاز بود می‌توانید همینجا پیام، عکس، ویدیو یا فایل ارسال کنید.
"""
    )

    await state.clear()

# ---------------- WHITELIST ----------------

@dp.message(F.text == "📜 Whitelist Request")
async def wl_start(message: types.Message, state: FSMContext):

    await state.set_state(Whitelist.username)

    await message.answer("لطفا یوزری که می‌خواهید وایت لیست شود را در چت بنویسید.")

@dp.message(Whitelist.username)
async def wl_send(message: types.Message, state: FSMContext):

    username = message.text

    text = f"""
Whitelist
Username: {safe(username)}
Telegram: {safe(get_username(message.from_user))}
Time: {now()}
Messages: 0
"""

    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="Accept", callback_data=f"wl_accept:{message.from_user.id}"),
                types.InlineKeyboardButton(text="Deny", callback_data=f"wl_deny:{message.from_user.id}")
            ]
        ]
    )

    await bot.send_message(STAFF_GROUP_ID, text, reply_markup=kb)

    await message.answer("✅ درخواست وایت لیست ارسال شد")

    await state.clear()

# ---------------- CONTACT ----------------

@dp.message(F.text == "👨‍💻 Contact Staff")
async def contact_start(message: types.Message, state: FSMContext):

    if message.from_user.id in user_ticket:
        await message.answer("⚠️ شما یک تیکت باز دارید.")
        return

    await state.set_state(Contact.reason)

    await message.answer("Reason را بنویسید.")

@dp.message(Contact.reason)
async def contact_create(message: types.Message, state: FSMContext):

    ticket = ticket_id()

    tickets[ticket] = {
        "type": "Contact Staff",
        "user": message.from_user.id,
        "messages": 0,
        "status": "open"
    }

    user_ticket[message.from_user.id] = ticket

    text = f"""
👨‍💻 Contact Staff

Username: {safe(get_username(message.from_user))}
Reason: {safe(message.text)}
Time: {now()}
Messages: 0
Ticket: {ticket}
"""

    await bot.send_message(
        STAFF_GROUP_ID,
        text,
        reply_markup=ticket_buttons(ticket)
    )

    await message.answer("✅ تیکت ساخته شد. منتظر پاسخ استف باشید.")

    await state.clear()

# ---------------- SHOP ----------------

@dp.message(F.text == "💎 Server Shop")
async def shop(message: types.Message):

    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="Rank", callback_data="shop_rank")],
            [types.InlineKeyboardButton(text="Coin", callback_data="shop_coin")]
        ]
    )

    await message.answer("💎 بخش فروشگاه سرور", reply_markup=kb)

# ---------------- RANK SHOP ----------------

@dp.callback_query(F.data == "shop_rank")
async def rank_shop(callback: types.CallbackQuery, state: FSMContext):

    if callback.from_user.id in user_ticket:
        await callback.message.answer("⚠️ شما یک تیکت باز دارید. اول باید همان تیکت بسته شود.")
        await callback.answer()
        return

    await callback.message.answer(
        """
Rank Shop

Vip » 49,000 Toman
Elite » 100,000 Toman
TheFellOmen » 190,000 Toman
Sponsor » 250,000 Toman
Lover » 400,000 Toman

اگر فقط نیاز به کیت رنک دارید
رنک و کیت مورد نظر را بنویسید.

مثلا:
کیت رنک الایت
"""
    )

    await state.set_state(ShopRank.text)
    await callback.answer()

@dp.message(ShopRank.text)
async def rank_ticket(message: types.Message, state: FSMContext):

    ticket = ticket_id()

    tickets[ticket] = {
        "type": "Rank Shop",
        "user": message.from_user.id,
        "messages": 0,
        "status": "open"
    }

    user_ticket[message.from_user.id] = ticket

    text = f"""
💎 Rank Shop

Username: {safe(get_username(message.from_user))}
Request: {safe(message.text)}
Time: {now()}
Messages: 0
Ticket: {ticket}
"""

    await bot.send_message(
        STAFF_GROUP_ID,
        text,
        reply_markup=ticket_buttons(ticket)
    )

    await message.answer("✅ درخواست رنک ارسال شد. منتظر پاسخ استف باشید.")

    await state.clear()

# ---------------- COIN SHOP ----------------

@dp.callback_query(F.data == "shop_coin")
async def coin_shop(callback: types.CallbackQuery, state: FSMContext):

    if callback.from_user.id in user_ticket:
        await callback.message.answer("⚠️ شما یک تیکت باز دارید. اول باید همان تیکت بسته شود.")
        await callback.answer()
        return

    await callback.message.answer(
        """
Coin Shop

50 Coin » 15,000 Toman
100 Coins » 30,000 Toman
150 Coins » 55,000 Toman
200 Coins » 80,000 Toman
250 Coins » 150,000 Toman

اگر مقدار بیشتری میخواهید مقدار را در چت بنویسید.
"""
    )

    await state.set_state(ShopCoin.text)
    await callback.answer()

@dp.message(ShopCoin.text)
async def coin_ticket(message: types.Message, state: FSMContext):

    ticket = ticket_id()

    tickets[ticket] = {
        "type": "Coin Shop",
        "user": message.from_user.id,
        "messages": 0,
        "status": "open"
    }

    user_ticket[message.from_user.id] = ticket

    text = f"""
🪙 Coin Shop

Username: {safe(get_username(message.from_user))}
Request: {safe(message.text)}
Time: {now()}
Messages: 0
Ticket: {ticket}
"""

    await bot.send_message(
        STAFF_GROUP_ID,
        text,
        reply_markup=ticket_buttons(ticket)
    )

    await message.answer("✅ درخواست کوین ارسال شد. منتظر پاسخ استف باشید.")

    await state.clear()

# ---------------- USER → STAFF ----------------

@dp.message(F.chat.type == "private")
async def user_messages(message: types.Message):

    uid = message.from_user.id

    if uid not in user_ticket:
        return

    ticket = user_ticket[uid]

    if ticket not in tickets:
        return

    if tickets[ticket]["status"] != "open":
        return

    tickets[ticket]["messages"] += 1

    await send_to_staff(ticket, message)

# ---------------- STAFF → USER ----------------

@dp.message(F.chat.id == STAFF_GROUP_ID)
async def staff_reply(message: types.Message):

    if not message.reply_to_message:
        return

    ticket = extract_ticket_from_message(message.reply_to_message)

    if not ticket:
        return

    if ticket not in tickets:
        return

    if tickets[ticket]["status"] != "open":
        await message.reply("⚠️ این تیکت بسته شده است.")
        return

    user = tickets[ticket]["user"]

    await send_to_user(user, message)

    tickets[ticket]["messages"] += 1

# ---------------- ACCEPT / DENY TICKETS ----------------

@dp.callback_query(F.data.startswith("accept:"))
async def accept_ticket(callback: types.CallbackQuery):

    ticket = callback.data.split(":")[1]

    if ticket not in tickets:
        await callback.answer("Ticket not found", show_alert=True)
        return

    if tickets[ticket]["status"] != "open":
        await callback.answer("Ticket is closed", show_alert=True)
        return

    user = tickets[ticket]["user"]

    await bot.send_message(
        user,
        f"✅ تیکت شما توسط استف قبول شد.\n\nTicket: {ticket}"
    )

    await callback.answer("Accepted")

@dp.callback_query(F.data.startswith("deny:"))
async def deny_ticket(callback: types.CallbackQuery):

    ticket = callback.data.split(":")[1]

    if ticket not in tickets:
        await callback.answer("Ticket not found", show_alert=True)
        return

    user = tickets[ticket]["user"]

    tickets[ticket]["status"] = "closed"
    user_ticket.pop(user, None)

    await bot.send_message(
        user,
        f"❌ تیکت شما توسط استف رد شد.\n\nTicket: {ticket}"
    )

    await callback.answer("Denied and Closed")

# ---------------- WHITELIST ACCEPT / DENY ----------------

@dp.callback_query(F.data.startswith("wl_accept"))
async def wl_accept(callback: types.CallbackQuery):

    uid = int(callback.data.split(":")[1])

    await bot.send_message(uid, "✅ درخواست وایت لیست شما قبول شد.")

    await callback.answer("Accepted")

@dp.callback_query(F.data.startswith("wl_deny"))
async def wl_deny(callback: types.CallbackQuery):

    uid = int(callback.data.split(":")[1])

    await bot.send_message(uid, "❌ درخواست وایت لیست شما رد شد.")

    await callback.answer("Denied")

# ---------------- CLOSE ----------------

@dp.callback_query(F.data.startswith("close:"))
async def close_ticket(callback: types.CallbackQuery):

    ticket = callback.data.split(":")[1]

    if ticket not in tickets:
        await callback.answer("Ticket not found", show_alert=True)
        return

    if tickets[ticket]["status"] == "closed":
        await callback.answer("Already closed", show_alert=True)
        return

    tickets[ticket]["status"] = "closed"

    user = tickets[ticket]["user"]

    user_ticket.pop(user, None)

    await bot.send_message(user, f"🔒 تیکت شما بسته شد.\n\nTicket: {ticket}")

    await callback.answer("Ticket Closed")

# ---------------- MAIN ----------------

async def main():

    keep_alive()

    await bot.delete_webhook(drop_pending_updates=True)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
