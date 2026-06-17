import asyncio
import os
import json
import random
import string
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

BOT_TOKEN = os.getenv("BOT_TOKEN")

STAFF_GROUP_ID = -1004332150226

WELCOME_STICKER = "WELCOME_STICKER_ID"
TICKET_STICKER = "TICKET_STICKER_ID"
SHOP_STICKER = "SHOP_STICKER_ID"

USERS_FILE = "users.json"

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher(storage=MemoryStorage())

TICKETS = {}
USERS = set()


# ---------------- USERS ----------------

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


# ---------------- TOOLS ----------------

def ticket_id():
    return "TK-" + "".join(random.choices(string.ascii_uppercase + string.digits,k=6))


def main_menu():

    return types.ReplyKeyboardMarkup(

        keyboard=[

            [types.KeyboardButton(text="Punishment Appeal")],

            [types.KeyboardButton(text="Whitelist Request")],

            [types.KeyboardButton(text="Contact Staff")],

            [types.KeyboardButton(text="Shop")]

        ],

        resize_keyboard=True
    )


def shop_menu():

    return types.InlineKeyboardMarkup(

        inline_keyboard=[

            [types.InlineKeyboardButton(text="Rank",callback_data="rank")],

            [types.InlineKeyboardButton(text="Coin",callback_data="coin")]

        ]

    )


def staff_buttons(ticket):

    return types.InlineKeyboardMarkup(

        inline_keyboard=[

            [

                types.InlineKeyboardButton(text="Accept",callback_data=f"accept:{ticket}"),

                types.InlineKeyboardButton(text="Deny",callback_data=f"deny:{ticket}")

            ],

            [

                types.InlineKeyboardButton(text="Reply",callback_data=f"reply:{ticket}")

            ]

        ]

    )


# ---------------- STATES ----------------

class Punish(StatesGroup):

    username = State()
    pid = State()
    reason = State()
    message = State()


class Whitelist(StatesGroup):

    username = State()
    message = State()


class Contact(StatesGroup):

    subject = State()
    message = State()


class Shop(StatesGroup):

    category = State()
    message = State()


# ---------------- START ----------------

@dp.message(Command("start"))
async def start(message: types.Message):

    add_user(message.from_user.id)

    await bot.send_sticker(message.chat.id,WELCOME_STICKER)

    text = """
به مرکز پشتیبانی سرور TheFellOmen خوش آمدید

از منوی زیر بخش مورد نظر خود را انتخاب کنید
"""

    await message.answer(text,reply_markup=main_menu())


# ---------------- PUNISHMENT ----------------

@dp.message(F.text=="Punishment Appeal")
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

    ticket = ticket_id()

    TICKETS[ticket]={"user":message.from_user.id}

    await bot.send_sticker(message.chat.id,TICKET_STICKER)

    text=f"""
Punishment Appeal

Minecraft: {data['username']}
Punishment ID: {data['pid']}

Reason:
{data['reason']}

Message:
{message.text}

Telegram: @{message.from_user.username}
UserID: {message.from_user.id}

Ticket: {ticket}
"""

    await bot.send_message(STAFF_GROUP_ID,text,reply_markup=staff_buttons(ticket))

    await message.answer("درخواست شما برای استاف ارسال شد",reply_markup=main_menu())

    await state.clear()


# ---------------- WHITELIST ----------------

@dp.message(F.text=="Whitelist Request")
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

    ticket=ticket_id()

    TICKETS[ticket]={"user":message.from_user.id}

    await bot.send_sticker(message.chat.id,TICKET_STICKER)

    text=f"""
Whitelist Request

Minecraft: {data['username']}

Message:
{message.text}

Telegram: @{message.from_user.username}

Ticket: {ticket}
"""

    await bot.send_message(STAFF_GROUP_ID,text,reply_markup=staff_buttons(ticket))

    await message.answer("درخواست شما ارسال شد",reply_markup=main_menu())

    await state.clear()


# ---------------- CONTACT ----------------

@dp.message(F.text=="Contact Staff")
async def contact_start(message: types.Message,state:FSMContext):

    await state.set_state(Contact.subject)

    await message.answer("موضوع پیام را بنویسید")


@dp.message(Contact.subject)
async def contact_subject(message: types.Message,state:FSMContext):

    await state.update_data(subject=message.text)

    await state.set_state(Contact.message)

    await message.answer("پیام خود را بنویسید")


@dp.message(Contact.message)
async def contact_finish(message: types.Message,state:FSMContext):

    data=await state.get_data()

    ticket=ticket_id()

    TICKETS[ticket]={"user":message.from_user.id}

    text=f"""
Contact Staff

Subject: {data['subject']}

Message:
{message.text}

Telegram: @{message.from_user.username}

Ticket: {ticket}
"""

    await bot.send_message(STAFF_GROUP_ID,text,reply_markup=staff_buttons(ticket))

    await message.answer("پیام شما برای استاف ارسال شد",reply_markup=main_menu())

    await state.clear()


# ---------------- SHOP ----------------

@dp.message(F.text=="Shop")
async def shop(message: types.Message):

    await bot.send_sticker(message.chat.id,SHOP_STICKER)

    await message.answer("بخش فروشگاه سرور",reply_markup=shop_menu())


@dp.callback_query(F.data=="rank")
async def rank(callback: types.CallbackQuery,state:FSMContext):

    await state.update_data(category="Rank")

    await state.set_state(Shop.message)

    text="""
Rank Shop

Vip » 49,000 Toman
Elite » 100,000 Toman
TheFellOmen » 190,000 Toman
Sponsor » 250,000 Toman
Lover » 400,000 Toman

اگر فقط نیاز به کیت دارید
نام رنک و کیت را بنویسید

مثال
کیت رنک الایت
"""

    await callback.message.edit_text(text)


@dp.callback_query(F.data=="coin")
async def coin(callback: types.CallbackQuery,state:FSMContext):

    await state.update_data(category="Coin")

    await state.set_state(Shop.message)

    text="""
Coin Shop

50 Coin » 15,000 Toman
100 Coins » 30,000 Toman
150 Coins » 55,000 Toman
200 Coins » 80,000 Toman
250 Coins » 150,000 Toman

اگر مقدار بیشتری میخواهید
عدد مورد نظر را در چت بنویسید
"""

    await callback.message.edit_text(text)


@dp.message(Shop.message)
async def shop_finish(message: types.Message,state:FSMContext):

    data=await state.get_data()

    ticket=ticket_id()

    TICKETS[ticket]={"user":message.from_user.id}

    text=f"""
Shop Order

Category: {data['category']}

Message:
{message.text}

Telegram: @{message.from_user.username}

Ticket: {ticket}
"""

    await bot.send_message(STAFF_GROUP_ID,text,reply_markup=staff_buttons(ticket))

    await message.answer("درخواست خرید ارسال شد",reply_markup=main_menu())

    await state.clear()


# ---------------- BROADCAST ----------------

@dp.message(Command("broadcast"))
async def broadcast(message: types.Message):

    if message.chat.id != STAFF_GROUP_ID:
        return

    if not message.reply_to_message:
        await message.reply("روی یک پیام ریپلای کنید")
        return

    msg = message.reply_to_message.text

    sent = 0

    for user in USERS:

        try:

            await bot.send_message(user,msg)

            sent+=1

        except:
            pass

    await message.reply(f"{sent} پیام ارسال شد")


# ---------------- MAIN ----------------

async def main():

    load_users()

    await bot.delete_webhook(drop_pending_updates=True)

    await dp.start_polling(bot)


if __name__=="__main__":

    asyncio.run(main())
