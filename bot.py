import asyncio
import os
import logging
import random
import string
import json
import html
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


BOT_TOKEN = os.getenv("BOT_TOKEN")

STAFF_GROUP_ID = -1004332150226

# استیکرها (می‌توانی FileID خودت را جایگزین کنی)
WELCOME_STICKER = "CAACAgIAAxkBAAEB123lDummyWelcomeSticker"
TICKET_STICKER = "CAACAgIAAxkBAAEB123lDummyTicketSticker"
SHOP_STICKER = "CAACAgIAAxkBAAEB123lDummyShopSticker"

USERS_FILE = "users.json"

logging.basicConfig(level=logging.INFO)

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher(storage=MemoryStorage())


# ---------- KEEP ALIVE ----------

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot Running"

def run():
    port = int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0",port=port)

def keep_alive():
    threading.Thread(target=run).start()


# ---------- DATA ----------

TICKETS = {}
REPLY_MODE = {}
TRANSCRIPTS = {}
USERS = set()


# ---------- USERS ----------

def load_users():

    global USERS

    if os.path.exists(USERS_FILE):

        with open(USERS_FILE,"r") as f:

            USERS = set(json.load(f))


def save_users():

    with open(USERS_FILE,"w") as f:

        json.dump(list(USERS),f)


def add_user(uid):

    USERS.add(uid)

    save_users()


# ---------- HELPERS ----------

def make_ticket():

    return "TK-" + "".join(random.choices(string.ascii_uppercase + string.digits,k=6))


def now():

    return datetime.now().strftime("%Y-%m-%d %H:%M")


def create_transcript(ticket):

    if ticket not in TRANSCRIPTS:

        return None

    msgs = TRANSCRIPTS[ticket]

    content = """
<html>
<head>
<meta charset="UTF-8">
<style>
body{background:#1e1e1e;color:white;font-family:Arial;padding:20px}
.msg{background:#2b2b2b;margin:10px;padding:10px;border-radius:6px}
.author{color:#7fb3ff}
.time{font-size:12px;color:gray}
</style>
</head>
<body>
<h2>Ticket Transcript</h2>
"""

    for m in msgs:

        content += f"""
<div class="msg">
<div class="author">{html.escape(m['author'])}</div>
<div>{html.escape(m['text'])}</div>
<div class="time">{m['time']}</div>
</div>
"""

    content += "</body></html>"

    name = f"transcript_{ticket}.html"

    with open(name,"w",encoding="utf-8") as f:

        f.write(content)

    return name


# ---------- MENUS ----------

def main_menu():

    return types.ReplyKeyboardMarkup(

        keyboard=[

            [types.KeyboardButton(text="اعتراض به بن")],

            [types.KeyboardButton(text="درخواست وایت لیست")],

            [types.KeyboardButton(text="تماس با استاف")],

            [types.KeyboardButton(text="فروشگاه سرور")]

        ],

        resize_keyboard=True

    )


def shop_menu():

    return types.InlineKeyboardMarkup(

        inline_keyboard=[

            [types.InlineKeyboardButton(text="خرید رنک",callback_data="rank")],

            [types.InlineKeyboardButton(text="خرید کوین",callback_data="coin")]

        ]

    )


def staff_buttons(ticket):

    return types.InlineKeyboardMarkup(

        inline_keyboard=[

            [

                types.InlineKeyboardButton(text="تایید",callback_data=f"accept:{ticket}"),

                types.InlineKeyboardButton(text="رد",callback_data=f"deny:{ticket}")

            ],

            [

                types.InlineKeyboardButton(text="پاسخ",callback_data=f"reply:{ticket}")

            ]

        ]

    )


# ---------- STATES ----------

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


# ---------- START ----------

@dp.message(Command("start"))
async def start(message: types.Message):

    add_user(message.from_user.id)

    await bot.send_sticker(message.chat.id,WELCOME_STICKER)

    text = """
به مرکز پشتیبانی سرور TheFellOmen خوش آمدید

از منوی زیر بخش مورد نظر خود را انتخاب کنید
"""

    await message.answer(text,reply_markup=main_menu())


# ---------- PUNISH ----------

@dp.message(F.text=="اعتراض به بن")
async def punish_start(message: types.Message,state:FSMContext):

    await state.set_state(Punish.username)

    await message.answer("نام ماینکرفت خود را ارسال کنید")


@dp.message(Punish.username)
async def punish_user(message: types.Message,state:FSMContext):

    await state.update_data(username=message.text)

    await state.set_state(Punish.pid)

    await message.answer("آیدی مجازات را ارسال کنید")


@dp.message(Punish.pid)
async def punish_pid(message: types.Message,state:FSMContext):

    await state.update_data(pid=message.text)

    await state.set_state(Punish.reason)

    await message.answer("دلیل اعتراض را بنویسید")


@dp.message(Punish.reason)
async def punish_reason(message: types.Message,state:FSMContext):

    await state.update_data(reason=message.text)

    await state.set_state(Punish.message)

    await message.answer("توضیح کامل خود را بنویسید")


