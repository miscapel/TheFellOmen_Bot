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


# --------------------- CONFIG ---------------------

BOT_TOKEN = os.getenv("BOT_TOKEN")
STAFF_GROUP_ID = int(os.getenv("STAFF_GROUP_ID"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

TICKETS = {}

# --------------------- KEEP ALIVE ---------------------

app = Flask(__name__)

@app.route("/")
def home():
    return "TheFellOmen Bot is Online"

def run_web():
    app.run(host="0.0.0.0", port=10000)


# --------------------- STATES ---------------------

class WhitelistFlow(StatesGroup):
    username = State()

class SupportFlow(StatesGroup):
    message = State()

class PunishmentFlow(StatesGroup):
    username = State()
    punish_id = State()
    reason = State()
    message = State()

class StaffReplyFlow(StatesGroup):
    message = State()


# --------------------- KEYBOARDS ---------------------

def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📜 Whitelist Request", callback_data="whitelist")],
        [InlineKeyboardButton(text="💎 Server Shop", callback_data="shop")],
        [InlineKeyboardButton(text="🆘 Support", callback_data="support")],
        [InlineKeyboardButton(text="⚖️ Punishment Appeal", callback_data="punishment")]
    ])

def shop_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎖 Rank Shop", callback_data="rank_shop")],
        [InlineKeyboardButton(text="🪙 Coin Shop", callback_data="coin_shop")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="start_menu")]
    ])

def back_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back to Menu", callback_data="start_menu")]
    ])

def back_shop():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back to Shop", callback_data="shop")]
    ])

def staff_buttons(ticket):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Accept", callback_data=f"accept_{ticket}"),
            InlineKeyboardButton(text="❌ Deny", callback_data=f"deny_{ticket}")
        ],
        [
            InlineKeyboardButton(text="💬 Reply", callback_data=f"reply_{ticket}")
        ]
    ])


# --------------------- START ---------------------

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "به ربات رسمی TheFellOmen خوش آمدید 🌙\n\n"
        "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
        reply_markup=main_menu()
    )


