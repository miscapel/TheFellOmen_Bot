import asyncio
import os
import logging
import random
import string
import threading
import json
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
USERS_FILE = "users.json"

logging.basicConfig(level=logging.INFO)

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher(storage=MemoryStorage())


app = Flask(__name__)

@app.route("/")
def home():
    return "Bot Running"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    t = threading.Thread(target=run)
    t.start()


TICKETS = {}
REPLY_MODE = {}
USERS = set()


def load_users():
    global USERS
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE,"r") as f:
            USERS = set(json.load(f))

def save_users():
    with open(USERS_FILE,"w") as f:
        json.dump(list(USERS),f)

def add_user(user):
    USERS.add(user)
    save_users()


def make_ticket():
    return "TK-" + "".join(random.choices(string.ascii_uppercase + string.digits,k=6))


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def main_menu():
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Punishment Appeal")],
            [types.KeyboardButton(text="Whitelist")],
            [types.KeyboardButton(text="Contact Staff")],
            [types.KeyboardButton(text="Shop")]
        ],
        resize_keyboard=True
    )


def inline_menu():
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="Punishment Appeal",callback_data="punish")],
            [types.InlineKeyboardButton(text="Whitelist",callback_data="whitelist")],
            [types.InlineKeyboardButton(text="Contact Staff",callback_data="contact")],
            [types.InlineKeyboardButton(text="Shop",callback_data="shop")]
        ]
    )


def shop_menu():
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="Rank",callback_data="rank")],
            [types.InlineKeyboardButton(text="Coin",callback_data="coin")],
            [types.InlineKeyboardButton(text="Back",callback_data="back")]
        ]
    )


def whitelist_menu():
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="Register Whitelist",callback_data="wl_start")],
            [types.InlineKeyboardButton(text="Back",callback_data="back")]
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


@dp.message(Command("start"))
async def start(message: types.Message):

    add_user(message.from_user.id)

    text="""
TheFellOmen Support Center

Welcome to server support.
Use buttons below.
"""

    await message.answer(text,reply_markup=inline_menu())
    await message.answer("Menu",reply_markup=main_menu())


@dp.callback_query(F.data=="back")
async def back(callback: types.CallbackQuery):

    await callback.message.edit_text(
        "Main Menu",
        reply_markup=inline_menu()
    )


async def start_punish(message,state):

    await state.set_state(Punish.username)

    await message.answer("Send Minecraft Username")


@dp.message(F.text=="Punishment Appeal")
async def punish_btn(message: types.Message,state:FSMContext):

    await start_punish(message,state)


@dp.callback_query(F.data=="punish")
async def punish_inline(callback: types.CallbackQuery,state:FSMContext):

    await start_punish(callback.message,state)


@dp.message(Punish.username)
async def punish_user(message: types.Message,state:FSMContext):

    await state.update_data(username=message.text)

    await state.set_state(Punish.pid)

    await message.answer("Send Punishment ID")


@dp.message(Punish.pid)
async def punish_id(message: types.Message,state:FSMContext):

    await state.update_data(pid=message.text)

    await state.set_state(Punish.reason)

    await message.answer("Write reason")


@dp.message(Punish.reason)
async def punish_reason(message: types.Message,state:FSMContext):

    await state.update_data(reason=message.text)

    await state.set_state(Punish.message)

    await message.answer("Write full message")


@dp.message(Punish.message)
async def punish_finish(message: types.Message,state:FSMContext):

    data = await state.get_data()
    ticket = make_ticket()

    username = message.from_user.username

    TICKETS[ticket] = {"user":message.from_user.id}

    text=f"""
Punishment Appeal

Minecraft: {data['username']}
Punishment ID: {data['pid']}
Reason: {data['reason']}

Message:
{message.text}

Telegram: @{username}
UserID: {message.from_user.id}

Ticket: {ticket}
Time: {now()}
"""

    await bot.send_message(STAFF_GROUP_ID,text,reply_markup=staff_buttons(ticket))

    await message.answer("Request sent",reply_markup=main_menu())

    await state.clear()


@dp.message(F.text=="Whitelist")
async def wl_menu(message: types.Message):

    await message.answer(
        "Whitelist Request",
        reply_markup=whitelist_menu()
    )


@dp.callback_query(F.data=="whitelist")
async def wl_inline(callback: types.CallbackQuery):

    await callback.message.edit_text(
        "Whitelist Request",
        reply_markup=whitelist_menu()
    )


@dp.callback_query(F.data=="wl_start")
async def wl_start(callback: types.CallbackQuery,state:FSMContext):

    await state.set_state(Whitelist.username)

    await callback.message.answer("Send Minecraft Username")


@dp.message(Whitelist.username)
async def wl_user(message: types.Message,state:FSMContext):

    await state.update_data(username=message.text)

    await state.set_state(Whitelist.message)

    await message.answer("Write message")


