import os
import asyncio
import threading
from flask import Flask
from aiogram import Bot, Dispatcher, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

BOT_TOKEN = os.getenv("BOT_TOKEN")
STAFF_GROUP_ID = int(os.getenv("STAFF_GROUP_ID"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

active_tickets = {}

# ---------------- KEEP ALIVE ----------------
app = Flask(__name__)
@app.route("/")
def home():
    return "Bot Online"

def run_web():
    app.run(host="0.0.0.0", port=10000)

# ---------------- STATES ----------------
class TicketState(StatesGroup):
    waiting_message = State()

class PunishmentState(StatesGroup):
    username = State()
    punishment_id = State()
    reason = State()
    message = State()

class StaffReply(StatesGroup):
    waiting = State()

# ---------------- MAIN MENU ----------------
def main_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📜 Whitelist", callback_data="whitelist")],
            [InlineKeyboardButton(text="🛒 Server Shop", callback_data="shop")],
            [InlineKeyboardButton(text="⚖️ Punishment Appeal", callback_data="punish")],
            [InlineKeyboardButton(text="💬 Contact Staff", callback_data="contact")]
        ]
    )

# ---------------- SHOP MENU ----------------
shop_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="💎 Rank", callback_data="rank"),
            InlineKeyboardButton(text="🪙 Coin", callback_data="coin")
        ]
    ]
)

# ---------------- STAFF BUTTONS ----------------
def staff_buttons(user_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Accept", callback_data=f"accept_{user_id}"),
                InlineKeyboardButton(text="❌ Deny", callback_data=f"deny_{user_id}"),
                InlineKeyboardButton(text="💬 Reply", callback_data=f"reply_{user_id}")
            ]
        ]
    )

# ---------------- START ----------------
@dp.message(Command("start"))
async def start(message: types.Message):

    await message.answer(
        "Welcome to TheFellOmen Services\n"
        "بخش مورد نظر را انتخاب کنید.",
        reply_markup=main_menu()
    )

# ---------------- TICKET CHECK ----------------
async def check_ticket(user_id, message):

    if user_id in active_tickets:
        await message.answer(
            "شما یک درخواست فعال دارید.\n"
            "لطفا تا بررسی آن صبر کنید."
        )
        return True

    return False

# ---------------- WHITELIST ----------------
@dp.callback_query(F.data == "whitelist")
async def whitelist(callback: types.CallbackQuery, state: FSMContext):

    if await check_ticket(callback.from_user.id, callback.message):
        return

    active_tickets[callback.from_user.id] = True

    await state.set_state(TicketState.waiting_message)
    await state.update_data(section="Whitelist")

    await callback.message.answer(
        "Whitelist Request\n\n"
        "یوزرنیم ماینکرفت خود را ارسال کنید."
    )

# ---------------- SHOP ----------------
@dp.callback_query(F.data == "shop")
async def shop(callback: types.CallbackQuery):
    await callback.message.answer(
        "Server Shop\n"
        "نوع خرید را انتخاب کنید.",
        reply_markup=shop_menu
    )

# ---------------- RANK ----------------
@dp.callback_query(F.data == "rank")
async def rank(callback: types.CallbackQuery, state: FSMContext):

    if await check_ticket(callback.from_user.id, callback.message):
        return

    active_tickets[callback.from_user.id] = True

    await state.set_state(TicketState.waiting_message)
    await state.update_data(section="Rank")

    await callback.message.answer(
        "Rank Shop\n\n"
        "Vip » 49,000 Toman\n"
        "Elite » 100,000 Toman\n"
        "TheFellOmen » 190,000 Toman\n"
        "Sponsor » 250,000 Toman\n"
        "Lover » 400,000 Toman\n\n"
        "رنک یا کیت مورد نظر خود را بنویسید."
    )

# ---------------- COIN ----------------
@dp.callback_query(F.data == "coin")
async def coin(callback: types.CallbackQuery, state: FSMContext):

    if await check_ticket(callback.from_user.id, callback.message):
        return

    active_tickets[callback.from_user.id] = True

    await state.set_state(TicketState.waiting_message)
    await state.update_data(section="Coin")

    await callback.message.answer(
        "Coin Shop\n\n"
        "50 Coin » 15,000 Toman\n"
        "100 Coins » 30,000 Toman\n"
        "150 Coins » 55,000 Toman\n"
        "200 Coins » 80,000 Toman\n"
        "250 Coins » 150,000 Toman\n\n"
        "مقدار کوین مورد نظر را ارسال کنید."
    )

