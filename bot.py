import os
import uuid
import html
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
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

TICKETS = {}

# ---------------- FLASK KEEP ALIVE ----------------

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running"

def run_web():
    app.run(host="0.0.0.0", port=10000)

# ---------------- STATES ----------------

class PunishmentAppeal(StatesGroup):
    username = State()
    punish_id = State()
    reason = State()
    message = State()

class WhitelistState(StatesGroup):
    username = State()

class SupportState(StatesGroup):
    message = State()

class StaffReply(StatesGroup):
    replying = State()

# ---------------- MENUS ----------------

def main_menu():

    keyboard = InlineKeyboardMarkup(inline_keyboard=[

        [InlineKeyboardButton(text="⚖️ Punishment Appeal", callback_data="punishment")],

        [InlineKeyboardButton(text="✅ Whitelist Request", callback_data="whitelist")],

        [InlineKeyboardButton(text="🎧 Contact Staff", callback_data="support")],

        [InlineKeyboardButton(text="🛒 Shop", callback_data="shop")]

    ])

    return keyboard

# ---------------- START ----------------

@dp.message(Command("start"))
async def start(message: types.Message):

    await message.answer(

        "🌙 به ربات سرور <b>TheFellOmen</b> خوش آمدید.\n\n"
        "از منوی زیر بخش مورد نظر خود را انتخاب کنید:\n\n"
        "⚖️ درخواست بررسی بن\n"
        "✅ درخواست وایت لیست\n"
        "🎧 ارتباط با مدیریت\n"
        "🛒 فروشگاه سرور",

        reply_markup=main_menu()

    )

# ---------------- PUNISHMENT ----------------

@dp.callback_query(F.data == "punishment")
async def punishment(call: types.CallbackQuery, state: FSMContext):

    await call.message.edit_text(

        "⚖️ <b>درخواست بررسی بن</b>\n\n"
        "درخواست خود را در چت به این صورت ارسال کنید:\n\n"
        "Username\n"
        "Punishment ID\n"
        "Reason\n"
        "Message\n\n"
        "مثال:\n"
        "miscapel\n"
        "14231\n"
        "Cheating\n"
        "Please unban me\n\n"
        "ابتدا یوزرنیم ماینکرفت خود را ارسال کنید."

    )

    await state.set_state(PunishmentAppeal.username)
    await call.answer()

# username

@dp.message(PunishmentAppeal.username)
async def punish_username(message: types.Message, state: FSMContext):

    await state.update_data(username=message.text)

    await message.answer(
        "✅ یوزرنیم دریافت شد.\n\n"
        "حالا <b>Punishment ID</b> خود را ارسال کنید."
    )

    await state.set_state(PunishmentAppeal.punish_id)

# punish id

@dp.message(PunishmentAppeal.punish_id)
async def punish_id(message: types.Message, state: FSMContext):

    await state.update_data(punish_id=message.text)

    await message.answer(
        "✅ Punishment ID ثبت شد.\n\n"
        "لطفاً دلیل بن شدن را بنویسید."
    )

    await state.set_state(PunishmentAppeal.reason)

# reason

@dp.message(PunishmentAppeal.reason)
async def punish_reason(message: types.Message, state: FSMContext):

    await state.update_data(reason=message.text)

    await message.answer(
        "لطفاً توضیح کامل درخواست خود را بنویسید."
    )

    await state.set_state(PunishmentAppeal.message)

# final message

