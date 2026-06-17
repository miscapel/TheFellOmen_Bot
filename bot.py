import os
import asyncio
import threading
from flask import Flask
from aiogram import Bot, Dispatcher, F, types
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

BOT_TOKEN = os.getenv("BOT_TOKEN")
STAFF_GROUP_ID = int(os.getenv("STAFF_GROUP_ID"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ---------------- KEEP ALIVE ----------------
app = Flask(__name__)
@app.route("/")
def home():
    return "Bot Online"

def run_web():
    app.run(host="0.0.0.0", port=10000)

# ---------------- STATES ----------------
class UserState(StatesGroup):
    waiting_data = State()

class StaffReplyState(StatesGroup):
    waiting_reply = State()

# ---------------- MAIN MENU ----------------
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📜 Whitelist")],
        [KeyboardButton(text="🛒 Server Shop")],
        [KeyboardButton(text="⚖️ Punishment Appeal")],
        [KeyboardButton(text="💬 Contact Staff")]
    ],
    resize_keyboard=True
)

# ---------------- SHOP BUTTONS ----------------
shop_buttons = InlineKeyboardMarkup(
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
        "از منوی پایین سرویس مورد نظر خود را انتخاب کنید.",
        reply_markup=main_menu
    )

# ---------------- WHITELIST ----------------
@dp.message(F.text == "📜 Whitelist")
async def whitelist(message: types.Message, state: FSMContext):
    await state.set_state(UserState.waiting_data)
    await state.update_data(section="Whitelist")

    await message.answer(
        "Whitelist Request\n\n"
        "یوزرنیم ماینکرفت خود را ارسال کنید."
    )

# ---------------- SERVER SHOP ----------------
@dp.message(F.text == "🛒 Server Shop")
async def shop(message: types.Message):
    await message.answer(
        "Server Shop\n"
        "نوع خرید خود را انتخاب کنید.",
        reply_markup=shop_buttons
    )

@dp.callback_query(F.data == "rank")
async def rank(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(UserState.waiting_data)
    await state.update_data(section="Rank Shop")

    await callback.message.answer(
        "Rank Shop\n\n"
        "Vip » 49,000 Toman\n"
        "Elite » 100,000 Toman\n"
        "TheFellOmen » 190,000 Toman\n"
        "Sponsor » 250,000 Toman\n"
        "Lover » 400,000 Toman\n\n"
        "نام رنک مورد نظر یا کیت درخواستی خود را ارسال کنید."
    )
    await callback.answer()

@dp.callback_query(F.data == "coin")
async def coin(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(UserState.waiting_data)
    await state.update_data(section="Coin Shop")

    await callback.message.answer(
        "Coin Shop\n\n"
        "50 Coin » 15,000 Toman\n"
        "100 Coins » 30,000 Toman\n"
        "150 Coins » 55,000 Toman\n"
        "200 Coins » 80,000 Toman\n"
        "250 Coins » 150,000 Toman\n\n"
        "مقدار کوین مورد نظر خود را ارسال کنید."
    )
    await callback.answer()

# ---------------- PUNISHMENT ----------------
@dp.message(F.text == "⚖️ Punishment Appeal")
async def punishment(message: types.Message, state: FSMContext):
    await state.set_state(UserState.waiting_data)
    await state.update_data(section="Punishment")

    await message.answer(
        "Punishment Appeal\n\n"
        "اطلاعات زیر را ارسال کنید:\n\n"
        "username\n"
        "Punishment ID\n"
        "Reason\n"
        "Message"
    )

# ---------------- CONTACT ----------------
@dp.message(F.text == "💬 Contact Staff")
async def contact(message: types.Message, state: FSMContext):
    await state.set_state(UserState.waiting_data)
    await state.update_data(section="Contact")

    await message.answer(
        "پیام خود را ارسال کنید.\n"
        "میتوانید متن، عکس یا ویدیو بفرستید."
    )

# ---------------- RECEIVE USER DATA ----------------
@dp.message(UserState.waiting_data)
async def receive_data(message: types.Message, state: FSMContext):

    data = await state.get_data()
    section = data.get("section")
    user_id = message.from_user.id

    caption = (
        f"New Request | {section}\n"
        f"User: {message.from_user.full_name}\n"
        f"ID: {user_id}\n\n"
    )

    if message.text:
        caption += message.text

    if message.photo:
        await bot.send_photo(
            STAFF_GROUP_ID,
            message.photo[-1].file_id,
            caption=caption,
            reply_markup=staff_buttons(user_id)
        )

    elif message.video:
        await bot.send_video(
            STAFF_GROUP_ID,
            message.video.file_id,
            caption=caption,
            reply_markup=staff_buttons(user_id)
        )

    else:
        await bot.send_message(
            STAFF_GROUP_ID,
            caption,
            reply_markup=staff_buttons(user_id)
        )

    await message.answer(
        "✅ درخواست شما ثبت شد.\n"
        "پس از بررسی نتیجه به شما اطلاع داده میشود.",
        reply_markup=main_menu
    )

    await state.clear()

# ---------------- STAFF REPLY ----------------
@dp.callback_query(F.data.startswith("reply_"))
async def staff_reply(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.data.split("_")[1]
    await state.update_data(reply_user=user_id)
    await state.set_state(StaffReplyState.waiting_reply)

    await callback.message.answer("پیام پاسخ خود را ارسال کنید.")
    await callback.answer()

@dp.message(StaffReplyState.waiting_reply)
async def send_reply(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get("reply_user")

    header = "پاسخ جدید از تیم مدیریت:\n\n"

    if message.text:
        await bot.send_message(user_id, header + message.text)
    elif message.photo:
        await bot.send_photo(user_id, message.photo[-1].file_id,
                             caption=header + (message.caption or ""))
    elif message.video:
        await bot.send_video(user_id, message.video.file_id,
                             caption=header + (message.caption or ""))

    await message.answer("✅ پاسخ ارسال شد.")
    await state.clear()

# ---------------- ACCEPT / DENY ----------------
@dp.callback_query(F.data.startswith("accept_"))
async def accept(callback: types.CallbackQuery):
    user_id = callback.data.split("_")[1]
    await bot.send_message(user_id, "✅ درخواست شما تایید شد.")
    await callback.answer("Accepted")

@dp.callback_query(F.data.startswith("deny_"))
async def deny(callback: types.CallbackQuery):
    user_id = callback.data.split("_")[1]
    await bot.send_message(user_id, "❌ درخواست شما رد شد.")
    await callback.answer("Denied")

# ---------------- RUN ----------------
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    asyncio.run(main())