@dp.message(Punish.message)
async def punish_finish(message: types.Message,state:FSMContext):

    data = await state.get_data()

    ticket = make_ticket()

    TICKETS[ticket]={"user":message.from_user.id}

    TRANSCRIPTS[ticket]=[]

    await bot.send_sticker(message.chat.id,TICKET_STICKER)

    text=f"""
اعتراض به بن

Minecraft: {data['username']}
Punishment ID: {data['pid']}
Reason: {data['reason']}

Message:
{message.text}

Telegram: @{message.from_user.username}
UserID: {message.from_user.id}

Ticket: {ticket}
"""

    await bot.send_message(STAFF_GROUP_ID,text,reply_markup=staff_buttons(ticket))

    await message.answer("درخواست شما ارسال شد",reply_markup=main_menu())

    await state.clear()


# ---------- WHITELIST ----------

@dp.message(F.text=="درخواست وایت لیست")
async def wl_start(message: types.Message,state:FSMContext):

    await state.set_state(Whitelist.username)

    await message.answer("نام ماینکرفت خود را ارسال کنید")


@dp.message(Whitelist.username)
async def wl_user(message: types.Message,state:FSMContext):

    await state.update_data(username=message.text)

    await state.set_state(Whitelist.message)

    await message.answer("پیام خود را بنویسید")


@dp.message(Whitelist.message)
async def wl_finish(message: types.Message,state:FSMContext):

    data=await state.get_data()

    ticket=make_ticket()

    TICKETS[ticket]={"user":message.from_user.id}

    await bot.send_sticker(message.chat.id,TICKET_STICKER)

    text=f"""
درخواست وایت لیست

Minecraft: {data['username']}

Message:
{message.text}

Telegram: @{message.from_user.username}

Ticket: {ticket}
"""

    await bot.send_message(STAFF_GROUP_ID,text,reply_markup=staff_buttons(ticket))

    await message.answer("درخواست ارسال شد",reply_markup=main_menu())

    await state.clear()


# ---------- CONTACT ----------

@dp.message(F.text=="تماس با استاف")
async def contact_start(message: types.Message,state:FSMContext):

    await state.set_state(Contact.reason)

    await message.answer("موضوع پیام را بنویسید")


@dp.message(Contact.reason)
async def contact_reason(message: types.Message,state:FSMContext):

    await state.update_data(reason=message.text)

    await state.set_state(Contact.message)

    await message.answer("پیام خود را بنویسید")


@dp.message(Contact.message)
async def contact_finish(message: types.Message,state:FSMContext):

    data=await state.get_data()

    ticket=make_ticket()

    TICKETS[ticket]={"user":message.from_user.id}

    text=f"""
تماس با استاف

موضوع: {data['reason']}

Message:
{message.text}

Telegram: @{message.from_user.username}

Ticket: {ticket}
"""

    await bot.send_message(STAFF_GROUP_ID,text,reply_markup=staff_buttons(ticket))

    await message.answer("تیکت شما ارسال شد",reply_markup=main_menu())

    await state.clear()


# ---------- SHOP ----------

@dp.message(F.text=="فروشگاه سرور")
async def shop(message: types.Message):

    await bot.send_sticker(message.chat.id,SHOP_STICKER)

    await message.answer("بخش فروشگاه",reply_markup=shop_menu())


@dp.callback_query(F.data=="rank")
async def rank(callback: types.CallbackQuery,state:FSMContext):

    await state.update_data(category="Rank")

    await state.set_state(Shop.message)

    await callback.message.answer("نام رنک و یوزرنیم ماینکرفت را بنویسید")


@dp.callback_query(F.data=="coin")
async def coin(callback: types.CallbackQuery,state:FSMContext):

    await state.update_data(category="Coin")

    await state.set_state(Shop.message)

    await callback.message.answer("تعداد کوین و یوزرنیم ماینکرفت را بنویسید")


@dp.message(Shop.message)
async def shop_finish(message: types.Message,state:FSMContext):

    data=await state.get_data()

    ticket=make_ticket()

    TICKETS[ticket]={"user":message.from_user.id}

    text=f"""
خرید از فروشگاه

Category: {data['category']}

Message:
{message.text}

Telegram: @{message.from_user.username}

Ticket: {ticket}
"""

    await bot.send_message(STAFF_GROUP_ID,text,reply_markup=staff_buttons(ticket))

    await message.answer("درخواست خرید ارسال شد",reply_markup=main_menu())

    await state.clear()


# ---------- STAFF ----------

@dp.callback_query(F.data.startswith("accept"))
async def accept(callback: types.CallbackQuery):

    ticket=callback.data.split(":")[1]

    user=TICKETS[ticket]["user"]

    await bot.send_message(user,"درخواست شما تایید شد")

    file=create_transcript(ticket)

    if file:

        await bot.send_document(STAFF_GROUP_ID,types.FSInputFile(file))

    await callback.message.reply(f"تیکت {ticket} تایید شد")


@dp.callback_query(F.data.startswith("deny"))
async def deny(callback: types.CallbackQuery):

    ticket=callback.data.split(":")[1]

    user=TICKETS[ticket]["user"]

    await bot.send_message(user,"درخواست شما رد شد")

    file=create_transcript(ticket)

    if file:

        await bot.send_document(STAFF_GROUP_ID,types.FSInputFile(file))

    await callback.message.reply(f"تیکت {ticket} رد شد")


# ---------- MAIN ----------

async def main():

    load_users()

    keep_alive()

    await bot.delete_webhook(drop_pending_updates=True)

    await dp.start_polling(bot)


if __name__=="__main__":

    asyncio.run(main())
