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

# ---------------- CONFIG ----------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
STAFF_GROUP_ID = int(os.getenv("STAFF_GROUP_ID"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ---------------- KEEP ALIVE ----------------
app = Flask(__name__)
@app.route("/")
def home():
    return "Bot is running"

def run_web():
    app.run(host="0.0.0.0", port=10000)

# ---------------- STATES ----------------
class UserState(StatesGroup):
    waiting_data = State()

# ---------------- MAIN MENU ----------------
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Whitelist")],
        [KeyboardButton(text="Server Shop")],
        [KeyboardButton(text="Punishment Appeal")],
        [KeyboardButton(text="Contact Staff")]
    ],
    resize_keyboard=True
)

# ---------------- SHOP BUTTONS ----------------
shop_buttons = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Rank", callback_data="rank_shop")],
    [InlineKeyboardButton(text="Coin", callback_data="coin_shop")]
])

# ---------------- STAFF ACTION BUTTONS ----------------
def staff_buttons(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Accept", callback_data=f"accept_{user_id}"),
            InlineKeyboardButton(text="❌ Deny", callback_data=f"deny_{user_id}")
        ]
    ])

# ---------------- START ----------------
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Please choose:", reply_markup=main_menu)

# ---------------- WHITELIST ----------------
@dp.message(F.text == "Whitelist")
async def whitelist(message: types.Message, state: FSMContext):
    await state.set_state(UserState.waiting_data)
    await state.update_data(section="Whitelist")
    await message.answer("لطفا یوزرنیم ای که میخواهید وایت لیست شود را بنویسید")

# ---------------- SERVER SHOP ----------------
@dp.message(F.text == "Server Shop")
async def shop(message: types.Message):
    await message.answer("Server Shop", reply_markup=shop_buttons)

@dp.callback_query(F.data == "rank_shop")
async def rank_shop(callback: types.CallbackQuery):
    await callback.message.answer(
        "Rank Shop \n"
        "Vip » 49,000 Toman\n"
        "Elite » 100,000 Toman\n"
        "TheFellOmen » 190,000 Toman \n"
        "Sponsor » 250,000 Toman\n"
        "Lover » 400,000 Toman\n\n"
        "اگر فقط نیاز به کیت رنک دارید رنک مورد نظر  و کیت ای که میخواهید را بنویسید مثلا کیت رنک الایت"
    )
    await callback.answer()

@dp.callback_query(F.data == "coin_shop")
async def coin_shop(callback: types.CallbackQuery):
    await callback.message.answer(
        "Coin Shop \n"
        "50 Coin » 15,000 Toman\n"
        "100 Coins » 30,000 Toman\n"
        "150 Coins » 55,000 Toman\n"
        "200 Coins »  80,000 Toman\n"
        "250 Coins » 150,000 Toman\n\n"
        "اگر مقدار کوین ای که میخواهید بیشتر از این هاست مقدار مورد نظر خودتون رو تو چت بنویسید"
    )
    await callback.answer()

# ---------------- PUNISHMENT APPEAL ----------------
@dp.message(F.text == "Punishment Appeal")
async def punishment(message: types.Message, state: FSMContext):
    await state.set_state(UserState.waiting_data)
    await state.update_data(section="Punishment")
    await message.answer(
        "لطفا یوز خود پانیشمنت ایدی و دلیل و توضیحاتتون رو بنویسید مثل \n"
        "username\n"
        "Punishment ID\n"
        "Reason \n"
        "Messages\n\n"
        "مثال \n"
        "miscapel\n"
        "12345\n"
        "cheating\n"
        "please unban me"
    )

# ---------------- CONTACT STAFF ----------------
@dp.message(F.text == "Contact Staff")
async def contact_staff(message: types.Message, state: FSMContext):
    await state.set_state(UserState.waiting_data)
    await state.update_data(section="Contact")
    await message.answer(
        "لطفا پیام ای که میخواهید برای استف ها برود را بنویسید. میتوانید عکس/ویدیو هم بفرستید"
    )

# ---------------- RECEIVE DATA ----------------
@dp.message(UserState.waiting_data)
async def receive_data(message: types.Message, state: FSMContext):
    data = await state.get_data()
    section = data.get("section")
    user_id = message.from_user.id

    caption = f"New {section}\nUser: {message.from_user.full_name}\nID: {user_id}\n\n"

    if message.text:
        caption += message.text

    if message.photo:
        await bot.send_photo(STAFF_GROUP_ID, message.photo[-1].file_id,
                             caption=caption,
                             reply_markup=staff_buttons(user_id))
    elif message.video:
        await bot.send_video(STAFF_GROUP_ID, message.video.file_id,
                             caption=caption,
                             reply_markup=staff_buttons(user_id))
    else:
        await bot.send_message(STAFF_GROUP_ID,
                               caption,
                               reply_markup=staff_buttons(user_id))

    await message.answer("ارسال شد ✅")
    await state.clear()

# ---------------- ACCEPT / DENY ----------------
@dp.callback_query(F.data.startswith("accept_"))
async def accept_user(callback: types.CallbackQuery):
    user_id = callback.data.split("_")[1]
    await bot.send_message(user_id, "درخواست شما تایید شد ✅")
    await callback.answer("Accepted")

@dp.callback_query(F.data.startswith("deny_"))
async def deny_user(callback: types.CallbackQuery):
    user_id = callback.data.split("_")[1]
    await bot.send_message(user_id, "درخواست شما رد شد ❌")
    await callback.answer("Denied")

# ---------------- RUN ----------------
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    asyncio.run(main())
