import asyncio
import os
import logging
import random
import string
import threading
from datetime import datetime

from flask import Flask

from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage


# ================= CONFIG =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
STAFF_GROUP_ID = -1004332150226

logging.basicConfig(level=logging.INFO)

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher(storage=MemoryStorage())


# ================= RENDER KEEP ALIVE =================

app = Flask(__name__)

@app.route("/")
def home():
    return "TheFellOmen Bot Running"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    t = threading.Thread(target=run)
    t.start()


# ================= DATA =================

TICKETS = {}
REPLY_MODE = {}


def make_ticket():
    return "TK-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


# ================= MENUS =================

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


def inline_menu():
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="⚖️ Punishment Appeal", callback_data="punish")],
            [types.InlineKeyboardButton(text="📜 Whitelist", callback_data="whitelist")],
            [types.InlineKeyboardButton(text="🆘 Contact Staff", callback_data="contact")],
            [types.InlineKeyboardButton(text="💎 Shop", callback_data="shop")]
        ]
    )


def shop_menu():
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="👑 Rank", callback_data="rank")],
            [types.InlineKeyboardButton(text="🪙 Coin", callback_data="coin")],
            [types.InlineKeyboardButton(text="🔙 Back", callback_data="back")]
        ]
    )


def whitelist_menu():
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="📜 Register Whitelist", callback_data="wl_start")],
            [types.InlineKeyboardButton(text="🔙 Back", callback_data="back")]
        ]
    )


def staff_buttons(ticket):
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="✅ Accept", callback_data=f"accept:{ticket}"),
                types.InlineKeyboardButton(text="❌ Deny", callback_data=f"deny:{ticket}")
            ],
            [
                types.InlineKeyboardButton(text="💬 Reply", callback_data=f"reply:{ticket}")
            ]
        ]
    )


# ================= STATES =================

class Punish(StatesGroup):
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


class Shop(StatesGroup):
    category = State()
    message = State()


# ================= START =================

@dp.message(Command("start"))
async def start(message: types.Message):

    text = """
🔥 <b>TheFellOmen Support Center</b>

به سیستم رسمی پشتیبانی سرور خوش آمدید.

از دکمه‌های زیر استفاده کنید.
"""

    await message.answer(
        text,
        reply_markup=inline_menu()
    )

    await message.answer(
        "Main Menu:",
        reply_markup=main_menu()
    )


# ================= BACK =================

@dp.callback_query(F.data == "back")
async def back(callback: types.CallbackQuery):

    await callback.message.edit_text(
        "Main Menu",
        reply_markup=inline_menu()
    )


# ================= PUNISHMENT =================

async def start_punish(message, state):

    await state.set_state(Punish.username)

    await message.answer("Minecraft Username خود را ارسال کنید.")


@dp.message(F.text == "⚖️ Punishment Appeal")
async def punish_btn(message: types.Message, state: FSMContext):
    await start_punish(message, state)


@dp.callback_query(F.data == "punish")
async def punish_inline(callback: types.CallbackQuery, state: FSMContext):

    await start_punish(callback.message, state)


@dp.message(Punish.username)
async def punish_user(message: types.Message, state: FSMContext):

    await state.update_data(username=message.text)

    await state.set_state(Punish.pid)

    await message.answer("Punishment ID را ارسال کنید.")


@dp.message(Punish.pid)
async def punish_id(message: types.Message, state: FSMContext):

    await state.update_data(pid=message.text)

    await state.set_state(Punish.reason)

    await message.answer("دلیل Appeal را بنویسید.")


@dp.message(Punish.reason)
async def punish_reason(message: types.Message, state: FSMContext):

    await state.update_data(reason=message.text)

    await state.set_state(Punish.message)

    await message.answer("توضیح کامل خود را ارسال کنید.")


@dp.message(Punish.message)
async def punish_finish(message: types.Message, state: FSMContext):

    data = await state.get_data()

    ticket = make_ticket()

    TICKETS[ticket] = {"user": message.from_user.id}

    text = f"""
⚖️ Punishment Appeal

Username: {data['username']}
Punishment ID: {data['pid']}
Reason: {data['reason']}

Message:
{message.text}

Time: {now()}

User ID: {message.from_user.id}
Ticket: {ticket}
"""

    await bot.send_message(
        STAFF_GROUP_ID,
        text,
        reply_markup=staff_buttons(ticket)
    )

    await message.answer(
        "✅ درخواست شما ارسال شد.",
        reply_markup=main_menu()
    )

    await state.clear()


# ================= WHITELIST =================

@dp.message(F.text == "📜 Whitelist")
async def wl_menu(message: types.Message):

    await message.answer(
        "Whitelist Request",
        reply_markup=whitelist_menu()
    )


@dp.callback_query(F.data == "whitelist")
async def wl_inline(callback: types.CallbackQuery):

    await callback.message.edit_text(
        "Whitelist Request",
        reply_markup=whitelist_menu()
    )


@dp.callback_query(F.data == "wl_start")
async def wl_start(callback: types.CallbackQuery, state: FSMContext):

    await state.set_state(Whitelist.username)

    await callback.message.answer("Minecraft Username را بنویسید.")


@dp.message(Whitelist.username)
async def wl_user(message: types.Message, state: FSMContext):

    await state.update_data(username=message.text)

    await state.set_state(Whitelist.message)

    await message.answer("توضیح خود را بنویسید.")


