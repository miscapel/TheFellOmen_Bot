import asyncio
import os
from datetime import datetime

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

BOT_TOKEN = os.getenv("BOT_TOKEN")
STAFF_GROUP_ID = -1004332150226

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher(storage=MemoryStorage())

# ---------------- STATES ----------------

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

# ---------------- KEYBOARDS ----------------

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

def shop_menu():
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="🏆 Rank Shop", callback_data="rank")],
            [types.InlineKeyboardButton(text="🪙 Coin Shop", callback_data="coin")]
        ]
    )

# ---------------- START ----------------

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "👋 خوش آمدید به ربات رسمی سرور\n\n"
        "از منوی زیر بخش مورد نظر خود را انتخاب کنید.",
        reply_markup=main_menu()
    )

# ---------------- PUNISHMENT APPEAL ----------------

@dp.message(F.text == "⚖️ Punishment Appeal")
async def appeal_start(message: types.Message, state: FSMContext):

    await state.set_state(Appeal.username)

    await message.answer(
        "🎮 لطفا یوزرنیم ماینکرفت خود را ارسال کنید."
    )

@dp.message(Appeal.username)
async def appeal_username(message: types.Message, state: FSMContext):

    await state.update_data(username=message.text)
    await state.set_state(Appeal.pid)

    await message.answer(
        "🆔 لطفا Punishment ID خود را ارسال کنید."
    )

@dp.message(Appeal.pid)
async def appeal_pid(message: types.Message, state: FSMContext):

    await state.update_data(pid=message.text)
    await state.set_state(Appeal.reason)

    await message.answer(
        "📄 دلیل درخواست رفع مجازات را بنویسید."
    )

@dp.message(Appeal.reason)
async def appeal_reason(message: types.Message, state: FSMContext):

    await state.update_data(reason=message.text)
    await state.set_state(Appeal.message)

    await message.answer(
        "✍️ توضیحات کامل خود را ارسال کنید.\n\n"
        "می‌توانید متن، عکس یا ویدیو بفرستید."
    )

@dp.message(Appeal.message)
async def appeal_finish(message: types.Message, state: FSMContext):

    data = await state.get_data()

    username = data["username"]
    pid = data["pid"]
    reason = data["reason"]

    time = datetime.now().strftime("%Y-%m-%d %H:%M")

    text = f"""
⚖️ <b>Punishment Appeal</b>

Username: {username}

Reason: {reason}

Punishment ID: {pid}

Time: {time}
"""

    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="✅ Accept", callback_data=f"accept_{message.from_user.id}"),
                types.InlineKeyboardButton(text="❌ Deny", callback_data=f"deny_{message.from_user.id}")
            ],
            [
                types.InlineKeyboardButton(text="💬 Reply", callback_data=f"reply_{message.from_user.id}")
            ]
        ]
    )

    if message.photo:
        await bot.send_photo(
            STAFF_GROUP_ID,
            message.photo[-1].file_id,
            caption=text + f"\n\nMessage:\n{message.caption}",
            reply_markup=keyboard
        )

    elif message.video:
        await bot.send_video(
            STAFF_GROUP_ID,
            message.video.file_id,
            caption=text + f"\n\nMessage:\n{message.caption}",
            reply_markup=keyboard
        )

    else:
        await bot.send_message(
            STAFF_GROUP_ID,
            text + f"\n\nMessage:\n{message.text}",
            reply_markup=keyboard
        )

    await message.answer(
        "✅ درخواست شما با موفقیت برای استاف ارسال شد.",
        reply_markup=main_menu()
    )

    await state.clear()

# ---------------- WHITELIST ----------------

@dp.message(F.text == "📜 Whitelist")
async def whitelist(message: types.Message, state: FSMContext):

    await state.set_state(Whitelist.username)

    await message.answer(
        "لطفا یوزری که میخواهید وایت لیست شود را بنویسید."
    )