@dp.message(PunishmentAppeal.message)
async def punish_final(message: types.Message, state: FSMContext):

    data = await state.get_data()

    username = data["username"]
    punish_id = data["punish_id"]
    reason = data["reason"]
    user_message = message.text

    ticket_id = str(uuid.uuid4())[:8]

    TICKETS[ticket_id] = message.from_user.id

    staff_text = (

        "🚨 <b>Punishment Appeal</b>\n\n"

        f"👤 User: {html.escape(message.from_user.full_name)}\n"
        f"🆔 UserID: <code>{message.from_user.id}</code>\n\n"

        f"🎮 Username: <b>{html.escape(username)}</b>\n"
        f"📌 Punishment ID: <code>{html.escape(punish_id)}</code>\n"
        f"⚠️ Reason: {html.escape(reason)}\n\n"

        f"💬 Message:\n{html.escape(user_message)}"

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

    await bot.send_message(
        STAFF_GROUP_ID,
        staff_text,
        reply_markup=keyboard
    )

    await message.answer(
        "✅ درخواست شما برای تیم مدیریت ارسال شد.\n"
        "پس از بررسی نتیجه برای شما ارسال خواهد شد."
    )

    await state.clear()

# ---------------- WHITELIST ----------------

@dp.callback_query(F.data == "whitelist")
async def whitelist(call: types.CallbackQuery, state: FSMContext):

    await call.message.edit_text(

        "✅ <b>درخواست Whitelist</b>\n\n"
        "برای ورود به سرور باید در لیست سفید قرار بگیرید.\n\n"
        "لطفاً یوزرنیم ماینکرفت خود را ارسال کنید.\n\n"
        "مثال:\n"
        "miscapel"

    )

    await state.set_state(WhitelistState.username)

    await call.answer()

@dp.message(WhitelistState.username)
async def whitelist_send(message: types.Message, state: FSMContext):

    username = message.text

    text = (

        "✅ <b>Whitelist Request</b>\n\n"

        f"👤 User: {message.from_user.full_name}\n"
        f"🆔 ID: <code>{message.from_user.id}</code>\n"
        f"🎮 Username: <b>{username}</b>"

    )

    await bot.send_message(STAFF_GROUP_ID, text)

    await message.answer(
        "✅ درخواست شما برای تیم مدیریت ارسال شد."
    )

    await state.clear()

# ---------------- SUPPORT ----------------

@dp.callback_query(F.data == "support")
async def support(call: types.CallbackQuery, state: FSMContext):

    await call.message.edit_text(

        "🎧 <b>ارتباط با تیم مدیریت</b>\n\n"
        "اگر سوال یا مشکلی دارید پیام خود را ارسال کنید.\n\n"
        "تیم مدیریت در سریع‌ترین زمان پاسخ خواهد داد."

    )

    await state.set_state(SupportState.message)

    await call.answer()

@dp.message(SupportState.message)
async def support_send(message: types.Message, state: FSMContext):

    ticket_id = str(uuid.uuid4())[:8]

    TICKETS[ticket_id] = message.from_user.id

    text = (

        "🎧 <b>Support Ticket</b>\n\n"

        f"👤 User: {message.from_user.full_name}\n"
        f"🆔 ID: <code>{message.from_user.id}</code>\n\n"

        f"💬 Message:\n{message.text}"

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

    await bot.send_message(
        STAFF_GROUP_ID,
        text,
        reply_markup=keyboard
    )

    await message.answer(
        "✅ پیام شما برای تیم مدیریت ارسال شد."
    )

    await state.clear()

# ---------------- SHOP ----------------

@dp.callback_query(F.data == "shop")
async def shop(call: types.CallbackQuery):

    await call.message.edit_text(

        "🛒 <b>فروشگاه سرور</b>\n\n"
        "برای خرید آیتم‌ها به لینک زیر مراجعه کنید:\n\n"
        "store link here"

    )

    await call.answer()

# ---------------- STAFF ACTIONS ----------------

@dp.callback_query(F.data.startswith("accept_"))
async def accept_ticket(call: types.CallbackQuery):

    ticket_id = call.data.split("_")[1]

    user_id = TICKETS.get(ticket_id)

    if user_id:
        await bot.send_message(
            user_id,
            "✅ درخواست شما توسط تیم مدیریت پذیرفته شد."
        )

    await call.answer("Accepted")

@dp.callback_query(F.data.startswith("deny_"))
async def deny_ticket(call: types.CallbackQuery):

    ticket_id = call.data.split("_")[1]

    user_id = TICKETS.get(ticket_id)

    if user_id:
        await bot.send_message(
            user_id,
            "❌ درخواست شما رد شد."
        )

    await call.answer("Denied")

@dp.callback_query(F.data.startswith("reply_"))
async def reply_ticket(call: types.CallbackQuery, state: FSMContext):

    ticket_id = call.data.split("_")[1]

    await state.update_data(ticket=ticket_id)

    await state.set_state(StaffReply.replying)

    await call.message.reply("پیام خود را برای کاربر ارسال کنید.")

    await call.answer()

@dp.message(StaffReply.replying)
async def send_reply(message: types.Message, state: FSMContext):

    data = await state.get_data()

    ticket_id = data["ticket"]

    user_id = TICKETS.get(ticket_id)

    if user_id:

        await bot.send_message(
            user_id,
            f"💬 پاسخ تیم مدیریت:\n\n{message.text}"
        )

    await message.answer("✅ پیام ارسال شد.")

    await state.clear()

# ---------------- MAIN ----------------

async def main():

    await bot.set_my_commands([

        BotCommand(command="start", description="شروع ربات"),
        BotCommand(command="punishment", description="درخواست بررسی بن"),
        BotCommand(command="whitelist", description="درخواست وایت لیست"),
        BotCommand(command="support", description="ارتباط با مدیریت"),
        BotCommand(command="shop", description="فروشگاه")

    ])

    await dp.start_polling(bot)

if __name__ == "__main__":

    threading.Thread(target=run_web).start()

    asyncio.run(main())