@dp.callback_query(F.data == "start_menu")
async def back_start(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text(
        "Main Menu:",
        reply_markup=main_menu()
    )


# --------------------- SHOP ---------------------

@dp.callback_query(F.data == "shop")
async def shop_page(call: types.CallbackQuery):
    await call.message.edit_text(
        "Welcome to TheFellOmen Shop\nSelect a category:",
        reply_markup=shop_menu()
    )


@dp.callback_query(F.data == "rank_shop")
async def rank_shop(call: types.CallbackQuery):
    await call.message.edit_text(
        "🎖 Rank Shop\n\n"
        "Vip » 49,000 Toman\n"
        "Elite » 100,000 Toman\n"
        "TheFellOmen » 190,000 Toman\n"
        "Sponsor » 250,000 Toman\n"
        "Lover » 400,000 Toman\n\n"
        "اگر فقط نیاز به کیت رنک دارید، نام رنک و کیت مورد نظر را بنویسید.\n"
        "مثال: کیت رنک الایت",
        reply_markup=back_shop()
    )


@dp.callback_query(F.data == "coin_shop")
async def coin_shop(call: types.CallbackQuery):
    await call.message.edit_text(
        "🪙 Coin Shop\n\n"
        "50 Coin » 15,000 Toman\n"
        "100 Coins » 30,000 Toman\n"
        "150 Coins » 55,000 Toman\n"
        "200 Coins » 80,000 Toman\n"
        "250 Coins » 150,000 Toman\n\n"
        "اگر مقدار کوین مورد نیاز شما بیشتر از این مقادیر است، عدد مورد نظر خود را ارسال کنید.",
        reply_markup=back_shop()
    )


# --------------------- WHITELIST ---------------------

@dp.callback_query(F.data == "whitelist")
async def whitelist_start(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text(
        "لطفاً نام کاربری ماینکرفت خود را ارسال کنید:",
        reply_markup=back_menu()
    )
    await state.set_state(WhitelistFlow.username)


@dp.message(WhitelistFlow.username)
async def whitelist_submit(message: types.Message, state: FSMContext):
    ticket = str(uuid.uuid4())[:8]
    TICKETS[ticket] = message.from_user.id

    staff_text = (
        "📜 New Whitelist Request\n\n"
        f"User: {message.from_user.full_name}\n"
        f"UserID: {message.from_user.id}\n"
        f"Minecraft Username: {message.text}"
    )

    await bot.send_message(STAFF_GROUP_ID, staff_text, reply_markup=staff_buttons(ticket))

    await message.answer("درخواست شما ارسال شد و توسط مدیریت بررسی خواهد شد ✅", reply_markup=back_menu())
    await state.clear()


# --------------------- SUPPORT ---------------------

@dp.callback_query(F.data == "support")
async def support_start(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text(
        "لطفاً پیام پشتیبانی خود را ارسال کنید:",
        reply_markup=back_menu()
    )
    await state.set_state(SupportFlow.message)


@dp.message(SupportFlow.message)
async def support_submit(message: types.Message, state: FSMContext):
    ticket = str(uuid.uuid4())[:8]
    TICKETS[ticket] = message.from_user.id

    staff_text = (
        "🆘 New Support Ticket\n\n"
        f"User: {message.from_user.full_name}\n"
        f"UserID: {message.from_user.id}\n\n"
        f"Message:\n{message.text}"
    )

    await bot.send_message(STAFF_GROUP_ID, staff_text, reply_markup=staff_buttons(ticket))

    await message.answer("تیکت شما ارسال شد، لطفاً منتظر پاسخ مدیریت باشید ✅", reply_markup=back_menu())
    await state.clear()


# --------------------- PUNISHMENT APPEAL ---------------------

@dp.callback_query(F.data == "punishment")
async def punish_start(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text(
        "برای شروع اعتراض، لطفاً نام کاربری ماینکرفت خود را وارد کنید:",
        reply_markup=back_menu()
    )
    await state.set_state(PunishmentFlow.username)


@dp.message(PunishmentFlow.username)
async def p1(message: types.Message, state: FSMContext):
    await state.update_data(username=message.text)
    await message.answer("لطفاً آیدی مجازات را وارد کنید:")
    await state.set_state(PunishmentFlow.punish_id)


@dp.message(PunishmentFlow.punish_id)
async def p2(message: types.Message, state: FSMContext):
    await state.update_data(punish_id=message.text)
    await message.answer("لطفاً دلیل مجازات را وارد کنید:")
    await state.set_state(PunishmentFlow.reason)


@dp.message(PunishmentFlow.reason)
async def p3(message: types.Message, state: FSMContext):
    await state.update_data(reason=message.text)
    await message.answer("متن کامل اعتراض خود را بنویسید:")
    await state.set_state(PunishmentFlow.message)


@dp.message(PunishmentFlow.message)
async def p4(message: types.Message, state: FSMContext):
    data = await state.get_data()
    ticket = str(uuid.uuid4())[:8]
    TICKETS[ticket] = message.from_user.id

    staff_text = (
        "⚖️ New Punishment Appeal\n\n"
        f"User: {message.from_user.full_name}\n"
        f"Username: {data['username']}\n"
        f"Punishment ID: {data['punish_id']}\n"
        f"Reason: {data['reason']}\n\n"
        f"Appeal:\n{message.text}"
    )

    await bot.send_message(STAFF_GROUP_ID, staff_text, reply_markup=staff_buttons(ticket))

    await message.answer("اعتراض شما ارسال شد و توسط مدیریت بررسی خواهد شد ✅", reply_markup=back_menu())
    await state.clear()


# --------------------- STAFF ACTIONS ---------------------

@dp.callback_query(F.data.startswith("accept_"))
async def accept(call: types.CallbackQuery):
    ticket = call.data.split("_")[1]
    user = TICKETS.get(ticket)

    if user:
        await bot.send_message(user, "درخواست شما تایید شد ✅")

    await call.answer("Accepted")


@dp.callback_query(F.data.startswith("deny_"))
async def deny(call: types.CallbackQuery):
    ticket = call.data.split("_")[1]
    user = TICKETS.get(ticket)

    if user:
        await bot.send_message(user, "درخواست شما رد شد ❌")

    await call.answer("Denied")


@dp.callback_query(F.data.startswith("reply_"))
async def reply_start(call: types.CallbackQuery, state: FSMContext):
    ticket = call.data.split("_")[1]
    await state.update_data(ticket=ticket)
    await state.set_state(StaffReplyFlow.message)
    await call.message.answer("لطفاً پیام خود را برای کاربر ارسال کنید:")


@dp.message(StaffReplyFlow.message)
async def reply_send(message: types.Message, state: FSMContext):
    data = await state.get_data()
    ticket = data["ticket"]
    user = TICKETS.get(ticket)

    if user:
        await bot.send_message(user, f"پاسخ مدیریت:\n\n{message.text}")

    await message.answer("پاسخ شما با موفقیت ارسال شد ✅")
    await state.clear()


# --------------------- RUN BOT ---------------------

async def main():
    await bot.set_my_commands([
        BotCommand(command="start", description="Start the bot")
    ])
    await dp.start_polling(bot)


if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    asyncio.run(main())