@dp.message(Whitelist.message)
async def wl_finish(message: types.Message, state: FSMContext):

    data = await state.get_data()

    ticket = make_ticket()

    TICKETS[ticket] = {"user": message.from_user.id}

    text = f"""
📜 Whitelist

Username: {data['username']}

Message:
{message.text}

Time: {now()}

User ID: {message.from_user.id}
Ticket: {ticket}
"""

    await bot.send_message(
        STAFF_GROUP_ID,
        text,
        reply_markup=staff_buttons(ticket)
    )

    await message.answer(
        "✅ درخواست ارسال شد.",
        reply_markup=main_menu()
    )

    await state.clear()


# ================= CONTACT =================

@dp.message(F.text == "🆘 Contact Staff")
async def contact_start(message: types.Message, state: FSMContext):

    await state.set_state(Contact.reason)

    await message.answer("دلیل تیکت را بنویسید.")


@dp.callback_query(F.data == "contact")
async def contact_inline(callback: types.CallbackQuery, state: FSMContext):

    await state.set_state(Contact.reason)

    await callback.message.answer("دلیل تیکت را بنویسید.")


@dp.message(Contact.reason)
async def contact_reason(message: types.Message, state: FSMContext):

    await state.update_data(reason=message.text)

    await state.set_state(Contact.message)

    await message.answer("پیام خود را ارسال کنید.")


@dp.message(Contact.message)
async def contact_finish(message: types.Message, state: FSMContext):

    data = await state.get_data()

    ticket = make_ticket()

    TICKETS[ticket] = {"user": message.from_user.id}

    text = f"""
📩 Contact Staff

Reason: {data['reason']}

Message:
{message.text}

Time: {now()}

User ID: {message.from_user.id}
Ticket: {ticket}
"""

    await bot.send_message(
        STAFF_GROUP_ID,
        text,
        reply_markup=staff_buttons(ticket)
    )

    await message.answer(
        "✅ تیکت ارسال شد.",
        reply_markup=main_menu()
    )

    await state.clear()


# ================= SHOP =================

@dp.message(F.text == "💎 Shop")
async def shop(message: types.Message):

    await message.answer(
        "💎 Server Shop",
        reply_markup=shop_menu()
    )


@dp.callback_query(F.data == "shop")
async def shop_inline(callback: types.CallbackQuery):

    await callback.message.edit_text(
        "💎 Server Shop",
        reply_markup=shop_menu()
    )


@dp.callback_query(F.data == "rank")
async def rank(callback: types.CallbackQuery, state: FSMContext):

    await state.update_data(category="Rank")

    await state.set_state(Shop.message)

    text = """
👑 Rank Shop

Vip » 49k
Elite » 100k
TheFellOmen » 190k
Sponsor » 250k
Lover » 400k

درخواست خرید خود را بنویسید.
"""

    await callback.message.edit_text(text)


@dp.callback_query(F.data == "coin")
async def coin(callback: types.CallbackQuery, state: FSMContext):

    await state.update_data(category="Coin")

    await state.set_state(Shop.message)

    text = """
🪙 Coin Shop

50 » 15k
100 » 30k
150 » 55k
200 » 80k
250 » 150k

درخواست خرید خود را بنویسید.
"""

    await callback.message.edit_text(text)


@dp.message(Shop.message)
async def shop_finish(message: types.Message, state: FSMContext):

    data = await state.get_data()

    ticket = make_ticket()

    TICKETS[ticket] = {"user": message.from_user.id}

    text = f"""
💎 Shop Order

Category: {data['category']}

Message:
{message.text}

Time: {now()}

User ID: {message.from_user.id}
Ticket: {ticket}
"""

    await bot.send_message(
        STAFF_GROUP_ID,
        text,
        reply_markup=staff_buttons(ticket)
    )

    await message.answer(
        "✅ درخواست خرید ارسال شد.",
        reply_markup=main_menu()
    )

    await state.clear()


# ================= STAFF =================

@dp.callback_query(F.data.startswith("accept"))
async def accept(callback: types.CallbackQuery):

    ticket = callback.data.split(":")[1]

    user = TICKETS[ticket]["user"]

    await bot.send_message(user, "✅ درخواست شما تایید شد.")

    await callback.answer("Accepted")


@dp.callback_query(F.data.startswith("deny"))
async def deny(callback: types.CallbackQuery):

    ticket = callback.data.split(":")[1]

    user = TICKETS[ticket]["user"]

    await bot.send_message(user, "❌ درخواست شما رد شد.")

    await callback.answer("Denied")


@dp.callback_query(F.data.startswith("reply"))
async def reply(callback: types.CallbackQuery):

    ticket = callback.data.split(":")[1]

    REPLY_MODE[callback.from_user.id] = ticket

    await callback.message.reply("پیام خود را ارسال کنید.")


@dp.message()
async def staff_reply(message: types.Message):

    if message.from_user.id not in REPLY_MODE:
        return

    ticket = REPLY_MODE[message.from_user.id]

    user = TICKETS[ticket]["user"]

    if message.photo:

        await bot.send_photo(
            user,
            message.photo[-1].file_id,
            caption="💬 پاسخ استاف"
        )

    elif message.video:

        await bot.send_video(
            user,
            message.video.file_id,
            caption="💬 پاسخ استاف"
        )

    else:

        await bot.send_message(
            user,
            f"💬 پاسخ استاف:\n\n{message.text}"
        )

    del REPLY_MODE[message.from_user.id]


# ================= MAIN =================

async def main():

    keep_alive()

    await bot.delete_webhook(drop_pending_updates=True)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
