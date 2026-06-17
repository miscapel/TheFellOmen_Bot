import asyncio
import html
import logging
import os
import threading
import uuid
from datetime import datetime

from aiogram import Bot, Dispatcher, F, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
from flask import Flask


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
STAFF_GROUP_ID = os.getenv("STAFF_GROUP_ID")
PORT = int(os.getenv("PORT", "10000"))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

if not STAFF_GROUP_ID:
    raise RuntimeError("STAFF_GROUP_ID is not set")

try:
    STAFF_GROUP_ID = int(STAFF_GROUP_ID)
except ValueError:
    raise RuntimeError("STAFF_GROUP_ID must be a number")


bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)

dp = Dispatcher(storage=MemoryStorage())

app = Flask(__name__)


# حافظه موقت تیکت‌ها
# روی Render Free اگر سرویس ری‌استارت شود، این اطلاعات پاک می‌شود.
TICKETS = {}
STAFF_MESSAGE_TO_TICKET = {}


class UserState(StatesGroup):
    punishment_appeal = State()
    whitelist = State()
    contact_staff = State()
    rank_shop_message = State()
    coin_shop_message = State()


class StaffState(StatesGroup):
    replying = State()


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def safe(value) -> str:
    if value is None:
        return "-"
    return html.escape(str(value))


def user_label(user: types.User) -> str:
    username = f"@{user.username}" if user.username else user.full_name
    return f"{safe(username)} | ID: <code>{user.id}</code>"


def main_menu_keyboard() -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="Punishment Appeal",
                    callback_data="menu:punishment",
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="Whitelist",
                    callback_data="menu:whitelist",
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="Contact Staff",
                    callback_data="menu:contact",
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="Shop",
                    callback_data="menu:shop",
                )
            ],
        ]
    )


def shop_keyboard() -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="Rank Shop",
                    callback_data="shop:rank",
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="Coin Shop",
                    callback_data="shop:coin",
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="بازگشت",
                    callback_data="menu:back",
                )
            ],
        ]
    )


def staff_ticket_keyboard(ticket_id: str) -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="Accept",
                    callback_data=f"ticket:accept:{ticket_id}",
                ),
                types.InlineKeyboardButton(
                    text="Deny",
                    callback_data=f"ticket:deny:{ticket_id}",
                ),
            ],
            [
                types.InlineKeyboardButton(
                    text="Reply",
                    callback_data=f"ticket:reply:{ticket_id}",
                )
            ],
        ]
    )


def simple_staff_keyboard(ticket_id: str) -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="Accept",
                    callback_data=f"ticket:accept:{ticket_id}",
                ),
                types.InlineKeyboardButton(
                    text="Deny",
                    callback_data=f"ticket:deny:{ticket_id}",
                ),
            ],
            [
                types.InlineKeyboardButton(
                    text="Reply",
                    callback_data=f"ticket:reply:{ticket_id}",
                )
            ],
        ]
    )


async def send_ticket_to_staff(
    *,
    ticket_type: str,
    user: types.User,
    text: str,
    reply_markup: types.InlineKeyboardMarkup | None = None,
) -> str:
    ticket_id = uuid.uuid4().hex[:10]

    TICKETS[ticket_id] = {
        "id": ticket_id,
        "type": ticket_type,
        "user_id": user.id,
        "user_name": user.full_name,
        "username": user.username,
        "created_at": now_text(),
        "status": "open",
    }

    sent = await bot.send_message(
        chat_id=STAFF_GROUP_ID,
        text=text,
        reply_markup=reply_markup,
    )

    TICKETS[ticket_id]["staff_message_id"] = sent.message_id
    STAFF_MESSAGE_TO_TICKET[sent.message_id] = ticket_id

    return ticket_id


@dp.message(Command("start"))
async def start_command(message: types.Message, state: FSMContext):
    await state.clear()

    text = (
        "سلام، به ربات TheFellOmen خوش آمدید.\n\n"
        "لطفاً یکی از بخش‌های زیر را انتخاب کنید:"
    )

    await message.answer(text, reply_markup=main_menu_keyboard())


@dp.message(Command("help"))
async def help_command(message: types.Message):
    text = (
        "راهنمای ربات:\n\n"
        "از دستور /start استفاده کنید و یکی از بخش‌ها را انتخاب کنید:\n\n"
        "Punishment Appeal - درخواست آن‌بن یا آن‌میوت\n"
        "Whitelist - درخواست وایت‌لیست شدن در سرور\n"
        "Contact Staff - ارتباط با استف و ساخت تیکت پشتیبانی\n"
        "Shop - فروشگاه رنک و کوین"
    )

    await message.answer(text)