@dp.message(Whitelist.username)
async def whitelist_user(message: types.Message, state: FSMContext):

    await state.update_data(username=message.text)
    await state.set_state(Whitelist.message)

    await message.answer(
        "اگر توضیحی دارید ارسال کنید (متن / عکس / ویدیو)"
    )

@dp.message(Whitelist.message)
async def whitelist_finish(message: types.Message, state: FSMContext):

    data = await state.get_data()
    time = datetime.now().strftime("%Y-%m-%d %H:%M")

    text = f"""
📜 <b>Whitelist</b>

Username: {data["username"]}

Time: {time}
"""

    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="✅ Accept", callback_data=f"accept_{message.from_user.id}"),
                types.InlineKeyboardButton(text="❌ Deny", callback_data=f"deny_{message.from_user.id}")
            ]
        ]
    )

    await bot.send_message(
        STAFF_GROUP_ID,
        text + f"\n\nMessages:\n{message.text}",
        reply_markup=keyboard
    )

    await message.answer("✅ درخواست وایت لیست ارسال شد.", reply_markup=main_menu())

    await state.clear()

# ---------------- CONTACT ----------------

@dp.message(F.text == "🆘 Contact Staff")
async def contact(message: types.Message, state: FSMContext):

    await state.set_state(Contact.reason)

    await message.answer(
        "📄 دلیل تماس با استاف را بنویسید."
    )

@dp.message(Contact.reason)
async def contact_reason(message: types.Message, state: FSMContext):

    await state.update_data(reason=message.text)
    await state.set_state(Contact.message)

    await message.answer(
        "✉️ پیام کامل خود را ارسال کنید.\n"
        "می‌توانید عکس یا ویدیو هم بفرستید."
    )

@dp.message(Contact.message)
async def contact_finish(message: types.Message, state: FSMContext):

    data = await state.get_data()
    time = datetime.now().strftime("%Y-%m-%d %H:%M")

    text = f"""
🆘 <b>Contact Staff</b>

Username: {message.from_user.username}

Reason: {data["reason"]}

Time: {time}
"""

    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="✅ Accept", callback_data=f"accept_{message.from_user.id}"),
                types.InlineKeyboardButton(text="❌ Deny", callback_data=f"deny_{message.from_user.id}")
            ],
            [
                types.InlineKeyboardButton(text="💬 Reply", callback_data=f"reply_{message.from_user.id}")
            ]
        ]
    )

    await bot.send_message(
        STAFF_GROUP_ID,
        text + f"\n\nMessages:\n{message.text}",
        reply_markup=keyboard
    )

    await message.answer("✅ پیام شما برای استاف ارسال شد.", reply_markup=main_menu())

    await state.clear()

# ---------------- SHOP ----------------

@dp.message(F.text == "💎 Shop")
async def shop(message: types.Message):

    await message.answer(
        "💎 فروشگاه سرور",
        reply_markup=shop_menu()
    )

@dp.callback_query(F.data == "rank")
async def rank(callback: types.CallbackQuery):

    await callback.message.answer(
"""
🏆 Rank Shop

Vip » 49,000 Toman
Elite » 100,000 Toman
TheFellOmen » 190,000 Toman
Sponsor » 250,000 Toman
Lover » 400,000 Toman

اگر فقط کیت رنک میخواهید
نام رنک و کیت را بنویسید

مثال:
کیت رنک الایت
"""
)

@dp.callback_query(F.data == "coin")
async def coin(callback: types.CallbackQuery):

    await callback.message.answer(
"""
🪙 Coin Shop

50 Coin » 15,000 Toman
100 Coins » 30,000 Toman
150 Coins » 55,000 Toman
200 Coins » 80,000 Toman
250 Coins » 150,000 Toman

اگر مقدار بیشتری نیاز دارید
عدد مورد نظر را در چت بنویسید.
"""
)

# ---------------- RUN ----------------

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