# ---------------- CONTACT ----------------
@dp.callback_query(F.data == "contact")
async def contact(callback: types.CallbackQuery, state: FSMContext):

    if await check_ticket(callback.from_user.id, callback.message):
        return

    active_tickets[callback.from_user.id] = True

    await state.set_state(TicketState.waiting_message)
    await state.update_data(section="Contact")

    await callback.message.answer(
        "پیام خود را برای استاف ارسال کنید."
    )

# ---------------- PUNISHMENT STEP 1 ----------------
@dp.callback_query(F.data == "punish")
async def punish(callback: types.CallbackQuery, state: FSMContext):

    if await check_ticket(callback.from_user.id, callback.message):
        return

    active_tickets[callback.from_user.id] = True

    await state.set_state(PunishmentState.username)

    await callback.message.answer(
        "مرحله 1\n"
        "Username خود را ارسال کنید."
    )

# step 2
@dp.message(PunishmentState.username)
async def punish_user(message: types.Message, state: FSMContext):

    await state.update_data(username=message.text)

    await state.set_state(PunishmentState.punishment_id)

    await message.answer("مرحله 2\nPunishment ID را ارسال کنید.")

# step 3
@dp.message(PunishmentState.punishment_id)
async def punish_id(message: types.Message, state: FSMContext):

    await state.update_data(pid=message.text)

    await state.set_state(PunishmentState.reason)

    await message.answer("مرحله 3\nReason را ارسال کنید.")

# step 4
@dp.message(PunishmentState.reason)
async def punish_reason(message: types.Message, state: FSMContext):

    await state.update_data(reason=message.text)

    await state.set_state(PunishmentState.message)

    await message.answer("مرحله 4\nتوضیحات خود را ارسال کنید.")

# finish
@dp.message(PunishmentState.message)
async def punish_finish(message: types.Message, state: FSMContext):

    data = await state.get_data()

    caption = (
        "Punishment Appeal\n\n"
        f"Username: {data['username']}\n"
        f"Punishment ID: {data['pid']}\n"
        f"Reason: {data['reason']}\n"
        f"Message: {message.text}\n\n"
        f"User ID: {message.from_user.id}"
    )

    await bot.send_message(
        STAFF_GROUP_ID,
        caption,
        reply_markup=staff_buttons(message.from_user.id)
    )

    await message.answer("درخواست شما ثبت شد.")

    await state.clear()

# ---------------- RECEIVE TICKETS ----------------
@dp.message(TicketState.waiting_message)
async def receive_ticket(message: types.Message, state: FSMContext):

    data = await state.get_data()
    section = data["section"]

    caption = (
        f"New Ticket | {section}\n"
        f"User: {message.from_user.full_name}\n"
        f"ID: {message.from_user.id}\n\n"
    )

    if message.text:
        caption += message.text

    if message.photo:
        await bot.send_photo(
            STAFF_GROUP_ID,
            message.photo[-1].file_id,
            caption=caption,
            reply_markup=staff_buttons(message.from_user.id)
        )
    else:
        await bot.send_message(
            STAFF_GROUP_ID,
            caption,
            reply_markup=staff_buttons(message.from_user.id)
        )

    await message.answer("درخواست شما ارسال شد.")

    await state.clear()

# ---------------- ACCEPT ----------------
@dp.callback_query(F.data.startswith("accept_"))
async def accept(callback: types.CallbackQuery):

    user_id = int(callback.data.split("_")[1])

    active_tickets.pop(user_id, None)

    await bot.send_message(user_id, "✅ درخواست شما تایید شد.")
    await callback.answer("Accepted")

# ---------------- DENY ----------------
@dp.callback_query(F.data.startswith("deny_"))
async def deny(callback: types.CallbackQuery):

    user_id = int(callback.data.split("_")[1])

    active_tickets.pop(user_id, None)

    await bot.send_message(user_id, "❌ درخواست شما رد شد.")
    await callback.answer("Denied")

# ---------------- REPLY ----------------
@dp.callback_query(F.data.startswith("reply_"))
async def reply(callback: types.CallbackQuery, state: FSMContext):

    user_id = callback.data.split("_")[1]

    await state.update_data(user=user_id)

    await state.set_state(StaffReply.waiting)

    await callback.message.answer("پیام پاسخ را ارسال کنید.")

# send reply
@dp.message(StaffReply.waiting)
async def send_reply(message: types.Message, state: FSMContext):

    data = await state.get_data()
    user_id = data["user"]

    await bot.send_message(
        user_id,
        "پاسخ جدید از تیم مدیریت:\n\n" + message.text
    )

    await message.answer("پاسخ ارسال شد.")

    await state.clear()

# ---------------- RUN ----------------
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    asyncio.run(main())