@dp.callback_query(F.data == "menu:back")
async def back_to_menu(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()

    await callback.message.edit_text(
        "لطفاً یکی از بخش‌های زیر را انتخاب کنید:",
        reply_markup=main_menu_keyboard(),
    )
    await callback.answer()


@dp.callback_query(F.data == "menu:punishment")
async def open_punishment_appeal(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(UserState.punishment_appeal)

    text = (
        "لطفاً دلیل پانیشمنت، پانیشمنت آیدی و یوزر گیم خودتون رو بنویسید.\n\n"
        "فرمت پیشنهادی:\n"
        "<code>Username: Steve\n"
        "Punishment ID: 12345\n"
        "Reason: درخواست آن‌بن\n"
        "Message: توضیحات کامل شما</code>"
    )

    await callback.message.edit_text(text)
    await callback.answer()


@dp.message(UserState.punishment_appeal)
async def receive_punishment_appeal(message: types.Message, state: FSMContext):
    raw_text = message.text or ""

    username = "-"
    punishment_id = "-"
    reason = "-"
    user_message = raw_text

    for line in raw_text.splitlines():
        lower = line.lower().strip()

        if lower.startswith("username:"):
            username = line.split(":", 1)[1].strip()
        elif lower.startswith("punishment id:"):
            punishment_id = line.split(":", 1)[1].strip()
        elif lower.startswith("punishment_id:"):
            punishment_id = line.split(":", 1)[1].strip()
        elif lower.startswith("id:"):
            punishment_id = line.split(":", 1)[1].strip()
        elif lower.startswith("reason:"):
            reason = line.split(":", 1)[1].strip()
        elif lower.startswith("message:"):
            user_message = line.split(":", 1)[1].strip()

    staff_text = (
        "Punishment Appeal\n"
        f"Username: {safe(username)}\n"
        f"Reason: {safe(reason)}\n"
        f"Message: {safe(user_message)}\n"
        f"Time: {safe(now_text())}\n"
        f"Punishment id: {safe(punishment_id)}"
    )

    ticket_id = uuid.uuid4().hex[:10]

    TICKETS[ticket_id] = {
        "id": ticket_id,
        "type": "Punishment Appeal",
        "user_id": message.from_user.id,
        "user_name": message.from_user.full_name,
        "username": message.from_user.username,
        "created_at": now_text(),
        "status": "open",
    }

    sent = await bot.send_message(
        chat_id=STAFF_GROUP_ID,
        text=staff_text,
        reply_markup=staff_ticket_keyboard(ticket_id),
    )

    TICKETS[ticket_id]["staff_message_id"] = sent.message_id
    STAFF_MESSAGE_TO_TICKET[sent.message_id] = ticket_id

    await message.answer(
        "درخواست Punishment Appeal شما برای استف ارسال شد.\n"
        "لطفاً منتظر پاسخ بمانید."
    )

    await state.clear()


@dp.callback_query(F.data == "menu:whitelist")
async def open_whitelist(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(UserState.whitelist)

    text = "لطفاً یوزری که می‌خواهید وایت‌لیست شود را در چت بنویسید."

    await callback.message.edit_text(text)
    await callback.answer()


@dp.message(UserState.whitelist)
async def receive_whitelist(message: types.Message, state: FSMContext):
    whitelist_username = message.text.strip() if message.text else "-"

    ticket_id = uuid.uuid4().hex[:10]

    staff_text = (
        "Whitelist\n"
        f"Username: {safe(whitelist_username)}\n"
        f"Time: {safe(now_text())}\n"
        f"Messages: {safe(message.text)}"
    )

    TICKETS[ticket_id] = {
        "id": ticket_id,
        "type": "Whitelist",
        "user_id": message.from_user.id,
        "user_name": message.from_user.full_name,
        "username": message.from_user.username,
        "created_at": now_text(),
        "status": "open",
    }

    sent = await bot.send_message(
        chat_id=STAFF_GROUP_ID,
        text=staff_text,
        reply_markup=simple_staff_keyboard(ticket_id),
    )

    TICKETS[ticket_id]["staff_message_id"] = sent.message_id
    STAFF_MESSAGE_TO_TICKET[sent.message_id] = ticket_id

    await message.answer(
        "درخواست وایت‌لیست شما برای استف ارسال شد.\n"
        "لطفاً منتظر بررسی بمانید."
    )

    await state.clear()


@dp.callback_query(F.data == "menu:contact")
async def open_contact_staff(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(UserState.contact_staff)

    text = (
        "لطفاً دلیل ارتباط با استف و پیام خودتون رو بنویسید.\n\n"
        "فرمت پیشنهادی:\n"
        "<code>Reason: مشکل خرید\n"
        "Message: توضیحات کامل شما</code>"
    )

    await callback.message.edit_text(text)
    await callback.answer()


@dp.message(UserState.contact_staff)
async def receive_contact_staff(message: types.Message, state: FSMContext):
    raw_text = message.text or ""

    reason = "-"
    user_message = raw_text

    for line in raw_text.splitlines():
        lower = line.lower().strip()

        if lower.startswith("reason:"):
            reason = line.split(":", 1)[1].strip()
        elif lower.startswith("message:"):
            user_message = line.split(":", 1)[1].strip()

    ticket_id = uuid.uuid4().hex[:10]

    staff_text = (
        "Contact Staff\n"
        f"Username: {user_label(message.from_user)}\n"
        f"Reason: {safe(reason)}\n"
        f"Time: {safe(now_text())}\n"
        f"Messages: {safe(user_message)}"
    )

    TICKETS[ticket_id] = {
        "id": ticket_id,
        "type": "Contact Staff",
        "user_id": message.from_user.id,
        "user_name": message.from_user.full_name,
        "username": message.from_user.username,
        "created_at": now_text(),
        "status": "open",
    }

    sent = await bot.send_message(
        chat_id=STAFF_GROUP_ID,
        text=staff_text,
        reply_markup=staff_ticket_keyboard(ticket_id),
    )

    TICKETS[ticket_id]["staff_message_id"] = sent.message_id
    STAFF_MESSAGE_TO_TICKET[sent.message_id] = ticket_id

    await message.answer(
        "تیکت پشتیبانی شما برای استف ارسال شد.\n"
        "لطفاً منتظر پاسخ بمانید."
    )

    await state.clear()


@dp.callback_query(F.data == "menu:shop")
async def open_shop(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()

    text = (
        "رنک‌ها و کوین‌ها در سرور\n\n"
        "لطفاً یکی از بخش‌های فروشگاه را انتخاب کنید:"
    )

    await callback.message.edit_text(text, reply_markup=shop_keyboard())
    await callback.answer()


@dp.callback_query(F.data == "shop:rank")
async def open_rank_shop(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(UserState.rank_shop_message)

    text = (
        "Rank Shop\n\n"
        "Vip » 49,000 Toman\n"
        "Elite » 100,000 Toman\n"
        "TheFellOmen » 190,000 Toman\n"
        "Sponsor » 250,000 Toman\n"
        "Lover » 400,000 Toman\n\n"
        "اگر فقط نیاز به کیت رنک دارید، رنک مورد نظر و کیتی که می‌خواهید را بنویسید.\n"
        "مثلاً:\n"
        "<code>کیت رنک الایت</code>"
    )

    await callback.message.edit_text(text)
    await callback.answer()


@dp.message(UserState.rank_shop_message)
async def receive_rank_shop_message(message: types.Message, state: FSMContext):
    ticket_id = uuid.uuid4().hex[:10]

    staff_text = (
        "Shop - Rank\n"
        f"Username: {user_label(message.from_user)}\n"
        f"Time: {safe(now_text())}\n"
        f"Messages: {safe(message.text)}"
    )

    TICKETS[ticket_id] = {
        "id": ticket_id,
        "type": "Shop - Rank",
        "user_id": message.from_user.id,
        "user_name": message.from_user.full_name,
        "username": message.from_user.username,
        "created_at": now_text(),
        "status": "open",
    }

    sent = await bot.send_message(
        chat_id=STAFF_GROUP_ID,
        text=staff_text,
        reply_markup=staff_ticket_keyboard(ticket_id),
    )

    TICKETS[ticket_id]["staff_message_id"] = sent.message_id
    STAFF_MESSAGE_TO_TICKET[sent.message_id] = ticket_id

    await message.answer(
        "درخواست رنک/کیت شما برای استف ارسال شد.\n"
        "لطفاً منتظر پاسخ بمانید."
    )

    await state.clear()


@dp.callback_query(F.data == "shop:coin")
async def open_coin_shop(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(UserState.coin_shop_message)

    text = (
        "Coin Shop\n\n"
        "50 Coin » 15,000 Toman\n"
        "100 Coins » 30,000 Toman\n"
        "150 Coins » 55,000 Toman\n"
        "200 Coins » 80,000 Toman\n"
        "250 Coins » 150,000 Toman\n\n"
        "اگر مقدار کوینی که می‌خواهید بیشتر از این‌هاست، مقدار مورد نظر خودتون رو تو چت بنویسید."
    )

    await callback.message.edit_text(text)
    await callback.answer()


@dp.message(UserState.coin_shop_message)
async def receive_coin_shop_message(message: types.Message, state: FSMContext):
    ticket_id = uuid.uuid4().hex[:10]

    staff_text = (
        "Shop - Coin\n"
        f"Username: {user_label(message.from_user)}\n"
        f"Time: {safe(now_text())}\n"
        f"Messages: {safe(message.text)}"
    )

    TICKETS[ticket_id] = {
        "id": ticket_id,
        "type": "Shop - Coin",
        "user_id": message.from_user.id,
        "user_name": message.from_user.full_name,
        "username": message.from_user.username,
        "created_at": now_text(),
        "status": "open",
    }

    sent = await bot.send_message(
        chat_id=STAFF_GROUP_ID,
        text=staff_text,
        reply_markup=staff_ticket_keyboard(ticket_id),
    )

    TICKETS[ticket_id]["staff_message_id"] = sent.message_id
    STAFF_MESSAGE_TO_TICKET[sent.message_id] = ticket_id

    await message.answer(
        "درخواست کوین شما برای استف ارسال شد.\n"
        "لطفاً منتظر پاسخ بمانید."
    )

    await state.clear()


@dp.callback_query(F.data.startswith("ticket:"))
async def handle_ticket_buttons(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")

    if len(parts) != 3:
        await callback.answer("داده نامعتبر است.", show_alert=True)
        return

    _, action, ticket_id = parts

    ticket = TICKETS.get(ticket_id)

    if not ticket:
        await callback.answer("این تیکت پیدا نشد یا ربات ری‌استارت شده است.", show_alert=True)
        return

    player_id = ticket["user_id"]

    if action == "accept":
        ticket["status"] = "accepted"

        await bot.send_message(
            chat_id=player_id,
            text=(
                "درخواست شما توسط استف تایید شد.\n"
                "لطفاً منتظر ادامه روند باشید."
            ),
        )

        await callback.answer("تیکت تایید شد.")
        await callback.message.reply("Accepted")

    elif action == "deny":
        ticket["status"] = "denied"

        await bot.send_message(
            chat_id=player_id,
            text=(
                "درخواست شما توسط استف رد شد.\n"
                "برای اطلاعات بیشتر می‌توانید دوباره تیکت ارسال کنید."
            ),
        )

        await callback.answer("تیکت رد شد.")
        await callback.message.reply("Denied")

    elif action == "reply":
        await state.set_state(StaffState.replying)
        await state.update_data(ticket_id=ticket_id)

        await callback.answer("پیام پاسخ را در همین گروه ارسال کنید.")
        await callback.message.reply(
            "لطفاً پاسخ خود را برای پلیر ارسال کنید.\n"
            "پیام بعدی شما برای پلیر فرستاده می‌شود."
        )

    else:
        await callback.answer("عملیات نامعتبر است.", show_alert=True)


@dp.message(StaffState.replying, F.chat.id == STAFF_GROUP_ID)
async def staff_reply_by_button(message: types.Message, state: FSMContext):
    data = await state.get_data()
    ticket_id = data.get("ticket_id")

    ticket = TICKETS.get(ticket_id)

    if not ticket:
        await message.reply("تیکت پیدا نشد یا ربات ری‌استارت شده است.")
        await state.clear()
        return

    player_id = ticket["user_id"]
    reply_text = message.text or message.caption

    if not reply_text:
        await message.reply("فقط پیام متنی قابل ارسال است.")
        return

    await bot.send_message(
        chat_id=player_id,
        text=(
            "پاسخ استف:\n\n"
            f"{safe(reply_text)}"
        ),
    )

    await message.reply("پاسخ برای پلیر ارسال شد.")
    await state.clear()


@dp.message(F.chat.id == STAFF_GROUP_ID)
async def staff_direct_reply(message: types.Message):
    if not message.reply_to_message:
        return

    ticket_id = STAFF_MESSAGE_TO_TICKET.get(message.reply_to_message.message_id)

    if not ticket_id:
        return

    ticket = TICKETS.get(ticket_id)

    if not ticket:
        await message.reply("تیکت پیدا نشد یا ربات ری‌استارت شده است.")
        return

    reply_text = message.text or message.caption

    if not reply_text:
        await message.reply("فقط پیام متنی قابل ارسال است.")
        return

    await bot.send_message(
        chat_id=ticket["user_id"],
        text=(
            "پاسخ استف:\n\n"
            f"{safe(reply_text)}"
        ),
    )

    await message.reply("پاسخ برای پلیر ارسال شد.")


@app.route("/")
def home():
    return "TheFellOmen Bot is running!"


def run_flask():
    app.run(host="0.0.0.0", port=PORT)


async def main():
    logging.info("Starting Flask server thread...")
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    logging.info("Starting bot polling...")
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