@dp.message(Whitelist.message)
async def wl_finish(message: types.Message,state:FSMContext):

    data = await state.get_data()
    ticket = make_ticket()

    username=message.from_user.username

    TICKETS[ticket]={"user":message.from_user.id}

    text=f"""
Whitelist Request

Minecraft: {data['username']}

Message:
{message.text}

Telegram: @{username}
UserID: {message.from_user.id}

Ticket: {ticket}
Time: {now()}
"""

    await bot.send_message(STAFF_GROUP_ID,text,reply_markup=staff_buttons(ticket))

    await message.answer("Whitelist request sent",reply_markup=main_menu())

    await state.clear()


@dp.message(F.text=="Contact Staff")
async def contact_start(message: types.Message,state:FSMContext):

    await state.set_state(Contact.reason)

    await message.answer("Write reason")


@dp.callback_query(F.data=="contact")
async def contact_inline(callback: types.CallbackQuery,state:FSMContext):

    await state.set_state(Contact.reason)

    await callback.message.answer("Write reason")


@dp.message(Contact.reason)
async def contact_reason(message: types.Message,state:FSMContext):

    await state.update_data(reason=message.text)

    await state.set_state(Contact.message)

    await message.answer("Write message")


@dp.message(Contact.message)
async def contact_finish(message: types.Message,state:FSMContext):

    data = await state.get_data()
    ticket = make_ticket()

    username=message.from_user.username

    TICKETS[ticket]={"user":message.from_user.id}

    text=f"""
Contact Staff

Reason: {data['reason']}

Message:
{message.text}

Telegram: @{username}
UserID: {message.from_user.id}

Ticket: {ticket}
Time: {now()}
"""

    await bot.send_message(STAFF_GROUP_ID,text,reply_markup=staff_buttons(ticket))

    await message.answer("Ticket sent",reply_markup=main_menu())

    await state.clear()


@dp.message(F.text=="Shop")
async def shop(message: types.Message):

    await message.answer("Server Shop",reply_markup=shop_menu())


@dp.callback_query(F.data=="shop")
async def shop_inline(callback: types.CallbackQuery):

    await callback.message.edit_text(
        "Server Shop",
        reply_markup=shop_menu()
    )


@dp.callback_query(F.data=="rank")
async def rank(callback: types.CallbackQuery,state:FSMContext):

    await state.update_data(category="Rank")

    await state.set_state(Shop.message)

    await callback.message.edit_text(
        "Write which rank you want and your minecraft username"
    )


@dp.callback_query(F.data=="coin")
async def coin(callback: types.CallbackQuery,state:FSMContext):

    await state.update_data(category="Coin")

    await state.set_state(Shop.message)

    await callback.message.edit_text(
        "Write how many coins you want and your minecraft username"
    )


@dp.message(Shop.message)
async def shop_finish(message: types.Message,state:FSMContext):

    data=await state.get_data()

    ticket=make_ticket()

    username=message.from_user.username

    TICKETS[ticket]={"user":message.from_user.id}

    text=f"""
Shop Order

Category: {data['category']}

Message:
{message.text}

Telegram: @{username}
UserID: {message.from_user.id}

Ticket: {ticket}
Time: {now()}
"""

    await bot.send_message(STAFF_GROUP_ID,text,reply_markup=staff_buttons(ticket))

    await message.answer("Order sent",reply_markup=main_menu())

    await state.clear()


@dp.callback_query(F.data.startswith("accept"))
async def accept(callback: types.CallbackQuery):

    ticket=callback.data.split(":")[1]

    user=TICKETS[ticket]["user"]

    await bot.send_message(user,"Your request accepted")

    await callback.message.reply(f"Ticket {ticket} accepted")

    await callback.answer()


@dp.callback_query(F.data.startswith("deny"))
async def deny(callback: types.CallbackQuery):

    ticket=callback.data.split(":")[1]

    user=TICKETS[ticket]["user"]

    await bot.send_message(user,"Your request denied")

    await callback.message.reply(f"Ticket {ticket} denied")

    await callback.answer()


@dp.callback_query(F.data.startswith("reply"))
async def reply(callback: types.CallbackQuery):

    ticket=callback.data.split(":")[1]

    REPLY_MODE[callback.from_user.id]=ticket

    await callback.message.reply("Send reply message")


@dp.message(F.chat.id==STAFF_GROUP_ID)
async def staff_reply(message: types.Message):

    if message.from_user.id not in REPLY_MODE:
        return

    ticket=REPLY_MODE[message.from_user.id]

    user=TICKETS[ticket]["user"]

    await bot.copy_message(user,message.chat.id,message.message_id)

    await message.reply("Reply sent")

    del REPLY_MODE[message.from_user.id]


@dp.message(Command("broadcast","announcement"))
async def broadcast(message: types.Message):

    if message.chat.id!=STAFF_GROUP_ID:
        return

    if not message.reply_to_message:
        await message.reply("Reply to a message then run command")
        return

    msg=message.reply_to_message

    for user in USERS:

        try:

            await bot.copy_message(user,msg.chat.id,msg.message_id)

        except:
            pass

    await message.reply("Broadcast sent")


async def main():

    load_users()

    keep_alive()

    await bot.delete_webhook(drop_pending_updates=True)

    await dp.start_polling(bot)


if __name__=="__main__":
    asyncio.run(main())
